"""
SIP客户端增强配置管理模块
提供灵活的配置管理、验证和动态更新功能
"""

import json
import yaml
import configparser
from typing import Dict, Any, Optional, Union
from pathlib import Path
import os
import logging
from dataclasses import dataclass, asdict
from copy import deepcopy


@dataclass
class SIPConfig:
    """
    SIP配置数据类
    定义SIP客户端的标准配置参数
    """
    # 服务器配置
    sip_server_host: str = "127.0.0.1"
    sip_server_port: int = 5060
    sip_transport: str = "UDP"
    
    # 本地配置
    local_host: str = "127.0.0.1"
    local_port: int = 5080
    
    # 用户认证配置
    username: str = "test"
    password: str = "password"
    realm: Optional[str] = None
    
    # 超时和重试配置
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    
    # 注册配置
    register_enabled: bool = True
    register_expires: int = 3600
    
    # 呼叫配置
    call_duration: int = 30
    enable_rtcp: bool = True
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "sip_client.log"
    enable_debug: bool = False
    
    # 性能配置
    max_concurrent_calls: int = 10
    buffer_size: int = 8192
    
    # 安全配置
    enable_tls: bool = False
    verify_certificate: bool = True
    certificate_path: Optional[str] = None


class ConfigValidator:
    """
    配置验证器
    验证配置参数的有效性
    """
    
    @staticmethod
    def validate_host(host: str) -> bool:
        """验证主机地址格式"""
        import re
        # IP地址或域名的基本验证
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9](\.[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9])*\.?$'
        return bool(re.match(ip_pattern, host) or re.match(domain_pattern, host))
    
    @staticmethod
    def validate_port(port: int) -> bool:
        """验证端口号范围"""
        return 1 <= port <= 65535
    
    @staticmethod
    def validate_transport(transport: str) -> bool:
        """验证传输协议"""
        return transport.upper() in ['UDP', 'TCP', 'TLS', 'WS', 'WSS']
    
    @staticmethod
    def validate_timeout(timeout: int) -> bool:
        """验证超时时间"""
        return 1 <= timeout <= 300
    
    @staticmethod
    def validate_log_level(level: str) -> bool:
        """验证日志级别"""
        return level.upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    @classmethod
    def validate_config(cls, config: SIPConfig) -> Dict[str, list]:
        """验证整个配置对象"""
        errors = []
        warnings = []
        
        # 验证主机地址
        if not cls.validate_host(config.sip_server_host):
            errors.append(f"无效的SIP服务器主机地址: {config.sip_server_host}")
        
        if not cls.validate_host(config.local_host):
            errors.append(f"无效的本地主机地址: {config.local_host}")
        
        # 验证端口
        if not cls.validate_port(config.sip_server_port):
            errors.append(f"无效的SIP服务器端口: {config.sip_server_port}")
        
        if not cls.validate_port(config.local_port):
            errors.append(f"无效的本地端口: {config.local_port}")
        
        # 验证传输协议
        if not cls.validate_transport(config.sip_transport):
            errors.append(f"无效的传输协议: {config.sip_transport}")
        
        # 验证超时时间
        if not cls.validate_timeout(config.timeout):
            errors.append(f"超时时间超出范围 (1-300): {config.timeout}")
        
        # 验证日志级别
        if not cls.validate_log_level(config.log_level):
            errors.append(f"无效的日志级别: {config.log_level}")
        
        # 检查潜在问题（警告）
        if config.local_port == config.sip_server_port:
            warnings.append("本地端口与服务器端口相同，可能导致冲突")
        
        if config.timeout < 5:
            warnings.append("超时时间过短，可能导致频繁超时")
        
        if config.max_retries < 1:
            warnings.append("重试次数过少")
        
        return {
            'errors': errors,
            'warnings': warnings
        }


class ConfigurationManager:
    """
    配置管理器
    处理配置的加载、保存、验证和动态更新
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.default_config = SIPConfig()
        self.current_config = deepcopy(self.default_config)
        self.config_history = [deepcopy(self.current_config)]
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 如果提供了配置文件路径，尝试加载配置
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            bool: 加载是否成功
        """
        try:
            path = Path(config_path)
            if not path.exists():
                self.logger.warning(f"配置文件不存在: {config_path}")
                return False
            
            # 根据文件扩展名选择解析器
            if path.suffix.lower() == '.json':
                return self._load_json_config(config_path)
            elif path.suffix.lower() in ['.yaml', '.yml']:
                return self._load_yaml_config(config_path)
            elif path.suffix.lower() == '.ini':
                return self._load_ini_config(config_path)
            else:
                self.logger.error(f"不支持的配置文件格式: {path.suffix}")
                return False
                
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            return False
    
    def _load_json_config(self, config_path: str) -> bool:
        """加载JSON格式的配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            # 更新当前配置
            for key, value in config_dict.items():
                if hasattr(self.current_config, key):
                    setattr(self.current_config, key, value)
            
            self.config_history.append(deepcopy(self.current_config))
            self.logger.info(f"成功从JSON文件加载配置: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"加载JSON配置失败: {str(e)}")
            return False
    
    def _load_yaml_config(self, config_path: str) -> bool:
        """加载YAML格式的配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            # 更新当前配置
            for key, value in config_dict.items():
                if hasattr(self.current_config, key):
                    setattr(self.current_config, key, value)
            
            self.config_history.append(deepcopy(self.current_config))
            self.logger.info(f"成功从YAML文件加载配置: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"加载YAML配置失败: {str(e)}")
            return False
    
    def _load_ini_config(self, config_path: str) -> bool:
        """加载INI格式的配置"""
        try:
            config_parser = configparser.ConfigParser()
            config_parser.read(config_path, encoding='utf-8')
            
            # 从DEFAULT节读取配置
            if 'DEFAULT' in config_parser:
                defaults = config_parser['DEFAULT']
                for key in defaults:
                    if hasattr(self.current_config, key):
                        value = self._convert_value(defaults[key], getattr(self.current_config, key))
                        setattr(self.current_config, key, value)
            
            # 从SIP_CLIENT节读取配置
            if 'SIP_CLIENT' in config_parser:
                sip_config = config_parser['SIP_CLIENT']
                for key in sip_config:
                    if hasattr(self.current_config, key):
                        value = self._convert_value(sip_config[key], getattr(self.current_config, key))
                        setattr(self.current_config, key, value)
            
            self.config_history.append(deepcopy(self.current_config))
            self.logger.info(f"成功从INI文件加载配置: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"加载INI配置失败: {str(e)}")
            return False
    
    def _convert_value(self, value_str: str, default_value):
        """将字符串值转换为适当的数据类型"""
        if isinstance(default_value, bool):
            return value_str.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default_value, int):
            try:
                return int(value_str)
            except ValueError:
                return default_value
        elif isinstance(default_value, float):
            try:
                return float(value_str)
            except ValueError:
                return default_value
        else:
            return value_str
    
    def save_config(self, config_path: str, format_type: str = 'json') -> bool:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
            format_type: 文件格式 ('json', 'yaml', 'ini')
            
        Returns:
            bool: 保存是否成功
        """
        try:
            config_dict = asdict(self.current_config)
            
            path = Path(config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type.lower() == 'json':
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)
            elif format_type.lower() == 'yaml':
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            elif format_type.lower() == 'ini':
                config_parser = configparser.ConfigParser()
                config_parser['DEFAULT'] = {}
                for key, value in config_dict.items():
                    config_parser['DEFAULT'][key] = str(value)
                
                with open(path, 'w', encoding='utf-8') as f:
                    config_parser.write(f)
            else:
                self.logger.error(f"不支持的配置格式: {format_type}")
                return False
            
            self.logger.info(f"成功保存配置到文件: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def validate_config(self) -> Dict[str, list]:
        """
        验证当前配置
        
        Returns:
            Dict: 验证结果，包含错误和警告
        """
        return ConfigValidator.validate_config(self.current_config)
    
    def update_config(self, **kwargs) -> Dict[str, list]:
        """
        动态更新配置参数
        
        Args:
            **kwargs: 配置参数键值对
            
        Returns:
            Dict: 验证结果
        """
        # 保存当前配置到历史
        self.config_history.append(deepcopy(self.current_config))
        
        # 更新配置参数
        for key, value in kwargs.items():
            if hasattr(self.current_config, key):
                setattr(self.current_config, key, value)
            else:
                self.logger.warning(f"未知的配置参数: {key}")
        
        # 验证更新后的配置
        validation_result = self.validate_config()
        
        if validation_result['errors']:
            self.logger.error(f"配置更新包含错误: {validation_result['errors']}")
            # 回滚到上一个配置
            self.config_history.pop()  # 移除刚才添加的配置
            self.current_config = self.config_history[-1]  # 恢复到上一个配置
        else:
            self.logger.info("配置更新成功")
        
        return validation_result
    
    def get_config_dict(self) -> Dict[str, Any]:
        """
        获取配置字典
        
        Returns:
            Dict: 配置参数字典
        """
        return asdict(self.current_config)
    
    def reset_to_default(self):
        """重置配置为默认值"""
        self.current_config = deepcopy(self.default_config)
        self.config_history.append(deepcopy(self.current_config))
        self.logger.info("配置已重置为默认值")
    
    def rollback_config(self) -> bool:
        """
        回滚到上一个配置
        
        Returns:
            bool: 回滚是否成功
        """
        if len(self.config_history) > 1:
            self.config_history.pop()  # 移除当前配置
            self.current_config = self.config_history[-1]  # 恢复到上一个配置
            self.logger.info("配置已回滚到上一个版本")
            return True
        else:
            self.logger.warning("没有可回滚的配置版本")
            return False
    
    def create_sample_config(self, config_path: str, format_type: str = 'json'):
        """
        创建示例配置文件
        
        Args:
            config_path: 配置文件路径
            format_type: 文件格式
        """
        sample_config = {
            "sip_server_host": "192.168.1.100",
            "sip_server_port": 5060,
            "sip_transport": "UDP",
            "local_host": "192.168.1.101",
            "local_port": 5080,
            "username": "alice",
            "password": "secret123",
            "timeout": 30,
            "max_retries": 3,
            "register_expires": 3600,
            "call_duration": 60,
            "log_level": "INFO",
            "log_file": "sip_client.log",
            "max_concurrent_calls": 50
        }
        
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format_type.lower() == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(sample_config, f, ensure_ascii=False, indent=2)
        elif format_type.lower() == 'yaml':
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)
        elif format_type.lower() == 'ini':
            config_parser = configparser.ConfigParser()
            config_parser['DEFAULT'] = sample_config
            with open(path, 'w', encoding='utf-8') as f:
                config_parser.write(f)


class DynamicConfigManager(ConfigurationManager):
    """
    动态配置管理器
    支持运行时配置更新和热重载
    """
    
    def __init__(self, config_path: Optional[str] = None, auto_reload: bool = True):
        super().__init__(config_path)
        self.auto_reload = auto_reload
        self.last_modified_time = 0
        self.config_file_path = config_path
    
    def check_config_changes(self) -> bool:
        """
        检查配置文件是否有更改
        
        Returns:
            bool: 是否有更改
        """
        if not self.config_file_path:
            return False
        
        try:
            current_mtime = os.path.getmtime(self.config_file_path)
            if current_mtime > self.last_modified_time:
                self.last_modified_time = current_mtime
                return True
            return False
        except OSError:
            return False
    
    def hot_reload_config(self) -> bool:
        """
        热重载配置文件
        
        Returns:
            bool: 重载是否成功
        """
        if self.check_config_changes():
            self.logger.info("检测到配置文件更改，正在重载...")
            temp_config = deepcopy(self.current_config)
            
            if self.load_config(self.config_file_path):
                validation_result = self.validate_config()
                if not validation_result['errors']:
                    self.logger.info("配置热重载成功")
                    return True
                else:
                    self.logger.error(f"重载的配置包含错误: {validation_result['errors']}")
                    # 恢复之前的配置
                    self.current_config = temp_config
                    return False
            else:
                self.logger.error("配置热重载失败")
                return False
        return False


# 全局配置管理器实例
config_manager = DynamicConfigManager()


def get_sip_config() -> SIPConfig:
    """
    获取当前SIP配置
    
    Returns:
        SIPConfig: 当前配置对象
    """
    return config_manager.current_config


def update_sip_config(**kwargs) -> bool:
    """
    更新SIP配置
    
    Args:
        **kwargs: 配置参数
        
    Returns:
        bool: 更新是否成功
    """
    validation_result = config_manager.update_config(**kwargs)
    return len(validation_result['errors']) == 0


def load_config_from_file(config_path: str) -> bool:
    """
    从文件加载配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        bool: 加载是否成功
    """
    return config_manager.load_config(config_path)


def save_config_to_file(config_path: str, format_type: str = 'json') -> bool:
    """
    保存配置到文件
    
    Args:
        config_path: 配置文件路径
        format_type: 文件格式
        
    Returns:
        bool: 保存是否成功
    """
    return config_manager.save_config(config_path, format_type)