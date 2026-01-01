"""
Agent 运行器模块
整合 MAI-UI Agent 与 ADB 操作，实现自动化任务执行
"""

import os
import sys
import json
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generator, Callable
from datetime import datetime
from PIL import Image

# 添加 src 目录到路径
src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from adb_utils import (
    take_screenshot, take_screenshot_file_mode, tap_device, long_press_device, swipe_direction,
    input_text_yadb, press_system_button, open_app, get_device_resolution
)

try:
    from mai_naivigation_agent import MAIUINaivigationAgent
    HAS_AGENT = True
except ImportError:
    HAS_AGENT = False
    print("[WARNING] MAI-UI Agent 未找到，将使用模拟模式")


@dataclass
class StepResult:
    """单步执行结果"""
    step_index: int
    screenshot: Image.Image
    thinking: str
    action: Dict[str, Any]
    action_type: str
    success: bool
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_index": self.step_index,
            "thinking": self.thinking,
            "action": self.action,
            "action_type": self.action_type,
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp
        }


class AgentRunner:
    """
    Agent 运行器
    管理 MAI-UI Agent 生命周期，执行任务并记录轨迹
    """
    
    def __init__(
        self,
        llm_base_url: str = "http://localhost:8000/v1",
        model_name: str = "MAI-UI-8B",
        device_id: Optional[str] = None,
        logs_dir: str = "d:/maigui/MAI-UI/logs",
        tools: Optional[List[Dict[str, Any]]] = None
    ):
        self.llm_base_url = llm_base_url
        self.model_name = model_name
        self.device_id = device_id
        self.logs_dir = logs_dir
        self.tools = tools
        self.auto_reply_enabled = False  # 是否启用自动回复
        
        # 状态
        self.is_running = False
        self.is_paused = False
        self.should_stop = False
        self.waiting_for_input = False
        self.user_input: Optional[str] = None
        self.pending_user_feedback: Optional[str] = None  # 恢复时注入的指令
        
        # 当前任务
        self.current_instruction: Optional[str] = None
        self.session_id: Optional[str] = None
        self.step_count = 0
        self.trajectory: List[StepResult] = []
        
        # Agent 实例
        self.agent: Optional[MAIUINaivigationAgent] = None
        
        # 回调
        self.on_step_complete: Optional[Callable[[StepResult], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        
        # 线程锁
        self._lock = threading.Lock()
        
        # 确保日志目录存在
        os.makedirs(logs_dir, exist_ok=True)
    
    def _init_agent(self):
        """初始化 Agent"""
        if not HAS_AGENT:
            return
        
        self.agent = MAIUINaivigationAgent(
            llm_base_url=self.llm_base_url,
            model_name=self.model_name,
            runtime_conf={
                "history_n": 3,
                "temperature": 0.0,
                "top_k": -1,
                "top_p": 1.0,
                "max_tokens": 2048,
            },
            tools=self.tools
        )
    
    def start_task(self, instruction: str) -> str:
        """
        开始新任务
        
        Args:
            instruction: 任务指令
        
        Returns:
            session_id
        """
        with self._lock:
            if self.is_running:
                raise RuntimeError("已有任务正在运行")
            
            # 生成 Session ID
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_instruction = instruction
            self.step_count = 0
            self.trajectory = []
            self.is_running = True
            self.is_paused = False
            self.should_stop = False
            self.waiting_for_input = False
            
            # 初始化 Agent
            self._init_agent()
            if self.agent:
                self.agent.reset()
            
            self._notify_status("🟢 任务已开始")
            
            return self.session_id
    
    def step(self) -> Optional[StepResult]:
        """
        执行单步
        
        Returns:
            StepResult 或 None（如果无法执行）
        """
        if not self.is_running:
            return None
        
        if self.is_paused:
            return None
        
        if self.should_stop:
            self._finish_task("stopped")
            return None
        
        try:
            # 1. 截图
            print(f"[AgentRunner] Step {self.step_count + 1}: Taking screenshot...")
            self.step_count += 1
            # 使用文件模式截图（更适合内网穿透等慢速网络）
            screenshot = take_screenshot_file_mode(self.device_id)
            print(f"[AgentRunner] Screenshot captured: {screenshot.size}")
            
            # 2. 调用 Agent 预测
            if self.agent:
                print(f"[AgentRunner] Predicting action with instruction: {self.current_instruction[:50]}...")
                
                # 缩小截图以减少 Token 消耗 (修复 Context Length Error)
                # 使用副本进行预测，保持原始截图用于日志和 UI
                pred_screenshot = screenshot.copy()
                max_dim = 1024
                if max(pred_screenshot.size) > max_dim:
                    ratio = max_dim / max(pred_screenshot.size)
                    new_size = (int(pred_screenshot.width * ratio), int(pred_screenshot.height * ratio))
                    pred_screenshot = pred_screenshot.resize(new_size, Image.LANCZOS)
                    print(f"[AgentRunner] Resized screenshot for prediction: {screenshot.size} -> {new_size}")
                
                obs = {"screenshot": pred_screenshot}
                
                # 如果有待消费的用户输入或恢复时的注入指令，传给 Agent
                feedback = self.pending_user_feedback or self.user_input
                if feedback:
                    print(f"[AgentRunner] Passing user feedback to agent: {feedback}")
                    obs["user_feedback"] = feedback
                    self.pending_user_feedback = None  # 消费掉
                    self.user_input = None
                prediction, action = self.agent.predict(self.current_instruction, obs)
                print(f"[AgentRunner] Agent prediction raw: {prediction[:100]}...")
                print(f"[AgentRunner] Agent action: {action}")
                
                # 解析思考过程
                thinking = ""
                if "<thinking>" in prediction:
                    thinking = prediction.split("<thinking>")[1].split("</thinking>")[0].strip()
            else:
                # 模拟模式
                action = {"action": "terminate", "status": "fail"}
                thinking = "Agent 未初始化"
                prediction = ""
            
            action_type = action.get("action", "unknown")
            
            # 3. 执行动作
            print(f"[AgentRunner] Executing action: {action_type}")
            success, message = self._execute_action(action, screenshot)
            print(f"[AgentRunner] Action result: success={success}, message={message}")
            
            # 4. 创建结果
            result = StepResult(
                step_index=self.step_count,
                screenshot=screenshot,
                thinking=thinking,
                action=action,
                action_type=action_type,
                success=success,
                message=message
            )
            
            self.trajectory.append(result)
            
            # 5. 保存日志
            self._save_step_log(result)
            
            # 6. 回调
            if self.on_step_complete:
                self.on_step_complete(result)
            
            # 7. 检查终止条件
            if action_type == "terminate":
                status = action.get("status", "unknown")
                self._finish_task(status)
            elif action_type == "answer":
                # answer 动作表示任务完成并给出答案，应该终止
                answer_text = action.get("text", "")
                self._finish_task("done")
                self._notify_status(f"✅ 任务完成: {answer_text}")
            elif action_type == "ask_user":
                question = action.get("text", "请提供更多信息")
                if self.auto_reply_enabled:
                    self._handle_auto_reply(screenshot, question)
                else:
                    self._wait_for_user_input(question)
            
            elif action_type == "AWAKE":
                # AWAKE 动作 (gelab-zero 兼容): 直接打开应用
                app_name = action.get("text", "") or action.get("value", "")
                success, msg = open_app(app_name, self.device_id, prefer_awake=True)
                return success, f"唤醒应用 (AWAKE): {msg}"
            
            elif action_type == "INFO":
                # INFO 动作 (gelab-zero 兼容): 等同于 ask_user
                text = action.get("text", "") or action.get("value", "")
                if self.auto_reply_enabled:
                    self._handle_auto_reply(screenshot, text)
                else:
                    self._wait_for_user_input(text)
                return True, f"信息 (INFO): {text}"
            
            return result
            
        except Exception as e:
            result = StepResult(
                step_index=self.step_count,
                screenshot=Image.new('RGB', (100, 100)),
                thinking="",
                action={"action": "error"},
                action_type="error",
                success=False,
                message=f"执行出错: {str(e)}"
            )
            self.trajectory.append(result)
            self._notify_status(f"🔴 执行出错: {e}")
            return result
    
    def _execute_action(self, action: Dict[str, Any], screenshot: Image.Image) -> tuple:
        """
        执行动作
        
        Returns:
            (success, message)
        """
        action_type = action.get("action", "unknown")
        img_width, img_height = screenshot.size
        
        try:
            if action_type == "click":
                coords = action.get("coordinate", [0.5, 0.5])
                x = int(coords[0] * img_width)
                y = int(coords[1] * img_height)
                success = tap_device(x, y, self.device_id)
                return success, f"点击 ({x}, {y})"
            
            elif action_type == "long_press":
                coords = action.get("coordinate", [0.5, 0.5])
                x = int(coords[0] * img_width)
                y = int(coords[1] * img_height)
                success = long_press_device(x, y, device_id=self.device_id)
                return success, f"长按 ({x}, {y})"
            
            elif action_type == "swipe":
                direction = action.get("direction", "up")
                coords = action.get("coordinate")
                x, y = None, None
                if coords:
                    x = int(coords[0] * img_width)
                    y = int(coords[1] * img_height)
                success = swipe_direction(direction, x, y, device_id=self.device_id)
                return success, f"滑动 {direction}"
            
            elif action_type == "type":
                text = action.get("text", "")
                success = input_text_yadb(text, self.device_id)
                return success, f"输入文本: {text[:20]}..."
            
            elif action_type == "system_button":
                button = action.get("button", "home")
                success = press_system_button(button, self.device_id)
                return success, f"按下 {button}"
            
            elif action_type == "open":
                app_name = action.get("text", "")
                success, msg = open_app(app_name, self.device_id, prefer_awake=True)
                return success, msg
            
            elif action_type == "wait":
                time.sleep(2)
                return True, "等待 2 秒"
            
            elif action_type == "terminate":
                status = action.get("status", "unknown")
                return True, f"任务终止: {status}"
            
            elif action_type == "answer":
                text = action.get("text", "")
                return True, f"回答: {text}"
            
            elif action_type == "ask_user":
                text = action.get("text", "")
                return True, f"询问用户: {text}"
            
            elif action_type == "mcp_call":
                # MCP 工具调用
                return self._handle_mcp_call(action)
            
            else:
                return False, f"未知动作类型: {action_type}"
                
        except Exception as e:
            return False, f"动作执行失败: {str(e)}"
    
    def _handle_mcp_call(self, action: Dict[str, Any]) -> tuple:
        """处理 MCP 工具调用"""
        tool_name = action.get("name", "unknown")
        arguments = action.get("arguments", {})
        
        # TODO: 实际实现 MCP 调用
        # 目前返回模拟结果
        self._notify_status(f"🔧 调用 MCP 工具: {tool_name}")
        
        return True, f"MCP 调用: {tool_name}({arguments})"
    
    def _wait_for_user_input(self, prompt: str):
        """等待用户输入"""
        self.waiting_for_input = True
        self.is_paused = True
        self._notify_status(f"🟡 等待用户输入: {prompt}")
    
    def provide_user_input(self, text: str):
        """提供用户输入"""
        with self._lock:
            if self.waiting_for_input:
                self.user_input = text
                self.waiting_for_input = False
                self.is_paused = False
                self._notify_status("🟢 已收到用户输入，继续执行")

    def _handle_auto_reply(self, screenshot: Image.Image, question: str):
        """生成并应用自动回复"""
        self._notify_status(f"🤖 正在生成自动回复: {question}")
        
        try:
            # 使用 Agent 的 LLM 实例生成回复
            # 构造一个简单的 prompter
            prompt = f"""# 角色
你将扮演一个正在使用 GUI Agent 完成任务的用户。

# 任务
阅读下方提供的背景信息，针对 [Agent 的澄清问题]，生成一个提供关键信息的、简短直接的回答。

# 背景信息
- **原始任务:** {self.current_instruction}
- **Agent 问的问题:** {question}

# 输出要求
- 你的回答必须极其简短和明确。
- 你的回答应直接命中问题的核心，解决 Agent 的疑惑。
- 不要进行任何额外的解释、对话或使用礼貌用语。
- 只输出回答本身，不要添加任何引号或其他修饰。
"""
            # 我们直接复用 Agent 的 llm 客户端
            # 这里的截图使用原始截图
            from utils import pil_to_base64
            encoded_string = pil_to_base64(screenshot)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url", 
                            "image_url": {"url": f"data:image/png;base64,{encoded_string}"}
                        }
                    ]
                }
            ]
            
            response = self.agent.llm.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=200,
                temperature=0.0
            )
            
            reply = response.choices[0].message.content.strip()
            print(f"[AgentRunner] Auto-reply generated: {reply}")
            
            self.user_input = reply
            self._notify_status(f"🤖 自动回复已生成: {reply}")
            
        except Exception as e:
            print(f"[AgentRunner] Auto-reply failed: {e}")
            self._wait_for_user_input(question)  # 失败则退回到等待人工输入

    
    def auto_run(self, max_steps: int = 50, step_delay: float = 1.0) -> Generator[StepResult, None, None]:
        """
        自动执行直到终止
        
        Args:
            max_steps: 最大步数
            step_delay: 步骤间延迟（秒）
        
        Yields:
            StepResult
        """
        for _ in range(max_steps):
            if self.should_stop or not self.is_running:
                break
            
            if self.is_paused:
                time.sleep(0.5)
                continue
            
            result = self.step()
            if result:
                yield result
                
                if result.action_type == "terminate":
                    break
            
            # 将延迟分成小段，以便能快速响应停止请求
            delay_elapsed = 0.0
            while delay_elapsed < step_delay:
                if self.should_stop:
                    break
                time.sleep(0.1)
                delay_elapsed += 0.1
    
    def pause(self):
        """暂停任务"""
        with self._lock:
            if self.is_running:
                self.is_paused = True
                self._notify_status("⏸ 任务已暂停")
    
    def resume(self):
        """恢复任务"""
        with self._lock:
            if self.is_running and self.is_paused:
                self.is_paused = False
                self._notify_status("▶ 任务已恢复")
    
    def stop(self):
        """停止任务"""
        with self._lock:
            self.should_stop = True
            self.is_running = False
            self.is_paused = False
            self._notify_status("⏹ 任务已停止")
    
    def _finish_task(self, status: str):
        """结束任务"""
        with self._lock:
            self.is_running = False
            self.is_paused = False
            self._notify_status(f"⚪ 任务已完成: {status}")
    
    def _save_step_log(self, result: StepResult):
        """保存步骤日志"""
        if not self.session_id:
            return
        
        session_dir = os.path.join(self.logs_dir, self.session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        # 保存截图
        screenshot_path = os.path.join(session_dir, f"step_{result.step_index:03d}.png")
        result.screenshot.save(screenshot_path)
        
        # 保存日志
        log_path = os.path.join(session_dir, "trajectory.jsonl")
        log_entry = result.to_dict()
        log_entry["screenshot_path"] = screenshot_path
        
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def _notify_status(self, status: str):
        """通知状态变化"""
        if self.on_status_change:
            self.on_status_change(status)
        print(f"[AgentRunner] {status}")
    
    def get_trajectory(self) -> List[StepResult]:
        """获取当前轨迹"""
        return self.trajectory.copy()
    
    def get_status(self) -> str:
        """获取当前状态"""
        if self.waiting_for_input:
            return "🟡 等待输入"
        elif self.is_paused:
            return "⏸ 已暂停"
        elif self.is_running:
            return "🟢 运行中"
        else:
            return "⚪ 就绪"
    
    def is_waiting_for_input(self) -> bool:
        """是否等待用户输入"""
        return self.waiting_for_input


# 全局单例
_runner: Optional[AgentRunner] = None


def get_runner() -> AgentRunner:
    """获取全局 AgentRunner 实例"""
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner


def reset_runner(**kwargs):
    """重置全局 AgentRunner"""
    global _runner
    _runner = AgentRunner(**kwargs)
    return _runner
