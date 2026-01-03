# MAI-UI
> MAI-UI Technical Report: Real-World Centric Foundation GUI Agents.

<p align="center">
  <a href="https://arxiv.org/abs/2512.22047"><img src="https://img.shields.io/badge/📄%20arXiv-Paper-red" alt="arXiv" /></a>
  <a href="https://tongyi-mai.github.io/MAI-UI//"><img src="https://img.shields.io/badge/🌐%20Website-Project%20Page-blue" alt="Website" /></a>
  <a href="https://huggingface.co/Tongyi-MAI"><img src="https://img.shields.io/badge/🤗%20Hugging%20Face-Model-orange" alt="Hugging Face Model" /></a>
</p>

![Overview PDF](./assets/img/overview.png)

## ✨ Highlights

This repository provides the official implementation of **MAI-UI**, a foundation GUI agent for Android automation. Key features include:

- 🖥️ **Gradio Web UI** - Interactive control panel with real-time trajectory visualization and device management
- 📱 **ADB Integration** - USB and wireless debugging support with scrcpy screen mirroring
- 🤖 **Multi-Model Support** - Pre-configured templates for vLLM, Qwen, OpenAI, and custom providers
- 🔧 **MCP Tools** - External tool integration (e.g., AMap navigation)
- 📦 **App Mapping** - Chinese app name to package name mapping for direct app launching
- ⚡ **One-Click Setup** - Automated dependency checking and environment validation

## 📰 News

* 🎁 **[2025-12-30]** Added Gradio Web UI for interactive control and trajectory visualization!
* 🎁 **[2025-12-29]** We release MAI-UI Technical Report on [arXiv](https://arxiv.org/abs/2512.22047)!
* 🎁 **[2025-12-29]** Initial release of [MAI-UI-8B](https://huggingface.co/Tongyi-MAI/MAI-UI-8B) and [MAI-UI-2B](https://huggingface.co/Tongyi-MAI/MAI-UI-2B) models on Hugging Face.

## 📑 Table of Contents

- [📖 Background](#-background)
- [🏆 Results](#-results)
- [🎥 Demo](#-demo)
- [🚀 Quick Start](#-installation--quick-start)
- [📝 Citation](#-citation)
- [📧 Contact](#-contact)
- [📄 License](#-license)

## 📖 Background

The development of GUI agents could revolutionize the next generation of human-computer interaction. Motivated by this vision, we present MAI-UI, a family of foundation GUI agents spanning the full spectrum of sizes, including 2B, 8B, 32B, and 235B-A22B variants. We identify four key challenges to realistic deployment: the lack of native agent–user interaction, the limits of UI-only operation, the absence of a practical deployment architecture, and brittleness in dynamic environments. MAI-UI addresses these issues with a unified methodology: a self-evolving data pipeline that expands the navigation data to include user interaction and MCP tool calls, a native device–cloud collaboration system that routes execution by task state, and an online RL framework with advanced optimizations to scale parallel environments and context length. 


## 🏆 Results

MAI-UI establishes new state-of-the-art across GUI grounding and mobile navigation. 

- On grounding benchmarks, it reaches 73.5% on ScreenSpot-Pro, 91.3% on MMBench GUI L2, 70.9% on OSWorld-G, and 49.2% on UI-Vision, surpassing Gemini-3-Pro and Seed1.8 on ScreenSpot-Pro. 

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

- On mobile GUI navigation, it sets a new SOTA of 76.7% on AndroidWorld, surpassing UI-Tars-2, Gemini-2.5-Pro and Seed1.8. On MobileWorld, MAI-UI obtains 41.7% success rate, significantly outperforming end-to-end GUI models and competitive with Gemini-3-Pro based agentic frameworks. 
<table align="center">
  <tr>
    <td align="center"><img src="./assets/img/aw.jpg" alt="AndroidWorld Results"/><br/><b>AndroidWorld</b></td>
    <td align="center"><img src="./assets/img/mw.jpg" alt="MobileWorld Results"/><br/><b>MobileWorld</b></td>
  </tr>
</table>

- Our online RL experiments show significant gains from scaling parallel environments from 32 to 512 (+5.2 points) and increasing environment step budget from 15 to 50 (+4.3 points).
<table align="center">
  <tr>
    <td align="center" width="50%"><img src="./assets/img/rl.jpg" alt="Online RL Results"/><br/><b>Online RL Results</b></td>
    <td align="center" width="50%"><img src="./assets/img/rl_env.jpg" alt="RL Environment Scaling"/><br/><b>RL Environment Scaling</b></td>
  </tr>
</table>

- Our device-cloud collaboration framework can dynamically select on-device or cloud execution based on task execution state and data sensitivity. It improves on-device performance by 33% and reduces cloud API calls by over 40%.

<table align="center">
  <tr>
    <td align="center" width="50%"><img src="./assets/img/dcc.jpg" alt="Device-cloud Collaboration"/><br/><b>Device-cloud Collaboration</b></td>
  </tr>
</table>

## 🎥 Demo

### Demo 1 - Daily Life Scenario

Trigger `ask_user` for more information to complete the task.

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/living.gif" height="400" alt="Daily Life Demo."/>
      <br/><b>User instruction: 去盒马买菜，买一份雪花牛肉卷、一份娃娃菜、一份金针菇，再随便买一个豆制品。对了，去日历中待办里检查下我老婆有什么要在盒马买的，我确认下要不要一起买</b>
    </td>
  </tr>
</table>

### Demo 2 - Navigation

Use `mcp_call` to invoke AMap tools for navigation.

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/navigation.gif" height="400" alt="Navigation Demo."/>
      <br/><b>User instruction: 我现在在阿里巴巴云谷园区，我要先去 招商银行取钱，再去城西银泰城。帮我规划公交地铁出行的路线，选一家在4公里以内的、用时最短的招商银行，两段行程总时间不要超过2小时，把规划行程记在笔 记中我一会看，标题为下午行程，内容为两段行程细节</b>
    </td>
  </tr>
</table>

### Demo 3 - Shopping

 Cross-apps collaboration to complete the task.

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/shopping.gif" height="400" alt="Shopping Demo."/>
      <br/><b>User instruction: Search “timeless earth 2026” on Xiaohongshu, save the one product image to your photo album, then use the saved image on Taobao to search for the same item and  add it to my shopping cart.</b>
    </td>
  </tr>
</table>

### Demo 4 - Work

Cross-apps collaboration to complete the task.

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/work.gif" height="400" alt="Work Demo."/>
      <br/><b>User instruction: 我需要紧急出差上海，帮我去12306查询现在最早从杭州西站去上海虹桥、有二等座票的班次，在钉钉前沿技术研讨群里把到达时间同步给大家，再把我和水番的会议日程改到明天同一时间，在群里发消息@他，礼貌解释因为临时出差调整会议时间，询问他明天是否有空</b>
    </td>
  </tr>
</table>

### Demo 5 - Device-only

Device-cloud collaboration for simple tasks, no need cloud model invocation.

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/dcc_simple_task.gif" height="400" alt="Device-cloud Collaboration Demo."/>
      <br/><b>User Instruction: 去飞猪查询12月25日去，28日回，杭州到三亚的往返机票</b>
    </td>
  </tr>
</table>

### Demo 6 - Device-cloud Collaboration

Device-cloud collaboration for complex tasks, requiring cloud model invocation when the task is beyond the device models capabilities.

<table align="center">
  <tr>
    <td align="center">
      <img src="./assets/gif/dcc_complex_task.gif" height="400" alt="Device-cloud Collaboration Demo."/>
      <br/><b>User Instruction: 去淘票票给我买一张25号下午的疯狂动物城2的电影票，选亲橙里的电影院，中间的座位，加一份可乐和爆米花的单人餐，停在最后的订单界面</b>
    </td>
  </tr>
</table>

## 🚀 Installation & Quick Start

### Step 1: Clone the Repository

```bash
git clone https://github.com/Tongyi-MAI/MAI-UI.git
cd MAI-UI
```

### Step 2: Android Device Execution Environment Setup

To enable MAI-UI to control your phone for task execution, you need to complete the following steps:

1. Enable developer mode and USB debugging on the phone.
2. Install the ADB tool and ensure that the computer can connect to the phone via ADB. (Skip if you already have ADB installed)
3. Connect the phone to the computer via USB cable and use `adb devices` command to confirm connection.

#### Step 2.1: Enable Developer Mode and USB Debugging

Generally, you can enable developer mode and USB debugging on Android phones by following these steps:

1. Go to the "Settings" app on your phone.
2. Find the "About Phone" or "System" option, and tap on the "Build Number" 10+ times until you see a message saying "You are now a developer."
3. Go back to the main "Settings" menu and find "Developer Options." **【Important, must enable】**
4. In "Developer Options," find and enable the "USB Debugging" feature. **【Important, must enable】**

Different phone brands may have slight variations, so please adjust according to your specific situation. Generally, searching for "*<phone brand>* how to enable developer mode" will yield relevant tutorials.

#### Step 2.2: Install ADB Tool

ADB (Android Debug Bridge) is a bridge tool for communication between Android devices and computers.

**Windows Users:**

1. Download the ADB tool package: https://dl.google.com/android/repository/platform-tools-latest-windows.zip and extract it to a suitable location.
2. Add the extracted folder path to the system environment variables:
   - Right-click "Computer" in the "Start" menu and select "Properties"
   - Click "Advanced system settings"
   - Click the "Environment Variables" button
   - In "System variables," find and select "Path," then click "Edit"
   - Click "New" and enter the extracted path of the ADB tool package
   - Click "OK" to save changes

**Mac and Linux Users:**

1. Install Homebrew (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Install the ADB tool:
```bash
brew install android-platform-tools
```

#### Step 2.3: Connect Android Device to Computer

After connecting your phone to the computer using a USB cable, run:

```bash
adb devices
```

If the connection is successful, you will see output similar to:

```bash
List of devices attached
AN2CVB4C28000731        device
```

If you do not see any devices, please check if the USB cable and USB debugging settings are correctly enabled. When connecting for the first time, an authorization prompt may pop up on the phone; select "Allow."

#### Wireless Debugging in Web UI (Recommended)

> ⚠️ **Important**: For new phones or after re-enabling developer mode, you must first connect via USB cable at least once. This initial USB connection authorizes the computer for ADB access. Once authorized, you can use wireless debugging without USB connection going forward.

1. **Prepare Device**
   - Ensure phone and computer are on the same WiFi network
   - On phone: Settings → Developer Options → Wireless Debugging (Enable)

2. **Connect Wireless Device**
   - Open Web UI (http://localhost:8868)
   - Find "📶 Wireless Debugging" section in the left panel
   - Enter the phone's IP address (visible in phone's wireless debugging settings)
   - Port defaults to 5555, modify as your phone settings
   - Click "🔗 Connect Wireless Device" button

3. **USB to Wireless**
   - If your device is USB connected:
   - Click "📡 Enable TCP/IP Mode (USB to Wireless)"
   - System will automatically get device IP and enable wireless mode
   - Disconnect USB cable and use wireless connection

4. **Manage Devices**
   - Click "🔄 Check Device Status" to view all connected devices
   - Click "📋 ADB Device List" to get detailed device connection information
   - Click "🔄 Restart ADB Service" to resolve ADB connection issues
   - System will show device type: 🔌 USB or 📶 Wireless
   - Click "✂️ Disconnect Wireless Device" to disconnect wireless connection

**Command Line Method:**

```bash
# Connect via WiFi
adb connect 192.168.1.100:5555

# Verify connection
adb devices

# Restart ADB service
adb kill-server
adb start-server
```

### Step 3: Start Model API Service with vLLM

Download the model from HuggingFace and deploy the API service using vLLM:

HuggingFace model path:  
- [MAI-UI-2B](https://huggingface.co/Tongyi-MAI/MAI-UI-2B)
- [MAI-UI-8B](https://huggingface.co/Tongyi-MAI/MAI-UI-8B)

#### Option A: Deploy with Docker (Recommended for Windows)

**Prerequisites:**
- Docker Desktop installed with WSL2 backend enabled
- NVIDIA GPU with compute capability 7.0+ (e.g., RTX 20xx/30xx/40xx, A100, etc.)
- NVIDIA drivers and NVIDIA Container Toolkit installed

**Step 1: Pull the official vLLM Docker image:**

```bash
docker pull vllm/vllm-openai:latest
```

**Step 2: Run the vLLM API server**

Choose one of the following methods based on your model source:

| Method | Model Source | Pros | Cons |
|--------|--------------|------|------|
| Method 1 | Local model files | Faster startup, offline capable | Requires pre-download |
| Method 2 | HuggingFace online | Auto-download, always latest | Requires internet, first-run slow |

**Method 1: Using Local Model (Recommended)**

If you have already downloaded the model to your local disk:

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
# ⚠️ Replace D:/path/to/your/MAI-UI-8B with your actual model path
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

**Method 2: Download from HuggingFace**

If you want to download the model from HuggingFace automatically:

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

> 💡 **Docker Parameter Reference:**
> | Parameter | Description |
> |-----------|-------------|
> | `-d` | Run container in background |
> | `--gpus all` | Enable all GPUs (`--gpus device=0` for specific GPU) |
> | `-v <host>:<container>` | Mount volume for model files |
> | `--ipc=host` | Share host IPC namespace (required for multi-process) |
> | `--name vllm-mai` | Container name for easy management |
> | `--max-model-len 8192` | Limit context length to reduce VRAM usage |
> | `--shm-size=16G` | Increase shared memory if needed |

**Verify the container is running:**

```bash
docker logs vllm-mai
```

**Stop and remove the container:**

```bash
docker stop vllm-mai && docker rm vllm-mai
```

#### Option B: Deploy with pip (Linux/WSL)

```bash
# Install vLLM
pip install vllm  # vllm>=0.11.0 and transformers>=4.57.0

# Start vLLM API server (replace MODEL_PATH with your local model path or HuggingFace model ID)
python -m vllm.entrypoints.openai.api_server \
    --model <huggingface_model_path> \
    --served-model-name MAI-UI-8B \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --trust-remote-code
```

> 💡 **Tips:**
> - Adjust `--tensor-parallel-size` based on your GPU count for multi-GPU inference
> - The model will be served at `http://localhost:8000/v1`

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run Cookbook Notebooks

We provide two notebooks in the `cookbook/` directory:

#### 5.1 Grounding Demo

The `grounding.ipynb` demonstrates how to use the MAI Grounding Agent to locate UI elements:

```bash
cd cookbook
jupyter notebook grounding.ipynb
```

Before running, update the API endpoint in the notebook:

```python
agent = MAIGroundingAgent(
    llm_base_url="http://localhost:8000/v1",  # Update to your vLLM server address
    model_name="MAI-UI-8B",                   # Use the served model name
    runtime_conf={
        "history_n": 3,
        "temperature": 0.0,
        "top_k": -1,
        "top_p": 1.0,
        "max_tokens": 2048,
    },
)
```

#### 5.2 Navigation Agent Demo

The `run_agent.ipynb` demonstrates the full UI navigation agent:

```bash
cd cookbook
jupyter notebook run_agent.ipynb
```

Similarly, update the API endpoint configuration:

```python
agent = MAIUINaivigationAgent(
    llm_base_url="http://localhost:8000/v1",  # Update to your vLLM server address
    model_name="MAI-UI-8B",                   # Use the served model name
    runtime_conf={
        "history_n": 3,
        "temperature": 0.0,
        "top_k": -1,
        "top_p": 1.0,
        "max_tokens": 2048,
    },
)
```

### Step 6: Run Web UI (Alternative)

We also provide a Gradio Web UI for interactive control:

```bash
python start_web_ui.py
```

Then visit `http://localhost:8868` in your browser.

---

## 🔧 Customization

### 📦 App Mapping Scanner

Automatically scan installed apps on the device and build a **Chinese app name → package name** mapping, enabling the agent to directly open apps.

**File Structure:**

```
Project Root/
├── default_package_map.yaml      # Default mapping library (160+ entries)
├── user_package_map.yaml         # User mappings (scan results + custom)
├── user_package_map.yaml.example # Template file
└── aapt2-8.5.0-11315950-windows/ # aapt2 tool (Windows)
```

**Features:**

- **Real-time Loading**: Changes to YAML files take effect immediately, no restart needed
- **Smart Scanning**: Prioritizes mapping table (instant), auto-parses unknown apps with aapt2
- **Priority**: `user_package_map.yaml` > `default_package_map.yaml`

**Usage:**

1. Directly edit `default_package_map.yaml` to add mappings
2. Or copy `user_package_map.yaml.example` to `user_package_map.yaml` for custom mappings

**⏱️ Scan Time Reference:**

| Match Type | Time per App | Description |
|-----------|-------------|-------------|
| Mapping Match | <1 sec | Quick lookup from 160+ mappings |
| Deep Parse | 5-15 sec | Pull APK and parse with aapt2 |

> ⚠️ **Note**: Deep scanning many apps may take a long time. Consider manually editing YAML files first.

**Getting package names:**

```bash
# List all installed apps
adb shell pm list packages

# Search for a specific app
adb shell pm list packages | grep wechat
```

---

## 📝 Citation

If you find this project useful for your research, please consider citing our works:

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

## 📧 Contact

For questions and support, please contact:

- **Hanzhang Zhou**  
  Email: [hanzhang.zhou@alibaba-inc.com](mailto:hanzhang.zhou@alibaba-inc.com)

- **Xu Zhang**  
  Email: [hanguang.zx@alibaba-inc.com](mailto:hanguang.zx@alibaba-inc.com)

- **Yue Wang**  
  Email: [yue.w@alibaba-inc.com](mailto:yue.w@alibaba-inc.com)

## 📄 License

MAI-UI Mobile is a foundation GUI agent developed by Alibaba Cloud and licensed under the Apache License (Version 2.0).

This product contains various third-party components under other open source licenses. 
See the NOTICE file for more information.

