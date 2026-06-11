# 從原始碼編譯 `pinocchio.casadi`

這份文件描述如何從 [HowardWhile/pinocchio](https://github.com/HowardWhile/pinocchio) 下載原始碼，並編譯出可在 Python 中使用的 `pinocchio.casadi`。

以下流程以 Ubuntu / ROS 2 Jazzy / Python 3.12 為例。重點是使用本機安裝的 CasADi wheel，並讓 Pinocchio 的 CasADi Python wrapper 以相容的 ABI 編譯。

## 需求

請先準備以下工具與套件：

- CMake
- C++17 compiler
- Python 3 與 pip
- Boost / Boost.Python
- Eigen3
- eigenpy
- urdfdom
- ROS 2 Jazzy 環境，若需要使用 xacro 或 ROS 版本的 urdfdom

在 Ubuntu / ROS Jazzy 環境中，可先載入 ROS 環境：

```bash
source /opt/ros/jazzy/setup.bash
```

## 下載原始碼

```bash
mkdir -p ~/workspaces/git_ws
cd ~/workspaces/git_ws

git clone --recursive https://github.com/HowardWhile/pinocchio.git
cd pinocchio
git checkout feature/build-casadi
```

若已經 clone 過，但 submodule 尚未初始化：

```bash
git submodule update --init --recursive
```

## 準備 CasADi Python wheel

建立一個本地資料夾放 CasADi wheel 內容：

```bash
python3 -m pip install --target .python-casadi --no-deps casadi
```

這裡刻意使用 `--no-deps`，避免 pip 把新的 NumPy wheel 安裝到 `.python-casadi`。Pinocchio / eigenpy 會使用系統的 NumPy，若 `.python-casadi` 中有 NumPy 2.x，可能在 import 時造成 ABI 警告或 crash。

確認 CasADi 可被載入：

```bash
PYTHONPATH="$PWD/.python-casadi:$PYTHONPATH" python3 -c "import casadi; print(casadi.__version__)"
```

## 設定 CMake

建立獨立的 build 與 install 目錄：

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

> (option) 如果 CMake 嘗試下載 `jrl-cmakemodules`，但目前環境沒有網路，可以先提供一份已存在的 `jrl-cmakemodules` source，並在 CMake 指令中加上：
>
> ```shell
> -DFETCHCONTENT_SOURCE_DIR_JRL-CMAKEMODULES=/path/to/jrl-cmakemodules-src
> ```



## 編譯

```bash
time cmake --build build-casadi-abi0 -j"$(nproc)"
```

> (option) 如果只想先確認 Python wrapper 能否編譯，可使用：
>
> ```shell
> time cmake --build build-casadi-abi0 --target pinocchio_pywrap_default -j"$(nproc)"
> time cmake --build build-casadi-abi0 --target pinocchio_pywrap_casadi -j"$(nproc)"
> ```

## 安裝

```bash
cmake --install build-casadi-abi0
```

> 安裝後，Python package 會位於 `install-casadi-abi0/lib/python3.12/site-packages`
>

## 設定執行環境

執行 Python 程式前，請設定 `PYTHONPATH` 與 `LD_LIBRARY_PATH`：

```bash
export PINOCCHIO_WS="$PWD"

export PYTHONPATH="$PINOCCHIO_WS/install-casadi-abi0/lib/python3.12/site-packages:$PINOCCHIO_WS/.python-casadi:${PYTHONPATH:-}"

export LD_LIBRARY_PATH="$PINOCCHIO_WS/install-casadi-abi0/lib:$PINOCCHIO_WS/.python-casadi/casadi:${LD_LIBRARY_PATH:-}"
```

請在 Pinocchio repo 根目錄執行以上指令。

> 如果尚未載入 ROS 2 Jazzy 環境，請先執行 `source /opt/ros/jazzy/setup.bash`，讓 ROS / urdfdom 相關 library path 進入目前 shell。

## 驗證 `pinocchio.casadi`

先測試 import：

```bash
python3 -c "import casadi; from pinocchio import casadi as cpin; print(cpin.__name__)"
```

預期輸出包含：

```text
pinocchio.casadi
```

## 使用 Unitree URDF 測試 ABA

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
$PINOCCHIO_WS/.python-casadi
```

### 找不到 `pinocchio.casadi`

請確認 `PYTHONPATH` 包含：

```text
$PINOCCHIO_WS/install-casadi-abi0/lib/python3.12/site-packages
```

並確認已經成功編譯與安裝 `pinocchio_pywrap_casadi`。

### 出現 `DeprecatedBool` converter warning

可能看到：

```text
RuntimeWarning: to-Python converter for pinocchio::python::DeprecatedBool already registered
```

這是因為同一個 Python process 同時載入 default wrapper 與 casadi wrapper，兩者都註冊了相同的 Boost.Python converter。此警告目前不影響 `pinocchio.casadi` 的 ABA 運算。
