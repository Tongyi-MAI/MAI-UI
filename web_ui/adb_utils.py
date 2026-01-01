"""
ADB 工具函数模块
提供 Android 设备连接、截图、操作等功能
"""

import subprocess
import re
import os
import time
from io import BytesIO
from typing import Tuple, List, Optional, Union
from PIL import Image


# ============ 设备缓存 (优化内网穿透性能) ============
class DeviceCache:
    """
    设备信息缓存，避免频繁调用 adb devices
    适用于内网穿透等慢速网络环境
    """
    def __init__(self, cache_ttl: float = 30.0):
        """
        Args:
            cache_ttl: 缓存有效期（秒），默认 30 秒
        """
        self._device_id: Optional[str] = None
        self._devices: List[str] = []
        self._resolution: Optional[Tuple[int, int]] = None
        self._last_check: float = 0
        self._cache_ttl = cache_ttl
    
    def get_device_id(self, force_refresh: bool = False) -> Optional[str]:
        """获取缓存的设备 ID，过期则刷新"""
        if force_refresh or self._is_expired():
            self._refresh()
        return self._device_id
    
    def get_devices(self, force_refresh: bool = False) -> List[str]:
        """获取缓存的设备列表"""
        if force_refresh or self._is_expired():
            self._refresh()
        return self._devices
    
    def set_device_id(self, device_id: str):
        """手动设置设备 ID（用于 Web UI 选择设备）"""
        self._device_id = device_id
        self._last_check = time.time()
    
    def set_resolution(self, width: int, height: int):
        """缓存设备分辨率"""
        self._resolution = (width, height)
    
    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """获取缓存的分辨率"""
        return self._resolution
    
    def invalidate(self):
        """清除缓存"""
        self._device_id = None
        self._devices = []
        self._resolution = None
        self._last_check = 0
    
    def _is_expired(self) -> bool:
        return time.time() - self._last_check > self._cache_ttl
    
    def _refresh(self):
        """刷新设备列表（延迟调用避免循环导入）"""
        # 直接使用 subprocess 避免循环导入
        import subprocess
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=10
            )
            self._devices = []
            if result.returncode == 0:
                lines = result.stdout.split('\n')[1:]
                for line in lines:
                    if '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        self._devices.append(device_id)
            
            if self._devices and (not self._device_id or self._device_id not in self._devices):
                self._device_id = self._devices[0]
            self._last_check = time.time()
        except Exception as e:
            print(f"[DeviceCache] 刷新设备列表失败: {e}")


# 全局设备缓存实例
device_cache = DeviceCache(cache_ttl=30.0)


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


# ============ 截图临时目录配置 ============
SCREENSHOT_TMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "tmp_screenshot")
SCREENSHOT_REMOTE_DIR = "/sdcard"  # 手机端临时目录


def take_screenshot_file_mode(
    device_id: Optional[str] = None,
    tmp_dir: str = SCREENSHOT_TMP_DIR,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    scale: float = 1.0,
    use_cache: bool = True,
    cleanup_remote: bool = True
) -> Image.Image:
    """
    截取设备屏幕（文件模式，更适合内网穿透等慢速网络）
    
    实现方式（参考 gelab-zero）：
    1. 在手机上执行 screencap 保存到 /sdcard
    2. 用 adb pull 拉取到本地
    3. 删除手机上的临时文件
    
    存储位置：
    - 手机端临时：/sdcard/screenshot_xxx.png
    - 电脑端：{logs}/tmp_screenshot/screenshot_xxx.png
    
    Args:
        device_id: 可选，指定设备 ID
        tmp_dir: 本地临时目录，默认 {logs}/tmp_screenshot
        timeout: 每个步骤的超时时间（秒），默认 30 秒
        max_retries: 最大重试次数，默认 3 次
        retry_delay: 重试间隔时间（秒），默认 1 秒
        scale: 缩放比例 (0.1-1.0)，默认 1.0 不缩放
        use_cache: 是否使用设备缓存，默认 True
        cleanup_remote: 是否删除手机上的临时文件，默认 True
    
    Returns:
        PIL Image 对象
    
    Raises:
        Exception: 截图失败时抛出
    """
    import uuid
    
    # 确保临时目录存在
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
        print(f"[Screenshot] 创建临时目录: {tmp_dir}")
    
    # 使用缓存获取设备 ID
    if use_cache and not device_id:
        cached_id = device_cache.get_device_id()
        if cached_id:
            device_id = cached_id
            print(f"[Screenshot] 使用缓存的设备 ID: {device_id}")
    
    # 如果没有缓存，检查设备
    if not device_id:
        devices, _ = get_adb_devices()
        if not devices:
            raise Exception("没有连接的 Android 设备，请先连接设备")
        device_id = devices[0]
        device_cache.set_device_id(device_id)
    
    # 生成唯一文件名
    filename = f"screenshot_{uuid.uuid4().hex[:8]}.png"
    remote_path = f"{SCREENSHOT_REMOTE_DIR}/{filename}"
    local_path = os.path.join(tmp_dir, filename)
    
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Screenshot] 文件模式截图 (第 {attempt}/{max_retries} 次)...")
            
            # Step 1: 在手机上截图并保存到 /sdcard
            cmd_capture = ["adb"]
            if device_id:
                cmd_capture.extend(["-s", device_id])
            cmd_capture.extend(["shell", "screencap", "-p", remote_path])
            
            stdout, stderr, code = run_adb_command(cmd_capture, timeout=timeout)
            if code != 0:
                last_error = f"手机端截图失败: {stderr}"
                print(f"[Screenshot] 步骤1失败 (尝试 {attempt}): {stderr}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
            
            print(f"[Screenshot] 手机端截图完成: {remote_path}")
            
            # Step 2: 拉取到本地
            cmd_pull = ["adb"]
            if device_id:
                cmd_pull.extend(["-s", device_id])
            cmd_pull.extend(["pull", remote_path, local_path])
            
            stdout, stderr, code = run_adb_command(cmd_pull, timeout=timeout)
            if code != 0:
                last_error = f"拉取截图失败: {stderr}"
                print(f"[Screenshot] 步骤2失败 (尝试 {attempt}): {stderr}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
            
            print(f"[Screenshot] 拉取完成: {local_path}")
            
            # Step 3: 删除手机上的临时文件
            if cleanup_remote:
                cmd_rm = ["adb"]
                if device_id:
                    cmd_rm.extend(["-s", device_id])
                cmd_rm.extend(["shell", "rm", remote_path])
                run_adb_command(cmd_rm, timeout=10)  # 不阻塞，失败也无所谓
            
            # Step 4: 读取本地图片
            if not os.path.exists(local_path):
                last_error = f"本地文件不存在: {local_path}"
                print(f"[Screenshot] 步骤4失败 (尝试 {attempt}): 文件不存在")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue
            
            image = Image.open(local_path)
            original_size = image.size
            
            # 缓存分辨率
            device_cache.set_resolution(original_size[0], original_size[1])
            
            # 缩放
            if scale < 1.0:
                new_width = int(original_size[0] * scale)
                new_height = int(original_size[1] * scale)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"[Screenshot] Scaled: {original_size} -> {image.size}")
            else:
                print(f"[Screenshot] 成功: {image.size} mode={image.mode}")
            
            # 清理本地临时文件（可选，保留用于调试）
            # os.remove(local_path)
            
            return image
            
        except Exception as e:
            last_error = str(e)
            print(f"[Screenshot] 异常 (尝试 {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
    
    # 所有重试都失败
    raise Exception(f"截图失败（已重试 {max_retries} 次）: {last_error}")


def take_screenshot(
    device_id: Optional[str] = None,
    timeout: int = 60,
    max_retries: int = 3,
    retry_delay: float = 2.0,
    scale: float = 1.0,
    use_cache: bool = True,
    quality: int = 80
) -> Image.Image:
    """
    截取设备屏幕（流模式，备用方案）
    
    使用 adb exec-out screencap 通过管道直接传输截图数据。
    如果在内网穿透等慢速网络环境下遇到超时，建议使用 take_screenshot_file_mode()
    
    Args:
        device_id: 可选，指定设备 ID（如果为空且 use_cache=True，则使用缓存）
        timeout: 超时时间（秒），默认 60 秒（适用于慢速网络/内网穿透）
        max_retries: 最大重试次数，默认 3 次
        retry_delay: 重试间隔时间（秒），默认 2 秒
        scale: 缩放比例 (0.1-1.0)，默认 1.0 不缩放，设为 0.5 可减少 75% 数据量
        use_cache: 是否使用设备缓存，默认 True（避免频繁调用 adb devices）
        quality: JPEG 压缩质量 (1-100)，用于返回时的可选压缩，默认 80
    
    Returns:
        PIL Image 对象
    
    Raises:
        Exception: 截图失败时抛出
    """
    
    # 使用缓存获取设备 ID（避免频繁调用 adb devices）
    if use_cache and not device_id:
        cached_id = device_cache.get_device_id()
        if cached_id:
            device_id = cached_id
            print(f"[Screenshot] 使用缓存的设备 ID: {device_id}")
    
    # 如果没有缓存，才检查设备
    if not device_id:
        devices, _ = get_adb_devices()
        if not devices:
            raise Exception("没有连接的 Android 设备，请先连接设备")
        device_id = devices[0]
        # 更新缓存
        device_cache.set_device_id(device_id)
    
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["exec-out", "screencap", "-p"])
    
    last_error = None
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Screenshot] 尝试截图 (第 {attempt}/{max_retries} 次, 超时 {timeout}s, 缩放 {scale})...")
            
            stdout, stderr, code = run_adb_command(cmd, binary=True, timeout=timeout)
            
            if code != 0:
                last_error = f"截图命令执行失败: {stderr}"
                print(f"[Screenshot] ADB Error (尝试 {attempt}): {stderr}")
                if attempt < max_retries:
                    print(f"[Screenshot] 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                continue
            
            if not stdout:
                last_error = "截图数据为空，请检查设备连接状态"
                print(f"[Screenshot] Empty stdout (尝试 {attempt})")
                if attempt < max_retries:
                    print(f"[Screenshot] 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                continue
                
            print(f"[Screenshot] Received {len(stdout)} bytes")
            
            # 查找 PNG 头 (89 50 4E 47 0D 0A 1A 0A)
            png_header = b'\x89PNG\r\n\x1a\n'
            if isinstance(stdout, str):
                stdout = stdout.encode('latin-1')
                
            start_index = stdout.find(png_header)
            if start_index == -1:
                last_error = "截图数据无效: 未找到 PNG 头"
                print(f"[Screenshot] No PNG header found (尝试 {attempt})")
                if attempt < max_retries:
                    print(f"[Screenshot] 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                continue
            
            if start_index > 0:
                print(f"[Screenshot] Found PNG header at offset {start_index}, trimming...")
                stdout = stdout[start_index:]
            
            try:
                image = Image.open(BytesIO(stdout))
                original_size = image.size
                
                # 缓存分辨率
                device_cache.set_resolution(original_size[0], original_size[1])
                
                # 如果需要缩放
                if scale < 1.0:
                    new_width = int(original_size[0] * scale)
                    new_height = int(original_size[1] * scale)
                    image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    print(f"[Screenshot] Scaled: {original_size} -> {image.size}")
                else:
                    print(f"[Screenshot] Valid image: {image.size} mode={image.mode}")
                
                return image
                
            except Exception as e:
                last_error = f"截图数据解析失败: {e}"
                print(f"[Screenshot] Image.open failed (尝试 {attempt}): {e}")
                if attempt < max_retries:
                    print(f"[Screenshot] 等待 {retry_delay}s 后重试...")
                    time.sleep(retry_delay)
                continue
                
        except Exception as e:
            last_error = str(e)
            print(f"[Screenshot] 异常 (尝试 {attempt}): {e}")
            if attempt < max_retries:
                print(f"[Screenshot] 等待 {retry_delay}s 后重试...")
                time.sleep(retry_delay)
    
    # 所有重试都失败
    raise Exception(f"截图失败（已重试 {max_retries} 次）: {last_error}")


def take_screenshot_fast(
    device_id: Optional[str] = None,
    scale: float = 0.5,
    timeout: int = 45
) -> Image.Image:
    """
    快速截图（针对慢速网络优化）
    
    使用较小的缩放比例和缓存，减少数据传输量
    
    Args:
        device_id: 可选，指定设备 ID
        scale: 缩放比例，默认 0.5（减少 75% 数据量）
        timeout: 超时时间，默认 45 秒
    
    Returns:
        PIL Image 对象
    """
    return take_screenshot(
        device_id=device_id,
        timeout=timeout,
        max_retries=2,
        retry_delay=1.5,
        scale=scale,
        use_cache=True
    )


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


def check_package_exists(package_name: str, device_id: Optional[str] = None) -> bool:
    """
    检查应用包是否存在于设备上
    
    Args:
        package_name: 包名
        device_id: 可选，指定设备 ID
    
    Returns:
        是否存在
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["shell", "pm", "path", package_name])
    
    stdout, _, code = run_adb_command(cmd, timeout=10)
    return code == 0 and "package:" in stdout


def open_app(
    app_name: str,
    device_id: Optional[str] = None,
    prefer_awake: bool = True,
    fallback_to_search: bool = True
) -> Tuple[bool, str]:
    """
    通过应用名称打开应用
    支持中文应用名（如"微信"）和包名（如"com.tencent.mm"）
    
    Args:
        app_name: 应用名称或包名
        device_id: 可选，指定设备 ID
        prefer_awake: 如果为 True，优先尝试用包名直接启动 (推荐)
        fallback_to_search: AWAKE 失败时是否返回"需要搜索"状态
    
    Returns:
        Tuple of (success, message)
        - success: 是否成功启动
        - message: 状态消息，如果需要搜索则包含 "NEED_SEARCH"
    """
    # 尝试解析应用名到包名
    package_name = None
    try:
        from package_map import find_package_name
        package_name = find_package_name(app_name)
        print(f"[App] 解析应用名: {app_name} -> {package_name}")
    except Exception as e:
        # 如果解析失败，检查是否本身就是包名格式
        if "." in app_name and app_name.count(".") >= 2:
            package_name = app_name
            print(f"[App] 使用原始包名: {app_name}")
        else:
            print(f"[App] 无法解析应用名: {app_name}, 错误: {e}")
            if fallback_to_search:
                return False, f"NEED_SEARCH:{app_name}"
            return False, f"无法解析应用名: {app_name}"
    
    if prefer_awake and package_name:
        # 先检查应用是否存在
        if check_package_exists(package_name, device_id):
            # 使用 monkey 命令启动应用
            cmd = ["adb"]
            if device_id:
                cmd.extend(["-s", device_id])
            cmd.extend(["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"])
            
            _, _, code = run_adb_command(cmd)
            if code == 0:
                return True, f"已启动: {app_name} ({package_name})"
            else:
                # monkey 失败,尝试 am start
                cmd2 = ["adb"]
                if device_id:
                    cmd2.extend(["-s", device_id])
                cmd2.extend(["shell", "am", "start", "-n", f"{package_name}/.MainActivity"])
                _, _, code2 = run_adb_command(cmd2)
                if code2 == 0:
                    return True, f"已启动 (am): {app_name}"
                
                # 都失败了
                if fallback_to_search:
                    return False, f"NEED_SEARCH:{app_name}"
                return False, f"启动失败: {app_name}"
        else:
            # 应用不存在
            print(f"[App] 应用未安装: {package_name}")
            if fallback_to_search:
                return False, f"NEED_SEARCH:{app_name}"
            return False, f"应用未安装: {app_name}"
    
    # 不优先 AWAKE 或没有包名，返回需要搜索
    if fallback_to_search:
        return False, f"NEED_SEARCH:{app_name}"
    return False, f"无法启动: {app_name}"


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
