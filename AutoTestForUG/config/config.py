#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理模块
用于加载和管理AutoTestForUG系统的配置信息
"""

import configparser
import os
import logging
from typing import Dict, Any


def load_config(config_path: str = './config/config.ini') -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    config = configparser.ConfigParser(interpolation=None)
    
    # 检查配置文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    # 读取配置文件
    config.read(config_path, encoding='utf-8')
    
    # 将配置转换为字典格式
    config_dict = {}
    
    for section_name in config.sections():
        config_dict[section_name] = {}
        for key, value in config.items(section_name):
            # 尝试转换数据类型
            config_dict[section_name][key] = _convert_value(value)
    
    return config_dict


def _convert_value(value: str) -> Any:
    """
    尝试将字符串值转换为合适的数据类型
    
    Args:
        value: 字符串值
        
    Returns:
        转换后的值
    """
    # 尝试转换为整数
    try:
        if '.' not in value:
            return int(value)
    except ValueError:
        pass
    
    # 尝试转换为浮点数
    try:
        return float(value)
    except ValueError:
        pass
    
    # 尝试转换为布尔值
    if value.lower() in ['true', 'yes', 'on', '1']:
        return True
    elif value.lower() in ['false', 'no', 'off', '0']:
        return False
    
    # 返回原始字符串
    return value


def save_config(config_dict: Dict[str, Any], config_path: str = './config/config.ini'):
    """
    保存配置到文件
    
    Args:
        config_dict: 配置字典
        config_path: 配置文件路径
    """
    config = configparser.ConfigParser()
    
    # 将字典转换为ConfigParser格式
    for section_name, section_data in config_dict.items():
        config.add_section(section_name)
        for key, value in section_data.items():
            config.set(section_name, key, str(value))
    
    # 写入配置文件
    with open(config_path, 'w', encoding='utf-8') as configfile:
        config.write(configfile)


def get_config_value(config_dict: Dict[str, Any], section: str, key: str, default=None):
    """
    从配置字典中获取特定值
    
    Args:
        config_dict: 配置字典
        section: 配置节名称
        key: 配置键名称
        default: 默认值
        
    Returns:
        配置值
    """
    return config_dict.get(section, {}).get(key, default)


def update_config_value(config_dict: Dict[str, Any], section: str, key: str, value: Any):
    """
    更新配置字典中的特定值
    
    Args:
        config_dict: 配置字典
        section: 配置节名称
        key: 配置键名称
        value: 新值
    """
    if section not in config_dict:
        config_dict[section] = {}
    config_dict[section][key] = value


if __name__ == "__main__":
    # 设置日志记录
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # 测试配置加载功能
    try:
        config = load_config()
        logger.info("配置加载成功:")
        for section, values in config.items():
            logger.info(f"[{section}]")
            for key, value in values.items():
                logger.info(f"  {key} = {value} ({type(value).__name__})")
    except Exception as e:
        logger.error(f"配置加载失败: {e}")