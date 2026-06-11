# Build `pinocchio.casadi` From Source

[English](README.md) | [繁體中文](README_zh.md)

For regular Pinocchio usage, prefer installing the ROS 2 Jazzy apt package first:

```bash
sudo apt install ros-jazzy-pinocchio
```

The main purpose of this document is to clone [HowardWhile/pinocchio](https://github.com/HowardWhile/pinocchio) and build the Python module that is not currently provided by the ROS apt package: `pinocchio.casadi`.

The commands below target Ubuntu / ROS 2 Jazzy / Python 3.12. The build uses a local CasADi Python wheel directory and compiles Pinocchio's CasADi Python wrapper against it.

## Requirements

These packages do not all come from the Pinocchio repository, and a ROS 2 Jazzy install does not always guarantee every development package is present. Prepare them in two groups: Ubuntu build tools and ROS 2 Jazzy packages.

Install the Ubuntu build tools and common development packages first:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  python3-pip \
  libboost-all-dev \
  libeigen3-dev
```

Then install the ROS 2 Jazzy packages used by this build for Python and URDF support:

```bash
sudo apt install -y \
  ros-jazzy-eigenpy \
  ros-jazzy-urdfdom \
  ros-jazzy-urdfdom-headers \
  ros-jazzy-xacro
```

Source the ROS 2 Jazzy environment:

```bash
source /opt/ros/jazzy/setup.bash
```

> If you already installed a full ROS 2 Jazzy desktop / development environment, some of these ROS packages may already be present. You can confirm them with commands such as `dpkg -l | grep ros-jazzy-eigenpy`.

## Download The Source

```bash
mkdir -p ~/workspaces/git_ws
cd ~/workspaces/git_ws

git clone --recursive https://github.com/HowardWhile/pinocchio.git
cd pinocchio
git checkout feature/build-casadi
```

If the repository was cloned without submodules, initialize them with:

```bash
git submodule update --init --recursive
```

## Prepare The CasADi Python Wheel

Install the CasADi Python wheel into a local directory:

```bash
rm -rf .python-casadi
python3 -m pip install --target .python-casadi --no-deps casadi
```

The `--no-deps` flag is intentional. It prevents pip from installing a newer NumPy wheel into `.python-casadi`. Pinocchio / eigenpy should keep using the system NumPy. If `.python-casadi` contains NumPy 2.x, importing the bindings may produce ABI warnings or crash.

Check that CasADi can be imported:

```bash
PYTHONPATH="$PWD/.python-casadi:$PYTHONPATH" python3 -c "import casadi; print(casadi.__version__)"
```

## Configure With CMake

Create separate build and install directories:

```bash
cmake -S . -B build-casadi-abi0 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/install-casadi-abi0" \
  -DBUILD_PYTHON_INTERFACE=ON \
  -DBUILD_WITH_CASADI_SUPPORT=ON \
  -DBUILD_WITH_URDF_SUPPORT=ON \
  -DBUILD_WITH_COLLISION_SUPPORT=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_TESTING=OFF \
  -DPYTHON_EXECUTABLE=/usr/bin/python3 \
  -Dcasadi_DIR="$PWD/.python-casadi/casadi/cmake" \
  -Deigenpy_DIR=/opt/ros/jazzy/lib/x86_64-linux-gnu/cmake/eigenpy
```

> (option) If CMake tries to fetch `jrl-cmakemodules` but your machine has no network access, provide an existing local source directory and add this option to the CMake command:
>
> ```shell
> -DFETCHCONTENT_SOURCE_DIR_JRL-CMAKEMODULES=/path/to/jrl-cmakemodules-src
> ```

## Build

```bash
time cmake --build build-casadi-abi0 -j"$(nproc)"
```

> (option) To quickly check only the Python wrappers, build these targets:
>
> ```shell
> time cmake --build build-casadi-abi0 --target pinocchio_pywrap_default -j"$(nproc)"
> time cmake --build build-casadi-abi0 --target pinocchio_pywrap_casadi -j"$(nproc)"
> ```

## Install

```bash
cmake --install build-casadi-abi0
```

> The installed Python package will be under `install-casadi-abi0/lib/python3.12/site-packages`.

## Set The Runtime Environment

Before running Python programs, set `PYTHONPATH` and `LD_LIBRARY_PATH`:

```bash
export PINOCCHIO_WS="$PWD"

export PYTHONPATH="$PINOCCHIO_WS/install-casadi-abi0/lib/python3.12/site-packages:$PINOCCHIO_WS/.python-casadi:${PYTHONPATH:-}"

export LD_LIBRARY_PATH="$PINOCCHIO_WS/install-casadi-abi0/lib:$PINOCCHIO_WS/.python-casadi/casadi:${LD_LIBRARY_PATH:-}"
```

Run these commands from the Pinocchio repository root.

> If the ROS 2 Jazzy environment has not been loaded yet, run `source /opt/ros/jazzy/setup.bash` first so the ROS / urdfdom library paths are available in the current shell.

> (option) If you use this build often, you can add the environment setup above to `~/.bashrc`. When adding it to `~/.bashrc`, replace `PINOCCHIO_WS` with a fixed path, for example:
>
> ```shell
> export PINOCCHIO_WS="$HOME/workspaces/git_ws/pinocchio"
> ```

## Verify `pinocchio.casadi`

Run a minimal import check:

```bash
python3 -c "import casadi; from pinocchio import casadi as cpin; print(cpin.__name__)"
```

Expected output includes:

```text
pinocchio.casadi
```

## Test ABA With URDFs

Download the Go2 and G1 URDF files into `~/Downloads/test_urdf`:

```bash
mkdir -p "$HOME/Downloads/test_urdf"

curl -L \
  -o "$HOME/Downloads/test_urdf/go2_description.urdf" \
  https://raw.githubusercontent.com/unitreerobotics/unitree_ros/master/robots/go2_description/urdf/go2_description.urdf

curl -L \
  -o "$HOME/Downloads/test_urdf/g1_29dof.urdf" \
  https://raw.githubusercontent.com/unitreerobotics/unitree_ros/master/robots/g1_description/g1_29dof.urdf
```

Sources:

- [Unitree Go2 description](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/go2_description)
- [Unitree G1 description](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/g1_description)

This branch includes a small smoke test. First test Go2:

Before running it, complete [Set The Runtime Environment](#set-the-runtime-environment) so the current shell has the required `PYTHONPATH` and `LD_LIBRARY_PATH`.

```bash
python3 examples/casadi/urdf-casadi-aba.py \
  "$HOME/Downloads/test_urdf/go2_description.urdf"
```

Then test G1:

```bash
python3 examples/casadi/urdf-casadi-aba.py \
  "$HOME/Downloads/test_urdf/g1_29dof.urdf"
```

On success, Go2 prints something like:

```text
pinocchio.casadi URDF ABA test
  model: nq=12, nv=12, joints=13
  aba expression shape: (12, 1)
  casadi function inputs: 3, outputs: 1
```

On success, G1 prints something like:

```text
pinocchio.casadi URDF ABA test
  model: nq=29, nv=29, joints=30
  aba expression shape: (29, 1)
  casadi function inputs: 3, outputs: 1
```

`aba` means Articulated Body Algorithm. It computes forward dynamics. This smoke test creates symbolic `q`, `v`, and `tau`, then checks that `pinocchio.casadi` can produce a CasADi symbolic acceleration expression.

## Troubleshooting

### `casadi` Cannot Be Imported

Make sure `PYTHONPATH` contains:

```text
$PINOCCHIO_WS/.python-casadi
```

### `pinocchio.casadi` Cannot Be Imported

Make sure `PYTHONPATH` contains:

```text
$PINOCCHIO_WS/install-casadi-abi0/lib/python3.12/site-packages
```

Also check that `pinocchio_pywrap_casadi` was built and installed successfully.

### `DeprecatedBool` Converter Warning

You may see:

```text
RuntimeWarning: to-Python converter for pinocchio::python::DeprecatedBool already registered
```

This happens because the same Python process loads both the default wrapper and the CasADi wrapper, and both register the same Boost.Python converter. It does not currently block `pinocchio.casadi` ABA computations.
