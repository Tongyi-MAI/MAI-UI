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
    image_to_base64, long_side_resize, draw_action_marker, export_trajectory_to_pdf
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

        // 自动滚动到最新内容（改进版）
        var userScrolling = false;
        var scrollTimeout = null;
        
        function setupScrollTracking() {
            // 轨迹窗口滚动检测
            var trajContainers = document.querySelectorAll('.trajectory-chatbot [data-testid="bot"], .trajectory-chatbot .bubble-wrap, .trajectory-chatbot [class*="message"]');
            trajContainers.forEach(function(el) {
                el.addEventListener('scroll', function() {
                    userScrolling = true;
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(function() { userScrolling = false; }, 3000);
                });
            });
        }
        
        setTimeout(setupScrollTracking, 2000);
        
        setInterval(function() {
            // 日志窗口自动滚动
            let logEl = document.querySelector('#log-window');
            let taskEnded = false;
            if (logEl && logEl.tagName === 'TEXTAREA') {
                taskEnded = logEl.value.includes('任务完成') || logEl.value.includes('⚪ 就绪') || logEl.value.includes('已停止');
                if (!taskEnded) {
                    logEl.scrollTop = logEl.scrollHeight;
                }
            }

            // 轨迹窗口自动滚动（改进选择器）
            if (!userScrolling && !taskEnded) {
                // 尝试多种可能的滚动容器
                var scrollTargets = [
                    '.trajectory-chatbot > div > div',
                    '.trajectory-chatbot [data-testid="bot"]',
                    '.trajectory-chatbot .bubble-wrap',
                    '.trajectory-chatbot > div'
                ];
                
                for (var i = 0; i < scrollTargets.length; i++) {
                    var el = document.querySelector(scrollTargets[i]);
                    if (el && el.scrollHeight > el.clientHeight) {
                        el.scrollTop = el.scrollHeight;
                        break;
                    }
                }
            }
        }, 200);
        
        // PDF 自动下载触发
        var lastPdfLink = null;
        setInterval(function() {
            // 查找 gr.File 组件中的下载链接
            var fileComponents = document.querySelectorAll('[data-testid="file"] a[download], .file-preview a[download], [class*="file"] a[href*=".pdf"]');
            fileComponents.forEach(function(link) {
                if (link.href && link.href.includes('.pdf') && link.href !== lastPdfLink) {
                    lastPdfLink = link.href;
                    // 自动触发下载
                    console.log('[MAI-UI] Auto-downloading PDF:', link.href);
                    link.click();
                }
            });
        }, 500);
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
                            enable_tcpip_btn = gr.Button("📡 启用TCP/IP", size="sm")
                        
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
                    return_to_desktop_chk = gr.Checkbox(label="🏠 执行前返回桌面", value=True, info="每次新任务开始时先返回桌面")
                    
                    user_input = gr.Textbox(
                        label="任务指令",
                        placeholder="输入任务指令...(Ctrl+Enter 提交)",
                        lines=3,
                        max_lines=5,
                        elem_id="user-input-box"
                    )
                    
                    with gr.Row():
                        submit_btn = gr.Button("▶ 执行/回复", variant="primary", scale=2, elem_id="submit-btn")
                        step_btn = gr.Button("⏭ 单步", scale=1)
                        pause_btn = gr.Button("⏸ 暂停", scale=1)
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
                        check_model_btn = gr.Button("🔍 检测连接", size="sm", scale=1)
                        model_status = gr.Textbox(
                            label="状态",
                            value="",
                            interactive=False,
                            scale=3
                        )
                    
                    with gr.Row():
                        device_dd = gr.Dropdown(label="当前设备", choices=[], value=None, scale=3)
                        refresh_dev_btn = gr.Button("🔄", scale=1)
                    
                    max_steps_slider = gr.Slider(
                        label="最大步数",
                        minimum=10,
                        maximum=200,
                        value=50,
                        step=10,
                        info="任务执行的最大步数限制"
                    )
                
                # 4. 实用工具
                with gr.Accordion("🛠 实用工具", open=False):
                    scrcpy_btn = gr.Button("🖥️ 启动屏幕镜像 (scrcpy)", variant="secondary")
                    scrcpy_status = gr.Textbox(label="状态", interactive=False, lines=1)

                    list_apps_btn = gr.Button("📲 获取应用列表", size="sm")
                    app_list_output = gr.Textbox(label="应用列表", lines=3, interactive=False)
                    
                    # 应用映射管理 (移植自 gelab-zero)
                    gr.Markdown("---")
                    gr.Markdown("#### 📦 应用映射管理")
                    
                    with gr.Row():
                        scan_apps_btn = gr.Button("🔍 扫描应用", variant="primary", size="sm")
                        deep_scan_chk = gr.Checkbox(label="深度扫描", value=True, scale=0)
                    scan_status = gr.Textbox(label="扫描状态", interactive=False, lines=2)
                    
                    # 应用映射编辑器
                    with gr.Accordion("📝 应用映射编辑器", open=False):
                        with gr.Tabs():
                            # Tab 1: 映射表预览
                            with gr.TabItem("📋 列表"):
                                with gr.Row():
                                    refresh_df_btn = gr.Button("🔄 刷新", size="sm")
                                    stats_btn = gr.Button("📊 统计", size="sm")
                                mapping_df = gr.Dataframe(
                                    label="应用名称 -> 包名映射",
                                    headers=["应用名", "包名"],
                                    datatype=["str", "str"],
                                    interactive=False,
                                    row_count=(10, "dynamic")
                                )
                                mapping_stats_txt = gr.Textbox(
                                    label="统计信息",
                                    value="",
                                    interactive=False,
                                    lines=2
                                )
                            
                            # Tab 2: 包名搜索
                            with gr.TabItem("🔎 搜索"):
                                search_input = gr.Textbox(
                                    label="应用名称",
                                    placeholder="输入应用名 (如: 微信)",
                                    lines=1
                                )
                                search_btn = gr.Button("🔎 查找包名", size="sm")
                                search_result = gr.Textbox(
                                    label="查找结果",
                                    lines=4,
                                    interactive=False
                                )
                            
                            # Tab 3: YAML 编辑器
                            with gr.TabItem("✏️ 编辑"):
                                mapping_textbox = gr.Textbox(
                                    label="应用名称 -> 包名映射 (YAML格式)",
                                    lines=10,
                                    placeholder="微信: com.tencent.mm\n抖音: com.ss.android.ugc.aweme\n# 注释行以 # 开头",
                                    interactive=True
                                )
                                with gr.Row():
                                    load_mapping_btn = gr.Button("📥 加载", size="sm")
                                    save_mapping_btn = gr.Button("💾 保存", size="sm", variant="primary")
                                    refresh_mapping_btn = gr.Button("🔄 刷新", size="sm")
                                mapping_status = gr.Textbox(label="操作状态", lines=1, interactive=False)
                            
                            # Tab 4: 批量导入
                            with gr.TabItem("📥 导入"):
                                gr.Markdown("**格式**: 应用名:包名 (一行一个)")
                                import_text = gr.Textbox(
                                    label="批量导入",
                                    placeholder="微信:com.tencent.mm\n抖音:com.ss.android.ugc.aweme",
                                    lines=6
                                )
                                import_btn = gr.Button("📥 导入", size="sm", variant="primary")
                                import_result = gr.Textbox(
                                    label="导入结果",
                                    lines=3,
                                    interactive=False
                                )
            
            # ========== 右栏：可视化 ==========
            with gr.Column(scale=2, min_width=600):
                with gr.Row():
                    # 轨迹显示
                    with gr.Column(scale=1):
                        gr.Markdown("### 📱 任务轨迹")
                        trajectory_output = gr.Chatbot(
                            label="轨迹回放",
                            height=660,
                            show_label=False,
                            elem_classes=["trajectory-chatbot"]
                        )
                        with gr.Row():
                            export_pdf_btn = gr.Button("📄 导出 PDF", size="sm")
                            export_file = gr.File(label="下载", visible=False)
                    
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
                            copy_log_btn = gr.Button("📋 复制", size="sm")
        
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
        
        # TCP/IP 启用（需要 USB 连接时使用）
        def enable_tcpip_handler():
            """启用 TCP/IP 模式 (adb tcpip 5555)"""
            import subprocess
            try:
                result = subprocess.run(
                    ["adb", "tcpip", "5555"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return "✅ TCP/IP 模式已启用 (端口 5555)\n现在可以拔掉 USB 并用 IP 连接"
                else:
                    return f"❌ 启用失败: {result.stderr.strip()[:50]}"
            except Exception as e:
                return f"❌ 错误: {str(e)[:50]}"
        
        enable_tcpip_btn.click(enable_tcpip_handler, outputs=[wireless_status])
        
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
        
        # 加载轨迹 (带任务信息头)
        def load_trajectory(session_id):
            if not session_id:
                return []
            logs = load_session_logs(session_id)
            # 从第一条日志尝试获取指令
            task_instruction = None
            if logs:
                first_log = logs[0]
                task_instruction = first_log.get("instruction", None)
            messages = logs_to_chatbot_messages(logs, task_instruction=task_instruction)
            return messages
        
        session_dropdown.change(load_trajectory, inputs=[session_dropdown], outputs=[trajectory_output])
        
        # PDF 导出
        def export_pdf_handler(session_id):
            if not session_id:
                return gr.update(value=None, visible=False)
            pdf_path = export_trajectory_to_pdf(session_id)
            if pdf_path:
                return gr.update(value=pdf_path, visible=True)
            else:
                return gr.update(value=None, visible=False)
        
        export_pdf_btn.click(export_pdf_handler, inputs=[session_dropdown], outputs=[export_file])
        
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
        
        # 模型连接检查
        def check_model_connection(base_url, model_name, api_key):
            """检查模型连接状态"""
            if not base_url:
                return "⚠️ 请先填写 Base URL"
            if not model_name:
                return "⚠️ 请先填写模型名称"
            
            import requests
            base = base_url.rstrip('/')
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # 判断是本地还是在线
            is_local = "localhost" in base or "127.0.0.1" in base or "0.0.0.0" in base
            api_type = "本地" if is_local else "在线"
            
            # 直接测试 /chat/completions 接口
            try:
                url = base + '/chat/completions'
                test_payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
                response = requests.post(url, json=test_payload, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    return f"✅ 连接成功 ({api_type})\n📍 {base}\n🤖 {model_name}"
                elif response.status_code == 404:
                    return f"❌ 模型 {model_name} 不存在"
                else:
                    try:
                        err_msg = response.json().get('error', {}).get('message', response.text[:80])
                    except:
                        err_msg = response.text[:80]
                    return f"❌ 请求失败 ({response.status_code})\n{err_msg}"
            except requests.exceptions.ConnectionError:
                return f"❌ 无法连接 {base}"
            except requests.exceptions.Timeout:
                return f"❌ 连接超时"
            except Exception as e:
                return f"❌ {str(e)[:60]}"
        
        check_model_btn.click(
            fn=check_model_connection,
            inputs=[base_url_input, model_name_input, api_key_input],
            outputs=[model_status]
        )
        
        # 暂停任务 (gelab-zero风格：返回runner的状态消息)
        def pause_task() -> str:
            global runner
            if runner and runner.is_running:
                return runner.pause()
            return "⚪ 没有运行中的任务"
        
        pause_btn.click(pause_task, outputs=task_status)
        
        # 启动 scrcpy
        scrcpy_btn.click(start_scrcpy, outputs=[scrcpy_status])

        # 获取应用列表
        list_apps_btn.click(get_available_apps, outputs=app_list_output)
        
        # 清空日志
        def clear_logs():
            return ""
        
        clear_log_btn.click(clear_logs, outputs=log_output)
        
        # 复制日志到剪贴板 (使用 JS)
        copy_log_btn.click(
            fn=None, inputs=[], outputs=[],
            js="""() => {
                let el = document.querySelector('#log-window textarea');
                if (el && el.value) {
                    navigator.clipboard.writeText(el.value).then(() => alert('已复制到剪贴板')).catch(() => alert('复制失败'));
                } else {
                    alert('没有日志可复制');
                }
            }"""
        )
        
        # ========== 核心：智能执行 (gelab-zero风格) ==========
        
        def start_task(instruction, base_url, model_name, device, auto_reply, return_to_desktop, max_steps):
            """
            智能执行 - 根据当前状态决定行为 (gelab-zero风格)
            - 情况1: 处于暂停状态 → 作为注入指令恢复
            - 情况2: 无输入且运行中 → 返回当前状态
            - 情况3: 运行中且等待输入 → 作为回复发送
            - 情况4: 运行中 → 提示先暂停/停止
            - 情况5: 空闲 → 启动新任务
            """
            global runner
            
            # 情况1: 处于暂停状态 → 作为注入指令恢复
            if runner and runner.is_paused:
                paused_session = runner.paused_session_id or runner.session_id
                if not paused_session:
                    runner.clear_pause_state()
                    yield "⚠️ 没有可继续的会话", [], ""
                    return
                
                # 恢复并注入
                injection = instruction.strip() if instruction.strip() else None
                runner.resume(injection=injection)
                runner.auto_reply_enabled = auto_reply
                session_id = paused_session
                log_text = f"[{session_id}] 任务已恢复"
                if injection:
                    log_text += f",注入指令: {injection}"
                log_text += "\n"
                
                yield "🟢 运行中", [], log_text
                
                # 继续执行流式循环
                for result in runner.auto_run(max_steps=int(max_steps), step_delay=1.5):
                    if runner.should_stop or not runner.is_running:
                        log_text += "\n\n⏹ 任务已停止"
                        trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                        yield "⏹ 已停止", trajectory, log_text
                        return
                    
                    log_text += f"\n步骤 {result.step_index}: {result.action_type} - {result.message}"
                    trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                    
                    if result.action_type == "terminate":
                        log_text += f"\n\n✅ 任务完成: {result.action.get('status', 'unknown')}"
                        yield runner.get_status(), trajectory, log_text
                        return
                    
                    if result.action_type == "ask_user":
                        log_text += f"\n\n🟡 等待用户输入..."
                        yield "🟡 等待输入", trajectory, log_text
                        return
                    
                    yield runner.get_status(), trajectory, log_text
                    
                    if runner.should_stop or not runner.is_running:
                        log_text += "\n\n⏹ 任务已停止"
                        trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                        yield "⏹ 已停止", trajectory, log_text
                        return
                
                # 最终状态
                trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                yield runner.get_status(), trajectory, log_text
                return
            
            # 情况2: 无输入时仅返回当前状态
            if not instruction.strip() and runner and runner.is_running:
                yield runner.get_status(), [], ""
                return
            
            # 情况3: 任务运行中且等待输入 → 作为回复发送
            if runner and runner.is_running and runner.waiting_for_input:
                runner.provide_user_input(instruction.strip())
                yield runner.get_status(), [], f"[回复] {instruction.strip()}\n"
                return
            
            # 情况4: 任务运行中 → 提示先暂停/停止
            if runner and runner.is_running:
                yield "⚠️ 任务运行中，请先暂停或停止", [], ""
                return
            
            # 情况5: 空闲/无任务 → 启动新任务
            if not instruction.strip():
                yield "⚠️ 请输入任务指令", [], ""
                return
            
            try:
                # 创建新任务
                runner = reset_runner(
                    llm_base_url=base_url,
                    model_name=model_name,
                    device_id=device if device else None,
                    return_to_desktop_on_start=return_to_desktop
                )
                runner.auto_reply_enabled = auto_reply
                session_id = runner.start_task(instruction)
                log_text = f"[{session_id}] 任务已启动: {instruction}\n"
                
                # 立即返回初始状态
                yield "🟢 运行中", [], log_text
                
                # 流式执行
                for result in runner.auto_run(max_steps=int(max_steps), step_delay=1.5):
                    if runner.should_stop or not runner.is_running:
                        log_text += "\n\n⏹ 任务已停止"
                        trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                        yield "⏹ 已停止", trajectory, log_text
                        return
                    
                    log_text += f"\n步骤 {result.step_index}: {result.action_type} - {result.message}"
                    trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                    
                    if result.action_type == "terminate":
                        log_text += f"\n\n✅ 任务完成: {result.action.get('status', 'unknown')}"
                        yield runner.get_status(), trajectory, log_text
                        return
                    
                    if result.action_type == "ask_user":
                        log_text += f"\n\n🟡 等待用户输入..."
                        yield "🟡 等待输入", trajectory, log_text
                        return
                    
                    yield runner.get_status(), trajectory, log_text
                    
                    if runner.should_stop or not runner.is_running:
                        log_text += "\n\n⏹ 任务已停止"
                        trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                        yield "⏹ 已停止", trajectory, log_text
                        return
                
                # 最终状态
                trajectory = logs_to_chatbot_messages(load_session_logs(session_id))
                yield runner.get_status(), trajectory, log_text
                
            except Exception as e:
                yield f"🔴 错误: {e}", [], str(e)
        
        submit_btn.click(
            start_task,
            inputs=[user_input, base_url_input, model_name_input, device_dd, auto_reply_chk, return_to_desktop_chk, max_steps_slider],
            outputs=[task_status, trajectory_output, log_output]
        )
        
        # 单步执行
        def step_task(instruction, base_url, model_name, device, auto_reply, return_to_desktop, current_logs):
            global runner
            
            if runner is None or not runner.is_running:
                # 初始化新任务
                if not instruction.strip():
                    return "⚠️ 请输入任务指令", [], ""
                
                runner = reset_runner(
                    llm_base_url=base_url,
                    model_name=model_name,
                    device_id=device if device else None,
                    return_to_desktop_on_start=return_to_desktop
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
            inputs=[user_input, base_url_input, model_name_input, device_dd, auto_reply_chk, return_to_desktop_chk, log_output],
            outputs=[task_status, trajectory_output, log_output]
        )
        
        # 停止任务 (确保清除暂停状态)
        def stop_task():
            global runner
            if runner:
                runner.stop()
                runner.clear_pause_state()  # 确保彻底清除暂停状态
                return "⏹ 已停止"
            return "⚪ 就绪"
        
        stop_btn.click(stop_task, outputs=task_status)
        
        # === gr.Timer 实时轮询 (gelab-zero 风格) ===
        timer = gr.Timer(2.0)  # 2秒刷新一次
        
        def poll_updates():
            """轮询更新 session 列表"""
            global runner
            sessions = get_available_sessions()
            # 如果有正在运行的任务，自动选择当前 session
            current_session = runner.session_id if runner and runner.is_running else None
            if current_session and current_session in sessions:
                return gr.Dropdown(choices=sessions, value=current_session)
            return gr.Dropdown(choices=sessions, value=sessions[0] if sessions else None)
        
        timer.tick(fn=poll_updates, outputs=[session_dropdown])
        
        # === 应用映射功能事件绑定 (移植自 gelab-zero) ===
        from web_ui.package_map_ui import (
            scan_apps_with_progress,
            get_package_mapping_dataframe,
            search_package_by_name,
            batch_import_mappings,
            get_mapping_statistics,
            load_user_mapping_yaml,
            save_user_mapping_yaml
        )
        from web_ui.package_scanner import load_user_package_map, save_user_package_map, get_user_package_map_path
        
        def scan_apps_to_mapping(deep_scan):
            """扫描应用并更新映射"""
            try:
                import subprocess
                result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
                device_lines = [l for l in result.stdout.split('\n')[1:] if '\tdevice' in l]
                if not device_lines:
                    return "❌ 没有检测到已连接的设备"
                
                device_id = device_lines[0].split('\t')[0]
                logs, status, count = scan_apps_with_progress(device_id=device_id, deep_scan=deep_scan)
                return status
            except Exception as e:
                return f"❌ 扫描失败: {str(e)[:100]}"
        
        scan_apps_btn.click(fn=scan_apps_to_mapping, inputs=[deep_scan_chk], outputs=[scan_status])
        
        # DataFrame 刷新
        refresh_df_btn.click(fn=lambda: get_package_mapping_dataframe(), outputs=[mapping_df])
        
        # 统计信息
        def get_stats_text():
            stats = get_mapping_statistics()
            return (
                f"默认映射: {stats['default_count']} 条\n"
                f"用户映射: {stats['user_count']} 条 (独有: {stats['user_only_count']})"
            )
        
        stats_btn.click(fn=get_stats_text, outputs=[mapping_stats_txt])
        
        # 包名搜索
        search_btn.click(fn=search_package_by_name, inputs=[search_input], outputs=[search_result])
        
        # YAML 编辑器事件
        def load_mapping_yaml():
            """加载 YAML 映射到编辑器"""
            try:
                mapping = load_user_package_map()
                if not mapping:
                    return "# 映射表为空，请先扫描或手动添加\n# 格式: 应用名称: 包名", f"ℹ️ 映射文件: {get_user_package_map_path()}"
                
                lines = ["# 用户自定义应用映射（可编辑）", ""]
                for name, pkg in sorted(mapping.items()):
                    lines.append(f"{name}: {pkg}")
                return "\n".join(lines), f"✅ 已加载 {len(mapping)} 条映射"
            except Exception as e:
                return f"# 加载失败: {e}", f"❌ {str(e)[:50]}"
        
        load_mapping_btn.click(fn=load_mapping_yaml, outputs=[mapping_textbox, mapping_status])
        refresh_mapping_btn.click(fn=load_mapping_yaml, outputs=[mapping_textbox, mapping_status])
        
        def save_mapping_yaml(yaml_content):
            """保存编辑器内容到 YAML"""
            try:
                mapping = {}
                for line in yaml_content.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if ':' in line:
                        parts = line.split(':', 1)
                        key = parts[0].strip().strip('"').strip("'")
                        value = parts[1].strip().strip('"').strip("'")
                        if key and value:
                            mapping[key] = value
                
                if not mapping:
                    return "⚠️ 没有有效的映射条目"
                
                success = save_user_package_map(mapping)
                if success:
                    return f"✅ 已保存 {len(mapping)} 条映射"
                else:
                    return "❌ 保存失败"
            except Exception as e:
                return f"❌ 保存出错: {str(e)[:50]}"
        
        save_mapping_btn.click(fn=save_mapping_yaml, inputs=[mapping_textbox], outputs=[mapping_status])
        
        # 批量导入
        import_btn.click(fn=batch_import_mappings, inputs=[import_text], outputs=[import_result])
    
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
