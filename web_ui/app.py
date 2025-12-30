"""
MAI-UI Gradio Web UI
提供用户友好的 Web 界面来使用 MAI-UI 进行 Android 设备自动化操作
集成轨迹可视化功能
"""

import gradio as gr
import os
import sys
import time
import threading
import subprocess
import yaml
from typing import Optional, Tuple, List, Dict, Any

# 添加必要路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
src_dir = os.path.join(os.path.dirname(current_dir), "src")
if os.path.exists(src_dir):
    sys.path.insert(0, src_dir)

from adb_utils import (
    get_adb_devices, connect_wireless_device, disconnect_wireless_device,
    check_adb_connection, restart_adb, get_available_apps
)
from trajectory_utils import (
    get_available_sessions, load_session_logs, logs_to_chatbot_messages,
    image_to_base64, long_side_resize, draw_action_marker
)
from agent_runner import AgentRunner, get_runner, reset_runner


# 全局 Runner
runner: Optional[AgentRunner] = None


def start_scrcpy():
    """启动 scrcpy 屏幕镜像"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        scrcpy_path = os.path.join(project_dir, "scrcpy-win64-v3.3.3", "scrcpy.exe")

        if not os.path.exists(scrcpy_path):
            return f"未找到 scrcpy.exe: {scrcpy_path}"

        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, encoding='utf-8')
        devices = [line.split('\t')[0] for line in result.stdout.split('\n')[1:] if '\tdevice' in line]

        if not devices:
            return "没有检测到已连接的设备"

        scrcpy_cmd = [scrcpy_path, '--no-audio']
        if len(devices) > 1:
            scrcpy_cmd.extend(['-s', devices[0]])

        def run_scrcpy():
            try:
                if os.name == 'nt':
                    subprocess.Popen(scrcpy_cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    subprocess.Popen(scrcpy_cmd)
            except Exception as e:
                print(f"[ERROR] 启动 scrcpy 失败: {e}")

        threading.Thread(target=run_scrcpy, daemon=True).start()
        time.sleep(0.5)
        return f"✅ scrcpy 已启动 (设备: {devices[0]})"

    except Exception as e:
        return f"启动失败: {str(e)}"


def create_ui():
    """创建 Gradio UI"""
    
    # 自定义 CSS
    custom_css = """
    /* 轨迹图片样式 */
    .trajectory-chatbot img {
        max-width: 320px !important;
        max-height: 560px !important;
        width: auto !important;
        height: auto !important;
        object-fit: contain !important;
        cursor: pointer;
        transition: opacity 0.2s;
        border-radius: 8px;
    }
    .trajectory-chatbot img:hover {
        opacity: 0.85;
    }
    .trajectory-chatbot .message {
        max-width: 100% !important;
    }
    
    /* 命令输入框 */
    #user-input-box textarea {
        overflow-y: auto !important;
        max-height: 120px !important;
    }
    
    /* 截图预览 */
    .screenshot-preview img {
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    """
    
    # Lightbox 脚本
    lightbox_head = """
    <style>
    #mai-lightbox {
        display: none;
        position: fixed;
        z-index: 999999;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.92);
        justify-content: center;
        align-items: center;
        flex-direction: column;
        cursor: zoom-out;
    }
    #mai-lightbox.visible {
        display: flex !important;
    }
    #mai-lightbox-img {
        max-width: 95%;
        max-height: 85%;
        object-fit: contain;
        border: 3px solid #fff;
        border-radius: 10px;
        box-shadow: 0 5px 40px rgba(0,0,0,0.6);
    }
    #mai-lightbox-controls {
        margin-top: 20px;
        display: flex;
        gap: 20px;
    }
    #mai-lightbox-controls button {
        padding: 12px 28px;
        font-size: 15px;
        border: none;
        border-radius: 25px;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.15s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    #mai-lightbox-controls button:hover { transform: scale(1.05); }
    #mai-lb-download { background: linear-gradient(135deg, #4CAF50, #2E7D32); color: white; }
    #mai-lb-close { background: linear-gradient(135deg, #f44336, #c62828); color: white; }
    
    .trajectory-chatbot img,
    [class*="chatbot"] img {
        cursor: zoom-in !important;
    }
    </style>
    <script>
    (function() {
        'use strict';
        console.log('[MAI-UI] Lightbox loading...');
        
        var lightbox = null, lightboxImg = null;
        
        function createLightbox() {
            if (document.getElementById('mai-lightbox')) {
                lightbox = document.getElementById('mai-lightbox');
                lightboxImg = document.getElementById('mai-lightbox-img');
                return;
            }
            
            lightbox = document.createElement('div');
            lightbox.id = 'mai-lightbox';
            lightbox.innerHTML = '<img id="mai-lightbox-img" src="" alt=""><div id="mai-lightbox-controls"><button id="mai-lb-download">📥 下载</button><button id="mai-lb-close">✕ 关闭</button></div>';
            document.body.appendChild(lightbox);
            
            lightboxImg = document.getElementById('mai-lightbox-img');
            
            lightbox.addEventListener('click', function(e) {
                if (e.target === lightbox || e.target.id === 'mai-lb-close') {
                    lightbox.classList.remove('visible');
                }
            });
            
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && lightbox.classList.contains('visible')) {
                    lightbox.classList.remove('visible');
                }
            });
            
            document.getElementById('mai-lb-download').addEventListener('click', function(e) {
                e.stopPropagation();
                if (!lightboxImg.src) return;
                var a = document.createElement('a');
                a.href = lightboxImg.src;
                a.download = 'mai_ui_' + Date.now() + '.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
        }
        
        function openLightbox(imgSrc) {
            createLightbox();
            lightboxImg.src = imgSrc;
            lightbox.classList.add('visible');
        }
        
        function isChatbotImage(el) {
            if (!el || el.tagName !== 'IMG') return false;
            var parent = el.closest('.trajectory-chatbot') || 
                         el.closest('[class*="chatbot"]') ||
                         el.closest('.message');
            return !!parent;
        }
        
        document.addEventListener('click', function(e) {
            if (isChatbotImage(e.target)) {
                e.preventDefault();
                e.stopPropagation();
                openLightbox(e.target.src);
            }
        }, true);
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createLightbox);
        } else {
            createLightbox();
        }
        
        // Ctrl+Enter 提交
        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                var inputBox = document.querySelector('#user-input-box textarea');
                var submitBtn = document.querySelector('#submit-btn');
                if (inputBox && submitBtn && document.activeElement === inputBox) {
                    e.preventDefault();
                    submitBtn.click();
                }
            }
        });

        // 自动滚动到最新内容
        setInterval(function() {
            // 日志窗口自动滚动
            let logEl = document.querySelector('#log-window');
            if (logEl && logEl.tagName === 'TEXTAREA') {
                let taskEnded = logEl.value.includes('任务完成') || logEl.value.includes('⚪ 就绪');
                if (!taskEnded) {
                    logEl.scrollTop = logEl.scrollHeight;
                }
            }

            // 轨迹窗口自动滚动
            let trajEl = document.querySelector('.trajectory-chatbot');
            if (trajEl) {
                let scrollContainer = trajEl.querySelector('[class*="chatbot"]') || trajEl;
                let logEl = document.querySelector('#log-window');
                let taskEnded = false;
                if (logEl && logEl.value) {
                    taskEnded = logEl.value.includes('任务完成') || logEl.value.includes('⚪ 就绪');
                }

                if (!taskEnded) {
                    scrollContainer.scrollTop = scrollContainer.scrollHeight;
                }
            }
        }, 100);
    })();
    </script>
    """
    
    # 加载配置
    config_path = os.path.join(os.path.dirname(current_dir), "model_config.yaml")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            full_config = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"[WARNING] 加载配置失败: {e}")
        full_config = {}
    
    # 准备 Provider 选项
    provider_choices = []
    for key, val in full_config.items():
        if key != "mcp_tools" and isinstance(val, dict):
            display = val.get("display_name", key)
            provider_choices.append((display, key))
    provider_choices.append(("自定义", "custom"))
    
    default_prov = provider_choices[0][1] if provider_choices else "custom"
    default_cfg = full_config.get(default_prov, {})
    
    # 构建界面
    with gr.Blocks(title="MAI-UI Web Console") as demo:
        
        gr.Markdown("## 🤖 MAI-UI 控制台")
        
        with gr.Row():
            # ========== 左栏：控制面板 ==========
            with gr.Column(scale=1, min_width=350):
                
                # 1. 设备管理
                with gr.Group():
                    gr.Markdown("### 📱 设备管理")
                    
                    device_status = gr.Textbox(
                        label="设备状态",
                        value="❓ 未检查",
                        interactive=False,
                        lines=3
                    )
                    with gr.Row():
                        check_status_btn = gr.Button("检查", size="sm", scale=1)
                        list_devices_btn = gr.Button("列表", size="sm", scale=1)
                        restart_adb_btn = gr.Button("重启ADB", size="sm", scale=1)
                    
                    with gr.Accordion("📶 无线调试", open=False):
                        with gr.Row():
                            wireless_ip = gr.Textbox(label="IP", placeholder="192.168.1.x", scale=3)
                            wireless_port = gr.Textbox(label="端口", value="5555", scale=1)
                        
                        with gr.Row():
                            connect_btn = gr.Button("🔗 连接", variant="primary", size="sm")
                            disconnect_btn = gr.Button("✂️ 断开", size="sm")
                        
                        wireless_status = gr.Textbox(label="状态", interactive=False, lines=1)
                
                # 2. 任务监控
                with gr.Group():
                    gr.Markdown("### 📊 任务监控")
                    
                    with gr.Row():
                        session_dropdown = gr.Dropdown(
                            label="Session",
                            choices=[],
                            value=None,
                            scale=5,
                            allow_custom_value=True
                        )
                        refresh_sessions_btn = gr.Button("🔄", size="sm", scale=1)
                    
                    task_status = gr.Textbox(
                        label="任务状态",
                        value="⚪ 就绪",
                        interactive=False,
                        lines=1
                    )
                    
                    auto_reply_chk = gr.Checkbox(label="🤖 自动回复 (Auto-Reply)", value=False)
                    
                    user_input = gr.Textbox(
                        label="任务指令",
                        placeholder="输入任务指令...(Ctrl+Enter 提交)",
                        lines=3,
                        max_lines=5,
                        elem_id="user-input-box"
                    )
                    
                    with gr.Row():
                        submit_btn = gr.Button("▶ 执行", variant="primary", scale=2, elem_id="submit-btn")
                        step_btn = gr.Button("⏭ 单步", scale=1)
                        stop_btn = gr.Button("⏹ 停止", variant="stop", scale=1)
                
                # 3. 参数配置
                with gr.Accordion("⚙️ 参数配置", open=False):
                    provider_dd = gr.Dropdown(
                        label="模型提供商",
                        choices=provider_choices,
                        value=default_prov
                    )
                    
                    base_url_input = gr.Textbox(
                        label="Base URL",
                        value=default_cfg.get("api_base", "http://localhost:8000/v1"),
                        interactive=True
                    )
                    
                    api_key_input = gr.Textbox(
                        label="API Key",
                        type="password",
                        value=default_cfg.get("api_key", ""),
                        interactive=True
                    )
                    
                    model_name_input = gr.Textbox(
                        label="模型名称",
                        value=default_cfg.get("default_model", "MAI-UI-8B"),
                        interactive=True
                    )
                    
                    with gr.Row():
                        device_dd = gr.Dropdown(label="当前设备", choices=[], value=None, scale=3)
                        refresh_dev_btn = gr.Button("🔄", scale=1)
                
                # 4. 实用工具
                with gr.Accordion("🛠 实用工具", open=False):
                    scrcpy_btn = gr.Button("🖥️ 启动屏幕镜像 (scrcpy)", variant="secondary")
                    scrcpy_status = gr.Textbox(label="状态", interactive=False, lines=1)

                    list_apps_btn = gr.Button("📲 获取应用列表", size="sm")
                    app_list_output = gr.Textbox(label="应用列表", lines=3, interactive=False)
            
            # ========== 右栏：可视化 ==========
            with gr.Column(scale=2, min_width=600):
                with gr.Row():
                    # 轨迹显示
                    with gr.Column(scale=1):
                        gr.Markdown("### 📱 任务轨迹")
                        trajectory_output = gr.Chatbot(
                            label="轨迹回放",
                            height=700,
                            show_label=False,
                            elem_classes=["trajectory-chatbot"]
                        )
                    
                    # 实时日志
                    with gr.Column(scale=1):
                        gr.Markdown("### 📋 实时日志")
                        log_output = gr.Textbox(
                            label="日志输出",
                            value="",
                            lines=25,
                            max_lines=30,
                            interactive=False,
                            elem_id="log-window"
                        )
                        with gr.Row():
                            clear_log_btn = gr.Button("🗑 清空", size="sm")
        
        # ========== 事件绑定 ==========
        
        # 全局状态
        logs_state = gr.State([])
        
        # 检查设备状态
        def check_status_handler():
            success, info = check_adb_connection()
            return info
        
        check_status_btn.click(check_status_handler, outputs=device_status)
        
        # 列出设备
        def list_devices_handler():
            devices, info = get_adb_devices()
            return info
        
        list_devices_btn.click(list_devices_handler, outputs=device_status)
        
        # 重启 ADB
        def restart_adb_handler():
            success, msg = restart_adb()
            return msg
        
        restart_adb_btn.click(restart_adb_handler, outputs=device_status)
        
        # 无线连接
        def connect_wireless_handler(ip, port):
            if not ip.strip():
                return "", "请输入 IP 地址"
            success, message = connect_wireless_device(ip, port)
            devices, device_info = get_adb_devices()
            return device_info, message
        
        connect_btn.click(connect_wireless_handler, inputs=[wireless_ip, wireless_port], outputs=[device_status, wireless_status])
        
        # 无线断开
        def disconnect_wireless_handler():
            success, message = disconnect_wireless_device()
            devices, device_info = get_adb_devices()
            return device_info, message
        
        disconnect_btn.click(disconnect_wireless_handler, outputs=[device_status, wireless_status])
        
        # 刷新设备列表
        def refresh_devices():
            devices, _ = get_adb_devices()
            valid = [d for d in devices if d and not d.startswith("错误") and d != "未找到设备"]
            return gr.Dropdown(choices=valid, value=valid[0] if valid else None)
        
        refresh_dev_btn.click(refresh_devices, outputs=device_dd)
        demo.load(refresh_devices, outputs=device_dd)
        
        # 刷新 Session 列表
        def refresh_sessions():
            sessions = get_available_sessions()
            return gr.Dropdown(choices=sessions, value=sessions[0] if sessions else None)
        
        refresh_sessions_btn.click(refresh_sessions, outputs=session_dropdown)
        demo.load(refresh_sessions, outputs=session_dropdown)
        
        # 加载轨迹
        def load_trajectory(session_id):
            if not session_id:
                return []
            logs = load_session_logs(session_id)
            messages = logs_to_chatbot_messages(logs)
            return messages
        
        session_dropdown.change(load_trajectory, inputs=[session_dropdown], outputs=[trajectory_output])
        
        # Provider 变更
        def on_provider_change(provider):
            if provider == "custom":
                return gr.update(value=""), gr.update(value=""), gr.update(value="MAI-UI-8B")
            cfg = full_config.get(provider, {})
            return (
                gr.update(value=cfg.get("api_base", "")),
                gr.update(value=cfg.get("api_key", "")),
                gr.update(value=cfg.get("default_model", "MAI-UI-8B"))
            )
        
        provider_dd.change(on_provider_change, inputs=[provider_dd], outputs=[base_url_input, api_key_input, model_name_input])
        
        # 截图
        # 启动 scrcpy
        scrcpy_btn.click(start_scrcpy, outputs=[scrcpy_status])

        # 获取应用列表
        list_apps_btn.click(get_available_apps, outputs=app_list_output)
        
        # 清空日志
        def clear_logs():
            return ""
        
        clear_log_btn.click(clear_logs, outputs=log_output)
        
        # ========== 核心：任务执行 ==========
        
        def start_task(instruction, base_url, model_name, device, auto_reply):
            """
            执行任务 - 使用生成器实现实时流式更新
            """
            global runner
            
            if not instruction.strip():
                yield "⚠️ 请输入任务指令", [], ""
                return
            
            try:
                runner = reset_runner(
                    llm_base_url=base_url,
                    model_name=model_name,
                    device_id=device if device else None
                )
                runner.auto_reply_enabled = auto_reply
                
                session_id = runner.start_task(instruction)
                log_text = f"[{session_id}] 任务已启动: {instruction}\n"
                
                # 立即返回初始状态
                yield "🟢 运行中", [], log_text
                
                # 流式执行
                for result in runner.auto_run(max_steps=30, step_delay=1.5):
                    log_text += f"\n步骤 {result.step_index}: {result.action_type} - {result.message}"
                    
                    # 加载最新轨迹
                    trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                    
                    if result.action_type == "terminate":
                        log_text += f"\n\n✅ 任务完成: {result.action.get('status', 'unknown')}"
                        yield runner.get_status(), trajectory, log_text
                        return
                    
                    if result.action_type == "ask_user":
                        log_text += f"\n\n🟡 等待用户输入..."
                        yield "🟡 等待输入", trajectory, log_text
                        return
                    
                    # 每步都 yield，实现实时更新
                    yield runner.get_status(), trajectory, log_text
                
                # 最终状态
                trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                yield runner.get_status(), trajectory, log_text
                
            except Exception as e:
                yield f"🔴 错误: {e}", [], str(e)
        
        submit_btn.click(
            start_task,
            inputs=[user_input, base_url_input, model_name_input, device_dd, auto_reply_chk],
            outputs=[task_status, trajectory_output, log_output]
        )
        
        # 单步执行
        def step_task(instruction, base_url, model_name, device, auto_reply, current_logs):
            global runner
            
            if runner is None or not runner.is_running:
                # 初始化新任务
                if not instruction.strip():
                    return "⚠️ 请输入任务指令", [], ""
                
                runner = reset_runner(
                    llm_base_url=base_url,
                    model_name=model_name,
                    device_id=device if device else None
                )
                runner.auto_reply_enabled = auto_reply
                runner.start_task(instruction)
            else:
                # 即使是运行中，也更新一下开关状态
                runner.auto_reply_enabled = auto_reply
            
            # 执行单步
            result = runner.step()
            
            if result:
                log_text = current_logs + f"\n步骤 {result.step_index}: {result.action_type} - {result.message}"
                trajectory = logs_to_chatbot_messages(load_session_logs(runner.session_id))
                return runner.get_status(), trajectory, log_text
            else:
                return runner.get_status() if runner else "⚪ 就绪", [], current_logs
        
        step_btn.click(
            step_task,
            inputs=[user_input, base_url_input, model_name_input, device_dd, auto_reply_chk, log_output],
            outputs=[task_status, trajectory_output, log_output]
        )
        
        # 停止任务
        def stop_task():
            global runner
            if runner:
                runner.stop()
                return "⏹ 已停止"
            return "⚪ 就绪"
        
        stop_btn.click(stop_task, outputs=task_status)
    
    return demo, custom_css, lightbox_head


if __name__ == "__main__":
    demo, css, head = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=8866,
        share=False,
        inbrowser=True,
        css=css,
        head=head
    )
