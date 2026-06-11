#!/usr/bin/env python3
#
# Copyright (c) 2026
#

import argparse

import casadi as ca
from pinocchio import casadi as cpin


def main():
    parser = argparse.ArgumentParser(
        description="Load a URDF or xacro with pinocchio.casadi and build a symbolic ABA expression."
    )
    parser.add_argument("urdf", help="Path to a URDF or xacro file")
    args = parser.parse_args()

    model = cpin.buildModelFromUrdf(args.urdf)
    data = model.createData()

    q = ca.SX.sym("q", model.nq)
    v = ca.SX.sym("v", model.nv)
    tau = ca.SX.sym("tau", model.nv)

    acceleration = cpin.aba(model, data, q, v, tau)
    aba_function = ca.Function("aba", [q, v, tau], [acceleration])

    print("pinocchio.casadi URDF ABA test")
    print(f"  model: nq={model.nq}, nv={model.nv}, joints={len(model.joints)}")
    print(f"  aba expression shape: {acceleration.shape}")
    print(f"  casadi function inputs: {aba_function.n_in()}, outputs: {aba_function.n_out()}")


if __name__ == "__main__":
    main()
