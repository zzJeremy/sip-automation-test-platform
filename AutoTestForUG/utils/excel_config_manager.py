#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Excel配置文件管理模块
提供标准化的Excel文件读取和写入接口，支持读取账号、密码、手机号等配置信息
"""
import os
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
import copy
from threading import Lock

from utils.utils import get_current_timestamp


class ExcelConfigManager:
    """
    Excel配置文件管理器
    提供标准化的Excel文件读取和写入接口，支持配置数据的缓存机制
    """
    
    def __init__(self, file_path: str = "号码配置.xlsx", auto_load: bool = True):
        """
        初始化配置管理器
        
        Args:
            file_path: Excel文件路径
            auto_load: 是否自动加载配置文件
        """
        self.file_path = file_path
        self.data_cache = None
        self.cache_timestamp = None
        self._lock = Lock()
        self.logger = self._setup_logger()
        
        if auto_load:
            self.load_config()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def load_config(self, force_reload: bool = False) -> bool:
        """
        加载Excel配置文件
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            加载是否成功
        """
        try:
            with self._lock:
                if not force_reload and self.data_cache is not None:
                    # 检查文件是否已被修改
                    if os.path.exists(self.file_path):
                        file_mtime = os.path.getmtime(self.file_path)
                        if self.cache_timestamp and file_mtime <= self.cache_timestamp:
                            self.logger.info(f"配置文件缓存仍然有效，无需重新加载: {self.file_path}")
                            return True
                
                # 检查文件是否存在
                if not os.path.exists(self.file_path):
                    self.logger.error(f"配置文件不存在: {self.file_path}")
                    return False
                
                # 读取Excel文件
                self.logger.info(f"正在加载Excel配置文件: {self.file_path}")
                df = pd.read_excel(self.file_path)
                
                # 验证必要的列是否存在
                required_columns = ['FXS账号', 'IP账号', '手机号码', '密码', '密码类型']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    self.logger.error(f"配置文件缺少必要列: {missing_columns}")
                    return False
                
                # 存储到缓存
                self.data_cache = df.copy()
                self.cache_timestamp = os.path.getmtime(self.file_path)
                
                self.logger.info(f"成功加载配置文件，共 {len(df)} 条记录")
                return True
                
        except Exception as e:
            self.logger.error(f"加载Excel配置文件失败: {str(e)}")
            return False
    
    def save_config(self, data: Optional[pd.DataFrame] = None, backup: bool = True) -> bool:
        """
        保存配置到Excel文件
        
        Args:
            data: 要保存的数据，如果为None则使用缓存数据
            backup: 是否备份原文件
            
        Returns:
            保存是否成功
        """
        try:
            with self._lock:
                if backup and os.path.exists(self.file_path):
                    # 创建备份文件
                    backup_path = f"{self.file_path}.backup_{get_current_timestamp().replace(' ', '_').replace(':', '-')}"
                    import shutil
                    shutil.copy2(self.file_path, backup_path)
                    self.logger.info(f"已创建备份文件: {backup_path}")
                
                # 确定要保存的数据
                save_data = data if data is not None else self.data_cache
                
                if save_data is None:
                    self.logger.error("没有数据可以保存")
                    return False
                
                # 保存到Excel文件
                with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                    save_data.to_excel(writer, sheet_name='账号配置', index=False)
                    
                    # 获取工作表对象以设置列宽
                    worksheet = writer.sheets['账号配置']
                    
                    # 设置列宽
                    column_widths = {
                        'A': 15,  # FXS账号
                        'B': 15,  # IP账号
                        'C': 15,  # 手机号码
                        'D': 20,  # 密码
                        'E': 30   # 密码类型
                    }
                    
                    for col, width in column_widths.items():
                        worksheet.column_dimensions[col].width = width
                
                self.logger.info(f"配置文件已保存: {self.file_path}")
                
                # 更新缓存时间戳
                self.cache_timestamp = os.path.getmtime(self.file_path)
                
                return True
                
        except Exception as e:
            self.logger.error(f"保存Excel配置文件失败: {str(e)}")
            return False
    
    def backup_config(self, backup_path: Optional[str] = None) -> str:
        """
        备份配置文件到指定路径
        
        Args:
            backup_path: 备份文件路径，如果为None则自动生成
            
        Returns:
            备份文件路径
        """
        import shutil
        from datetime import datetime
        
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.file_path}.backup_{timestamp}"
        
        if os.path.exists(self.file_path):
            shutil.copy2(self.file_path, backup_path)
            self.logger.info(f"配置文件已备份到: {backup_path}")
            return backup_path
        else:
            self.logger.error(f"源配置文件不存在: {self.file_path}")
            raise FileNotFoundError(f"源配置文件不存在: {self.file_path}")
    
    def restore_config(self, backup_path: str) -> bool:
        """
        从备份文件恢复配置
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            恢复是否成功
        """
        import shutil
        
        if not os.path.exists(backup_path):
            self.logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        try:
            # 备份当前文件以防万一
            if os.path.exists(self.file_path):
                recovery_backup = f"{self.file_path}.recovery_backup_{get_current_timestamp().replace(' ', '_').replace(':', '-')}"
                shutil.copy2(self.file_path, recovery_backup)
                self.logger.info(f"已创建恢复前备份: {recovery_backup}")
            
            # 恢复备份文件
            shutil.copy2(backup_path, self.file_path)
            self.logger.info(f"已从备份恢复配置文件: {backup_path} -> {self.file_path}")
            
            # 清除缓存以强制重新加载
            self.clear_cache()
            
            return True
        except Exception as e:
            self.logger.error(f"恢复配置文件失败: {str(e)}")
            return False
    
    def list_backups(self) -> List[str]:
        """
        列出所有备份文件
        
        Returns:
            备份文件路径列表
        """
        import glob
        
        backup_pattern = f"{self.file_path}.backup_*"
        backups = glob.glob(backup_pattern)
        
        # 按修改时间排序，最新的在前
        backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        self.logger.info(f"找到 {len(backups)} 个备份文件")
        return backups
    
    def get_all_accounts(self) -> Optional[pd.DataFrame]:
        """
        获取所有账号配置信息
        
        Returns:
            账号配置DataFrame，失败时返回None
        """
        if self.data_cache is None:
            if not self.load_config():
                return None
        return self.data_cache.copy()
    
    def get_account_by_number(self, account_number: str) -> Optional[Dict[str, Any]]:
        """
        根据账号号码获取配置信息
        
        Args:
            account_number: 账号号码
            
        Returns:
            账号配置信息字典，不存在时返回None
        """
        if self.data_cache is None:
            if not self.load_config():
                return None
        
        # 查找FXS账号或IP账号匹配的记录
        # 需要考虑从Excel读取的数据可能是float类型
        def is_matching_account(account_val, target_account):
            if pd.isna(account_val) or str(account_val).lower() == 'nan':
                return False
            if str(account_val) == target_account:
                return True
            if isinstance(account_val, float) and str(int(account_val)) == target_account:
                return True
            return False
        
        mask = (
            self.data_cache.apply(lambda row: is_matching_account(row['FXS账号'], account_number), axis=1) |
            self.data_cache.apply(lambda row: is_matching_account(row['IP账号'], account_number), axis=1)
        )
        
        result_df = self.data_cache[mask]
        
        if len(result_df) == 0:
            return None
        
        # 返回第一条匹配记录
        row = result_df.iloc[0]
        # 将可能的浮点数转换为整数字符串
        fxs_account = ''
        if pd.notna(row['FXS账号']) and str(row['FXS账号']).lower() != 'nan':
            fxs_val = row['FXS账号']
            if isinstance(fxs_val, float) and fxs_val.is_integer():
                fxs_account = str(int(fxs_val))
            else:
                fxs_account = str(fxs_val)
        
        ip_account = ''
        if pd.notna(row['IP账号']) and str(row['IP账号']).lower() != 'nan':
            ip_val = row['IP账号']
            if isinstance(ip_val, float) and ip_val.is_integer():
                ip_account = str(int(ip_val))
            else:
                ip_account = str(ip_val)
        
        mobile_number = ''
        if pd.notna(row['手机号码']) and str(row['手机号码']).lower() != 'nan':
            mobile_val = row['手机号码']
            if isinstance(mobile_val, float) and mobile_val.is_integer():
                mobile_number = str(int(mobile_val))
            else:
                mobile_number = str(mobile_val)
        
        password = str(row['密码']) if pd.notna(row['密码']) else ''
        password_type = str(row['密码类型']) if pd.notna(row['密码类型']) else ''
        
        return {
            'FXS账号': fxs_account,
            'IP账号': ip_account, 
            '手机号码': mobile_number,
            '密码': password,
            '密码类型': password_type
        }
    
    def get_mobile_number_by_account(self, account_number: str) -> Optional[str]:
        """
        根据账号获取对应的手机号码
        
        Args:
            account_number: 账号号码
            
        Returns:
            手机号码，不存在时返回None
        """
        account_info = self.get_account_by_number(account_number)
        if account_info:
            return account_info['手机号码']
        return None
    
    def get_password_by_account(self, account_number: str) -> Optional[str]:
        """
        根据账号获取对应的密码
        
        Args:
            account_number: 账号号码
            
        Returns:
            密码，不存在时返回None
        """
        account_info = self.get_account_by_number(account_number)
        if account_info:
            return account_info['密码']
        return None
    
    def get_fxs_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有FXS账号
        
        Returns:
            FXS账号列表
        """
        if self.data_cache is None:
            if not self.load_config():
                return []
        
        fxs_mask = self.data_cache['FXS账号'].notna() & (self.data_cache['FXS账号'] != '') & (self.data_cache['FXS账号'] != 'nan')
        fxs_df = self.data_cache[fxs_mask]
        
        result = []
        for _, row in fxs_df.iterrows():
            # 处理数据类型
            fxs_account = ''
            if pd.notna(row['FXS账号']) and str(row['FXS账号']).lower() != 'nan':
                fxs_val = row['FXS账号']
                if isinstance(fxs_val, float) and fxs_val.is_integer():
                    fxs_account = str(int(fxs_val))
                else:
                    fxs_account = str(fxs_val)
            
            mobile_number = ''
            if pd.notna(row['手机号码']) and str(row['手机号码']).lower() != 'nan':
                mobile_val = row['手机号码']
                if isinstance(mobile_val, float) and mobile_val.is_integer():
                    mobile_number = str(int(mobile_val))
                else:
                    mobile_number = str(mobile_val)
            
            password = str(row['密码']) if pd.notna(row['密码']) else ''
            password_type = str(row['密码类型']) if pd.notna(row['密码类型']) else ''
            
            result.append({
                'FXS账号': fxs_account,
                '手机号码': mobile_number,
                '密码': password,
                '密码类型': password_type
            })
        
        return result
    
    def get_ip_accounts(self) -> List[Dict[str, Any]]:
        """
        获取所有IP账号
        
        Returns:
            IP账号列表
        """
        if self.data_cache is None:
            if not self.load_config():
                return []
        
        ip_mask = self.data_cache['IP账号'].notna() & (self.data_cache['IP账号'] != '') & (self.data_cache['IP账号'] != 'nan')
        ip_df = self.data_cache[ip_mask]
        
        result = []
        for _, row in ip_df.iterrows():
            # 处理数据类型
            ip_account = ''
            if pd.notna(row['IP账号']) and str(row['IP账号']).lower() != 'nan':
                ip_val = row['IP账号']
                if isinstance(ip_val, float) and ip_val.is_integer():
                    ip_account = str(int(ip_val))
                else:
                    ip_account = str(ip_val)
            
            mobile_number = ''
            if pd.notna(row['手机号码']) and str(row['手机号码']).lower() != 'nan':
                mobile_val = row['手机号码']
                if isinstance(mobile_val, float) and mobile_val.is_integer():
                    mobile_number = str(int(mobile_val))
                else:
                    mobile_number = str(mobile_val)
            
            password = str(row['密码']) if pd.notna(row['密码']) else ''
            password_type = str(row['密码类型']) if pd.notna(row['密码类型']) else ''
            
            result.append({
                'IP账号': ip_account,
                '手机号码': mobile_number,
                '密码': password,
                '密码类型': password_type
            })
        
        return result
    
    def update_account_password(self, account_number: str, new_password: str, 
                              password_type: str = "自定义密码") -> bool:
        """
        更新账号密码
        
        Args:
            account_number: 账号号码
            new_password: 新密码
            password_type: 密码类型描述
            
        Returns:
            更新是否成功
        """
        if self.data_cache is None:
            if not self.load_config():
                return False
        
        # 查找并更新记录，需要考虑数据类型差异
        def is_matching_account(account_val, target_account):
            if pd.isna(account_val) or str(account_val).lower() == 'nan':
                return False
            if str(account_val) == target_account:
                return True
            if isinstance(account_val, float) and str(int(account_val)) == target_account:
                return True
            return False
        
        mask = (
            self.data_cache.apply(lambda row: is_matching_account(row['FXS账号'], account_number), axis=1) |
            self.data_cache.apply(lambda row: is_matching_account(row['IP账号'], account_number), axis=1)
        )
        
        if mask.any():
            idx = self.data_cache[mask].index[0]
            self.data_cache.loc[idx, '密码'] = new_password
            self.data_cache.loc[idx, '密码类型'] = password_type
            
            self.logger.info(f"账号 {account_number} 的密码已更新")
            return True
        else:
            self.logger.warning(f"账号 {account_number} 未找到，无法更新密码")
            return False
    
    def add_new_account(self, account_number: str, phone_number: str, password: str, 
                       password_type: str = "新增账号", is_fxs: bool = True) -> bool:
        """
        添加新账号
        
        Args:
            account_number: 账号号码
            phone_number: 手机号码
            password: 密码
            password_type: 密码类型
            is_fxs: 是否为FXS账号，否则为IP账号
            
        Returns:
            添加是否成功
        """
        if self.data_cache is None:
            if not self.load_config():
                return False
        
        try:
            new_row = {
                'FXS账号': account_number if is_fxs else "",
                'IP账号': account_number if not is_fxs else "",
                '手机号码': phone_number,
                '密码': password,
                '密码类型': password_type
            }
            
            # 将新行添加到数据框
            self.data_cache = pd.concat([self.data_cache, pd.DataFrame([new_row])], 
                                      ignore_index=True)
            
            self.logger.info(f"新账号 {account_number} 已添加")
            return True
            
        except Exception as e:
            self.logger.error(f"添加新账号失败: {str(e)}")
            return False
    
    def validate_config_data(self) -> Dict[str, Any]:
        """
        验证配置数据的完整性
        
        Returns:
            验证结果字典
        """
        if self.data_cache is None:
            if not self.load_config():
                return {'valid': False, 'errors': ['配置文件加载失败']}
        
        errors = []
        warnings = []
        
        # 验证必要列
        required_columns = ['FXS账号', 'IP账号', '手机号码', '密码', '密码类型']
        missing_columns = [col for col in required_columns if col not in self.data_cache.columns]
        if missing_columns:
            errors.append(f"缺少必要列: {missing_columns}")
        
        # 验证数据行数
        if len(self.data_cache) == 0:
            errors.append("配置文件为空")
        
        # 验证账号格式和唯一性
        all_accounts = []
        fxs_accounts = self.data_cache['FXS账号'].dropna().tolist()
        ip_accounts = self.data_cache['IP账号'].dropna().tolist()
        
        # 过滤空字符串
        fxs_accounts = [acc for acc in fxs_accounts if acc != '']
        ip_accounts = [acc for acc in ip_accounts if acc != '']
        
        all_accounts = fxs_accounts + ip_accounts
        
        # 检查重复账号
        if len(all_accounts) != len(set(all_accounts)):
            warnings.append("检测到重复账号")
        
        # 验证手机号码和账号的一致性
        mobile_numbers = [str(num) for num in self.data_cache['手机号码'].tolist() if pd.notna(num)]
        if set(mobile_numbers) != set(all_accounts):
            warnings.append("手机号码与账号不完全匹配")
        
        # 验证密码规则
        passwords = [pwd for pwd in self.data_cache['密码'].tolist() if pd.notna(pwd)]
        import string
        valid_chars = set(string.digits + string.ascii_letters + "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
        
        invalid_passwords = []
        for pwd in passwords:
            if not isinstance(pwd, str):
                invalid_passwords.append(f"非字符串类型: {pwd}")
                continue
                
            if not (4 <= len(pwd) <= 12):
                invalid_passwords.append(f"长度错误: {pwd}")
                continue
            
            pwd_chars = set(str(pwd))
            if not pwd_chars.issubset(valid_chars):
                invalid_passwords.append(f"包含非法字符: {pwd}")
        
        if invalid_passwords:
            warnings.extend(invalid_passwords)
        
        result = {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_records': len(self.data_cache),
                'fxs_accounts': len(fxs_accounts),
                'ip_accounts': len(ip_accounts),
                'unique_accounts': len(set(all_accounts))
            }
        }
        
        return result
    
    def refresh_cache(self) -> bool:
        """
        刷新缓存，强制重新加载配置文件
        
        Returns:
            刷新是否成功
        """
        return self.load_config(force_reload=True)
    
    def get_accounts_by_condition(self, condition_func) -> List[Dict[str, Any]]:
        """
        根据条件函数筛选账号
        
        Args:
            condition_func: 筛选条件函数，接收一行数据作为参数，返回True/False
            
        Returns:
            符合条件的账号列表
        """
        if self.data_cache is None:
            if not self.load_config():
                return []
        
        result = []
        for _, row in self.data_cache.iterrows():
            # 将行转换为字典传递给条件函数，处理数据类型
            fxs_account = ''
            if pd.notna(row['FXS账号']) and str(row['FXS账号']).lower() != 'nan':
                fxs_val = row['FXS账号']
                if isinstance(fxs_val, float) and fxs_val.is_integer():
                    fxs_account = str(int(fxs_val))
                else:
                    fxs_account = str(fxs_val)
            
            ip_account = ''
            if pd.notna(row['IP账号']) and str(row['IP账号']).lower() != 'nan':
                ip_val = row['IP账号']
                if isinstance(ip_val, float) and ip_val.is_integer():
                    ip_account = str(int(ip_val))
                else:
                    ip_account = str(ip_val)
            
            mobile_number = ''
            if pd.notna(row['手机号码']) and str(row['手机号码']).lower() != 'nan':
                mobile_val = row['手机号码']
                if isinstance(mobile_val, float) and mobile_val.is_integer():
                    mobile_number = str(int(mobile_val))
                else:
                    mobile_number = str(mobile_val)
            
            password = str(row['密码']) if pd.notna(row['密码']) else ''
            password_type = str(row['密码类型']) if pd.notna(row['密码类型']) else ''
            
            row_dict = {
                'FXS账号': fxs_account,
                'IP账号': ip_account,
                '手机号码': mobile_number,
                '密码': password,
                '密码类型': password_type
            }
            if condition_func(row_dict):
                result.append(row_dict)
        
        return result
    
    def get_accounts_by_password_type(self, password_type: str) -> List[Dict[str, Any]]:
        """
        根据密码类型筛选账号
        
        Args:
            password_type: 密码类型
            
        Returns:
            符合条件的账号列表
        """
        if self.data_cache is None:
            if not self.load_config():
                return []
        
        filtered_df = self.data_cache[self.data_cache['密码类型'] == password_type]
        
        result = []
        for _, row in filtered_df.iterrows():
            # 处理数据类型
            fxs_account = ''
            if pd.notna(row['FXS账号']) and str(row['FXS账号']).lower() != 'nan':
                fxs_val = row['FXS账号']
                if isinstance(fxs_val, float) and fxs_val.is_integer():
                    fxs_account = str(int(fxs_val))
                else:
                    fxs_account = str(fxs_val)
            
            ip_account = ''
            if pd.notna(row['IP账号']) and str(row['IP账号']).lower() != 'nan':
                ip_val = row['IP账号']
                if isinstance(ip_val, float) and ip_val.is_integer():
                    ip_account = str(int(ip_val))
                else:
                    ip_account = str(ip_val)
            
            mobile_number = ''
            if pd.notna(row['手机号码']) and str(row['手机号码']).lower() != 'nan':
                mobile_val = row['手机号码']
                if isinstance(mobile_val, float) and mobile_val.is_integer():
                    mobile_number = str(int(mobile_val))
                else:
                    mobile_number = str(mobile_val)
            
            password = str(row['密码']) if pd.notna(row['密码']) else ''
            pwd_type = str(row['密码类型']) if pd.notna(row['密码类型']) else ''
            
            result.append({
                'FXS账号': fxs_account,
                'IP账号': ip_account,
                '手机号码': mobile_number,
                '密码': password,
                '密码类型': pwd_type
            })
        
        return result
    
    def get_accounts_by_range(self, start_account: int, end_account: int) -> List[Dict[str, Any]]:
        """
        根据账号范围筛选账号
        
        Args:
            start_account: 起始账号
            end_account: 结束账号
            
        Returns:
            指定范围内的账号列表
        """
        if self.data_cache is None:
            if not self.load_config():
                return []
        
        result = []
        for _, row in self.data_cache.iterrows():
            # 检查FXS账号或IP账号是否在范围内
            fxs_account = row['FXS账号']
            ip_account = row['IP账号']
            
            account_in_range = False
            if pd.notna(fxs_account) and str(fxs_account) != '' and str(fxs_account).lower() != 'nan':
                try:
                    fxs_int = int(float(fxs_account)) if isinstance(fxs_account, float) else int(fxs_account)
                    if start_account <= fxs_int <= end_account:
                        account_in_range = True
                except ValueError:
                    continue  # 跳过无法转换为整数的账号
            
            if not account_in_range and pd.notna(ip_account) and str(ip_account) != '' and str(ip_account).lower() != 'nan':
                try:
                    ip_int = int(float(ip_account)) if isinstance(ip_account, float) else int(ip_account)
                    if start_account <= ip_int <= end_account:
                        account_in_range = True
                except ValueError:
                    continue  # 跳过无法转换为整数的账号
            
            if account_in_range:
                # 处理数据类型
                fxs_acc = ''
                if pd.notna(row['FXS账号']) and str(row['FXS账号']).lower() != 'nan':
                    fxs_val = row['FXS账号']
                    if isinstance(fxs_val, float) and fxs_val.is_integer():
                        fxs_acc = str(int(fxs_val))
                    else:
                        fxs_acc = str(fxs_val)
                
                ip_acc = ''
                if pd.notna(row['IP账号']) and str(row['IP账号']).lower() != 'nan':
                    ip_val = row['IP账号']
                    if isinstance(ip_val, float) and ip_val.is_integer():
                        ip_acc = str(int(ip_val))
                    else:
                        ip_acc = str(ip_val)
                
                mobile_number = ''
                if pd.notna(row['手机号码']) and str(row['手机号码']).lower() != 'nan':
                    mobile_val = row['手机号码']
                    if isinstance(mobile_val, float) and mobile_val.is_integer():
                        mobile_number = str(int(mobile_val))
                    else:
                        mobile_number = str(mobile_val)
                
                password = str(row['密码']) if pd.notna(row['密码']) else ''
                password_type = str(row['密码类型']) if pd.notna(row['密码类型']) else ''
                
                result.append({
                    'FXS账号': fxs_acc,
                    'IP账号': ip_acc,
                    '手机号码': mobile_number,
                    '密码': password,
                    '密码类型': password_type
                })
        
        return result
    
    def update_multiple_accounts(self, updates: List[Dict[str, str]]) -> Dict[str, int]:
        """
        批量更新账号信息
        
        Args:
            updates: 更新信息列表，每个元素包含{'account': '账号', 'password': '新密码', 'password_type': '密码类型'}
            
        Returns:
            更新结果统计 {'success': 成功数量, 'failed': 失败数量}
        """
        if self.data_cache is None:
            if not self.load_config():
                return {'success': 0, 'failed': len(updates)}
        
        success_count = 0
        failed_count = 0
        
        for update in updates:
            account_number = update.get('account')
            new_password = update.get('password')
            password_type = update.get('password_type', '批量更新')
            
            if not account_number or not new_password:
                self.logger.warning(f"跳过无效的更新信息: {update}")
                failed_count += 1
                continue
            
            if self.update_account_password(account_number, new_password, password_type):
                success_count += 1
            else:
                failed_count += 1
        
        return {'success': success_count, 'failed': failed_count}
    
    def clear_cache(self):
        """清空缓存数据"""
        with self._lock:
            self.data_cache = None
            self.cache_timestamp = None
            self.logger.info("配置缓存已清空")