"""
Package Map Web UI 模块
提供应用包名映射的扫描、查看、编辑、搜索和批量导入功能

移植自 gelab-zero 项目并针对 MAI-UI 进行适配
"""

import os
import pandas as pd
from typing import Optional, Tuple, List, Dict, Any

# 导入 MAI-UI 的 package_map 和 package_scanner
from web_ui.package_map import get_package_name_map, find_package_name, get_list_of_package_names
from web_ui.package_scanner import (
    scan_device_apps,
    merge_scan_result,
    load_user_package_map,
    save_user_package_map,
    get_user_package_map_path
)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_apps_with_progress(
    device_id: Optional[str] = None,
    progress_callback=None,
    deep_scan: bool = True
) -> Tuple[str, str, int]:
    """
    扫描设备应用并返回结果

    Args:
        device_id: 设备 ID
        progress_callback: 进度回调函数
        deep_scan: 是否深度扫描（使用 aapt2）

    Returns:
        Tuple of (log_text, status_message, app_count)
    """
    log_lines = []
    log_lines.append("🔍 开始扫描设备应用...\n")

    def progress_adapter(current, total, pkg, status=None):
        """适配进度回调"""
        if progress_callback:
            progress_val = current / total if total > 0 else 0
            label = f"[{current}/{total}] {pkg}"
            if status == 'mapping':
                label += " ✅ (映射匹配)"
            elif status == 'parsed':
                label += " 🔍 (深度解析)"
            else:
                label += " ⚠️ (fallback)"
            progress_callback(progress_val, desc=label)

        log_lines.append(f"{current}/{total} - {pkg} - {status or 'processing'}\n")

    try:
        apps = scan_device_apps(
            device_id=device_id,
            progress_callback=progress_adapter,
            deep_scan=deep_scan
        )

        # 合并到用户映射
        merge_scan_result(apps)

        log_lines.append(f"\n✅ 扫描完成！共发现 {len(apps)} 个应用")
        log_lines.append(f"📝 映射已保存到: {get_user_package_map_path()}")

        stats = f"✅ 扫描完成，共发现 {len(apps)} 个应用"
        return "".join(log_lines), stats, len(apps)

    except Exception as e:
        error_msg = f"❌ 扫描失败: {str(e)}"
        log_lines.append(error_msg)
        return "".join(log_lines), error_msg, 0


def get_package_mapping_dataframe() -> pd.DataFrame:
    """
    获取映射表的 DataFrame 格式

    Returns:
        pandas DataFrame with columns ['应用名', '包名']
    """
    mapping_list = get_list_of_package_names()
    
    # 转换为 DataFrame 格式
    if mapping_list:
        df = pd.DataFrame([
            {"应用名": item.get("app_name", ""), "包名": item.get("package_name", "")}
            for item in mapping_list
        ])
    else:
        df = pd.DataFrame(columns=['应用名', '包名'])

    return df


def search_package_by_name(app_name: str) -> str:
    """
    智能查找包名

    Args:
        app_name: 应用名称（支持中文）

    Returns:
        查找结果字符串
    """
    if not app_name or not app_name.strip():
        return "⚠️ 请输入应用名称"

    app_name = app_name.strip()

    try:
        package_name = find_package_name(app_name)
        result = f"✅ 找到映射:\n📱 应用名: {app_name}\n📦 包名: {package_name}"

        # 检查是否是默认映射还是用户映射
        user_map = load_user_package_map()
        if app_name in user_map:
            result += "\n📌 来源: 用户自定义映射"
        else:
            result += "\n📌 来源: 默认映射"

        return result

    except AssertionError:
        # 尝试模糊搜索
        current_map = get_package_name_map()
        app_name_lower = app_name.lower()

        matches = []
        for key, value in current_map.items():
            if app_name_lower in key.lower() or key.lower() in app_name_lower:
                matches.append((key, value))

        if matches:
            result = f"⚠️ 未找到精确匹配，但有 {len(matches)} 个相似结果:\n\n"
            for i, (app, pkg) in enumerate(matches[:10], 1):
                result += f"{i}. {app} -> {pkg}\n"
            return result
        else:
            return f"❌ 未找到应用: {app_name}\n\n💡 提示: 您可以扫描设备应用来添加映射"

    except Exception as e:
        return f"❌ 查找出错: {str(e)}"


def load_user_mapping_yaml() -> str:
    """
    加载用户映射 YAML 内容

    Returns:
        YAML 文件内容
    """
    user_map_file = get_user_package_map_path()

    if not os.path.exists(user_map_file):
        return f"# 用户自定义映射文件 (user_package_map.yaml)\n# 文件不存在，将自动创建\n\n"

    try:
        with open(user_map_file, 'r', encoding='utf-8') as f:
            content = f.read()
            return content if content.strip() else "# 空文件\n"
    except Exception as e:
        return f"# 读取文件失败: {str(e)}\n"


def save_user_mapping_yaml(yaml_content: str) -> str:
    """
    保存用户映射 YAML 内容

    Args:
        yaml_content: YAML 内容

    Returns:
        状态消息
    """
    user_map_file = get_user_package_map_path()

    try:
        # 验证 YAML 格式
        import yaml
        parsed = yaml.safe_load(yaml_content)
        if parsed is None:
            parsed = {}
        if not isinstance(parsed, dict):
            return "❌ YAML 格式错误: 根元素必须是字典"

        # 保存
        with open(user_map_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        return f"✅ 映射表已保存 ({len(parsed)} 条记录)\n📁 文件: {user_map_file}"

    except Exception as e:
        if 'yaml' in str(type(e).__module__).lower():
            return f"❌ YAML 格式错误: {str(e)}\n\n💡 提示: 请确保格式为 '应用名: 包名'"
        return f"❌ 保存失败: {str(e)}"


def batch_import_mappings(mappings_text: str) -> str:
    """
    从文本批量导入映射

    Args:
        mappings_text: 映射文本，格式为 "应用名:包名" (一行一个)

    Returns:
        状态消息
    """
    if not mappings_text or not mappings_text.strip():
        return "⚠️ 请输入要导入的映射"

    lines = mappings_text.strip().split('\n')
    new_mappings = {}
    errors = []

    for line_num, line in enumerate(lines, 1):
        line = line.strip()

        # 跳过注释和空行
        if not line or line.startswith('#'):
            continue

        # 解析
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                app_name = parts[0].strip()
                package_name = parts[1].strip()

                if app_name and package_name:
                    new_mappings[app_name] = package_name
                else:
                    errors.append(f"第 {line_num} 行: 应用名或包名为空")
            else:
                errors.append(f"第 {line_num} 行: 格式错误")
        else:
            errors.append(f"第 {line_num} 行: 缺少冒号分隔符")

    if not new_mappings:
        return "❌ 没有有效的映射可导入\n\n" + "\n".join(errors)

    # 合并到现有映射
    existing = load_user_package_map()
    original_count = len(existing)
    updated = 0

    for app_name, package_name in new_mappings.items():
        if app_name not in existing:
            existing[app_name] = package_name
            updated += 1
        else:
            errors.append(f"⚠️ {app_name}: 已存在，已跳过")

    # 保存
    save_user_package_map(existing)

    result = f"✅ 导入完成:\n"
    result += f"• 新增: {updated} 条\n"
    result += f"• 已存在: {len(new_mappings) - updated} 条\n"
    result += f"• 总计: {len(existing)} 条映射\n"

    if errors:
        result += f"\n⚠️ 警告:\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            result += f"\n... 还有 {len(errors) - 10} 条警告"

    return result


def get_mapping_statistics() -> Dict[str, Any]:
    """
    获取映射表统计信息

    Returns:
        统计信息字典
    """
    default_map = get_package_name_map()
    user_map = load_user_package_map()

    # 计算用户独有映射
    user_only = {k: v for k, v in user_map.items() if k not in default_map}

    return {
        "default_count": len(default_map),
        "user_count": len(user_map),
        "user_only_count": len(user_only),
        "total_count": len(default_map),  # 用户映射会覆盖默认映射
        "user_map_path": get_user_package_map_path()
    }
