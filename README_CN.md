# MAI-UI

> MAI-UI 技术报告：面向真实世界的基础 GUI 智能体

<p align="center">
  <a href="https://arxiv.org/abs/2512.22047"><img src="https://img.shields.io/badge/📄%20arXiv-论文-red" alt="arXiv" /></a>
  <a href="https://tongyi-mai.github.io/MAI-UI//"><img src="https://img.shields.io/badge/🌐%20Website-项目主页-blue" alt="Website" /></a>
  <a href="https://huggingface.co/Tongyi-MAI"><img src="https://img.shields.io/badge/🤗%20Hugging%20Face-模型-orange" alt="Hugging Face Model" /></a>
</p>

![Overview PDF](./assets/img/overview.png)

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

### 步骤 2：使用 vLLM 启动模型 API 服务

从 HuggingFace 下载模型并使用 vLLM 部署 API 服务：

**HuggingFace 模型路径：**
- [MAI-UI-2B](https://huggingface.co/Tongyi-MAI/MAI-UI-2B)
- [MAI-UI-8B](https://huggingface.co/Tongyi-MAI/MAI-UI-8B)

**使用 vLLM 部署模型：**

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

### 步骤 3：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 4：运行 Cookbook 示例

我们在 `cookbook/` 目录提供了两个 Notebook：

#### 4.1 Grounding 演示

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

#### 4.2 Navigation Agent 演示

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
### 步骤 5：运行 Web UI（可选）

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
