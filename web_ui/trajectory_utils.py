"""
轨迹可视化工具模块
提供日志加载、Chatbot 格式转换、动作标记绘制等功能
"""

import os
import json
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw


LOGS_DIR = "d:/maigui/MAI-UI/logs"


def long_side_resize(image: Image.Image, long_side: int = 400) -> Image.Image:
    """
    将图片长边限制到指定尺寸
    
    Args:
        image: PIL Image
        long_side: 长边目标尺寸
    
    Returns:
        调整后的 PIL Image
    """
    w, h = image.size
    if max(w, h) <= long_side:
        return image
    
    if w > h:
        new_w = long_side
        new_h = int(h * long_side / w)
    else:
        new_h = long_side
        new_w = int(w * long_side / h)
    
    return image.resize((new_w, new_h), Image.LANCZOS)


def image_to_base64(image: Image.Image) -> str:
    """
    将 PIL 图片转换为 base64 Data URL
    
    Args:
        image: PIL Image
    
    Returns:
        base64 Data URL 字符串
    """
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def get_available_sessions(logs_dir: str = LOGS_DIR) -> List[str]:
    """
    获取所有可用的 session ID 列表
    
    Args:
        logs_dir: 日志目录
    
    Returns:
        session ID 列表，按时间倒序排列
    """
    if not os.path.exists(logs_dir):
        return []
    
    sessions = []
    for name in os.listdir(logs_dir):
        session_dir = os.path.join(logs_dir, name)
        if os.path.isdir(session_dir):
            # 检查是否有 trajectory.jsonl
            if os.path.exists(os.path.join(session_dir, "trajectory.jsonl")):
                sessions.append(name)
    
    # 按名称倒序（新的在前）
    sessions.sort(reverse=True)
    return sessions


def load_session_logs(session_id: str, logs_dir: str = LOGS_DIR) -> List[Dict[str, Any]]:
    """
    加载指定 session 的日志
    
    Args:
        session_id: Session ID
        logs_dir: 日志目录
    
    Returns:
        日志条目列表
    """
    log_path = os.path.join(logs_dir, session_id, "trajectory.jsonl")
    
    if not os.path.exists(log_path):
        return []
    
    logs = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
    except Exception as e:
        print(f"[ERROR] 加载日志失败: {e}")
    
    return logs


def logs_to_chatbot_messages(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将日志转换为 Gradio 6.x Chatbot 格式的消息列表

    Gradio 6.x Chatbot 格式：
    [
        {
            "role": "assistant",
            "content": [
                "文本内容",
                {"path": "path/to/image.png", "alt_text": "描述"}
            ]  # 或纯字符串
        }
    ]

    Args:
        logs: 日志条目列表

    Returns:
        Chatbot messages 列表
    """
    messages = []

    for log in logs:
        step_index = log.get("step_index", 0)
        thinking = log.get("thinking", "")
        action = log.get("action", {})
        action_type = log.get("action_type", "unknown")
        message = log.get("message", "")
        screenshot_path = log.get("screenshot_path", "")

        # 1. 构建文本内容
        content_parts = []
        content_parts.append(f"**步骤 {step_index}**")

        if thinking:
            content_parts.append(f"\n💭 *思考*: {thinking[:200]}..." if len(thinking) > 200 else f"\n💭 *思考*: {thinking}")

        action_text = format_action(action_type, action)
        content_parts.append(f"\n🎯 *动作*: {action_text}")
        content_parts.append(f"\n📝 *结果*: {message}")

        text_content = "\n".join(content_parts)

        # 2. 准备 content（支持文本+图片）
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                img = Image.open(screenshot_path)
                img = long_side_resize(img, 400)

                # 在图上绘制动作标记
                img = draw_action_marker(img, action, action_type)

                # 保存带标记的图片
                marked_path = screenshot_path.replace('.png', '_marked.png')
                img.save(marked_path)

                # Gradio 6.x 格式：图片需要使用字典格式
                image_message = {
                    "path": marked_path,
                    "alt_text": f"步骤 {step_index}: {action_type}"
                }
                # content 为列表：[文本字符串, 图片字典]
                content = [text_content, image_message]
            except Exception as e:
                print(f"[WARNING] 加载截图失败: {e}")
                content = text_content
        else:
            content = text_content

        # 3. 构建消息（Gradio 6.x 字典格式）
        messages.append({
            "role": "assistant",
            "content": content
        })

    return messages


def format_action(action_type: str, action: Dict[str, Any]) -> str:
    """
    格式化动作为可读字符串
    
    Args:
        action_type: 动作类型
        action: 动作字典
    
    Returns:
        格式化的动作描述
    """
    if action_type == "click":
        coords = action.get("coordinate", [0, 0])
        return f"点击 ({coords[0]:.3f}, {coords[1]:.3f})"
    
    elif action_type == "long_press":
        coords = action.get("coordinate", [0, 0])
        return f"长按 ({coords[0]:.3f}, {coords[1]:.3f})"
    
    elif action_type == "swipe":
        direction = action.get("direction", "unknown")
        return f"滑动 {direction}"
    
    elif action_type == "type":
        text = action.get("text", "")
        return f"输入: \"{text[:30]}{'...' if len(text) > 30 else ''}\""
    
    elif action_type == "system_button":
        button = action.get("button", "unknown")
        return f"系统按钮: {button}"
    
    elif action_type == "open":
        app = action.get("text", "unknown")
        return f"打开应用: {app}"
    
    elif action_type == "wait":
        return "等待"
    
    elif action_type == "terminate":
        status = action.get("status", "unknown")
        return f"终止 ({status})"
    
    elif action_type == "answer":
        text = action.get("text", "")
        return f"回答: \"{text[:50]}{'...' if len(text) > 50 else ''}\""
    
    elif action_type == "ask_user":
        text = action.get("text", "")
        return f"询问用户: \"{text[:50]}{'...' if len(text) > 50 else ''}\""
    
    elif action_type == "mcp_call":
        name = action.get("name", "unknown")
        return f"MCP 调用: {name}"
    
    else:
        return f"{action_type}: {action}"


def draw_action_marker(
    image: Image.Image,
    action: Dict[str, Any],
    action_type: str
) -> Image.Image:
    """
    在截图上绘制动作标记
    
    Args:
        image: PIL Image
        action: 动作字典
        action_type: 动作类型
    
    Returns:
        标记后的 PIL Image
    """
    if action_type not in ["click", "long_press", "swipe"]:
        return image
    
    img = image.copy()
    draw = ImageDraw.Draw(img)
    img_width, img_height = img.size
    
    coords = action.get("coordinate")
    if not coords:
        return image
    
    # 计算绝对坐标
    x = int(coords[0] * img_width)
    y = int(coords[1] * img_height)
    
    if action_type == "click":
        # 绘制红色圆圈和十字
        radius = 15
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            outline='red', width=3
        )
        inner_radius = 5
        draw.ellipse(
            (x - inner_radius, y - inner_radius, x + inner_radius, y + inner_radius),
            fill='red'
        )
        # 十字线
        line_length = 25
        draw.line((x - line_length, y, x - radius - 3, y), fill='red', width=2)
        draw.line((x + radius + 3, y, x + line_length, y), fill='red', width=2)
        draw.line((x, y - line_length, x, y - radius - 3), fill='red', width=2)
        draw.line((x, y + radius + 3, x, y + line_length), fill='red', width=2)
    
    elif action_type == "long_press":
        # 绘制蓝色圆圈（双环）
        radius = 15
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            outline='blue', width=3
        )
        radius2 = 22
        draw.ellipse(
            (x - radius2, y - radius2, x + radius2, y + radius2),
            outline='blue', width=2
        )
    
    elif action_type == "swipe":
        # 绘制箭头
        direction = action.get("direction", "up")
        arrow_length = 40
        
        if direction == "up":
            end_x, end_y = x, y - arrow_length
        elif direction == "down":
            end_x, end_y = x, y + arrow_length
        elif direction == "left":
            end_x, end_y = x - arrow_length, y
        elif direction == "right":
            end_x, end_y = x + arrow_length, y
        else:
            end_x, end_y = x, y - arrow_length
        
        # 主线
        draw.line((x, y, end_x, end_y), fill='green', width=4)
        
        # 箭头头部
        draw.ellipse(
            (end_x - 6, end_y - 6, end_x + 6, end_y + 6),
            fill='green'
        )
        draw.ellipse(
            (x - 4, y - 4, x + 4, y + 4),
            fill='green', outline='white', width=1
        )
    
    return img


def trajectory_to_markdown(logs: List[Dict[str, Any]]) -> str:
    """
    将轨迹转换为 Markdown 格式
    
    Args:
        logs: 日志条目列表
    
    Returns:
        Markdown 字符串
    """
    lines = ["# 任务轨迹\n"]
    
    for log in logs:
        step_index = log.get("step_index", 0)
        thinking = log.get("thinking", "")
        action_type = log.get("action_type", "unknown")
        action = log.get("action", {})
        message = log.get("message", "")
        timestamp = log.get("timestamp", "")
        
        lines.append(f"## 步骤 {step_index}")
        lines.append(f"*时间: {timestamp}*\n")
        
        if thinking:
            lines.append(f"**思考**: {thinking}\n")
        
        action_text = format_action(action_type, action)
        lines.append(f"**动作**: {action_text}\n")
        lines.append(f"**结果**: {message}\n")
        lines.append("---\n")
    
    return "\n".join(lines)
