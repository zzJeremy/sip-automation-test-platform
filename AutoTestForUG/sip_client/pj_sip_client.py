"""
基于PJSIP库的SIP客户端实现
提供生产级的SIP功能实现
"""

from typing import Dict, Any, Optional
import logging
import sys
import os

# 尝试导入PJSIP，如果未安装则提供替代实现
PJSIP_AVAILABLE = False
pj = None

try:
    import pjsua2 as pj
    PJSIP_AVAILABLE = True
    logging.info("PJSIP库已成功导入")
except ImportError as e:
    logging.warning(f"PJSIP库导入失败: {e}，将使用模拟实现")
    # 尝试通过其他方式查找pjsua2
    try:
        # 在Windows环境下，有时需要特殊处理
        if sys.platform.startswith('win'):
            # 尝试添加可能的PJSIP安装路径
            import site
            site.addsitedir(os.path.join(site.getsitepackages()[0], "pjsip"))
            import pjsua2 as pj
            PJSIP_AVAILABLE = True
            logging.info("从备用路径成功导入PJSIP库")
    except ImportError:
        pass

from .sip_client_base import SIPClientBase


class PJSIPSIPClient(SIPClientBase):
    """
    基于PJSIP库的SIP客户端实现
    提供生产级的SIP功能实现
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化PJSIP客户端
        
        Args:
            config: 配置参数
        """
        if not PJSIP_AVAILABLE:
            logging.warning("PJSIP库不可用，将使用模拟实现")
            # 初始化模拟状态
            self.config = config
            self.ep = None
            self.account = None
            self.current_call = None
            return
        
        self.config = config
        
        try:
            self.ep = pj.Endpoint()
            
            # 初始化端点
            ep_config = pj.EpConfig()
            # 设置用户代理字符串
            ep_config.userAgent = "AutoTestForUG-PJSIP-Client/1.0"
            
            self.ep.libCreate()
            self.ep.libInit(ep_config)
            
            # 启动SIP传输
            transport_config = pj.TransportConfig()
            transport_config.port = config.get('local_port', 5060)
            # 设置绑定地址
            transport_config.bindAddr = config.get('local_host', '127.0.0.1')
            
            self.transport_id = self.ep.transportCreate(
                pj.PJSIP_TRANSPORT_UDP, 
                transport_config
            )
            
            # 启动端点
            self.ep.libStart()
            
            self.account = None
            self.current_call = None
            
            logging.info("PJSIP客户端初始化成功")
            
        except Exception as e:
            logging.error(f"PJSIP客户端初始化失败: {e}")
            # 如果初始化失败，仍然允许创建对象但标记为不可用
            self.ep = None
            self.account = None
            self.current_call = None
            raise
    
    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """
        执行SIP注册
        """
        if not PJSIP_AVAILABLE:
            return False
            
        # 创建账户配置
        account_config = pj.AccountConfig()
        account_config.idUri = f"sip:{username}@{self.config.get('sip_server_host', '127.0.0.1')}"
        account_config.regConfig.registrarUri = f"sip:{self.config.get('sip_server_host', '127.0.0.1')}"
        
        # 设置认证
        cred = pj.AuthCredInfo(
            "digest", 
            "*", 
            username, 
            0, 
            password
        )
        account_config.sipConfig.authCreds.append(cred)
        
        # 创建账户
        self.account = PJSIPAccount(self, account_config)
        try:
            self.account.create(account_config)
            return True
        except Exception as e:
            logging.error(f"PJSIP注册失败: {str(e)}")
            return False
    
    def make_call(self, from_uri: str, to_uri: str, timeout: int = 30) -> bool:
        """
        发起SIP呼叫
        """
        if not PJSIP_AVAILABLE or not self.account:
            return False
            
        try:
            # 创建呼叫
            call = pj.Call(self.account)
            call_param = pj.CallOpParam()
            call_param.opt.audioCount = 1
            call_param.opt.videoCount = 0
            
            # 发起呼叫
            call.makeCall(to_uri, call_param)
            self.current_call = call
            return True
        except Exception as e:
            logging.error(f"PJSIP呼叫失败: {str(e)}")
            return False
    
    def send_message(self, from_uri: str, to_uri: str, content: str) -> bool:
        """
        发送SIP消息
        """
        if not PJSIP_AVAILABLE or not self.account:
            return False
            
        try:
            # 使用PJSIP发送消息
            im_data = pj.SendInstantMessageParam()
            im_data.content = content
            self.account.sendInstantMessage(to_uri, im_data)
            return True
        except Exception as e:
            logging.error(f"PJSIP消息发送失败: {str(e)}")
            return False
    
    def unregister(self) -> bool:
        """
        取消SIP注册
        """
        if not PJSIP_AVAILABLE or not self.account:
            return False
            
        try:
            acc_config = pj.AccountConfig()
            acc_config.regConfig.timeoutSec = 0  # 立即取消注册
            self.account.modify(acc_config)
            return True
        except Exception as e:
            logging.error(f"PJSIP取消注册失败: {str(e)}")
            return False
    
    def close(self):
        """
        关闭SIP客户端
        """
        if not PJSIP_AVAILABLE:
            return
            
        try:
            if self.current_call:
                self.current_call.hangup(pj.CallOpParam())
            if self.account:
                self.account.delete()
            self.ep.libDestroy()
        except Exception as e:
            logging.error(f"关闭PJSIP客户端时出错: {str(e)}")


if PJSIP_AVAILABLE:
    class PJSIPAccount(pj.Account):
        """
        PJSIP账户类
        """
        def __init__(self, client, account_config):
            pj.Account.__init__(self)
            self.client = client
            self.account_config = account_config
        
        def onRegState(self, prm):
            """
            注册状态回调
            """
            logging.info(f"注册状态: {prm.code} - {prm.reason}")
        
        def onIncomingCall(self, prm):
            """
            来电回调
            """
            logging.info(f"收到呼叫: {prm.rdata}")
else:
    # 当PJSIP不可用时，定义一个模拟类
    class PJSIPAccount:
        """
        模拟的PJSIP账户类，用于PJSIP不可用时的兼容
        """
        def __init__(self, client, account_config):
            self.client = client
            self.account_config = account_config