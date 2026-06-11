#
# Copyright (c) 2020 INRIA
#
# ruff: noqa: F401, F403, F405

# Manually register submodules
import math
import os
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import casadi as _casadi

from .. import utils
from ..explog import exp, log
from ..pinocchio_pywrap_casadi import *
from ..pinocchio_pywrap_casadi import __raw_version__, __version__

sys.modules["pinocchio.casadi.rpy"] = rpy
sys.modules["pinocchio.casadi.cholesky"] = cholesky

if WITH_COLLISION:
    import coal
    from coal import (
        CachedMeshLoader,
        CollisionGeometry,
        CollisionResult,
        Contact,
        DistanceResult,
        MeshLoader,
        StdVec_CollisionResult,
        StdVec_Contact,
        StdVec_DistanceResult,
    )

    # Pickling support becauso Vec3s is registered by
    # coal and pinocchio (see pinocchio/binding/python/multibody/data.hpp)
    coal.StdVec_Vec3s.__safe_for_unpickling__ = True
    coal.StdVec_Vec3s.__getstate_manages_dict__ = True

    # Deprecated, should be removed in next major release
    hppfcl = coal


def _parse_vector(text, default):
    if text is None:
        return np.array(default, dtype=float)
    return np.fromstring(text, sep=" ", dtype=float)


def _origin_to_matrix(origin):
    if origin is None:
        xyz = np.zeros(3)
        rpy = np.zeros(3)
    else:
        xyz = _parse_vector(origin.get("xyz"), [0.0, 0.0, 0.0])
        rpy = _parse_vector(origin.get("rpy"), [0.0, 0.0, 0.0])

    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rx = np.array([[1.0, 0.0, 0.0], [0.0, cr, -sr], [0.0, sr, cr]])
    ry = np.array([[cp, 0.0, sp], [0.0, 1.0, 0.0], [-sp, 0.0, cp]])
    rz = np.array([[cy, -sy, 0.0], [sy, cy, 0.0], [0.0, 0.0, 1.0]])

    transform = np.eye(4)
    transform[:3, :3] = rz @ ry @ rx
    transform[:3, 3] = xyz
    return transform


def _se3(transform):
    return SE3(_casadi.SX(transform[:3, :3]), _casadi.SX(transform[:3, 3]))


def _link_inertia(link):
    inertial = link.find("inertial")
    if inertial is None:
        return None, None

    mass_node = inertial.find("mass")
    inertia_node = inertial.find("inertia")
    if mass_node is None or inertia_node is None:
        return None, None

    mass = float(mass_node.get("value", "0"))
    ixx = float(inertia_node.get("ixx", "0"))
    ixy = float(inertia_node.get("ixy", "0"))
    ixz = float(inertia_node.get("ixz", "0"))
    iyy = float(inertia_node.get("iyy", "0"))
    iyz = float(inertia_node.get("iyz", "0"))
    izz = float(inertia_node.get("izz", "0"))
    inertia = np.array([[ixx, ixy, ixz], [ixy, iyy, iyz], [ixz, iyz, izz]], dtype=float)

    placement = _origin_to_matrix(inertial.find("origin"))
    rotation = placement[:3, :3]
    lever = placement[:3, 3]
    return (
        Inertia(
            _casadi.SX(mass),
            _casadi.SX(lever),
            _casadi.SX(rotation @ inertia @ rotation.T),
        ),
        placement,
    )


def _axis_joint(joint_type, axis):
    if joint_type == "revolute":
        return JointModelRevoluteUnaligned(axis[0], axis[1], axis[2])
    if joint_type == "prismatic":
        return JointModelPrismaticUnaligned(axis[0], axis[1], axis[2])
    if joint_type == "continuous":
        if np.allclose(axis, [1.0, 0.0, 0.0]):
            return JointModelRUBX()
        if np.allclose(axis, [0.0, 1.0, 0.0]):
            return JointModelRUBY()
        if np.allclose(axis, [0.0, 0.0, 1.0]):
            return JointModelRUBZ()
        raise NotImplementedError("continuous joints are only supported on X, Y or Z axes")
    raise NotImplementedError(f"unsupported URDF joint type: {joint_type}")


def _load_urdf_xml(filename):
    path = pathlib.Path(filename)
    if path.suffix == ".xacro":
        env = os.environ.copy()
        ros_python_path = "/opt/ros/jazzy/lib/python3.12/site-packages"
        python_path = env.get("PYTHONPATH", "")
        if ros_python_path not in python_path.split(os.pathsep):
            env["PYTHONPATH"] = os.pathsep.join(
                item for item in [python_path, ros_python_path] if item
            )
        result = subprocess.run(
            ["xacro", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
            env=env,
        )
        return result.stdout
    return path.read_text()


def buildModelFromXML(xml_stream, mimic=False):
    if mimic:
        raise NotImplementedError("mimic joints are not supported by the pure Python CasADi URDF loader")

    root = ET.fromstring(xml_stream)
    model = Model()

    links = {link.get("name"): link for link in root.findall("link")}
    children = {}
    child_links = set()
    for joint in root.findall("joint"):
        parent = joint.find("parent").get("link")
        child = joint.find("child").get("link")
        children.setdefault(parent, []).append(joint)
        child_links.add(child)

    root_links = [name for name in links if name not in child_links]
    if len(root_links) != 1:
        raise ValueError(f"expected one URDF root link, found {len(root_links)}")

    identity = np.eye(4)

    def append_link_inertia(link_name, parent_joint_id, placement):
        inertia, inertial_placement = _link_inertia(links[link_name])
        if inertia is not None:
            model.appendBodyToJoint(parent_joint_id, inertia, _se3(placement @ inertial_placement))

    def visit(link_name, parent_joint_id, link_placement):
        append_link_inertia(link_name, parent_joint_id, link_placement)

        for joint in children.get(link_name, []):
            joint_type = joint.get("type")
            child_link = joint.find("child").get("link")
            joint_placement = link_placement @ _origin_to_matrix(joint.find("origin"))

            if joint_type == "fixed":
                visit(child_link, parent_joint_id, joint_placement)
                continue

            axis = _parse_vector(
                joint.find("axis").get("xyz") if joint.find("axis") is not None else None,
                [1.0, 0.0, 0.0],
            )
            joint_id = model.addJoint(
                parent_joint_id,
                _axis_joint(joint_type, axis),
                _se3(joint_placement),
                joint.get("name"),
            )
            visit(child_link, joint_id, identity)

    visit(root_links[0], 0, identity)
    return model


def buildModelFromUrdf(filename, mimic=False):
    return buildModelFromXML(_load_urdf_xml(filename), mimic=mimic)
