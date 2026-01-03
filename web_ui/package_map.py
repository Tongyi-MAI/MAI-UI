"""
应用名称 -> 包名 映射模块

映射完全从 YAML 文件加载，实时读取，无需重启程序:
1. default_package_map.yaml - 默认通用映射（项目提供的常用应用）
2. user_package_map.yaml - 用户自定义映射（优先级最高）

修改 YAML 文件后立即生效，无需重启程序。
"""

import os
import difflib

# 获取项目根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_MAP_FILE = os.path.join(_PROJECT_ROOT, "default_package_map.yaml")
_USER_MAP_FILE = os.path.join(_PROJECT_ROOT, "user_package_map.yaml")


def _load_yaml_map(file_path: str) -> dict:
    """从 YAML 文件加载映射"""
    if not os.path.exists(file_path):
        return {}
    
    try:
        import yaml
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except ImportError:
        # 没有 yaml 库，使用简单解析
        mapping = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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
        except Exception:
            return {}
    except Exception:
        return {}


def get_package_name_map() -> dict:
    """
    实时获取合并的映射表（每次调用都重新加载）
    
    加载顺序：默认映射 -> 用户映射（覆盖）
    修改 YAML 文件后立即生效，无需重启程序
    
    Returns:
        合并后的 {应用名: 包名} 映射字典
    """
    # 1. 加载默认映射
    merged_map = _load_yaml_map(_DEFAULT_MAP_FILE)
    
    # 2. 加载用户映射并合并（用户映射优先级更高）
    user_map = _load_yaml_map(_USER_MAP_FILE)
    merged_map.update(user_map)
    
    return merged_map


# 为了向后兼容，提供一个属性访问方式
# 注意：这个变量在模块加载时只执行一次，不会实时刷新
# 如需实时刷新，请使用 get_package_name_map() 函数
package_name_map = get_package_name_map()


def reload_package_name_map():
    """
    刷新全局映射表（如果需要兼容旧代码）
    """
    global package_name_map
    package_name_map = get_package_name_map()


def find_package_name(app_name: str) -> str:
    """
    根据应用名查找包名（实时读取 YAML）
    
    查找顺序:
    1. 精确匹配（大小写敏感）
    2. 小写匹配
    3. 模糊匹配
    
    Args:
        app_name: 应用名称
        
    Returns:
        包名
        
    Raises:
        AssertionError: 找不到匹配的包名
    """
    # 实时加载映射表
    current_map = get_package_name_map()
    
    app_name_lowered = app_name.lower()
    
    # 1. 精确匹配
    if app_name in current_map:
        return current_map[app_name]
    
    # 2. 小写匹配
    map_lowered = {k.lower(): v for k, v in current_map.items()}
    if app_name_lowered in map_lowered:
        return map_lowered[app_name_lowered]
    
    # 3. 模糊匹配
    max_match = {
        "name": None,
        "score": 0
    }
    
    for key in current_map.keys():
        score = difflib.SequenceMatcher(None, app_name_lowered, key.lower()).ratio()
        if score > max_match["score"]:
            max_match["name"] = key
            max_match["score"] = score
    
    assert max_match['name'] is not None, f"Cannot find package name for app {app_name}"
    
    return current_map[max_match['name']]


def get_list_of_package_names() -> list:
    """
    获取所有应用映射列表（实时读取）
    
    Returns:
        [{"app_name": "微信", "package_name": "com.tencent.mm"}, ...]
    """
    current_map = get_package_name_map()
    return [{"app_name": app_name, "package_name": package_name} 
            for app_name, package_name in current_map.items()]
