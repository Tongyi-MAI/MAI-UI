# MAI-UI

> MAI-UI 技术报告：面向真实世界的基础 GUI 智能体

<p align="center">
  <a href="https://arxiv.org/abs/2512.22047"><img src="https://img.shields.io/badge/📄%20arXiv-论文-red" alt="arXiv" /></a>
  <a href="https://tongyi-mai.github.io/MAI-UI//"><img src="https://img.shields.io/badge/🌐%20Website-项目主页-blue" alt="Website" /></a>
  <a href="https://huggingface.co/Tongyi-MAI"><img src="https://img.shields.io/badge/🤗%20Hugging%20Face-模型-orange" alt="Hugging Face Model" /></a>
</p>

![Overview PDF](./assets/img/overview.png)

## ✨ 项目亮点

本仓库提供 **MAI-UI** 的官方实现，一个面向 Android 自动化的基础 GUI 智能体。主要特性包括：

- 🖥️ **Gradio Web UI** - 交互式控制面板，支持实时轨迹可视化和设备管理
- 📱 **ADB 集成** - USB 和无线调试支持，集成 scrcpy 屏幕镜像
- 🤖 **多模型支持** - 预配置 vLLM、通义千问、OpenAI 等多种模型提供商
- 🔧 **MCP 工具** - 外部工具集成（如高德地图导航）
- 📦 **应用映射** - 中文应用名到包名映射，支持直接启动应用
- ⚡ **一键启动** - 自动依赖检查和环境验证

## 📰 最新动态

* 🎁 **[2025-12-30]** 添加 Gradio Web UI，支持可视化操作和轨迹回放！
* 🎁 **[2025-12-29]** 发布 MAI-UI 技术报告 [arXiv](https://arxiv.org/abs/2512.22047)！
* 🎁 **[2025-12-29]** 在 Hugging Face 首次发布 [MAI-UI-8B](https://huggingface.co/Tongyi-MAI/MAI-UI-8B) 和 [MAI-UI-2B](https://huggingface.co/Tongyi-MAI/MAI-UI-2B) 模型。

## 📑 目录

- [📖 背景介绍](#-背景介绍)
- [🏆 性能表现](#-性能表现)
- [🎥 演示](#-演示)
- [🚀 快速开始](#-快速开始)
- [🖥️ Web UI](#️-web-ui)
- [📝 引用](#-引用)
- [📧 联系我们](#-联系我们)
- [📄 许可证](#-许可证)

## 📖 背景介绍

GUI 智能体的发展将革新下一代人机交互方式。基于这一愿景，我们推出 MAI-UI——一系列覆盖全尺寸谱系的基础 GUI 智能体，包括 2B、8B、32B 和 235B-A22B 等变体。

我们识别出实际部署的四大关键挑战：
1. 缺乏原生的智能体-用户交互
2. 纯 UI 操作的局限性
3. 缺乏实用的部署架构
4. 在动态环境中的脆弱性

MAI-UI 通过统一方法论解决这些问题：
- **自演进数据管道**：扩展导航数据以包含用户交互和 MCP 工具调用
- **原生端云协同系统**：根据任务状态动态路由执行
- **在线强化学习框架**：高级优化以扩展并行环境和上下文长度

## 🏆 性能表现

MAI-UI 在 GUI 定位和移动端导航方面建立了新的 SOTA。

### GUI 定位基准测试

| 基准测试 | MAI-UI 得分 |
|---------|-------------|
| ScreenSpot-Pro | **73.5%** |
| MMBench GUI L2 | **91.3%** |
| OSWorld-G | **70.9%** |
| UI-Vision | **49.2%** |

在 ScreenSpot-Pro 上超越 Gemini-3-Pro 和 Seed1.8。

<table align="center">
  <tr>
    <td align="center"><img src="./assets/img/sspro.jpg" alt="ScreenSpot-Pro Results"/><br/><b>ScreenSpot-Pro</b></td>
    <td align="center"><img src="./assets/img/uivision.jpg" alt="UI-Vision Results"/><br/><b>UI-Vision</b></td>
  </tr>
  <tr>
    <td align="center"><img src="./assets/img/mmbench.jpg" alt="MMBench GUI L2 Results"/><br/><b>MMBench GUI L2</b></td>
    <td align="center"><img src="./assets/img/osworld-g.jpg" alt="OSWorld-G Results"/><br/><b>OSWorld-G</b></td>
  </tr>
</table>

### 移动端 GUI 导航

- **AndroidWorld**: 76.7% SOTA，超越 UI-Tars-2、Gemini-2.5-Pro 和 Seed1.8
- **MobileWorld**: 41.7%，显著优于端到端 GUI 模型

<table align="center">
  <tr>
    <td align="center"><img src="./assets/img/aw.jpg" alt="AndroidWorld Results"/><br/><b>AndroidWorld</b></td>
    <td align="center"><img src="./assets/img/mw.jpg" alt="MobileWorld Results"/><br/><b>MobileWorld</b></td>
  </tr>
</table>

### 强化学习扩展

- 并行环境从 32 扩展到 512：+5.2 分
- 环境步数从 15 增加到 50：+4.3 分

### 端云协同

- 设备端性能提升 33%
- 云端 API 调用减少超过 40%

## 🎥 演示

### 演示 1 - 日常生活场景

触发 `ask_user` 获取更多信息以完成任务。

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/living.gif" height="400" alt="Daily Life Demo."/>
      <br/><b>用户指令：去盒马买菜，买一份雪花牛肉卷、一份娃娃菜、一份金针菇，再随便买一个豆制品。对了，去日历中待办里检查下我老婆有什么要在盒马买的，我确认下要不要一起买</b>
    </td>
  </tr>
</table>

### 演示 2 - 导航

使用 `mcp_call` 调用高德地图工具进行导航。

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/navigation.gif" height="400" alt="Navigation Demo."/>
      <br/><b>用户指令：我现在在阿里巴巴云谷园区，我要先去招商银行取钱，再去城西银泰城。帮我规划公交地铁出行的路线，选一家在4公里以内的、用时最短的招商银行，两段行程总时间不要超过2小时，把规划行程记在笔记中我一会看，标题为下午行程，内容为两段行程细节</b>
    </td>
  </tr>
</table>

### 演示 3 - 购物

跨应用协作完成任务。

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/shopping.gif" height="400" alt="Shopping Demo."/>
      <br/><b>用户指令：在小红书搜索 "timeless earth 2026"，将产品图片保存到相册，然后在淘宝使用保存的图片搜索相同商品并加入购物车</b>
    </td>
  </tr>
</table>

### 演示 4 - 工作

跨应用协作完成任务。

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/work.gif" height="400" alt="Work Demo."/>
      <br/><b>用户指令：我需要紧急出差上海，帮我去12306查询现在最早从杭州西站去上海虹桥、有二等座票的班次，在钉钉前沿技术研讨群里把到达时间同步给大家，再把我和水番的会议日程改到明天同一时间，在群里发消息@他，礼貌解释因为临时出差调整会议时间，询问他明天是否有空</b>
    </td>
  </tr>
</table>

### 演示 5 - 纯设备端

端云协同处理简单任务，无需调用云端模型。

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/dcc_simple_task.gif" height="400" alt="Device-cloud Collaboration Demo."/>
      <br/><b>用户指令：去飞猪查询12月25日去，28日回，杭州到三亚的往返机票</b>
    </td>
  </tr>
</table>

### 演示 6 - 端云协同

端云协同处理复杂任务，当任务超出设备模型能力时调用云端模型。

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/dcc_complex_task.gif" height="400" alt="Device-cloud Collaboration Demo."/>
      <br/><b>用户指令：去淘票票给我买一张25号下午的疯狂动物城2的电影票，选亲橙里的电影院，中间的座位，加一份可乐和爆米花的单人餐，停在最后的订单界面</b>
    </td>
  </tr>
</table>

## 🚀 快速开始

### 步骤 1：克隆仓库

```bash
git clone https://github.com/Tongyi-MAI/MAI-UI.git
cd MAI-UI
```

### 步骤 2：安卓设备执行环境搭建

为了让 MAI-UI 能够控制手机执行任务，你需要完成以下步骤来配置手机执行环境：

1. 在手机上开启开发者模式和 USB 调试。
2. 安装 ADB 工具，并确保电脑可以通过 ADB 连接手机。（如果你已经安装过 adb 工具，可跳过此步骤）
3. 通过 USB 数据线将手机连接到电脑，并使用 `adb devices` 命令确认连接成功。

#### 步骤 2.1：开启开发者模式和 USB 调试

通常可以按如下步骤在安卓手机上开启开发者模式和 USB 调试：

1. 打开手机上的「设置」应用。
2. 找到「关于手机」或「系统」选项，连续点击「版本号」10 次以上，直到看到"您已处于开发者模式"或类似提示。
3. 返回「设置」主页面，找到「开发者选项」。**【重要，必须开启】**
4. 在「开发者选项」中，找到并开启「USB 调试」功能，按照屏幕提示完成 USB 调试的启用。**【重要，必须开启】**

不同品牌手机的具体步骤可能略有差异，请根据实际情况调整。一般可以搜索「*<手机品牌>* 如何开启开发者模式」获得具体教程。

#### 步骤 2.2：安装 ADB 工具

ADB（Android Debug Bridge，安卓调试桥）是连接安卓设备与电脑进行通信的工具。

**Windows 用户：**

1. 下载 ADB 工具压缩包：https://dl.google.com/android/repository/platform-tools-latest-windows.zip 并解压到合适的位置。
2. 将解压后的文件夹路径加入系统环境变量：
   - 在「开始」菜单中右键点击「计算机」，选择「属性」
   - 点击「高级系统设置」
   - 点击「环境变量」按钮
   - 在「系统变量」区域找到并选中「Path」变量，然后点击「编辑」
   - 点击「新建」，然后输入 ADB 工具解压后的路径
   - 点击「确定」保存更改

**Mac 和 Linux 用户：**

1. 安装 Homebrew（如果尚未安装）：
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. 使用以下命令安装 ADB 工具：
```bash
brew install android-platform-tools
```

#### 步骤 2.3：将安卓设备连接到电脑

使用 USB 数据线将手机连接到电脑后，执行：

```bash
adb devices
```

如果连接成功，你会看到类似如下的输出：

```bash
List of devices attached
AN2CVB4C28000731        device
```

如果没有看到任何设备，请检查数据线连接是否正常，以及手机上的 USB 调试选项是否正确开启。首次连接手机时，手机上可能会弹出授权提示，只需选择「允许」即可。

#### Web UI 中的无线调试（推荐）

1. **准备设备**
   - 确保手机和电脑在同一 WiFi 网络
   - 手机上：设置 → 开发者选项 → 无线调试（启用）

2. **连接无线设备**
   - 打开 Web UI (http://localhost:8868)
   - 在左侧面板找到「📶 无线调试」部分
   - 输入手机的 IP 地址（可以在手机的无线调试设置中查看）
   - 端口默认为 5555，根据你的实际手机情况修改
   - 点击「🔗 连接无线设备」按钮

3. **USB 转无线**
   - 如果您的设备是 USB 连接：
   - 点击「📡 启用TCP/IP模式（USB转无线）」
   - 系统会自动获取设备 IP 并启用无线模式
   - 断开 USB 线后即可使用无线连接

4. **管理设备**
   - 点击「🔄 检查设备状态」查看所有已连接的设备
   - 点击「📋 ADB设备列表」获取详细的设备连接信息
   - 点击「🔄 重启ADB服务」解决 ADB 连接问题
   - 系统会显示设备类型：🔌 USB 或 📶 无线
   - 点击「✂️ 断开无线设备」可以断开无线连接

**命令行方式：**

```bash
# 通过 WiFi 连接
adb connect 192.168.1.100:5555

# 验证连接
adb devices

# 重启 ADB 服务
adb kill-server
adb start-server
```

### 步骤 3：使用 vLLM 启动模型 API 服务

从 HuggingFace 下载模型并使用 vLLM 部署 API 服务：

**HuggingFace 模型路径：**
- [MAI-UI-2B](https://huggingface.co/Tongyi-MAI/MAI-UI-2B)
- [MAI-UI-8B](https://huggingface.co/Tongyi-MAI/MAI-UI-8B)

#### 方式 A：使用 Docker 部署（推荐 Windows 用户使用）

**前置要求：**
- 已安装 Docker Desktop 并启用 WSL2 后端
- NVIDIA GPU（计算能力 7.0+，如 RTX 20xx/30xx/40xx、A100 等）
- 已安装 NVIDIA 驱动和 NVIDIA Container Toolkit

**步骤 1：拉取官方 vLLM Docker 镜像：**

```bash
docker pull vllm/vllm-openai:latest
```

**步骤 2：运行 vLLM API 服务**

根据模型来源选择以下方式之一：

| 方式 | 模型来源 | 优点 | 缺点 |
|------|----------|------|------|
| 方式 1 | 本地模型文件 | 启动快、可离线使用 | 需要预先下载 |
| 方式 2 | HuggingFace 在线 | 自动下载、始终最新 | 需要网络、首次启动慢 |

**方式 1：使用本地模型（推荐）**

如果你已经将模型下载到本地磁盘：

```bash
# Linux/Mac
docker run -d --gpus all \
    -v /path/to/your/MAI-UI-8B:/model \
    -p 8000:8000 \
    --ipc=host \
    --name vllm-mai \
    vllm/vllm-openai:latest \
    --model /model \
    --served-model-name MAI-UI-8B \
    --trust-remote-code \
    --max-model-len 8192
```

```powershell
# Windows PowerShell
# ⚠️ 请将 D:/path/to/your/MAI-UI-8B 替换为你的实际模型路径
docker run -d --gpus all `
    -v D:/path/to/your/MAI-UI-8B:/model `
    -p 8000:8000 `
    --ipc=host `
    --name vllm-mai `
    vllm/vllm-openai:latest `
    --model /model `
    --served-model-name MAI-UI-8B `
    --trust-remote-code `
    --max-model-len 8192
```

**方式 2：从 HuggingFace 下载**

如果你想自动从 HuggingFace 下载模型：

```bash
# Linux/Mac
docker run -d --gpus all \
    -v ~/.cache/huggingface:/root/.cache/huggingface \
    -p 8000:8000 \
    --ipc=host \
    --name vllm-mai \
    vllm/vllm-openai:latest \
    --model Tongyi-MAI/MAI-UI-8B \
    --served-model-name MAI-UI-8B \
    --trust-remote-code \
    --max-model-len 8192
```

```powershell
# Windows PowerShell
docker run -d --gpus all `
    -v ${env:USERPROFILE}/.cache/huggingface:/root/.cache/huggingface `
    -p 8000:8000 `
    --ipc=host `
    --name vllm-mai `
    vllm/vllm-openai:latest `
    --model Tongyi-MAI/MAI-UI-8B `
    --served-model-name MAI-UI-8B `
    --trust-remote-code `
    --max-model-len 8192
```

> 💡 **Docker 参数说明：**
> | 参数 | 说明 |
> |------|------|
> | `-d` | 后台运行容器 |
> | `--gpus all` | 启用所有 GPU（`--gpus device=0` 指定特定 GPU） |
> | `-v <主机>:<容器>` | 挂载模型文件卷 |
> | `--ipc=host` | 共享主机 IPC 命名空间（多进程必需） |
> | `--name vllm-mai` | 容器命名，方便管理 |
> | `--max-model-len 8192` | 限制上下文长度以减少显存占用 |
> | `--shm-size=16G` | 如有需要，增加共享内存 |

**验证容器是否正常运行：**

```bash
docker logs vllm-mai
```

**停止并删除容器：**

```bash
docker stop vllm-mai && docker rm vllm-mai
```

#### 方式 B：使用 pip 部署（Linux/WSL）

```bash
# 安装 vLLM
pip install vllm  # vllm>=0.11.0 且 transformers>=4.57.0

# 启动 vLLM API 服务（将 MODEL_PATH 替换为您的本地模型路径或 HuggingFace 模型 ID）
python -m vllm.entrypoints.openai.api_server \
    --model <huggingface_model_path> \
    --served-model-name MAI-UI-8B \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --trust-remote-code
```

> 💡 **提示：**
> - 根据 GPU 数量调整 `--tensor-parallel-size` 以进行多 GPU 推理
> - 模型将在 `http://localhost:8000/v1` 提供服务

### 步骤 4：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 5：运行 Cookbook 示例

我们在 `cookbook/` 目录提供了两个 Notebook：

#### 5.1 Grounding 演示

`grounding.ipynb` 演示如何使用 MAI Grounding Agent 定位 UI 元素：

```bash
cd cookbook
jupyter notebook grounding.ipynb
```

运行前，更新 Notebook 中的 API 端点：

```python
agent = MAIGroundingAgent(
    llm_base_url="http://localhost:8000/v1",  # 更新为您的 vLLM 服务地址
    model_name="MAI-UI-8B",                   # 使用服务模型名称
    runtime_conf={
        "history_n": 3,
        "temperature": 0.0,
        "top_k": -1,
        "top_p": 1.0,
        "max_tokens": 2048,
    },
)
```

#### 5.2 Navigation Agent 演示

`run_agent.ipynb` 演示完整的 UI 导航智能体：

```bash
cd cookbook
jupyter notebook run_agent.ipynb
```

同样更新 API 端点配置：

```python
agent = MAIUINaivigationAgent(
    llm_base_url="http://localhost:8000/v1",  # 更新为您的 vLLM 服务地址
    model_name="MAI-UI-8B",                   # 使用服务模型名称
    runtime_conf={
        "history_n": 3,
        "temperature": 0.0,
        "top_k": -1,
        "top_p": 1.0,
        "max_tokens": 2048,
    },
)
### 步骤 6：运行 Web UI（可选）

我们还提供了一个基于 Gradio 的 Web UI，以实现交互式控制和轨迹回放：

```bash
python start_web_ui.py
```

访问地址：`http://localhost:8868`

---

## 🖥️ Web UI

Web UI 实现了以下可视化操作和功能：

### 功能特性

| 功能 | 说明 |
|------|------|
| 📱 设备管理 | USB/无线 ADB 连接、设备状态检查 |
| 🎯 任务执行 | 自动/单步执行、暂停/停止控制 |
| 📊 轨迹可视化 | Chatbot 格式展示、截图动作标记 |
| 🔍 图片预览 | Lightbox 放大查看截图 |
| ⚙️ 参数配置 | 模型提供商选择、API 配置 |
| 🛠️ MCP 工具 | 支持外部工具调用（如高德地图） |

### 启动 Web UI

```bash
python start_web_ui.py
```

访问地址：`http://localhost:8868`

### 配置模型提供商

编辑 `model_config.yaml`：

```yaml
vllm_local:
  display_name: "vLLM 本地"
  api_base: "http://localhost:8000/v1"
  api_key: ""
  default_model: "MAI-UI-8B"
```

### Web UI 界面布局

```
┌─────────────────────────────────────────────────────────────┐
│                    MAI-UI 控制台                              │
├──────────────────┬──────────────────────────────────────────┤
│  📱 设备管理      │  📱 任务轨迹          │  📋 实时日志      │
│  ├ 设备状态      │  ├ 步骤截图+动作      │  ├ 终端输出       │
│  └ 无线调试      │  └ 思考过程          │  └ 执行状态       │
├──────────────────┤                      │                  │
│  📊 任务监控      │                      │                  │
│  ├ Session 选择  │                      │                  │
│  ├ 任务指令输入   │                      │                  │
│  └ 执行/停止控制  │                      │                  │
├──────────────────┤                      │                  │
│  ⚙️ 参数配置      │                      │                  │
│  └ 模型/设备选择  │                      │                  │
└──────────────────┴──────────────────────────────────────────┘
```

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Enter` | 提交任务指令 |
| `ESC` | 关闭图片预览 |

---

## 🔧 自定义配置

### 扩展应用名映射 (package_map.py)

`web_ui/package_map.py` 文件包含了中文应用名到 Android 包名的映射。这使得 Agent 可以直接打开像 "微信" 或 "淘宝" 这样的应用而无需搜索。

**添加自定义应用：**

1. 打开 `web_ui/package_map.py`
2. 在 `package_name_map` 字典中添加条目：

```python
package_name_map = {
    # ... 现有条目 ...
    
    # 添加您的自定义应用
    "我的App": "com.example.myapp",
    "自定义应用": "com.custom.app",
}
```

3. 该映射支持模糊匹配 - 如果未找到精确匹配，系统将使用字符串相似度找到最接近的匹配项。

**获取包名：**

您可以使用以下命令查找任何已安装应用的包名：

```bash
# 列出所有已安装的应用
adb shell pm list packages

# 搜索特定应用
adb shell pm list packages | grep wechat
```

---

## 📝 引用

如果您认为本项目对您的研究有帮助，请考虑引用我们的工作：

```bibtex
@misc{zhou2025maiuitechnicalreportrealworld,
      title={MAI-UI Technical Report: Real-World Centric Foundation GUI Agents}, 
      author={Hanzhang Zhou and Xu Zhang and Panrong Tong and Jianan Zhang and Liangyu Chen and Quyu Kong and Chenglin Cai and Chen Liu and Yue Wang and Jingren Zhou and Steven Hoi},
      year={2025},
      eprint={2512.22047},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2512.22047}, 
}
@misc{chen2025uiinsenhancingguigrounding,
      title={UI-Ins: Enhancing GUI Grounding with Multi-Perspective Instruction-as-Reasoning}, 
      author={Liangyu Chen and Hanzhang Zhou and Chenglin Cai and Jianan Zhang and Panrong Tong and Quyu Kong and Xu Zhang and Chen Liu and Yuqi Liu and Wenxuan Wang and Yue Wang and Qin Jin and Steven Hoi},
      year={2025},
      eprint={2510.20286},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2510.20286}, 
}
@misc{kong2025mobileworldbenchmarkingautonomousmobile,
      title={MobileWorld: Benchmarking Autonomous Mobile Agents in Agent-User Interactive, and MCP-Augmented Environments}, 
      author={Quyu Kong and Xu Zhang and Zhenyu Yang and Nolan Gao and Chen Liu and Panrong Tong and Chenglin Cai and Hanzhang Zhou and Jianan Zhang and Liangyu Chen and Zhidan Liu and Steven Hoi and Yue Wang},
      year={2025},
      eprint={2512.19432},
      archivePrefix={arXiv},
      primaryClass={cs.AI},
      url={https://arxiv.org/abs/2512.19432}, 
}
```

## 📧 联系我们

如有问题或需要支持，请联系：

- **Hanzhang Zhou**  
  邮箱：[hanzhang.zhou@alibaba-inc.com](mailto:hanzhang.zhou@alibaba-inc.com)

- **Xu Zhang**  
  邮箱：[hanguang.zx@alibaba-inc.com](mailto:hanguang.zx@alibaba-inc.com)

- **Yue Wang**  
  邮箱：[yue.w@alibaba-inc.com](mailto:yue.w@alibaba-inc.com)

## 📄 许可证

MAI-UI Mobile 是由阿里云开发的基础 GUI 智能体，采用 Apache License（版本 2.0）许可。

本产品包含各种第三方组件，采用其他开源许可证。详情请参阅 NOTICE 文件。
