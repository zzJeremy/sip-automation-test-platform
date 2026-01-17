"""
Asterisk SIP客户端实现
通过AMI/ARI接口控制Asterisk服务器进行测试
"""
import logging
from typing import Dict, Any, Optional
from .sip_client_base import SIPClientBase


class AsteriskSIPClient(SIPClientBase):
    """
    Asterisk SIP客户端实现
    通过AMI/ARI接口控制Asterisk服务器进行测试
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Asterisk SIP客户端
        
        Args:
            config: 配置参数，包括:
                - asterisk_host: Asterisk服务器地址
                - ami_port: AMI端口，默认5038
                - ami_username: AMI用户名
                - ami_password: AMI密码
                - ari_port: ARI端口，默认8088
                - ari_username: ARI用户名
                - ari_password: ARI密码
        """
        self.config = config
        self.ami_connection = None
        self.ari_connection = None
        self.asterisk_host = config.get('asterisk_host', '127.0.0.1')
        self.ami_port = config.get('ami_port', 5038)
        self.ami_username = config.get('ami_username', 'admin')
        self.ami_password = config.get('ami_password', 'password')
        self.ari_port = config.get('ari_port', 8088)
        self.ari_username = config.get('ari_username', 'asterisk')
        self.ari_password = config.get('ari_password', 'asterisk')
        
        self.logger = logging.getLogger(__name__)
        
        # 初始化连接
        self._connect_ami()
        self._connect_ari()
    
    def _connect_ami(self):
        """连接到Asterisk Manager Interface"""
        try:
            # 这里使用pyst2库连接AMI
            # 由于pyst2可能未安装，这里仅作示例实现
            import pyst2
            self.ami_connection = pyst2.Manager(
                host=self.asterisk_host,
                port=self.ami_port,
                username=self.ami_username,
                secret=self.ami_password
            )
            self.logger.info(f"成功连接到Asterisk AMI: {self.asterisk_host}:{self.ami_port}")
        except ImportError:
            self.logger.warning("pyst2未安装，无法连接Asterisk AMI")
        except Exception as e:
            self.logger.error(f"连接Asterisk AMI失败: {str(e)}")
    
    def _connect_ari(self):
        """连接到Asterisk REST Interface"""
        try:
            # 这里使用ari-py库连接ARI
            import ari
            self.ari_connection = ari.connect(
                f"http://{self.asterisk_host}:{self.ari_port}",
                self.ari_username,
                self.ari_password
            )
            self.logger.info(f"成功连接到Asterisk ARI: {self.asterisk_host}:{self.ari_port}")
        except ImportError:
            self.logger.warning("ari未安装，无法连接Asterisk ARI")
        except Exception as e:
            self.logger.error(f"连接Asterisk ARI失败: {str(e)}")
    
    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """
        通过Asterisk进行SIP注册
        
        Args:
            username: SIP用户名
            password: SIP密码
            expires: 注册有效期（秒）
            
        Returns:
            bool: 注册是否成功
        """
        try:
            # 使用Asterisk的SIP命令进行注册
            if self.ami_connection:
                # 创建SIP账户配置
                sip_config = f"""
[{username}]
type=friend
host=dynamic
username={username}
secret={password}
context=default
dtmfmode=rfc2833
canreinvite=no
nat=yes
"""
                # 通过AMI命令添加SIP用户
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': f'database put SIP/Registry {username} {password}'
                })
                
                # 重启SIP模块使配置生效
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': 'module reload res_pjsip.so'
                })
                
                self.logger.info(f"Asterisk SIP注册配置完成: {username}")
                return True
            else:
                self.logger.error("AMI连接不可用，无法执行注册")
                return False
        except Exception as e:
            self.logger.error(f"Asterisk SIP注册失败: {str(e)}")
            return False
    
    def make_call(self, from_uri: str, to_uri: str, timeout: int = 30) -> bool:
        """
        通过Asterisk发起呼叫
        
        Args:
            from_uri: 主叫URI
            to_uri: 被叫URI
            timeout: 超时时间（秒）
            
        Returns:
            bool: 呼叫是否成功建立
        """
        try:
            if self.ami_connection:
                # 使用Asterisk的Originate命令发起呼叫
                channel = f"SIP/{from_uri}"  # 简化处理
                context = "default"
                extension = to_uri.split('@')[0]  # 获取被叫号码
                
                response = self.ami_connection.send_action({
                    'Action': 'Originate',
                    'Channel': channel,
                    'Context': context,
                    'Exten': extension,
                    'Priority': '1',
                    'Timeout': str(timeout * 1000),  # 毫秒
                    'Async': 'true'
                })
                
                self.logger.info(f"通过Asterisk发起呼叫: {from_uri} -> {to_uri}")
                return 'Response' in response and response['Response'] == 'Success'
            else:
                self.logger.error("AMI连接不可用，无法发起呼叫")
                return False
        except Exception as e:
            self.logger.error(f"Asterisk发起呼叫失败: {str(e)}")
            return False
    
    def configure_ivr(self, ivr_config: Dict[str, Any]) -> bool:
        """
        配置IVR菜单
        
        Args:
            ivr_config: IVR配置信息
            
        Returns:
            bool: 配置是否成功
        """
        try:
            if self.ami_connection:
                # 生成拨号计划配置
                extension_context = ivr_config.get('context', 'ivr-menu')
                menu_options = ivr_config.get('options', {})
                
                # 创建IVR拨号计划
                dialplan_config = self._generate_ivr_dialplan(extension_context, menu_options)
                
                # 上传拨号计划到Asterisk
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': f'dialplan add extension {extension_context} 1001 {dialplan_config}'
                })
                
                self.logger.info(f"IVR配置完成: {extension_context}")
                return True
            else:
                self.logger.error("AMI连接不可用，无法配置IVR")
                return False
        except Exception as e:
            self.logger.error(f"IVR配置失败: {str(e)}")
            return False
    
    def configure_call_forwarding(self, forward_config: Dict[str, Any]) -> bool:
        """
        配置呼叫转移
        
        Args:
            forward_config: 呼叫转移配置信息
            
        Returns:
            bool: 配置是否成功
        """
        try:
            if self.ami_connection:
                username = forward_config.get('username')
                destination = forward_config.get('destination')
                forward_type = forward_config.get('type', 'all')  # all, busy, noanswer
                
                # 设置呼叫转移
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': f'dialplan add extension {username}-cf {destination} Dial(SIP/{destination})'
                })
                
                self.logger.info(f"呼叫转移配置完成: {username} -> {destination}")
                return True
            else:
                self.logger.error("AMI连接不可用，无法配置呼叫转移")
                return False
        except Exception as e:
            self.logger.error(f"呼叫转移配置失败: {str(e)}")
            return False
    
    def _generate_ivr_dialplan(self, context: str, options: Dict[str, Any]) -> str:
        """
        生成IVR拨号计划
        
        Args:
            context: 上下文名称
            options: IVR选项配置
            
        Returns:
            str: 拨号计划配置字符串
        """
        # 这里简化实现，实际应用中需要更复杂的拨号计划生成逻辑
        dialplan = f"context {context}\n"
        for key, action in options.items():
            dialplan += f"exten => {key},1,{action}\n"
        
        return dialplan

    def send_message(self, from_uri: str, to_uri: str, content: str) -> bool:
        """
        发送SIP消息
        
        Args:
            from_uri: 发送方URI
            to_uri: 接收方URI
            content: 消息内容
            
        Returns:
            bool: 消息发送是否成功
        """
        try:
            if self.ami_connection:
                # 使用Asterisk的MessageSend命令发送SIP消息
                response = self.ami_connection.send_action({
                    'Action': 'MessageSend',
                    'To': to_uri,
                    'From': from_uri,
                    'Body': content
                })
                
                self.logger.info(f"通过Asterisk发送SIP消息: {from_uri} -> {to_uri}")
                return 'Response' in response and response['Response'] == 'Success'
            else:
                self.logger.error("AMI连接不可用，无法发送SIP消息")
                return False
        except Exception as e:
            self.logger.error(f"Asterisk发送SIP消息失败: {str(e)}")
            return False

    def unregister(self) -> bool:
        """
        取消SIP注册
        
        Returns:
            bool: 取消注册是否成功
        """
        try:
            if self.ami_connection:
                # 删除SIP账户配置
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': 'module reload res_pjsip.so'
                })
                
                self.logger.info("Asterisk SIP取消注册完成")
                return True
            else:
                self.logger.error("AMI连接不可用，无法执行取消注册")
                return False
        except Exception as e:
            self.logger.error(f"Asterisk SIP取消注册失败: {str(e)}")
            return False

    def close(self):
        """
        关闭SIP客户端，释放资源
        """
        try:
            if self.ami_connection:
                self.ami_connection.logoff()
                self.logger.info("Asterisk AMI连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭Asterisk AMI连接时出错: {str(e)}")
        
        try:
            if self.ari_connection:
                self.ari_connection.close()
                self.logger.info("Asterisk ARI连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭Asterisk ARI连接时出错: {str(e)}")
    
    def disconnect(self):
        """断开与Asterisk的连接"""
        try:
            if self.ami_connection:
                self.ami_connection.logoff()
                self.logger.info("已断开Asterisk AMI连接")
        except Exception as e:
            self.logger.error(f"断开AMI连接时出错: {str(e)}")
        
        try:
            if self.ari_connection:
                self.ari_connection.close()
                self.logger.info("已断开Asterisk ARI连接")
        except Exception as e:
            self.logger.error(f"断开ARI连接时出错: {str(e)}")