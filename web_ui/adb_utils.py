"""
ADB 工具函数模块
提供 Android 设备连接、截图、操作等功能
"""

import subprocess
import re
import os
from io import BytesIO
from typing import Tuple, List, Optional, Union
from PIL import Image


# YADB 路径配置 (用于支持中文输入)
YADB_REMOTE_PATH = "/data/local/tmp/yadb"
YADB_LOCAL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "yadb")

def run_adb_command(
    command: List[str],
    timeout: int = 30,
    binary: bool = False,
    device_id: Optional[str] = None
) -> Tuple[Union[str, bytes], str, int]:
    """
    运行 ADB 命令
    
    Args:
        command: 命令参数列表
        timeout: 超时时间（秒）
        binary: 是否返回二进制输出
        device_id: 指定设备 ID
    
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    if device_id and device_id not in command:
        # 在 adb 后面插入 -s device_id
        if command and command[0] == "adb":
            command = ["adb", "-s", device_id] + command[1:]
    
    print(f"[ADB] {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=not binary,
            timeout=timeout,
            encoding=None if binary else 'utf-8',
            errors=None if binary else 'replace'
        )
        if result.returncode != 0:
            print(f"[ADB Error] Code: {result.returncode}, Stderr: {result.stderr[:200] if result.stderr else 'None'}")
        return result.stdout, result.stderr if not binary else result.stderr.decode('utf-8', errors='replace'), result.returncode
    except subprocess.TimeoutExpired:
        return "" if not binary else b"", "命令超时", -1
    except Exception as e:
        return "" if not binary else b"", str(e), -1


def get_adb_devices() -> Tuple[List[str], str]:
    """
    获取所有已连接的 ADB 设备
    
    Returns:
        Tuple of (device_id_list, status_message)
    """
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )
        devices = []
        device_details = []

        if result.returncode == 0:
            lines = result.stdout.split('\n')[1:]
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
                    device_type = "📶 无线" if ':' in device_id else "🔌 USB"
                    device_details.append(f"{device_type}: {device_id}")

        if not device_details:
            return [], "未找到设备"

        device_list = "\n".join(device_details)
        return devices, f"已连接设备 ({len(devices)}个):\n\n{device_list}\n\n默认设备: {devices[0]}"
    except Exception as e:
        return [], f"获取设备列表失败: {str(e)}"


def connect_wireless_device(ip_address: str, port: str = "5555") -> Tuple[bool, str]:
    """
    连接无线设备
    
    Args:
        ip_address: 设备 IP 地址
        port: 端口号，默认 5555
    
    Returns:
        Tuple of (success, message)
    """
    try:
        parts = ip_address.strip().split('.')
        if len(parts) != 4:
            return False, "无效的 IP 地址格式"

        connect_addr = f"{ip_address}:{port}"
        result = subprocess.run(
            ["adb", "connect", connect_addr],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=10
        )

        if result.returncode == 0:
            devices_result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            if connect_addr in devices_result.stdout and "device" in devices_result.stdout:
                return True, f"成功连接到无线设备: {connect_addr}"
            else:
                return False, "连接失败，请检查设备设置"
        else:
            return False, f"连接失败: {result.stderr.strip() if result.stderr else result.stdout.strip()}"

    except subprocess.TimeoutExpired:
        return False, "连接超时"
    except Exception as e:
        return False, f"连接出错: {str(e)}"


def disconnect_wireless_device(device_id: Optional[str] = None) -> Tuple[bool, str]:
    """
    断开无线设备
    
    Args:
        device_id: 可选，指定设备 ID
    
    Returns:
        Tuple of (success, message)
    """
    try:
        cmd = ["adb", "disconnect"] if not device_id else ["adb", "disconnect", device_id]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        return True, "已断开无线设备连接"
    except Exception as e:
        return False, f"断开连接出错: {str(e)}"


def take_screenshot(device_id: Optional[str] = None) -> Image.Image:
    """
    截取设备屏幕
    
    Args:
        device_id: 可选，指定设备 ID
    
    Returns:
        PIL Image 对象
    
    Raises:
        Exception: 截图失败时抛出
    """
    # 先检查是否有设备连接
    devices, _ = get_adb_devices()
    if not devices:
        raise Exception("没有连接的 Android 设备，请先连接设备")
    
    # 如果没有指定设备，使用第一个
    if not device_id and devices:
        device_id = devices[0]
    
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["exec-out", "screencap", "-p"])
    
    stdout, stderr, code = run_adb_command(cmd, binary=True)
    
    if code != 0:
        print(f"[Screenshot] ADB Error: {stderr}")
        raise Exception(f"截图命令执行失败: {stderr}")
    
    if not stdout:
        print("[Screenshot] Empty stdout")
        raise Exception(f"截图数据为空，请检查设备连接状态")
        
    print(f"[Screenshot] Received {len(stdout)} bytes")
    
    # 查找 PNG 头 (89 50 4E 47 0D 0A 1A 0A)
    png_header = b'\x89PNG\r\n\x1a\n'
    if isinstance(stdout, str):
        stdout = stdout.encode('latin-1')  # 再次确保是 bytes
        
    start_index = stdout.find(png_header)
    if start_index == -1:
        print(f"[Screenshot] No PNG header found")
        print(f"[Screenshot] First 100 bytes: {stdout[:100]}")
        raise Exception(f"截图数据无效: 未找到 PNG 头 (通常是因为 ADB 返回了文本警告信息)")
    
    if start_index > 0:
        print(f"[Screenshot] Found PNG header at offset {start_index}, trimming warning message...")
        stdout = stdout[start_index:]
    
    try:
        image = Image.open(BytesIO(stdout))
        print(f"[Screenshot] Valid image: {image.size} mode={image.mode}")
        return image
    except Exception as e:
        print(f"[Screenshot] Image.open failed: {e}")
        print(f"[Screenshot] First 64 bytes hex: {stdout[:64].hex()}")
        raise Exception(f"截图数据解析失败: {e}，请检查设备是否正常连接")


def get_device_resolution(device_id: Optional[str] = None) -> Tuple[int, int]:
    """
    获取设备屏幕分辨率
    
    Args:
        device_id: 可选，指定设备 ID
    
    Returns:
        Tuple of (width, height)
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "wm", "size"])
    
    stdout, stderr, code = run_adb_command(cmd)
    
    if code == 0 and stdout:
        match = re.search(r'(\d+)x(\d+)', stdout)
        if match:
            return int(match.group(1)), int(match.group(2))
    
    # 默认分辨率
    return 1080, 1920


def tap_device(x: int, y: int, device_id: Optional[str] = None) -> bool:
    """
    点击设备屏幕
    
    Args:
        x: X 坐标
        y: Y 坐标
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "tap", str(x), str(y)])
    
    _, _, code = run_adb_command(cmd)
    return code == 0


def long_press_device(x: int, y: int, duration: int = 1000, device_id: Optional[str] = None) -> bool:
    """
    长按设备屏幕
    
    Args:
        x: X 坐标
        y: Y 坐标
        duration: 按压时间（毫秒）
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "swipe", str(x), str(y), str(x), str(y), str(duration)])
    
    _, _, code = run_adb_command(cmd)
    return code == 0


def swipe_device(
    x1: int, y1: int, x2: int, y2: int,
    duration: int = 300,
    device_id: Optional[str] = None
) -> bool:
    """
    滑动设备屏幕
    
    Args:
        x1, y1: 起始坐标
        x2, y2: 结束坐标
        duration: 滑动时间（毫秒）
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)])
    
    _, _, code = run_adb_command(cmd)
    return code == 0


def swipe_direction(
    direction: str,
    x: Optional[int] = None,
    y: Optional[int] = None,
    distance: int = 500,
    device_id: Optional[str] = None
) -> bool:
    """
    按方向滑动
    
    Args:
        direction: 方向 (up, down, left, right)
        x, y: 起始坐标（可选，默认屏幕中心）
        distance: 滑动距离
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    width, height = get_device_resolution(device_id)
    
    if x is None:
        x = width // 2
    if y is None:
        y = height // 2
    
    direction = direction.lower()
    if direction == 'up':
        x2, y2 = x, y - distance
    elif direction == 'down':
        x2, y2 = x, y + distance
    elif direction == 'left':
        x2, y2 = x - distance, y
    elif direction == 'right':
        x2, y2 = x + distance, y
    else:
        return False
    
    return swipe_device(x, y, x2, y2, device_id=device_id)


def input_text(text: str, device_id: Optional[str] = None) -> bool:
    """
    输入文本
    
    Args:
        text: 要输入的文本
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    # 转义特殊字符
    escaped_text = text.replace(' ', '%s').replace("'", "").replace('"', '').replace('&', '').replace('<', '').replace('>', '')
    
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "text", escaped_text])
    
    _, _, code = run_adb_command(cmd)
    return code == 0


def install_yadb(device_id: Optional[str] = None) -> bool:
    """
    安装 YADB 到设备 (用于支持中文输入)
    
    Args:
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    if not os.path.exists(YADB_LOCAL_PATH):
        print(f"[YADB] 本地文件不存在: {YADB_LOCAL_PATH}")
        return False
    
    # 检查远程是否已存在
    check_cmd = ["adb"]
    if device_id:
        check_cmd.extend(["-s", device_id])
    check_cmd.extend(["shell", "ls", YADB_REMOTE_PATH])
    
    stdout, _, code = run_adb_command(check_cmd)
    if code == 0 and "No such file" not in stdout:
        print(f"[YADB] 已安装在设备上")
        return True
    
    # 推送到设备
    push_cmd = ["adb"]
    if device_id:
        push_cmd.extend(["-s", device_id])
    push_cmd.extend(["push", YADB_LOCAL_PATH, YADB_REMOTE_PATH])
    
    _, _, code = run_adb_command(push_cmd, timeout=30)
    if code == 0:
        # 设置执行权限
        chmod_cmd = ["adb"]
        if device_id:
            chmod_cmd.extend(["-s", device_id])
        chmod_cmd.extend(["shell", "chmod", "+x", YADB_REMOTE_PATH])
        run_adb_command(chmod_cmd)
        print(f"[YADB] 安装成功")
        return True
    
    print(f"[YADB] 安装失败")
    return False


def input_text_yadb(text: str, device_id: Optional[str] = None) -> bool:
    """
    使用 YADB 输入文本 (支持中文和特殊字符)
    
    Args:
        text: 要输入的文本
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    # 确保 yadb 已安装
    install_yadb(device_id)
    
    # 空格替换为下划线 (yadb 约定)
    escaped_text = text.replace(" ", "_")
    
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend([
        "shell",
        "app_process",
        "-Djava.class.path=" + YADB_REMOTE_PATH,
        "/data/local/tmp",
        "com.ysbing.yadb.Main",
        "-keyboard",
        escaped_text
    ])
    
    _, _, code = run_adb_command(cmd, timeout=10)
    return code == 0


# 系统按键映射
SYSTEM_BUTTONS = {
    'home': 'KEYCODE_HOME',
    'back': 'KEYCODE_BACK',
    'menu': 'KEYCODE_MENU',
    'enter': 'KEYCODE_ENTER',
    'power': 'KEYCODE_POWER',
    'volume_up': 'KEYCODE_VOLUME_UP',
    'volume_down': 'KEYCODE_VOLUME_DOWN',
}


def press_system_button(button: str, device_id: Optional[str] = None) -> bool:
    """
    按下系统按钮
    
    Args:
        button: 按钮名称 (home, back, menu, enter, power, volume_up, volume_down)
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    keycode = SYSTEM_BUTTONS.get(button.lower())
    if not keycode:
        # 尝试直接使用作为 keycode
        keycode = button.upper() if button.upper().startswith('KEYCODE_') else f'KEYCODE_{button.upper()}'
    
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "input", "keyevent", keycode])
    
    _, _, code = run_adb_command(cmd)
    return code == 0


def open_app(app_name: str, device_id: Optional[str] = None) -> bool:
    """
    通过应用名称打开应用
    支持中文应用名（如"微信"）和包名（如"com.tencent.mm"）
    
    Args:
        app_name: 应用名称或包名
        device_id: 可选，指定设备 ID
    
    Returns:
        是否成功
    """
    # 尝试解析应用名到包名
    try:
        from package_map import find_package_name
        package_name = find_package_name(app_name)
        print(f"[App] 解析应用名: {app_name} -> {package_name}")
    except Exception as e:
        # 如果解析失败，直接使用原始名称（可能已经是包名）
        package_name = app_name
        print(f"[App] 使用原始包名: {app_name}")
    
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    
    # 使用 monkey 命令启动应用
    cmd.extend(["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])
    
    _, _, code = run_adb_command(cmd)
    return code == 0


def restart_adb() -> Tuple[bool, str]:
    """
    重启 ADB 服务
    
    Returns:
        Tuple of (success, message)
    """
    try:
        subprocess.run(["adb", "kill-server"], capture_output=True, text=True, timeout=10)
        import time
        time.sleep(1)
        subprocess.run(["adb", "start-server"], capture_output=True, text=True, timeout=10)
        
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = [f"📱 {line.split()[0]}" for line in lines[1:] if '\tdevice' in line]
            if devices:
                return True, f"✅ ADB 重启成功\n当前设备:\n" + "\n".join(devices)
            return True, "✅ ADB 重启成功\n当前无设备连接"
        return False, "❌ ADB 重启失败"
    except Exception as e:
        return False, f"❌ 重启出错: {str(e)}"


def check_adb_connection() -> Tuple[bool, str]:
    """
    检查 ADB 连接状态
    
    Returns:
        Tuple of (connected, status_message)
    """
    try:
        subprocess.run(["adb", "start-server"], capture_output=True, text=True, timeout=5)
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            devices = []
            for line in lines[1:]:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        devices.append(f"📱 {parts[0]} - {parts[1]}")

            if devices:
                return True, f"✅ ADB 服务正常\n已连接设备:\n" + "\n".join(devices)
            else:
                return False, "⚠️ ADB 服务正常但无设备连接"
        return False, "❌ ADB 命令执行失败"

    except FileNotFoundError:
        return False, "❌ ADB 未安装或未添加到 PATH"
    except subprocess.TimeoutExpired:
        return False, "❌ ADB 命令超时"
    except Exception as e:
        return False, f"❌ 检查 ADB 连接时出错: {str(e)}"


def get_available_apps(device_id: Optional[str] = None) -> str:
    """
    获取设备上已安装的第三方应用列表
    
    Args:
        device_id: 可选，指定设备 ID
    
    Returns:
        应用列表字符串
    """
    try:
        cmd = ["adb"]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["shell", "pm", "list", "packages", "-3"])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=30
        )
        if result.returncode != 0:
            return "获取失败"
        apps = [line.replace('package:', '').strip() for line in result.stdout.splitlines() if line.strip()]
        apps.sort()
        return "\n".join(apps)
    except Exception as e:
        return str(e)
