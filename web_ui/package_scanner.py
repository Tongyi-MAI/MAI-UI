"""
应用包名扫描器模块

功能:
1. 通过 ADB 获取已安装应用的包名列表
2. 获取每个应用的中文显示名称
3. 读写 user_package_map.yaml 文件

依赖: 无需手机端安装额外工具，使用系统自带命令
"""

import os
import sys
import subprocess
import re
from typing import Optional

# 添加项目根目录到路径
if "." not in sys.path:
    sys.path.append(".")

# YAML 配置文件路径（项目根目录）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USER_PACKAGE_MAP_FILE = os.path.join(PROJECT_ROOT, "user_package_map.yaml")


def _get_adb_command(device_id: Optional[str] = None) -> str:
    """获取 ADB 命令前缀"""
    if device_id is None:
        return "adb"
    return f"adb -s {device_id}"


def get_installed_packages(device_id: Optional[str] = None) -> list[str]:
    """
    获取第三方应用包名列表
    
    Args:
        device_id: 设备 ID，为 None 时使用默认设备
        
    Returns:
        包名列表
    """
    adb_cmd = _get_adb_command(device_id)
    cmd = f"{adb_cmd} shell pm list packages -3"
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, 
            text=True, encoding='utf-8', errors='ignore', timeout=30
        )
        if result.returncode != 0:
            print(f"[WARNING] pm list packages failed: {result.stderr}")
            return []
        
        packages = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("package:"):
                pkg = line.replace("package:", "").strip()
                if pkg:
                    packages.append(pkg)
        return packages
    except subprocess.TimeoutExpired:
        print("[ERROR] get_installed_packages timeout")
        return []
    except Exception as e:
        print(f"[ERROR] get_installed_packages: {e}")
        return []


def get_app_label_via_dumpsys(device_id: Optional[str], package_name: str) -> Optional[str]:
    """
    通过 dumpsys package 获取应用名称
    
    尝试解析 applicationInfo 中的 labelRes 或直接获取 label
    
    Args:
        device_id: 设备 ID
        package_name: 包名
        
    Returns:
        应用名称，失败返回 None
    """
    adb_cmd = _get_adb_command(device_id)
    
    # 方法1: 尝试使用 cmd package 获取应用信息
    cmd = f'{adb_cmd} shell dumpsys package {package_name}'
    
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, encoding='utf-8', errors='ignore', timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        output = result.stdout
        
        # 尝试从 applicationInfo 行提取 labelRes
        # 格式: labelRes=0x7f150001 微信 nonLocalizedLabel=null
        # 或者: labelRes=0x7f150001 nonLocalizedLabel=微信
        
        # 查找包含 labelRes 的行
        for line in output.splitlines():
            if 'labelRes=' in line and 'nonLocalizedLabel=' in line:
                # 尝试提取 nonLocalizedLabel 的值
                match = re.search(r'nonLocalizedLabel=(\S+)', line)
                if match:
                    label = match.group(1)
                    if label and label != 'null':
                        return label
                
                # 尝试提取 labelRes= 和 nonLocalizedLabel= 之间的文本
                match = re.search(r'labelRes=0x[a-fA-F0-9]+\s+(.+?)\s+nonLocalizedLabel', line)
                if match:
                    label = match.group(1).strip()
                    if label and label != 'null':
                        return label
        
        return None
        
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"[WARNING] dumpsys failed for {package_name}: {e}")
        return None


def get_app_label_via_aapt(device_id: Optional[str], package_name: str) -> Optional[str]:
    """
    通过 aapt 获取应用名称（如果设备上有 aapt）
    
    Args:
        device_id: 设备 ID
        package_name: 包名
        
    Returns:
        应用名称，失败返回 None
    """
    adb_cmd = _get_adb_command(device_id)
    
    try:
        # 1. 获取 APK 路径
        cmd_path = f'{adb_cmd} shell pm path {package_name}'
        result = subprocess.run(
            cmd_path, shell=True, capture_output=True,
            text=True, encoding='utf-8', errors='ignore', timeout=5
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return None
        
        # 解析 APK 路径: package:/data/app/xxx/base.apk
        apk_path = result.stdout.strip().replace("package:", "").strip()
        if not apk_path:
            return None
        
        # 2. 检查设备上是否有 aapt
        # 优先检查 /data/local/tmp/aapt (用户 push 的)
        # 然后检查系统自带的 /system/bin/aapt
        aapt_paths = ['/data/local/tmp/aapt', '/system/bin/aapt', 'aapt']
        aapt_cmd = None
        
        for aapt_path in aapt_paths:
            check_cmd = f'{adb_cmd} shell {aapt_path} version 2>/dev/null'
            check_result = subprocess.run(
                check_cmd, shell=True, capture_output=True,
                text=True, timeout=3
            )
            if check_result.returncode == 0:
                aapt_cmd = aapt_path
                break
        
        if aapt_cmd is None:
            return None
        
        # 3. 使用 aapt 获取应用名
        cmd_aapt = f'{adb_cmd} shell {aapt_cmd} dump badging "{apk_path}" 2>/dev/null'
        result = subprocess.run(
            cmd_aapt, shell=True, capture_output=True,
            text=True, encoding='utf-8', errors='ignore', timeout=10
        )
        
        if result.returncode != 0:
            return None
        
        # 解析 application-label 或 application-label-zh-CN
        output = result.stdout
        
        # 优先中文标签
        match = re.search(r"application-label-zh[^:]*:'([^']+)'", output)
        if match:
            return match.group(1)
        
        # 然后通用标签
        match = re.search(r"application-label:'([^']+)'", output)
        if match:
            return match.group(1)
        
        return None
        
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        print(f"[WARNING] aapt failed for {package_name}: {e}")
        return None


def get_app_label_via_local_apk(device_id: Optional[str], package_name: str, tmp_dir: str = None) -> Optional[str]:
    """
    通过拉取 APK 到本地并解析获取应用名称（最可靠的方法）
    
    使用 Python zipfile 解析 APK 中的资源，提取应用名称
    
    Args:
        device_id: 设备 ID
        package_name: 包名
        tmp_dir: 临时文件目录
        
    Returns:
        应用名称，失败返回 None
    """
    import zipfile
    import tempfile
    import struct
    
    adb_cmd = _get_adb_command(device_id)
    
    if tmp_dir is None:
        tmp_dir = tempfile.gettempdir()
    
    local_apk_path = os.path.join(tmp_dir, f"{package_name}_temp.apk")
    
    try:
        # 1. 获取 APK 路径
        cmd_path = f'{adb_cmd} shell pm path {package_name}'
        result = subprocess.run(
            cmd_path, shell=True, capture_output=True,
            text=True, encoding='utf-8', errors='ignore', timeout=5
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            return None
        
        # 解析 APK 路径
        apk_path = result.stdout.strip().split('\n')[0].replace("package:", "").strip()
        if not apk_path:
            return None
        
        # 2. 拉取 APK 到本地
        cmd_pull = f'{adb_cmd} pull "{apk_path}" "{local_apk_path}"'
        result = subprocess.run(
            cmd_pull, shell=True, capture_output=True,
            text=True, encoding='utf-8', errors='ignore', timeout=60
        )
        
        if result.returncode != 0 or not os.path.exists(local_apk_path):
            return None
        
        # 3. 解析 APK 获取应用名
        label = _parse_apk_label(local_apk_path)
        
        return label
        
    except Exception as e:
        print(f"[WARNING] local APK parsing failed for {package_name}: {e}")
        return None
    finally:
        # 清理临时文件
        if os.path.exists(local_apk_path):
            try:
                os.remove(local_apk_path)
            except:
                pass
def _parse_apk_label(apk_path: str) -> Optional[str]:
    """
    解析 APK 文件获取应用名称
    
    优先使用 aapt2（能正确获取中文名），再用 androguard 作为 fallback
    """
    # 方法1: 优先使用 aapt2（能正确获取中文名）
    try:
        import shutil
        aapt2_path = shutil.which('aapt2')
        
        # 如果 PATH 中没有，尝试项目目录下的 aapt2
        if not aapt2_path:
            project_aapt2 = os.path.join(PROJECT_ROOT, 'aapt2-8.5.0-11315950-windows', 'aapt2.exe')
            custom_paths = [
                project_aapt2,
                os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\build-tools\34.0.0\aapt2.exe'),
                os.path.expandvars(r'%LOCALAPPDATA%\Android\Sdk\build-tools\33.0.0\aapt2.exe'),
            ]
            for p in custom_paths:
                if os.path.exists(p):
                    aapt2_path = p
                    break
        
        if aapt2_path:
            result = subprocess.run(
                [aapt2_path, 'dump', 'badging', apk_path],
                capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30
            )
            if result.returncode == 0:
                # 解析 application-label (优先简体中文)
                zh_cn_label = None   # 简体中文 (zh-CN, zh-Hans)
                zh_tw_label = None   # 繁体中文 (zh-TW, zh-Hant, zh-HK)
                zh_label = None      # 通用中文 (zh)
                default_label = None
                
                for line in result.stdout.splitlines():
                    # 优先级1: 简体中文
                    if 'application-label-zh-CN' in line or 'application-label-zh-Hans' in line:
                        match = re.search(r"application-label-zh[^:]*:'([^']+)'", line)
                        if match:
                            zh_cn_label = match.group(1)
                    # 优先级2: 繁体中文
                    elif 'application-label-zh-TW' in line or 'application-label-zh-Hant' in line or 'application-label-zh-HK' in line:
                        match = re.search(r"application-label-zh[^:]*:'([^']+)'", line)
                        if match and not zh_tw_label:
                            zh_tw_label = match.group(1)
                    # 优先级3: 通用中文
                    elif 'application-label-zh:' in line:
                        match = re.search(r"application-label-zh:'([^']+)'", line)
                        if match:
                            zh_label = match.group(1)
                    # 优先级4: 默认标签
                    elif "application-label:'" in line and not default_label:
                        match = re.search(r"application-label:'([^']+)'", line)
                        if match:
                            default_label = match.group(1)
                
                # 按优先级返回：简体 > 繁体 > 通用中文 > 默认
                if zh_cn_label:
                    return zh_cn_label
                if zh_tw_label:
                    return zh_tw_label
                if zh_label:
                    return zh_label
                if default_label:
                    return default_label
    except Exception:
        pass
    
    # 方法2: 使用 androguard（作为 fallback）
    try:
        from androguard.core.apk import APK
        import logging
        logging.getLogger('androguard').setLevel(logging.ERROR)
        
        apk = APK(apk_path)
        app_name = apk.get_app_name()
        if app_name:
            return app_name
            
    except ImportError:
        pass
    except Exception:
        pass
    
    return None



def _extract_label_from_arsc(arsc_data: bytes) -> Optional[str]:
    """
    从 resources.arsc 中提取应用名称（启发式方法，不够准确）
    """
    try:
        # 将字节转为字符串进行搜索
        text = arsc_data.decode('utf-8', errors='ignore')
        
        # 查找中文字符串（2-10个字符，较短的更可能是应用名）
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]{2,10}')
        matches = chinese_pattern.findall(text)
        
        if matches:
            # 优先返回较短的匹配（应用名通常较短）
            valid_matches = sorted([m for m in matches if 2 <= len(m) <= 6], key=len)
            if valid_matches:
                return valid_matches[0]
        
        return None
    except Exception:
        return None


def get_app_label(device_id: Optional[str], package_name: str, use_local_parsing: bool = True) -> str:
    """
    获取应用名称（自动 fallback）
    
    尝试顺序:
    1. 从 package_map.py 反向查找（最快最可靠）
    2. 从用户映射查找
    3. dumpsys package (系统自带)
    4. aapt (如果设备上有)
    5. 本地 APK 解析（使用 aapt2，默认启用）
    6. 返回包名的最后一部分
    
    Args:
        device_id: 设备 ID
        package_name: 包名
        use_local_parsing: 是否使用本地 APK 解析（默认启用）
        
    Returns:
        应用名称或包名
    """
    # 1. 优先从 package_map.py 反向查找中文名（最快最可靠）
    try:
        from web_ui.package_map import get_package_name_map
        package_name_map = get_package_name_map()
        # 反向查找：给定包名，找到对应的中文名
        for app_name, pkg in package_name_map.items():
            if pkg == package_name:
                return app_name
    except ImportError:
        pass
    
    # 2. 从用户映射查找
    user_map = load_user_package_map()
    for app_name, pkg in user_map.items():
        if pkg == package_name:
            return app_name
    
    # 3. 尝试 dumpsys (系统自带，但不一定有中文名)
    label = get_app_label_via_dumpsys(device_id, package_name)
    if label:
        return label
    
    # 4. 尝试设备上的 aapt
    label = get_app_label_via_aapt(device_id, package_name)
    if label:
        return label
    
    # 5. 尝试本地 APK 解析（使用 aapt2，拉取 APK 并解析）
    if use_local_parsing:
        label = get_app_label_via_local_apk(device_id, package_name)
        if label:
            return label
    
    # 6. fallback: 返回包名的最后一部分作为名称
    parts = package_name.split('.')
    return parts[-1] if parts else package_name


def scan_device_apps(device_id: Optional[str] = None, progress_callback=None, deep_scan: bool = True) -> dict[str, str]:
    """
    智能扫描设备应用，返回 {app_name: package_name} 映射
    
    扫描逻辑:
    1. 获取设备上所有第三方应用包名
    2. 对每个包名:
       a. 先尝试从【用户映射 + 内置映射】反向查找中文名
       b. 如果找不到且启用深度扫描 → 用 aapt2 获取中文名
       c. 都失败则用包名片段
    3. 结果保存到 user_package_map.yaml
    
    Args:
        device_id: 设备 ID
        progress_callback: 进度回调函数 callback(current, total, package_name, status)
                          status: 'mapping' (从映射匹配) 或 'parsing' (深度扫描)
        deep_scan: 是否对未匹配应用进行深度扫描（默认启用）
        
    Returns:
        应用名称到包名的映射字典
    """
    packages = get_installed_packages(device_id)
    total = len(packages)
    
    if total == 0:
        print("[WARNING] No packages found on device")
        return {}
    
    # 构建合并的反向映射表：包名 -> 中文名
    reverse_map = {}
    
    # 1. 加载用户映射（优先级最高）
    user_map = load_user_package_map()
    for app_name, pkg in user_map.items():
        reverse_map[pkg] = app_name
    
    # 2. 加载内置映射
    try:
        from web_ui.package_map import get_package_name_map
        package_name_map = get_package_name_map()
        for app_name, pkg in package_name_map.items():
            if pkg not in reverse_map:  # 不覆盖用户映射
                reverse_map[pkg] = app_name
    except ImportError:
        pass
    
    print(f"[INFO] 合并映射表共 {len(reverse_map)} 条记录")
    
    mapping = {}
    matched_count = 0
    parsed_count = 0
    
    for i, pkg in enumerate(packages):
        status = 'unknown'
        
        # 1. 优先从合并映射查找
        if pkg in reverse_map:
            label = reverse_map[pkg]
            status = 'mapping'
            matched_count += 1
        elif deep_scan:
            # 2. 深度扫描：使用 aapt2 解析 APK
            if progress_callback:
                progress_callback(i + 1, total, pkg, 'parsing')
            
            label = get_app_label_via_local_apk(device_id, pkg)
            if label:
                status = 'parsed'
                parsed_count += 1
            else:
                # fallback 到包名片段
                parts = pkg.split('.')
                label = parts[-1] if parts else pkg
                status = 'fallback'
        else:
            # 3. 不启用深度扫描，使用包名片段
            parts = pkg.split('.')
            label = parts[-1] if parts else pkg
            status = 'fallback'
        
        if progress_callback:
            progress_callback(i + 1, total, pkg, status)
        
        # 避免重复: 如果应用名已存在，添加后缀区分
        final_label = label
        counter = 1
        while final_label in mapping and mapping[final_label] != pkg:
            final_label = f"{label}_{counter}"
            counter += 1
        
        mapping[final_label] = pkg
    
    print(f"[INFO] 扫描完成: 总计 {total} 个应用, "
          f"映射匹配 {matched_count} 个, "
          f"深度解析 {parsed_count} 个")
    
    return mapping


def load_user_package_map() -> dict[str, str]:
    """
    加载用户自定义映射
    
    Returns:
        应用名称到包名的映射字典，文件不存在返回空字典
    """
    if not os.path.exists(USER_PACKAGE_MAP_FILE):
        return {}
    
    try:
        import yaml
        with open(USER_PACKAGE_MAP_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except ImportError:
        # 如果没有安装 yaml，使用简单的解析方式
        mapping = {}
        try:
            with open(USER_PACKAGE_MAP_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip().strip('"').strip("'")
                            value = parts[1].strip().strip('"').strip("'")
                            if key and value:
                                mapping[key] = value
            return mapping
        except Exception as e:
            print(f"[WARNING] Failed to parse user_package_map.yaml: {e}")
            return {}
    except Exception as e:
        print(f"[WARNING] Failed to load user_package_map.yaml: {e}")
        return {}


def save_user_package_map(mapping: dict[str, str]) -> bool:
    """
    保存用户自定义映射
    
    Args:
        mapping: 应用名称到包名的映射字典
        
    Returns:
        是否保存成功
    """
    try:
        import yaml
        with open(USER_PACKAGE_MAP_FILE, 'w', encoding='utf-8') as f:
            f.write("# 用户自定义应用名称 -> 包名映射\n")
            f.write("# 此文件由扫描功能自动生成，也可手动编辑\n")
            f.write("# 优先级高于 package_map.py 中的默认映射\n\n")
            yaml.dump(mapping, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        return True
    except ImportError:
        # 如果没有安装 yaml，使用简单的格式
        try:
            with open(USER_PACKAGE_MAP_FILE, 'w', encoding='utf-8') as f:
                f.write("# 用户自定义应用名称 -> 包名映射\n")
                f.write("# 此文件由扫描功能自动生成，也可手动编辑\n")
                f.write("# 优先级高于 package_map.py 中的默认映射\n\n")
                for app_name, pkg_name in mapping.items():
                    # 如果名称包含特殊字符，加引号
                    if ':' in app_name or '#' in app_name:
                        f.write(f'"{app_name}": {pkg_name}\n')
                    else:
                        f.write(f'{app_name}: {pkg_name}\n')
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save user_package_map.yaml: {e}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to save user_package_map.yaml: {e}")
        return False


def merge_scan_result(new_mapping: dict[str, str]) -> dict[str, str]:
    """
    将扫描结果合并到用户映射（不覆盖现有条目）
    
    Args:
        new_mapping: 新扫描的映射
        
    Returns:
        合并后的映射
    """
    existing = load_user_package_map()
    
    # 新映射中不覆盖已存在的条目
    for app_name, pkg_name in new_mapping.items():
        if app_name not in existing:
            existing[app_name] = pkg_name
    
    # 保存合并后的映射
    save_user_package_map(existing)
    
    return existing


def get_user_package_map_path() -> str:
    """获取用户映射文件路径"""
    return USER_PACKAGE_MAP_FILE


# 测试代码
if __name__ == "__main__":
    print("=== 扫描设备应用 ===")
    
    def progress(current, total, pkg):
        print(f"[{current}/{total}] 正在扫描: {pkg}")
    
    apps = scan_device_apps(progress_callback=progress)
    
    print(f"\n=== 扫描结果 ({len(apps)} 个应用) ===")
    for name, pkg in sorted(apps.items()):
        print(f"  {name}: {pkg}")
    
    print(f"\n=== 保存到 {USER_PACKAGE_MAP_FILE} ===")
    merged = merge_scan_result(apps)
    print(f"合并后共 {len(merged)} 条映射")
