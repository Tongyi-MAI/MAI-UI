#!/usr/bin/env python3
"""
启动 MAI-UI Web UI
"""

import os
import sys
import subprocess


def check_dependencies():
    """检查依赖是否安装"""
    print("检查依赖...")
    
    try:
        import gradio as gr
        print("  ✓ Gradio 已安装")
    except ImportError:
        print("  ✗ Gradio 未安装，请运行: pip install gradio>=4.0.0")
        return False

    try:
        import PIL
        print("  ✓ Pillow 已安装")
    except ImportError:
        print("  ✗ Pillow 未安装，请运行: pip install Pillow")
        return False

    try:
        from openai import OpenAI
        print("  ✓ OpenAI 已安装")
    except ImportError:
        print("  ✗ OpenAI 未安装，请运行: pip install openai")
        return False

    try:
        import yaml
        print("  ✓ PyYAML 已安装")
    except ImportError:
        print("  ✗ PyYAML 未安装，请运行: pip install pyyaml")
        return False

    return True


def check_adb():
    """检查ADB连接"""
    print("\n检查 ADB...")
    try:
        result = subprocess.run(["adb", "version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("  ✓ ADB 已安装")
            
            # 检查设备连接
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            lines = result.stdout.strip().split('\n')[1:]
            devices = [l.split('\t')[0] for l in lines if '\tdevice' in l]
            if devices:
                print(f"  ✓ 已连接设备: {', '.join(devices)}")
            else:
                print("  ⚠ 未检测到已连接的设备")
            return True
        else:
            print("  ⚠ ADB 未正确安装")
            return False
    except FileNotFoundError:
        print("  ⚠ ADB 未找到，请确保 ADB 已安装并添加到系统 PATH")
        return False
    except subprocess.TimeoutExpired:
        print("  ⚠ ADB 命令超时")
        return False
    except Exception as e:
        print(f"  ⚠ ADB 检查失败: {e}")
        return False


def kill_port(port):
    """尝试清理占用端口的进程 (Windows)"""
    if os.name != 'nt':
        return
    
    try:
        cmd_find = f"netstat -ano | findstr :{port}"
        result = subprocess.run(cmd_find, shell=True, capture_output=True, text=True)
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        if int(pid) != os.getpid():
                            print(f"  发现占用端口 {port} 的进程 PID: {pid}，正在终止...")
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"  清理端口时出错: {e}")


def main():
    print("=" * 50)
    print("       MAI-UI Web UI 启动器")
    print("=" * 50)
    print()

    # 检查依赖
    if not check_dependencies():
        print("\n请先安装缺失的依赖后再启动")
        sys.exit(1)

    # 检查 ADB（非强制）
    check_adb()

    # 检查 web_ui 目录
    web_ui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui")
    if not os.path.exists(web_ui_dir):
        print(f"\n✗ web_ui 目录不存在: {web_ui_dir}")
        sys.exit(1)

    # 将 web_ui 和 src 目录添加到 Python 路径
    sys.path.insert(0, web_ui_dir)
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
    if os.path.exists(src_dir):
        sys.path.insert(0, src_dir)

    # 端口配置
    target_port = 8868
    print(f"\n检查端口 {target_port}...")
    kill_port(target_port)

    # 启动 Gradio
    print("\n正在启动 Web 界面...")
    try:
        from app import create_ui
        
        demo, css, head = create_ui()
        
        print(f"\n{'=' * 50}")
        print(f"  访问地址: http://localhost:{target_port}")
        print(f"{'=' * 50}\n")
        
        demo.launch(
            server_name="0.0.0.0",
            server_port=target_port,
            share=False,
            inbrowser=True,
            show_error=True,
            quiet=False,
            css=css,
            head=head,
            allowed_paths=["d:\\maigui\\MAI-UI\\logs"]
        )
    except ImportError as e:
        print(f"\n✗ 导入失败: {e}")
        print("请确保 web_ui/app.py 存在且正确")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
