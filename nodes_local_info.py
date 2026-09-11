import os
import sys
import configparser
import subprocess
import time
from pathlib import Path
import platform

def get_custom_nodes_path():
    """获取custom_nodes文件夹路径"""
    # 从launcher.ini文件获取ComfyUI路径
    launcher_ini = os.path.join('starter', 'launcher.ini')
    
    if os.path.exists(launcher_ini):
        config = configparser.ConfigParser()
        config.read(launcher_ini, encoding='utf-8')
        
        # 检查是否启用了自定义ComfyUI路径
        if config.has_section('paths') and config.has_option('paths', 'custom_comfyui_path_enabled'):
            custom_path_enabled = config.getboolean('paths', 'custom_comfyui_path_enabled')
            
            if custom_path_enabled and config.has_option('paths', 'comfyui_path'):
                comfyui_path = config.get('paths', 'comfyui_path')
                if comfyui_path:
                    # 如果是Python解释器路径，获取其上级目录的ComfyUI文件夹
                    if comfyui_path.endswith('python.exe'):
                        parent_dir = os.path.dirname(os.path.dirname(comfyui_path))
                        comfyui_path = os.path.join(parent_dir, "ComfyUI")
                    
                    custom_nodes_path = os.path.join(comfyui_path, "custom_nodes")
                    print(f"[调试-get_custom_nodes_path] 从launcher.ini获取路径: {custom_nodes_path}")
                    return custom_nodes_path
    
    # 如果无法从launcher.ini获取路径，使用默认路径
    # 处理PyInstaller打包后的路径问题
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件，使用应用程序所在目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行，使用当前工作目录
        base_path = os.getcwd()
            
    custom_nodes_path = os.path.join(base_path, "ComfyUI", "custom_nodes")
    print(f"[调试-get_custom_nodes_path] 使用默认路径: {custom_nodes_path}")
    return custom_nodes_path

def load_nodes_from_ini():
    """从ini文件加载节点列表"""
    nodes_list_ini = os.path.join('starter', 'nodes_list.ini')
    
    if not os.path.exists(nodes_list_ini):
        print(f"[调试-load_nodes_from_ini] 节点列表文件不存在")
        return [], []
    
    config = configparser.ConfigParser()
    config.read(nodes_list_ini, encoding='utf-8')
    
    enabled_nodes = []
    disabled_nodes = []
    
    # 读取启用的节点
    if config.has_section('enabled_nodes'):
        for key, value in config.items('enabled_nodes'):
            enabled_nodes.append(value)
    
    # 读取禁用的节点
    if config.has_section('disabled_nodes'):
        # 获取所有禁用节点的显示名称
        display_names = []
        original_names = []
        
        for key, value in config.items('disabled_nodes'):
            if key.endswith('_display'):
                display_names.append((key, value))
            elif key.endswith('_original'):
                original_names.append((key, value))
        
        # 将显示名称和原始名称配对
        for display_key, display_value in display_names:
            node_index = display_key.split('_')[1]
            original_key = f'node_{node_index}_original'
            
            # 查找对应的原始名称
            original_value = None
            for orig_key, orig_value in original_names:
                if orig_key == original_key:
                    original_value = orig_value
                    break
            
            if original_value:
                disabled_nodes.append((display_value, original_value))
    
    print(f"[调试-load_nodes_from_ini] 从ini文件加载节点列表，启用节点: {len(enabled_nodes)}个，禁用节点: {len(disabled_nodes)}个")
    return enabled_nodes, disabled_nodes

def get_proxy_settings():
    """从配置文件获取代理设置"""
    nodes_ini = os.path.join('starter', 'nodes.ini')
    git_ini = os.path.join('starter', 'git.ini')
    launcher_ini = os.path.join('starter', 'launcher.ini')
    
    # 默认设置
    proxy_enabled = False
    http_proxy = "127.0.0.1"
    proxy_port = "7890"
    proxy_type = "system"
    git_source = "GitHub官方(国外)"
    
    # 从nodes.ini获取代理设置
    if os.path.exists(nodes_ini):
        try:
            config = configparser.ConfigParser()
            config.read(nodes_ini, encoding='utf-8')
            
            if config.has_section('git'):
                if config.has_option('git', 'proxy_enabled'):
                    proxy_enabled = config.getboolean('git', 'proxy_enabled')
                if config.has_option('git', 'source'):
                    git_source = config.get('git', 'source')
        except Exception as e:
            print(f"[错误-get_proxy_settings] 读取nodes.ini失败: {str(e)}")
    
    # 从git.ini获取代理设置
    if os.path.exists(git_ini):
        try:
            config = configparser.ConfigParser()
            config.read(git_ini, encoding='utf-8')
            
            if config.has_section('git'):
                if config.has_option('git', 'proxy_enabled'):
                    proxy_enabled = config.getboolean('git', 'proxy_enabled')
                if config.has_option('git', 'source'):
                    git_source = config.get('git', 'source')
        except Exception as e:
            print(f"[错误-get_proxy_settings] 读取git.ini失败: {str(e)}")
    
    # 从launcher.ini获取代理设置
    if os.path.exists(launcher_ini):
        try:
            config = configparser.ConfigParser()
            config.read(launcher_ini, encoding='utf-8')
            
            if config.has_section('proxy'):
                if config.has_option('proxy', 'http_proxy'):
                    http_proxy = config.get('proxy', 'http_proxy')
                if config.has_option('proxy', 'port'):
                    proxy_port = config.get('proxy', 'port')
                if config.has_option('proxy', 'proxy_type'):
                    proxy_type = config.get('proxy', 'proxy_type')
        except Exception as e:
            print(f"[错误-get_proxy_settings] 读取launcher.ini失败: {str(e)}")
    
    return proxy_enabled, http_proxy, proxy_port, proxy_type, git_source

def update_nodes_version_info(single_node=None):
    """更新节点版本信息
    
    Args:
        single_node: 如果指定，只更新该节点的信息
    
    Returns:
        dict: 更新信息字典
    """
    try:
        # 获取custom_nodes路径
        custom_nodes_path = get_custom_nodes_path()
        if not os.path.exists(custom_nodes_path):
            print(f"[错误-update_nodes_version_info] custom_nodes路径不存在: {custom_nodes_path}")
            return {}
        
        # 获取节点列表
        enabled_nodes, disabled_nodes = load_nodes_from_ini()
        all_nodes = enabled_nodes.copy()
        for display_name, original_name in disabled_nodes:
            all_nodes.append(display_name)
        
        # 如果指定了单个节点，只更新该节点
        if single_node and single_node in all_nodes:
            nodes_to_update = [single_node]
        else:
            nodes_to_update = all_nodes
        
        # 创建或获取git_info部分
        nodes_list_git_ini = os.path.join('starter', 'nodes_list_git.ini')
        config = configparser.ConfigParser()
        
        # 如果文件存在，先读取现有内容
        if os.path.exists(nodes_list_git_ini):
            config.read(nodes_list_git_ini, encoding='utf-8')
        
        if not config.has_section('git_info'):
            config.add_section('git_info')
        
        # 更新节点版本信息
        total_nodes = len(nodes_to_update)
        for i, node_name in enumerate(nodes_to_update):
            # 只打印节点名称，不显示进度
            print(f"[节点] 正在处理: {node_name}")
            
            # 获取节点路径
            node_path = os.path.join(custom_nodes_path, node_name)
            
            # 检查节点是否存在
            if not os.path.exists(node_path):
                config.set('git_info', f'{node_name}_current_version', '非Git安装')
                config.set('git_info', f'{node_name}_last_commit_time', '无')
                config.set('git_info', f'{node_name}_has_update', 'False')
                continue
            
            # 检查是否是Git仓库
            git_dir = os.path.join(node_path, '.git')
            if not os.path.exists(git_dir):
                config.set('git_info', f'{node_name}_current_version', '非Git安装')
                config.set('git_info', f'{node_name}_last_commit_time', '无')
                config.set('git_info', f'{node_name}_has_update', 'False')
                continue
            
            try:
                # 创建隐藏控制台的startupinfo
                startupinfo = None
                if platform.system() == 'Windows':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                # 获取最新提交的哈希值
                git_cmd = ['git', '-C', node_path, 'rev-parse', '--short', 'HEAD']
                process = subprocess.Popen(git_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    config.set('git_info', f'{node_name}_current_version', 'Unknown')
                    config.set('git_info', f'{node_name}_last_commit_time', 'Unknown')
                    config.set('git_info', f'{node_name}_has_update', 'False')
                    continue
                
                commit_hash = stdout.strip()
                
                # 获取最新提交的日期
                git_cmd = ['git', '-C', node_path, 'show', '-s', '--format=%ci', 'HEAD']
                process = subprocess.Popen(git_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, startupinfo=startupinfo)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    config.set('git_info', f'{node_name}_current_version', commit_hash)
                    config.set('git_info', f'{node_name}_last_commit_time', 'Unknown')
                    config.set('git_info', f'{node_name}_has_update', 'False')
                    continue
                
                commit_date = stdout.strip()
                
                # 将日期转换为指定格式 (YYYY-MM-DD HH:MM:SS)
                try:
                    date_obj = time.strptime(commit_date, '%Y-%m-%d %H:%M:%S %z')
                    # 直接使用实际年份
                    formatted_date = time.strftime('%Y-%m-%d %H:%M:%S', date_obj)
                    
                    # 注释掉原来将年份加2000的代码
                    # future_year = date_obj.tm_year + 2000
                    # formatted_date = time.strftime(f'{future_year}-%m-%d %H:%M:%S', date_obj)
                except ValueError:
                    formatted_date = commit_date
                
                # 更新配置
                config.set('git_info', f'{node_name}_current_version', commit_hash)
                config.set('git_info', f'{node_name}_last_commit_time', formatted_date)
                config.set('git_info', f'{node_name}_has_update', 'False')
                
            except Exception as e:
                print(f"[错误-update_nodes_version_info] 获取节点 {node_name} 的Git信息失败: {str(e)}")
                config.set('git_info', f'{node_name}_current_version', 'Unknown')
                config.set('git_info', f'{node_name}_last_commit_time', 'Unknown')
                config.set('git_info', f'{node_name}_has_update', 'False')
        
        # 保存配置到nodes_list_git.ini文件
        with open(nodes_list_git_ini, 'w', encoding='utf-8') as f:
            config.write(f)
        
        print(f"[调试-update_nodes_version_info] 节点版本信息更新完成")
        
        # 读取更新后的节点版本信息
        return load_version_info_from_ini()
    
    except Exception as e:
        print(f"[错误-update_nodes_version_info] 更新节点版本信息失败: {str(e)}")
        return {}

def load_version_info_from_ini():
    """从ini文件加载节点版本信息
    
    Returns:
        dict: 版本信息字典，格式为 {node_name: {"version": "...", "date": "...", "has_update": bool}}
    """
    nodes_list_git_ini = os.path.join('starter', 'nodes_list_git.ini')
    version_info = {}
    
    if not os.path.exists(nodes_list_git_ini):
        print(f"[警告-load_version_info_from_ini] 节点Git信息文件不存在: {nodes_list_git_ini}")
        return version_info
    
    try:
        config = configparser.ConfigParser()
        config.read(nodes_list_git_ini, encoding='utf-8')
        
        if not config.has_section('git_info'):
            print(f"[警告-load_version_info_from_ini] 节点Git信息文件中没有git_info部分")
            return version_info
        
        # 获取所有节点的版本信息
        nodes = set()
        for key in config.options('git_info'):
            if key.endswith('_current_version'):
                node_name = key.replace('_current_version', '')
                nodes.add(node_name)
        
        for node_name in nodes:
            node_info = {}
            
            # 获取版本信息
            if config.has_option('git_info', f'{node_name}_current_version'):
                version = config.get('git_info', f'{node_name}_current_version')
                node_info['version'] = version
            else:
                node_info['version'] = "需刷新"
            
            # 获取日期信息
            if config.has_option('git_info', f'{node_name}_last_commit_time'):
                date = config.get('git_info', f'{node_name}_last_commit_time')
                node_info['date'] = date
            else:
                node_info['date'] = "需刷新"
            
            # 获取更新状态
            if config.has_option('git_info', f'{node_name}_has_update'):
                has_update = config.getboolean('git_info', f'{node_name}_has_update')
                node_info['has_update'] = has_update
            else:
                node_info['has_update'] = False
            
            version_info[node_name] = node_info
    
    except Exception as e:
        print(f"[错误-load_version_info_from_ini] 加载节点版本信息失败: {str(e)}")
    
    return version_info

def apply_version_info_to_ui(nodes_list_widget, version_info):
    """将版本信息应用到UI
    
    Args:
        nodes_list_widget: 节点列表控件
        version_info: 版本信息字典
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from qfluentwidgets import BodyLabel, InfoBar, InfoBarPosition
    
    update_count = 0
    
    # 应用版本信息到UI
    for i in range(nodes_list_widget.count()):
        item = nodes_list_widget.item(i)
        if item:
            data = item.data(Qt.UserRole)
            if data and isinstance(data, dict):
                display_name = data.get("display_name", "")
                
                # 检查该节点是否有版本信息
                if display_name in version_info:
                    node_info = version_info[display_name]
                    
                    # 检查该节点是否有更新
                    if node_info.get('has_update', False):
                        update_count += 1
                        
                        # 获取节点控件
                        widget = nodes_list_widget.itemWidget(item)
                        if widget:
                            # 查找名称标签
                            for child in widget.findChildren(BodyLabel):
                                if hasattr(child, 'property') and child.property("original_text"):
                                    # 设置为feb201颜色
                                    child.setStyleSheet("color: #feb201; font-weight: bold;")
                                    # 强制应用样式
                                    child.style().unpolish(child)
                                    child.style().polish(child)
                                    child.update()  # 强制更新显示
                                    break
    
    # 只有在有更新时才显示信息
    if update_count > 0:
        parent = nodes_list_widget.parent()
        InfoBar.success(
            title="更新检查完成",
            content=f"发现 {update_count} 个节点有可用更新",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=3000,
            parent=parent
        )

def get_node_git_version_and_date(node_path):
    """获取节点的Git版本和日期信息
    
    Args:
        node_path: 节点路径
        
    Returns:
        tuple: (版本, 日期时间)
    """
    try:
        # 获取节点名称
        node_name = os.path.basename(node_path)
        
        # 从ini文件加载版本信息
        nodes_list_git_ini = os.path.join('starter', 'nodes_list_git.ini')
        
        if not os.path.exists(nodes_list_git_ini):
            print(f"[警告-get_node_git_version_and_date] 节点Git信息文件不存在: {nodes_list_git_ini}")
            return "需刷新", "需刷新"
        
        config = configparser.ConfigParser()
        config.read(nodes_list_git_ini, encoding='utf-8')
        
        if not config.has_section('git_info'):
            print(f"[警告-get_node_git_version_and_date] 节点Git信息文件中没有git_info部分")
            return "需刷新", "需刷新"
        
        # 获取版本信息
        version = "需刷新"
        date_time = "需刷新"
        
        if config.has_option('git_info', f'{node_name}_current_version'):
            version = config.get('git_info', f'{node_name}_current_version')
        
        if config.has_option('git_info', f'{node_name}_last_commit_time'):
            date_time = config.get('git_info', f'{node_name}_last_commit_time')
        
        return version, date_time
    
    except Exception as e:
        print(f"[错误-get_node_git_version_and_date] 获取节点Git版本和日期失败: {str(e)}")
        return "获取失败", "获取失败"

def main():
    """主函数，用于命令行调用"""
    import argparse
    import platform
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='更新节点版本信息')
    parser.add_argument('--single', type=str, help='只更新指定的单个节点')
    args = parser.parse_args()
    
    # 在Windows上隐藏控制台窗口
    if platform.system() == 'Windows':
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    print("开始更新节点版本信息...")
    
    # 更新节点版本信息
    update_nodes_version_info(args.single)
    
    print("节点版本信息更新完成")

if __name__ == "__main__":
    main()