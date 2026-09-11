import json
import os
import configparser
from pathlib import Path

class DataModel:
    def __init__(self):
        # 确保starter目录存在
        os.makedirs('starter', exist_ok=True)
        self.config_file = os.path.join('starter', 'launcher.ini')
        self.config = configparser.ConfigParser()
        
        # 默认设置
        self.default_settings = {
            'proxy': {
                'enabled': False,
                'proxy_type': 'system',  # 新增：代理类型，可选值：system（系统代理）或socks5
                'http_proxy': '127.0.0.1',
                'https_proxy': '127.0.0.1',
                'port': '7897',
                'only_for_startup': True  # 新增：代理设置只对启动面板生效
            },
            'network': {
                'lan_access': False,
                'listen': '0.0.0.0',
                'port': '8188',
                'custom_port_enabled': False
            },
            'performance': {
                'advanced_enabled': False
            },
            'paths': {
                'custom_comfyui_path_enabled': False,
                'comfyui_path': ''
            },
            'advanced': {
                'output_dir_enabled': False,
                'output_dir': '',
                'input_dir_enabled': False,
                'input_dir': '',
                'vram_enabled': False,  # 是否启用显存模式设置
                'vram_mode': 'normal',  # 可选值: gpu_only, high, normal, low, no, cpu
                'disable_metadata': False,
                'restart_command_intercept_enabled': True,  # 是否启用重启命令接管
                'restart_command_keyword': 'Restarting...'  # 重启命令关键词
            }
        }
        
        # 加载配置文件，如果不存在则创建默认配置
        self.load_config()
    
    def load_config(self):
        """加载配置文件，如果不存在则使用默认配置"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            # 使用默认配置
            for section, options in self.default_settings.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                for key, value in options.items():
                    self.config.set(section, key, str(value))
            # 保存默认配置到文件
            self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_value(self, section, key, default=None):
        """获取配置值"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def set_value(self, section, key, value):
        """设置配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
    
    def get_bool(self, section, key, default=False):
        """获取布尔值配置"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default
    
    def check_python_embedded(self):
        """检查python.exe是否存在"""
        # 检查是否启用了自定义Python路径
        if self.get_bool('paths', 'custom_comfyui_path_enabled'):
            custom_path = self.get_value('paths', 'comfyui_path')
            if custom_path:
                # 直接使用自定义的python.exe路径
                return Path(custom_path).exists()
        
        # 默认路径检查
        python_exe = Path('python_embeded/python.exe')
        return python_exe.exists()
        
    def get_comfyui_path(self):
        """获取ComfyUI路径"""
        if self.get_bool('paths', 'custom_comfyui_path_enabled'):
            return self.get_value('paths', 'comfyui_path')
        return ''


class NodesDataModel:
    """节点面板数据模型，用于处理节点面板的设置"""
    def __init__(self):
        # 确保starter目录存在
        os.makedirs('starter', exist_ok=True)
        self.config_file = os.path.join('starter', 'nodes.ini')
        self.config = configparser.ConfigParser()
        
        # 默认设置
        self.default_settings = {
            'pip_mirror': {
                # 'enabled': True, # 这个参数不需要了。
                'mirror_name': '清华大学-更新及时',
                'mirror_source': '-i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn',
                'proxy_enabled': False
            },
            'git': {
                'proxy_enabled': False,
                'source': 'GitHub官方(国外)'
            }
        }
        
        # 加载配置文件，如果不存在则创建默认配置
        self.load_config()
    
    def load_config(self):
        """加载配置文件，如果不存在则使用默认配置"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            # 使用默认配置
            for section, options in self.default_settings.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                for key, value in options.items():
                    self.config.set(section, key, str(value))
            # 保存默认配置到文件
            self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_value(self, section, key, default=None):
        """获取配置值"""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default
    
    def set_value(self, section, key, value):
        """设置配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
    
    def get_bool(self, section, key, default=False):
        """获取布尔值配置"""
        try:
            return self.config.getboolean(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return default