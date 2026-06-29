# 從原始碼編譯 `pinocchio.casadi`

[English](README.md) | [繁體中文](README_zh.md)

一般使用 Pinocchio 時，建議優先透過 ROS 2 Jazzy 的 apt package 安裝：

```bash
sudo apt install ros-jazzy-pinocchio
```

這份文件的主要目的，是從 [HowardWhile/pinocchio](https://github.com/HowardWhile/pinocchio) 下載原始碼，編譯出 ROS apt 版目前沒有提供的 Python module：`pinocchio.casadi`。

以下流程以 Ubuntu / ROS 2 Jazzy / Python 3.12 為例。重點是從原始碼建立 ABI 1 CasADi，並讓 Pinocchio default 與 CasADi Python wrappers 使用相同 ABI。

## 需求

這些套件不全是 Pinocchio repo 內建，也不保證只安裝 ROS 2 Jazzy 就全部具備。建議分成 Ubuntu build tools 與 ROS 2 Jazzy packages 兩部分準備。

先安裝 Ubuntu 端的編譯工具與常用 development packages：

```bash
sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
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

再準備 ROS 2 Jazzy 端提供給 Pinocchio 找到的 Python / URDF 相關 packages：

```bash
sudo apt install -y \
  ros-jazzy-eigenpy \
  ros-jazzy-urdfdom \
  ros-jazzy-urdfdom-headers \
  ros-jazzy-xacro
```

載入 ROS 2 Jazzy 環境：

```bash
source /opt/ros/jazzy/setup.bash
```

> 如果已經安裝完整的 ROS 2 Jazzy desktop / development 環境，上面部分 ROS packages 可能已經存在；可以用 `dpkg -l | grep ros-jazzy-eigenpy` 之類的方式確認。

## 下載原始碼

```bash
mkdir -p ~/workspaces/git_ws
cd ~/workspaces/git_ws

git clone --recursive https://github.com/HowardWhile/pinocchio.git
cd pinocchio
```

若已經 clone 過，但 submodule 尚未初始化：

```bash
git submodule update --init --recursive
```

## 編譯 ABI 1 CasADi

不要直接使用 x86_64 的 pip CasADi wheel。該 wheel 使用
`_GLIBCXX_USE_CXX11_ABI=0`，但 ROS 2 Jazzy 的 Pinocchio、eigenpy 與一般 GCC
build 預設使用 ABI 1。若 default 與 CasADi wrapper 使用不同 ABI，將
`pinocchio.Model` 傳給 `pinocchio.casadi.Model` 時可能直接 segmentation fault。

此分支已將 CasADi 3.7.2 固定為 `external/casadi` submodule。完成上一節的
`git submodule update --init --recursive` 後，直接從該目錄建立 ABI 1 安裝：

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

確認 Python module 與 Ipopt 可以使用：

```bash
env \
  PYTHONPATH="$CASADI_PREFIX/python" \
  LD_LIBRARY_PATH="$CASADI_PREFIX/lib" \
  python3 -c "import casadi as ca; x=ca.MX.sym('x'); s=ca.nlpsol('s','ipopt',{'x':x,'f':(x-2)**2}); print(float(s(x0=0)['x']))"
```

## 設定 CMake

回到 Pinocchio repo，建立獨立的 ABI 1 build 與 install 目錄：

```bash
cd ~/workspaces/git_ws/pinocchio
export CASADI_PREFIX="$PWD/install-casadi-dependency-abi1"

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
  -Deigenpy_DIR=/opt/ros/jazzy/lib/x86_64-linux-gnu/cmake/eigenpy
```

> (option) 如果 CMake 嘗試下載 `jrl-cmakemodules`，但目前環境沒有網路，可以先提供一份已存在的 `jrl-cmakemodules` source，並在 CMake 指令中加上：
>
> ```shell
> -DFETCHCONTENT_SOURCE_DIR_JRL-CMAKEMODULES=/path/to/jrl-cmakemodules-src
> ```



## 編譯

```bash
time cmake --build build-casadi-abi1 -j"$(nproc)"
```

> (option) 如果只想先確認 Python wrapper 能否編譯，可使用：
>
> ```shell
> time cmake --build build-casadi-abi1 --target pinocchio_pywrap_default -j"$(nproc)"
> time cmake --build build-casadi-abi1 --target pinocchio_pywrap_casadi -j"$(nproc)"
> ```

## 安裝

```bash
cmake --install build-casadi-abi1
```

> 安裝後，Python package 會位於 `install-casadi-abi1/lib/python3.12/site-packages`
>

## 設定執行環境

執行 Python 程式前，請設定 `PYTHONPATH` 與 `LD_LIBRARY_PATH`：

```bash
export PINOCCHIO_WS="$HOME/workspaces/git_ws/pinocchio"
export CASADI_PREFIX="$PINOCCHIO_WS/install-casadi-dependency-abi1"

export PYTHONPATH="$PINOCCHIO_WS/install-casadi-abi1/lib/python3.12/site-packages:$CASADI_PREFIX/python:${PYTHONPATH:-}"

export LD_LIBRARY_PATH="$PINOCCHIO_WS/install-casadi-abi1/lib:$CASADI_PREFIX/lib:${LD_LIBRARY_PATH:-}"
```

請在 Pinocchio repo 根目錄執行以上指令。

> 如果尚未載入 ROS 2 Jazzy 環境，請先執行 `source /opt/ros/jazzy/setup.bash`，讓 ROS / urdfdom 相關 library path 進入目前 shell。

> (option) 如果會經常使用這個 build，可以將以上環境設定加入 `~/.bashrc`。加入 `~/.bashrc` 時，請將 `PINOCCHIO_WS` 改成固定路徑，例如：
>
> ```shell
> export PINOCCHIO_WS="$HOME/workspaces/git_ws/pinocchio"
> ```

## 驗證 `pinocchio.casadi`

先測試 import：

```bash
python3 -c "import casadi; from pinocchio import casadi as cpin; print(cpin.__name__)"
```

預期輸出包含：

```text
pinocchio.casadi
```

只測 import 或 CasADi 端的 ABA 不足以發現 default/CasADi wrapper ABI 不一致。
必須另外測試跨 wrapper model conversion：

```bash
python3 -c "import pinocchio as pin; from pinocchio import casadi as cpin; cpin.Model(pin.buildSampleModelManipulator()); print('ABI1 cross-wrapper OK')"
```

成功時應顯示：

```text
ABI1 cross-wrapper OK
```

## 使用 URDF 測試 ABA

下載 Go2 與 G1 的 URDF 到 `~/Downloads/test_urdf`：

```bash
mkdir -p "$HOME/Downloads/test_urdf"

curl -L \
  -o "$HOME/Downloads/test_urdf/go2_description.urdf" \
  https://raw.githubusercontent.com/unitreerobotics/unitree_ros/master/robots/go2_description/urdf/go2_description.urdf

curl -L \
  -o "$HOME/Downloads/test_urdf/g1_29dof.urdf" \
  https://raw.githubusercontent.com/unitreerobotics/unitree_ros/master/robots/g1_description/g1_29dof.urdf
```

來源：

- [Unitree Go2 description](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/go2_description)
- [Unitree G1 description](https://github.com/unitreerobotics/unitree_ros/tree/master/robots/g1_description)

此分支提供一個簡單測試程式。先測 Go2：

執行前，請先完成上一節的[設定執行環境](#設定執行環境)，確保目前 shell 已經包含 `PYTHONPATH` 與 `LD_LIBRARY_PATH`。

```bash
python3 examples/casadi/urdf-casadi-aba.py \
  "$HOME/Downloads/test_urdf/go2_description.urdf"
```

再測 G1：

```bash
python3 examples/casadi/urdf-casadi-aba.py \
  "$HOME/Downloads/test_urdf/g1_29dof.urdf"
```

Go2 成功時會看到類似：

```text
pinocchio.casadi URDF ABA test
  model: nq=12, nv=12, joints=13
  aba expression shape: (12, 1)
  casadi function inputs: 3, outputs: 1
```

G1 成功時會看到類似：

```text
pinocchio.casadi URDF ABA test
  model: nq=29, nv=29, joints=30
  aba expression shape: (29, 1)
  casadi function inputs: 3, outputs: 1
```

`aba` 是 Articulated Body Algorithm，用於前向動力學。這個測試會建立 symbolic `q`、`v`、`tau`，並確認 `pinocchio.casadi` 可以產生 CasADi symbolic acceleration expression。

## 常見問題

### 找不到 `casadi`

請確認 `PYTHONPATH` 包含：

```text
$CASADI_PREFIX/python
```

### 找不到 `pinocchio.casadi`

請確認 `PYTHONPATH` 包含：

```text
$PINOCCHIO_WS/install-casadi-abi1/lib/python3.12/site-packages
```

並確認已經成功編譯與安裝 `pinocchio_pywrap_casadi`。

### 出現 `DeprecatedBool` converter warning

可能看到：

```text
RuntimeWarning: to-Python converter for pinocchio::python::DeprecatedBool already registered
```

這是因為同一個 Python process 同時載入 default wrapper 與 casadi wrapper，兩者都註冊了相同的 Boost.Python converter。此警告目前不影響 `pinocchio.casadi` 的 ABA 運算。

### 確認沒有載入舊 ABI 0 安裝

若曾按照舊版流程使用 `install-casadi-abi0` 或 `.python-casadi`，請從
`~/.bashrc`、`PYTHONPATH` 與 `LD_LIBRARY_PATH` 移除，並開啟新的 shell。

```bash
python3 -c "import casadi, pinocchio; print(casadi.__file__); print(pinocchio.__file__)"
```

輸出路徑應分別位於 `install-casadi-dependency-abi1` 與
`install-casadi-abi1`。
