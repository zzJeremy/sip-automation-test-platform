"""
设备控制器
提供统一接口控制SIP设备，支持多种设备类型和控制方式
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


class DeviceController(ABC):
    """设备控制器抽象基类"""
    
    @abstractmethod
    def connect_device(self, device_config: Dict[str, Any]):
        """连接设备"""
        pass
    
    @abstractmethod
    def send_command(self, command: str, **kwargs):
        """发送命令到设备"""
        pass
    
    @abstractmethod
    def get_device_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """断开设备连接"""
        pass


class WebDeviceController(DeviceController):
    """基于Web的设备控制器"""
    
    def __init__(self, device_url: str):
        self.device_url = device_url
        self.driver = None
        self.wait = None
        self.logger = logging.getLogger(__name__)
    
    def connect_device(self, device_config: Dict[str, Any]):
        """连接到设备的Web管理界面"""
        try:
            # 配置Chrome选项
            chrome_options = Options()
            if device_config.get('headless', False):
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 启动浏览器
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            
            # 登录设备管理界面
            login_url = device_config.get('login_url', self.device_url)
            username = device_config.get('username', 'admin')
            password = device_config.get('password', 'admin')
            
            self.driver.get(login_url)
            
            # 查找登录表单元素并登录
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            password_field = self.driver.find_element(By.NAME, "password")
            login_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)
            login_button.click()
            
            # 等待登录完成
            time.sleep(2)
            
            self.logger.info(f"成功连接到设备: {self.device_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"连接设备失败: {str(e)}")
            return False
    
    def send_command(self, command: str, **kwargs):
        """通过Web界面发送命令到设备"""
        if not self.driver:
            raise RuntimeError("设备未连接")
        
        try:
            if command == "register_sip_account":
                return self._register_sip_account(kwargs)
            elif command == "make_call":
                return self._make_call(kwargs)
            elif command == "configure_sip_settings":
                return self._configure_sip_settings(kwargs)
            elif command == "get_status":
                return self._get_device_status()
            else:
                self.logger.warning(f"未知命令: {command}")
                return False
                
        except Exception as e:
            self.logger.error(f"发送命令失败: {str(e)}")
            return False
    
    def _register_sip_account(self, params: Dict[str, Any]) -> bool:
        """注册SIP账户"""
        try:
            # 导航到SIP账户配置页面
            sip_config_url = f"{self.device_url}/sip_config"
            self.driver.get(sip_config_url)
            
            # 填写SIP账户信息
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "account_name"))
            )
            server_field = self.driver.find_element(By.NAME, "server_address")
            auth_user_field = self.driver.find_element(By.NAME, "auth_user")
            password_field = self.driver.find_element(By.NAME, "password")
            
            username_field.clear()
            username_field.send_keys(params.get('username', ''))
            server_field.clear()
            server_field.send_keys(params.get('server', ''))
            auth_user_field.clear()
            auth_user_field.send_keys(params.get('auth_user', params.get('username', '')))
            password_field.clear()
            password_field.send_keys(params.get('password', ''))
            
            # 保存配置
            save_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            save_button.click()
            
            time.sleep(2)  # 等待保存完成
            return True
            
        except Exception as e:
            self.logger.error(f"注册SIP账户失败: {str(e)}")
            return False
    
    def _make_call(self, params: Dict[str, Any]) -> bool:
        """发起呼叫"""
        try:
            # 导航到呼叫页面
            call_url = f"{self.device_url}/call"
            self.driver.get(call_url)
            
            # 输入被叫号码
            number_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "number"))
            )
            number_field.clear()
            number_field.send_keys(params.get('to_number', ''))
            
            # 点击呼叫按钮
            call_button = self.driver.find_element(By.ID, "call_button")
            call_button.click()
            
            time.sleep(1)  # 等待呼叫发起
            return True
            
        except Exception as e:
            self.logger.error(f"发起呼叫失败: {str(e)}")
            return False
    
    def _configure_sip_settings(self, params: Dict[str, Any]) -> bool:
        """配置SIP设置"""
        try:
            # 导航到SIP设置页面
            sip_settings_url = f"{self.device_url}/sip_settings"
            self.driver.get(sip_settings_url)
            
            # 配置各种SIP参数
            for param_name, param_value in params.items():
                try:
                    field = self.driver.find_element(By.NAME, param_name)
                    field.clear()
                    field.send_keys(str(param_value))
                except:
                    # 如果字段不存在，跳过
                    continue
            
            # 保存设置
            save_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
            save_button.click()
            
            time.sleep(2)  # 等待设置生效
            return True
            
        except Exception as e:
            self.logger.error(f"配置SIP设置失败: {str(e)}")
            return False
    
    def _get_device_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        try:
            status_url = f"{self.device_url}/status"
            self.driver.get(status_url)
            
            # 提取设备状态信息
            status_info = {}
            
            # 尝试获取常见状态字段
            try:
                registration_status = self.driver.find_element(By.ID, "registration_status").text
                status_info['registration_status'] = registration_status
            except:
                status_info['registration_status'] = 'unknown'
            
            try:
                firmware_version = self.driver.find_element(By.ID, "firmware_version").text
                status_info['firmware_version'] = firmware_version
            except:
                status_info['firmware_version'] = 'unknown'
            
            try:
                uptime = self.driver.find_element(By.ID, "uptime").text
                status_info['uptime'] = uptime
            except:
                status_info['uptime'] = 'unknown'
            
            return status_info
            
        except Exception as e:
            self.logger.error(f"获取设备状态失败: {str(e)}")
            return {'error': str(e)}
    
    def get_device_status(self) -> Dict[str, Any]:
        """获取设备状态"""
        return self._get_device_status()
    
    def disconnect(self):
        """断开设备连接"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
            self.logger.info("设备连接已断开")


class SipDeviceController(DeviceController):
    """SIP设备控制器 - 通过SIP协议直接控制设备"""
    
    def __init__(self, sip_address: str):
        self.sip_address = sip_address
        self.connected = False
        self.logger = logging.getLogger(__name__)
    
    def connect_device(self, device_config: Dict[str, Any]):
        """连接SIP设备"""
        try:
            # 这里可以实现SIP协议级别的连接
            # 例如使用PJSIP库或其他SIP客户端库
            self.connected = True
            self.logger.info(f"SIP设备连接成功: {self.sip_address}")
            return True
        except Exception as e:
            self.logger.error(f"SIP设备连接失败: {str(e)}")
            return False
    
    def send_command(self, command: str, **kwargs):
        """发送SIP命令到设备"""
        if not self.connected:
            raise RuntimeError("设备未连接")
        
        try:
            if command == "register":
                return self._sip_register(kwargs)
            elif command == "unregister":
                return self._sip_unregister()
            elif command == "subscribe":
                return self._sip_subscribe(kwargs)
            elif command == "publish":
                return self._sip_publish(kwargs)
            else:
                self.logger.warning(f"未知SIP命令: {command}")
                return False
        except Exception as e:
            self.logger.error(f"发送SIP命令失败: {str(e)}")
            return False
    
    def _sip_register(self, params: Dict[str, Any]) -> bool:
        """SIP注册"""
        # 实现SIP注册逻辑
        self.logger.info(f"向 {self.sip_address} 发送注册请求")
        # 这里需要实际的SIP协议实现
        return True
    
    def _sip_unregister(self) -> bool:
        """SIP取消注册"""
        self.logger.info(f"向 {self.sip_address} 发送取消注册请求")
        return True
    
    def _sip_subscribe(self, params: Dict[str, Any]) -> bool:
        """SIP订阅"""
        event_type = params.get('event', 'presence')
        self.logger.info(f"向 {self.sip_address} 发送{event_type}订阅请求")
        return True
    
    def _sip_publish(self, params: Dict[str, Any]) -> bool:
        """SIP发布"""
        event_type = params.get('event', 'presence')
        content = params.get('content', '')
        self.logger.info(f"向 {self.sip_address} 发布{event_type}事件")
        return True
    
    def get_device_status(self) -> Dict[str, Any]:
        """获取SIP设备状态"""
        if not self.connected:
            return {'status': 'disconnected'}
        
        # 这里可以实现实际的状态查询逻辑
        return {
            'status': 'registered',
            'address': self.sip_address,
            'last_activity': time.time()
        }
    
    def disconnect(self):
        """断开SIP设备连接"""
        self.connected = False
        self.logger.info(f"SIP设备连接已断开: {self.sip_address}")


class DeviceControllerFactory:
    """设备控制器工厂类"""
    
    @staticmethod
    def create_controller(controller_type: str, **kwargs) -> DeviceController:
        """
        创建设备控制器
        
        Args:
            controller_type: 控制器类型 ('web', 'sip', 'snmp', etc.)
            **kwargs: 控制器初始化参数
            
        Returns:
            DeviceController: 设备控制器实例
        """
        if controller_type.lower() == 'web':
            device_url = kwargs.get('device_url', 'http://localhost')
            return WebDeviceController(device_url)
        elif controller_type.lower() == 'sip':
            sip_address = kwargs.get('sip_address', 'sip:localhost')
            return SipDeviceController(sip_address)
        else:
            raise ValueError(f"不支持的控制器类型: {controller_type}")


class MultiDeviceManager:
    """多设备管理器"""
    
    def __init__(self):
        self.controllers: Dict[str, DeviceController] = {}
        self.logger = logging.getLogger(__name__)
    
    def add_device(self, device_id: str, controller: DeviceController):
        """添加设备控制器"""
        self.controllers[device_id] = controller
    
    def remove_device(self, device_id: str):
        """移除设备控制器"""
        if device_id in self.controllers:
            controller = self.controllers[device_id]
            controller.disconnect()
            del self.controllers[device_id]
    
    def execute_on_all_devices(self, command: str, **kwargs) -> Dict[str, Any]:
        """在所有设备上执行命令"""
        results = {}
        for device_id, controller in self.controllers.items():
            try:
                result = controller.send_command(command, **kwargs)
                results[device_id] = result
            except Exception as e:
                results[device_id] = {'error': str(e)}
        
        return results
    
    def get_all_statuses(self) -> Dict[str, Any]:
        """获取所有设备状态"""
        statuses = {}
        for device_id, controller in self.controllers.items():
            try:
                status = controller.get_device_status()
                statuses[device_id] = status
            except Exception as e:
                statuses[device_id] = {'error': str(e)}
        
        return statuses