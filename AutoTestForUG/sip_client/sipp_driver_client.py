"""
SIPp驱动客户端
作为SIPp的驱动适配器，负责生成场景文件、启动SIPp进程、监控状态、收集报告
"""
import os
import tempfile
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import json
import logging
from .sip_client_base import SIPClientBase


class SIPpDriverClient(SIPClientBase):
    """
    SIPp驱动客户端
    作为SIPp的驱动适配器，负责生成场景文件、启动SIPp进程、监控状态、收集报告
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.sipp_path = config.get('sipp_path', 'sipp')
        self.temp_dir = config.get('temp_dir', tempfile.gettempdir())
        self.current_process = None
        self.current_scenario_file = None
        self.logger = logging.getLogger(__name__)
        
    def _generate_scenario_xml(self, scenario_type: str, params: Dict[str, Any]) -> str:
        """生成SIPp场景XML文件"""
        if scenario_type == "register":
            return self._generate_register_scenario(params)
        elif scenario_type == "invite":
            return self._generate_invite_scenario(params)
        else:
            raise ValueError(f"不支持的场景类型: {scenario_type}")
    
    def _generate_register_scenario(self, params: Dict[str, Any]) -> str:
        """生成注册场景XML"""
        scenario = f"""<?xml version="1.0" encoding="ISO-8859-1" ?>
<!DOCTYPE scenario SYSTEM "sipp.dtd">
<scenario name="REGISTER Scenario">
  <send retrans="500">
    <![CDATA[
      REGISTER sip:{params.get('domain', 'example.com')} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: <sip:{params.get('username', 'test')}@{params.get('domain', 'example.com')}>;tag=[pid]SIPpTag00[call_number]
      To: <sip:{params.get('username', 'test')}@{params.get('domain', 'example.com')}>
      Call-ID: [call_id]
      CSeq: 1 REGISTER
      Contact: <sip:{params.get('username', 'test')}@[local_ip]:[local_port]>
      Max-Forwards: 70
      Expires: {params.get('expires', 3600)}
      User-Agent: SIPp/Win32
      Content-Length: 0
    ]]>
  </send>

  <recv response="200" optional="false">
    <action>
      <ereg regexp=".*" search_in="hdr" header="Expires:" assign_to="1" />
    </action>
  </recv>

  <ResponseTimeRepartition value="10, 20, 30, 40, 50, 100, 150, 200" />
  <CallLengthRepartition value="10, 50, 100, 500, 1000, 5000, 10000" />
</scenario>"""
        return scenario
    
    def _generate_invite_scenario(self, params: Dict[str, Any]) -> str:
        """生成呼叫场景XML"""
        scenario = f"""<?xml version="1.0" encoding="ISO-8859-1" ?>
<!DOCTYPE scenario SYSTEM "sipp.dtd">
<scenario name="INVITE Scenario">
  <send retrans="500">
    <![CDATA[
      INVITE sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: <sip:{params.get('caller', 'caller')}@{params.get('domain', 'example.com')}>;tag=[pid]SIPpTag00[call_number]
      To: <sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')}>
      Call-ID: [call_id]
      CSeq: 1 INVITE
      Contact: <sip:{params.get('caller', 'caller')}@[local_ip]:[local_port]>
      Max-Forwards: 70
      Content-Type: application/sdp
      Content-Length: [len]

      v=0
      o=user1 53655765 2353687637 IN IP[local_ip_type] [local_ip]
      s=-
      c=IN IP[media_ip_type] [media_ip]
      t=0 0
      m=audio [media_port] RTP/AVP 0
      a=rtpmap:0 PCMU/8000
    ]]>
  </send>

  <recv response="100" optional="true">
  </recv>

  <recv response="180" optional="true">
  </recv>

  <recv response="183" optional="true">
  </recv>

  <recv response="200" rtd="true">
  </recv>

  <send>
    <![CDATA[
      ACK sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: <sip:{params.get('caller', 'caller')}@{params.get('domain', 'example.com')}>;tag=[pid]SIPpTag00[call_number]
      To: <sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')}>;
      Call-ID: [call_id]
      CSeq: 1 ACK
      Contact: <sip:{params.get('caller', 'caller')}@[local_ip]:[local_port]>
      Max-Forwards: 70
      Content-Length: 0
    ]]>
  </send>

  <pause milliseconds="5000" />

  <send retrans="500">
    <![CDATA[
      BYE sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: <sip:{params.get('caller', 'caller')}@{params.get('domain', 'example.com')}>;tag=[pid]SIPpTag00[call_number]
      To: <sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')};
      Call-ID: [call_id]
      CSeq: 2 BYE
      Contact: <sip:{params.get('caller', 'caller')}@[local_ip]:[local_port]>
      Max-Forwards: 70
      Content-Length: 0
    ]]>
  </send>

  <recv response="200" crlf="true">
  </recv>

  <ResponseTimeRepartition value="10, 20, 30, 40, 50, 100, 150, 200" />
  <CallLengthRepartition value="10, 50, 100, 500, 1000, 5000, 10000" />
</scenario>"""
        return scenario

    def _run_sipp_command(self, scenario_file: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行SIPp命令并收集结果"""
        try:
            # 构建SIPp命令
            cmd = [
                self.sipp_path,
                "-sf", scenario_file,
                params.get('server_host', '127.0.0.1'),
                "-p", str(params.get('server_port', 5060)),
                "-i", params.get('local_ip', '127.0.0.1'),
                "-m", str(params.get('max_calls', 1)),
                "-trace_err",  # 启用错误跟踪
                "-trace_msg",  # 启用消息跟踪
                "-td",  # 启用调试
            ]
            
            # 添加认证信息
            if 'auth_username' in params and 'auth_password' in params:
                cmd.extend(["-au", params['auth_username'], "-ap", params['auth_password']])
            
            # 执行命令
            self.logger.info(f"执行SIPp命令: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=params.get('timeout', 30)
            )
            
            # 解析结果
            success = result.returncode == 0
            output = result.stdout
            error = result.stderr
            
            return {
                "success": success,
                "return_code": result.returncode,
                "output": output,
                "error": error,
                "cmd": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            self.logger.error("SIPp命令执行超时")
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": "命令执行超时",
                "cmd": " ".join(cmd) if 'cmd' in locals() else ""
            }
        except Exception as e:
            self.logger.error(f"SIPp命令执行失败: {e}")
            return {
                "success": False,
                "return_code": -1,
                "output": "",
                "error": str(e),
                "cmd": " ".join(cmd) if 'cmd' in locals() else ""
            }

    def register(self, username: str, password: str, expires: int = 3600) -> bool:
        """执行SIP注册"""
        try:
            # 准备参数
            params = {
                'username': username,
                'domain': self.config.get('domain', 'example.com'),
                'expires': expires,
                'server_host': self.config.get('server_host', '127.0.0.1'),
                'server_port': self.config.get('server_port', 5060),
                'local_ip': self.config.get('local_ip', '127.0.0.1'),
                'auth_username': username,
                'auth_password': password,
                'max_calls': 1,
                'timeout': 30
            }
            
            # 生成场景文件
            scenario_content = self._generate_register_scenario(params)
            scenario_file = os.path.join(self.temp_dir, f"register_{username}_{int(time.time())}.xml")
            
            with open(scenario_file, 'w', encoding='utf-8') as f:
                f.write(scenario_content)
            
            # 运行SIPp
            result = self._run_sipp_command(scenario_file, params)
            
            # 清理临时文件
            if os.path.exists(scenario_file):
                os.remove(scenario_file)
            
            return result["success"]
        except Exception as e:
            self.logger.error(f"注册失败: {e}")
            return False

    def make_call(self, caller: str, callee: str) -> bool:
        """发起SIP呼叫"""
        try:
            # 准备参数
            params = {
                'caller': caller,
                'callee': callee,
                'domain': self.config.get('domain', 'example.com'),
                'server_host': self.config.get('server_host', '127.0.0.1'),
                'server_port': self.config.get('server_port', 5060),
                'local_ip': self.config.get('local_ip', '127.0.0.1'),
                'max_calls': 1,
                'timeout': 30
            }
            
            # 生成场景文件
            scenario_content = self._generate_invite_scenario(params)
            scenario_file = os.path.join(self.temp_dir, f"invite_{caller}_{callee}_{int(time.time())}.xml")
            
            with open(scenario_file, 'w', encoding='utf-8') as f:
                f.write(scenario_content)
            
            # 运行SIPp
            result = self._run_sipp_command(scenario_file, params)
            
            # 清理临时文件
            if os.path.exists(scenario_file):
                os.remove(scenario_file)
            
            return result["success"]
        except Exception as e:
            self.logger.error(f"呼叫失败: {e}")
            return False

    def send_message(self, sender: str, recipient: str, content: str) -> bool:
        """发送SIP消息"""
        # SIPp主要用于呼叫流程，消息发送功能可以扩展
        self.logger.warning("SIPp客户端暂时不支持发送消息功能")
        return False

    def unregister(self) -> bool:
        """取消SIP注册"""
        try:
            # 通过设置Expires为0来取消注册
            params = {
                'username': self.config.get('username', 'test'),
                'domain': self.config.get('domain', 'example.com'),
                'expires': 0,  # 设置为0表示取消注册
                'server_host': self.config.get('server_host', '127.0.0.1'),
                'server_port': self.config.get('server_port', 5060),
                'local_ip': self.config.get('local_ip', '127.0.0.1'),
                'auth_username': self.config.get('username', 'test'),
                'auth_password': self.config.get('password', ''),
                'max_calls': 1,
                'timeout': 30
            }
            
            # 生成场景文件
            scenario_content = self._generate_register_scenario(params)
            scenario_file = os.path.join(self.temp_dir, f"unregister_{int(time.time())}.xml")
            
            with open(scenario_file, 'w', encoding='utf-8') as f:
                f.write(scenario_content)
            
            # 运行SIPp
            result = self._run_sipp_command(scenario_file, params)
            
            # 清理临时文件
            if os.path.exists(scenario_file):
                os.remove(scenario_file)
            
            return result["success"]
        except Exception as e:
            self.logger.error(f"取消注册失败: {e}")
            return False

    def close(self):
        """关闭客户端"""
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.current_process.kill()