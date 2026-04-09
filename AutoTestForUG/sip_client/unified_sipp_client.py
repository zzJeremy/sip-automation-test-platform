"""
统一SIPp客户端实现
整合了sipp_controller.py和sipp_driver_client.py的功能
"""
import os
import tempfile
import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import json
import logging
import threading
from .sip_client_base import SIPClientBase


class UnifiedSIPpClient(SIPClientBase):
    """
    统一的SIPp客户端实现
    整合了SIPp控制器和驱动客户端的功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化统一SIPp客户端
        
        Args:
            config: 配置参数，包括:
                - sipp_path: SIPp可执行文件路径
                - temp_dir: 临时文件目录
                - server_host: 服务器主机地址
                - server_port: 服务器端口
                - local_ip: 本地IP地址
                - domain: SIP域
        """
        self.config = config
        self.sipp_path = config.get('sipp_path', 'sipp')
        self.temp_dir = config.get('temp_dir', tempfile.gettempdir())
        self.current_process = None
        self.current_scenario_file = None
        self.logger = logging.getLogger(__name__)
        self.processes = {}  # 存储运行中的SIPp进程
        self.temp_files = []  # 存储临时文件路径
        
        # 验证SIPp可执行文件是否存在
        if not self._verify_sipp_executable():
            self.logger.warning(f"SIPp可执行文件不存在于路径: {self.sipp_path}")
    
    def _verify_sipp_executable(self) -> bool:
        """验证SIPp可执行文件是否存在"""
        try:
            result = subprocess.run([self.sipp_path, '-v'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _generate_scenario_xml(self, scenario_type: str, params: Dict[str, Any]) -> str:
        """
        生成SIPp场景XML文件
        
        Args:
            scenario_type: 场景类型 ('basic_call', 'registration', 'options', 'invite', 'register')
            params: 场景参数
        
        Returns:
            生成的XML内容
        """
        if scenario_type in ['basic_call', 'invite']:
            return self._generate_invite_scenario(params)
        elif scenario_type in ['registration', 'register']:
            return self._generate_register_scenario(params)
        elif scenario_type == 'options':
            return self._generate_options_scenario(params)
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
      To: <sip:{params.get('callee', 'callee')}@{params.get('domain', 'example.com')}>;
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

    def _generate_options_scenario(self, params: Dict[str, Any]) -> str:
        """生成OPTIONS场景XML"""
        target_host = params.get('target_host', '127.0.0.1')
        target_port = params.get('target_port', '5060')
        
        return f'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<!DOCTYPE scenario SYSTEM "sipp.dtd">

<scenario name="OPTIONS Ping">
  <send retrans="500">
    <![CDATA[
      OPTIONS sip:{target_host}:{target_port} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: sipp <sip:sipp@[local_ip]:[local_port]>;tag=[pid][time]
      To: sut <sip:sut@[remote_ip]:[remote_port]>
      Call-ID: [call_id]
      CSeq: 1 OPTIONS
      Max-Forwards: 70
      Content-Length: 0
    ]]>
  </send>

  <recv response="200" rtd="true">
  </recv>

  <ResponseTimeRepartition value="10, 20, 30, 40, 50, 100, 150, 200"/>
</scenario>'''

    def _run_sipp_command(self, scenario_file: str, destination: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        运行SIPp命令并收集结果
        
        Args:
            scenario_file: 场景文件路径
            destination: 目标地址 (host:port)
            options: 运行选项，如 -i, -p, -r 等
        
        Returns:
            包含执行结果的字典
        """
        if options is None:
            options = {}
        
        # 构建命令
        cmd = [self.sipp_path, destination, "-sf", scenario_file]
        
        # 添加选项
        for key, value in options.items():
            if isinstance(value, bool) and value:
                cmd.append(key)
            elif not isinstance(value, bool):
                cmd.extend([key, str(value)])
        
        # 添加日志文件
        log_file = os.path.join(tempfile.gettempdir(), f"sipp_{int(time.time())}.log")
        cmd.extend(["-trace_err", "-trace_msg", "-ooc", "1", "-fd", "1"])
        
        self.logger.info(f"Running SIPp command: {' '.join(cmd)}")
        
        try:
            # 启动SIPp进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 记录进程信息
            process_info = {
                'pid': process.pid,
                'command': cmd,
                'start_time': time.time(),
                'log_file': log_file,
                'process': process
            }
            
            # 将进程信息存储起来
            self.processes[process.pid] = process_info
            
            # 等待进程完成
            stdout, stderr = process.communicate(timeout=options.get('timeout', 300))
            
            process_info.update({
                'return_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'end_time': time.time(),
                'duration': time.time() - process_info['start_time']
            })
            
            # 从进程列表中移除已完成的进程
            del self.processes[process.pid]
            
            return process_info
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            result = {
                'return_code': -1,
                'stdout': stdout,
                'stderr': stderr,
                'error': 'Process timed out'
            }
            # 从进程列表中移除已终止的进程
            if process.pid in self.processes:
                del self.processes[process.pid]
            return result
        except FileNotFoundError:
            result = {
                'return_code': -1,
                'error': f'SIPp executable not found at {self.sipp_path}'
            }
            return result
        except Exception as e:
            result = {
                'return_code': -1,
                'error': str(e)
            }
            return result

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
            
            # 添加到临时文件列表以便后续清理
            self.temp_files.append(scenario_file)
            
            # 运行SIPp
            destination = f"{params['server_host']}:{params['server_port']}"
            options = {
                '-i': params['local_ip'],
                '-p': str(params.get('local_port', 6060)),
                '-m': params['max_calls'],
                '-timeout': params['timeout']
            }
            
            if 'auth_username' in params and 'auth_password' in params:
                options['-au'] = params['auth_username']
                options['-ap'] = params['auth_password']
            
            result = self._run_sipp_command(scenario_file, destination, options)
            
            return result.get("return_code", -1) == 0 or result.get("success", False)
        except Exception as e:
            self.logger.error(f"注册失败: {e}")
            return False

    def make_call(self, from_uri: str, to_uri: str, timeout: int = 30) -> bool:
        """发起SIP呼叫"""
        try:
            # 从URI中提取信息
            caller = from_uri.split('@')[0] if '@' in from_uri else from_uri
            callee = to_uri.split('@')[0] if '@' in to_uri else to_uri
            domain = to_uri.split('@')[1] if '@' in to_uri else self.config.get('domain', 'example.com')
            
            # 准备参数
            params = {
                'caller': caller,
                'callee': callee,
                'domain': domain,
                'server_host': self.config.get('server_host', '127.0.0.1'),
                'server_port': self.config.get('server_port', 5060),
                'local_ip': self.config.get('local_ip', '127.0.0.1'),
                'max_calls': 1,
                'timeout': timeout
            }
            
            # 生成场景文件
            scenario_content = self._generate_invite_scenario(params)
            scenario_file = os.path.join(self.temp_dir, f"invite_{caller}_{callee}_{int(time.time())}.xml")
            
            with open(scenario_file, 'w', encoding='utf-8') as f:
                f.write(scenario_content)
            
            # 添加到临时文件列表以便后续清理
            self.temp_files.append(scenario_file)
            
            # 运行SIPp
            destination = f"{params['server_host']}:{params['server_port']}"
            options = {
                '-i': params['local_ip'],
                '-p': str(params.get('local_port', 6060)),
                '-m': params['max_calls'],
                '-timeout': params['timeout']
            }
            
            result = self._run_sipp_command(scenario_file, destination, options)
            
            return result.get("return_code", -1) == 0 or result.get("success", False)
        except Exception as e:
            self.logger.error(f"呼叫失败: {e}")
            return False

    def send_message(self, from_uri: str, to_uri: str, content: str) -> bool:
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
            
            # 添加到临时文件列表以便后续清理
            self.temp_files.append(scenario_file)
            
            # 运行SIPp
            destination = f"{params['server_host']}:{params['server_port']}"
            options = {
                '-i': params['local_ip'],
                '-p': str(params.get('local_port', 6060)),
                '-m': params['max_calls'],
                '-timeout': params['timeout']
            }
            
            if params['auth_username'] and params['auth_password']:
                options['-au'] = params['auth_username']
                options['-ap'] = params['auth_password']
            
            result = self._run_sipp_command(scenario_file, destination, options)
            
            return result.get("return_code", -1) == 0 or result.get("success", False)
        except Exception as e:
            self.logger.error(f"取消注册失败: {e}")
            return False

    def run_custom_scenario(self, scenario_type: str, params: Dict[str, Any], 
                           destination: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        运行自定义场景
        
        Args:
            scenario_type: 场景类型
            params: 场景参数
            destination: 目标地址
            options: 运行选项
        
        Returns:
            执行结果
        """
        try:
            # 生成场景文件
            scenario_content = self._generate_scenario_xml(scenario_type, params)
            scenario_file = os.path.join(self.temp_dir, f"custom_{scenario_type}_{int(time.time())}.xml")
            
            with open(scenario_file, 'w', encoding='utf-8') as f:
                f.write(scenario_content)
            
            # 添加到临时文件列表以便后续清理
            self.temp_files.append(scenario_file)
            
            # 运行SIPp
            result = self._run_sipp_command(scenario_file, destination, options)
            
            return result
        except Exception as e:
            self.logger.error(f"运行自定义场景失败: {e}")
            return {'success': False, 'error': str(e)}

    def get_running_processes(self) -> List[Dict[str, Any]]:
        """获取当前运行的SIPp进程信息"""
        return list(self.processes.values())

    def kill_all_processes(self):
        """终止所有运行中的SIPp进程"""
        for pid, process_info in self.processes.items():
            try:
                process_info['process'].kill()
                self.logger.info(f"Terminated process {pid}")
            except ProcessLookupError:
                self.logger.info(f"Process {pid} already terminated")
            except Exception as e:
                self.logger.warning(f"Error killing process {pid}: {e}")
        
        self.processes.clear()

    def cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
                self.logger.info(f"Removed temporary file: {temp_file}")
            except OSError as e:
                self.logger.warning(f"Error removing temporary file {temp_file}: {e}")
        
        self.temp_files.clear()

    def close(self):
        """关闭客户端，清理资源"""
        self.kill_all_processes()
        self.cleanup_temp_files()