# Build `pinocchio.casadi` from Source

[English](README.md) | [繁體中文](README_zh.md)

For general Pinocchio use, we recommend installing the ROS 2 Jazzy apt package:

```bash
sudo apt install ros-jazzy-pinocchio
```

The main purpose of this document is to clone [HowardWhile/pinocchio](https://github.com/HowardWhile/pinocchio) and build the Python module that is not currently provided by the ROS apt package: `pinocchio.casadi`.

The commands below target Ubuntu / ROS 2 Jazzy / Python 3.12. They build CasADi from source with ABI 1, then build the Pinocchio default and CasADi Python wrappers with the same ABI.

## Requirements

These packages do not all come from the Pinocchio repository, and installing ROS 2 Jazzy alone does not guarantee that every development package is present. Prepare them in two groups: Ubuntu build tools and ROS 2 Jazzy packages.

Install the Ubuntu build tools and common development packages first:

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  dpkg-dev \
  git \
  gfortran \
  swig \
  python3-pip \
  python3-dev \
  python3-numpy \
  libboost-all-dev \
  libeigen3-dev \
  liblapack-dev \
  pkg-config \
  coinor-libipopt-dev
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

## Download the Source

```bash
mkdir -p ~/workspaces/git_ws
cd ~/workspaces/git_ws

git clone --recursive https://github.com/HowardWhile/pinocchio.git
cd pinocchio
```

If the repository was cloned without submodules, initialize them with:

```bash
git submodule update --init --recursive
```

## Build CasADi with ABI 1

For consistent results on amd64 and arm64, do not use a pip CasADi wheel in this
workflow. The tested x86_64 CasADi 3.7.2 wheel uses
`_GLIBCXX_USE_CXX11_ABI=0`, and wheel ABI settings may differ by architecture.
ROS 2 Jazzy Pinocchio, eigenpy, and standard GCC builds default to ABI 1. If the
default and CasADi wrappers use different ABIs, passing a `pinocchio.Model` to
`pinocchio.casadi.Model` may cause a segmentation fault.

This branch pins CasADi 3.7.2 as the `external/casadi` submodule. After running
`git submodule update --init --recursive`, build and install an independent
ABI 1 version from that directory:

```bash
cd ~/workspaces/git_ws/pinocchio

export PINOCCHIO_WS="$PWD"
export CASADI_SOURCE="$PINOCCHIO_WS/external/casadi"
export CASADI_BUILD="$PINOCCHIO_WS/build-casadi-dependency-abi1"
export CASADI_PREFIX="$PINOCCHIO_WS/install-casadi-dependency-abi1"

cmake -S "$CASADI_SOURCE" -B "$CASADI_BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$CASADI_PREFIX" \
  -DPYTHON_PREFIX="$CASADI_PREFIX/python" \
  -DWITH_PYTHON=ON \
  -DWITH_PYTHON3=ON \
  -DWITH_IPOPT=ON \
  -DCMAKE_CXX_FLAGS="-D_GLIBCXX_USE_CXX11_ABI=1"

cmake --build "$CASADI_BUILD" -j"$(nproc)"
cmake --install "$CASADI_BUILD"
```

Check that the Python module and Ipopt work:

```bash
env \
  PYTHONPATH="$CASADI_PREFIX/python" \
  LD_LIBRARY_PATH="$CASADI_PREFIX/lib" \
  python3 -c "import casadi as ca; x=ca.MX.sym('x'); s=ca.nlpsol('s','ipopt',{'x':x,'f':(x-2)**2}); print(float(s(x0=0)['x']))"
```

## Configure with CMake

Return to the Pinocchio repository and create separate ABI 1 build and install directories:

```bash
cd ~/workspaces/git_ws/pinocchio
export CASADI_PREFIX="$PWD/install-casadi-dependency-abi1"

EIGENPY_MULTIARCH="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"
case "$EIGENPY_MULTIARCH" in
  x86_64-linux-gnu|aarch64-linux-gnu) ;;
  *) echo "Unsupported architecture: $EIGENPY_MULTIARCH"; exit 1 ;;
esac

cmake -S . -B build-casadi-abi1 \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PWD/install-casadi-abi1" \
  -DCMAKE_CXX_FLAGS="-D_GLIBCXX_USE_CXX11_ABI=1" \
  -DBUILD_PYTHON_INTERFACE=ON \
  -DBUILD_WITH_CASADI_SUPPORT=ON \
  -DBUILD_WITH_URDF_SUPPORT=ON \
  -DBUILD_WITH_COLLISION_SUPPORT=OFF \
  -DBUILD_EXAMPLES=OFF \
  -DBUILD_TESTING=OFF \
  -DPYTHON_EXECUTABLE=/usr/bin/python3 \
  -Dcasadi_DIR="$CASADI_PREFIX/lib/cmake/casadi" \
  -Deigenpy_DIR="/opt/ros/jazzy/lib/${EIGENPY_MULTIARCH}/cmake/eigenpy"
```

> (option) If CMake tries to fetch `jrl-cmakemodules` but your machine has no network access, provide an existing local source directory and add this option to the CMake command:
>
> ```shell
> -DFETCHCONTENT_SOURCE_DIR_JRL-CMAKEMODULES=/path/to/jrl-cmakemodules-src
> ```

## Build

```bash
time cmake --build build-casadi-abi1 -j"$(nproc)"
```

> (option) To quickly check only the Python wrappers, build these targets:
>
> ```shell
> time cmake --build build-casadi-abi1 --target pinocchio_pywrap_default -j"$(nproc)"
> time cmake --build build-casadi-abi1 --target pinocchio_pywrap_casadi -j"$(nproc)"
> ```

## Install

```bash
cmake --install build-casadi-abi1
```

> The installed Python package will be under `install-casadi-abi1/lib/python3.12/site-packages`.

## Set the Runtime Environment

Before running Python programs, set `PYTHONPATH` and `LD_LIBRARY_PATH`:

```bash
export PINOCCHIO_WS="$PWD"
export CASADI_PREFIX="$PINOCCHIO_WS/install-casadi-dependency-abi1"
export PYTHONPATH="$PINOCCHIO_WS/install-casadi-abi1/lib/python3.12/site-packages:$CASADI_PREFIX/python:${PYTHONPATH:-}"
export LD_LIBRARY_PATH="$PINOCCHIO_WS/install-casadi-abi1/lib:$CASADI_PREFIX/lib:${LD_LIBRARY_PATH:-}"
```

Run these commands from the Pinocchio repository root.

> If the ROS 2 Jazzy environment has not been loaded yet, run `source /opt/ros/jazzy/setup.bash` first so the ROS / urdfdom library paths are available in the current shell.

> (option) If you use this build often, you can add the environment setup above to `~/.bashrc`. When adding it to `~/.bashrc`, replace `PINOCCHIO_WS` with a fixed path, for example:
>
> ```shell
> export PINOCCHIO_WS="$HOME/workspaces/git_ws/pinocchio"
> ```

## Verify `pinocchio.casadi`

First confirm that both CMake builds were configured for ABI 1:

```bash
grep '^CMAKE_CXX_FLAGS:' "$PINOCCHIO_WS/build-casadi-dependency-abi1/CMakeCache.txt"
grep '^CMAKE_CXX_FLAGS:' "$PINOCCHIO_WS/build-casadi-abi1/CMakeCache.txt"
```

Both lines must contain:

```text
-D_GLIBCXX_USE_CXX11_ABI=1
```

Run a minimal import check:

```bash
python3 -c "import casadi; from pinocchio import casadi as cpin; print(cpin.__name__)"
```

Expected output includes:

```text
pinocchio.casadi
```

An import check or a CasADi-only ABA test is not enough to detect an ABI mismatch
between the default and CasADi wrappers. Also test cross-wrapper model conversion:

```bash
python3 -c "import pinocchio as pin; from pinocchio import casadi as cpin; cpin.Model(pin.buildSampleModelManipulator()); print('ABI1 cross-wrapper OK')"
```

Expected output:

```text
ABI1 cross-wrapper OK
```

The expected result is the same on both supported architectures:

| Component | amd64 | arm64 |
| --- | --- | --- |
| CasADi C++ library and Python module | ABI 1 | ABI 1 |
| Pinocchio default library and Python wrapper | ABI 1 | ABI 1 |
| Pinocchio CasADi library and Python wrapper | ABI 1 | ABI 1 |

The only architecture-specific value is `EIGENPY_MULTIARCH`, which resolves to
`x86_64-linux-gnu` on amd64 and `aarch64-linux-gnu` on arm64.

## Test ABA with URDFs

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

ABA stands for Articulated Body Algorithm. It computes forward dynamics. This smoke test creates symbolic `q`, `v`, and `tau`, then checks that `pinocchio.casadi` can produce a CasADi symbolic acceleration expression.

## Troubleshooting

### `casadi` Cannot Be Imported

Make sure `PYTHONPATH` contains:

```text
$CASADI_PREFIX/python
```

### `pinocchio.casadi` Cannot Be Imported

Make sure `PYTHONPATH` contains:

```text
$PINOCCHIO_WS/install-casadi-abi1/lib/python3.12/site-packages
```

Also check that `pinocchio_pywrap_casadi` was built and installed successfully.

### `DeprecatedBool` Converter Warning

You may see:

```text
RuntimeWarning: to-Python converter for pinocchio::python::DeprecatedBool already registered
```

This happens because the same Python process loads both the default wrapper and the CasADi wrapper, and both register the same Boost.Python converter. This warning does not currently affect `pinocchio.casadi` ABA computations.

### Check That the Old ABI 0 Install Is Not Loaded

If you previously used `install-casadi-abi0` or `.python-casadi`, remove those
paths from `~/.bashrc`, `PYTHONPATH`, and `LD_LIBRARY_PATH`, then open a new shell.

```bash
python3 -c "import casadi, pinocchio; print(casadi.__file__); print(pinocchio.__file__)"
```

The paths should point to `install-casadi-dependency-abi1` and
`install-casadi-abi1`, respectively.
