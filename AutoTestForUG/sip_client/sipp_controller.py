"""
SIPp控制器模块
提供高级API封装SIPp的命令行接口，实现SIPp进程的生命周期管理
"""
import subprocess
import tempfile
import os
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import threading
import signal
import logging


class SIPpController:
    """
    SIPp控制器，用于管理SIPp进程的生命周期
    """
    
    def __init__(self, sipp_path: str = "sipp"):
        self.sipp_path = sipp_path
        self.processes = {}  # 存储运行中的SIPp进程
        self.temp_files = []  # 存储临时文件路径
        self.logger = logging.getLogger(__name__)
    
    def run_scenario(self, scenario_file: str, destination: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        运行SIPp场景
        
        Args:
            scenario_file: SIPp场景文件路径
            destination: 目标地址 (host:port)
            options: 运行选项，如 -i, -p, -r 等
        
        Returns:
            包含进程信息和执行结果的字典
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
            
            # 等待进程完成
            stdout, stderr = process.communicate(timeout=options.get('timeout', 300))
            
            process_info.update({
                'return_code': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'end_time': time.time(),
                'duration': time.time() - process_info['start_time']
            })
            
            return process_info
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return {
                'return_code': -1,
                'stdout': stdout,
                'stderr': stderr,
                'error': 'Process timed out'
            }
        except FileNotFoundError:
            return {
                'return_code': -1,
                'error': f'SIPp executable not found at {self.sipp_path}'
            }
        except Exception as e:
            return {
                'return_code': -1,
                'error': str(e)
            }
    
    def generate_scenario_xml(self, scenario_type: str, params: Dict[str, Any]) -> str:
        """
        生成SIPp场景XML文件
        
        Args:
            scenario_type: 场景类型 ('basic_call', 'registration', 'options', 等)
            params: 场景参数
        
        Returns:
            生成的XML文件路径
        """
        if scenario_type == 'basic_call':
            xml_content = self._create_basic_call_scenario(params)
        elif scenario_type == 'registration':
            xml_content = self._create_registration_scenario(params)
        elif scenario_type == 'options':
            xml_content = self._create_options_scenario(params)
        else:
            raise ValueError(f"Unknown scenario type: {scenario_type}")
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
        temp_file.write(xml_content)
        temp_file.close()
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def _create_basic_call_scenario(self, params: Dict[str, Any]) -> str:
        """创建基本呼叫场景XML"""
        # 从参数中提取值，提供默认值
        remote_host = params.get('remote_host', '127.0.0.1')
        remote_port = params.get('remote_port', '5060')
        caller = params.get('caller', '1001')
        callee = params.get('callee', '1002')
        
        return f'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<!DOCTYPE scenario SYSTEM "sipp.dtd">

<scenario name="Basic Sipstone UAC">
  <send retrans="500">
    <![CDATA[
      INVITE sip:{callee}@{remote_host}:{remote_port} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: sipp <sip:{caller}@{remote_host}:{remote_port}>;tag=[pid][time]
      To: sut <sip:{callee}@{remote_host}:{remote_port}>
      Call-ID: [call_id]
      CSeq: 1 INVITE
      Contact: sip:sipp@[local_ip]:[local_port]
      Max-Forwards: 70
      Subject: Performance Test
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

  <recv response="200" rtd="true">
  </recv>

  <send>
    <![CDATA[
      ACK sip:{callee}@{remote_host}:{remote_port} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: sipp <sip:{caller}@{remote_host}:{remote_port}>;tag=[pid][time]
      To: sut <sip:{callee}@{remote_host}:{remote_port}>[peer_tag_param]
      Call-ID: [call_id]
      CSeq: 1 ACK
      Contact: sip:sipp@[local_ip]:[local_port]
      Max-Forwards: 70
      Content-Length: 0
    ]]>
  </send>

  <pause milliseconds="10000"/>

  <send retrans="500">
    <![CDATA[
      BYE sip:{callee}@{remote_host}:{remote_port} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: sipp <sip:{caller}@{remote_host}:{remote_port}>;tag=[pid][time]
      To: sut <sip:{callee}@{remote_host}:{remote_port}>[peer_tag_param]
      Call-ID: [call_id]
      CSeq: 2 BYE
      Contact: sip:sipp@[local_ip]:[local_port]
      Max-Forwards: 70
      Content-Length: 0
    ]]>
  </send>

  <recv response="200" crlf="true">
  </recv>

  <ResponseTimeRepartition value="10, 20, 30, 40, 50, 100, 150, 200"/>
  <CallLengthRepartition value="10, 50, 100, 500, 1000, 2000, 3000, 4000, 5000"/>

</scenario>'''
    
    def _create_registration_scenario(self, params: Dict[str, Any]) -> str:
        """创建注册场景XML"""
        registrar_host = params.get('registrar_host', '127.0.0.1')
        registrar_port = params.get('registrar_port', '5060')
        username = params.get('username', 'testuser')
        domain = params.get('domain', 'example.com')
        expires = params.get('expires', '3600')
        
        return f'''<?xml version="1.0" encoding="ISO-8859-1" ?>
<!DOCTYPE scenario SYSTEM "sipp.dtd">

<scenario name="Basic Registration">
  <send retrans="500">
    <![CDATA[
      REGISTER sip:{domain}:{registrar_port} SIP/2.0
      Via: SIP/2.0/[transport] [local_ip]:[local_port];branch=[branch]
      From: <sip:{username}@{domain}>;tag=[pid][time]
      To: <sip:{username}@{domain}>
      Call-ID: [call_id]
      CSeq: 1 REGISTER
      Contact: <sip:{username}@[local_ip]:[local_port]>;expires={expires}
      Max-Forwards: 70
      Expires: {expires}
      User-Agent: SIPp/Win32
      Content-Length: 0
    ]]>
  </send>

  <recv response="401" optional="true">
    <action>
      <!-- Extract authentication information if needed -->
    </action>
  </recv>

  <recv response="200" rtd="true">
  </recv>

  <ResponseTimeRepartition value="10, 20, 30, 40, 50, 100, 150, 200"/>
</scenario>'''
    
    def _create_options_scenario(self, params: Dict[str, Any]) -> str:
        """创建OPTIONS场景XML"""
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
    
    def kill_all_processes(self):
        """终止所有运行中的SIPp进程"""
        for pid, process_info in self.processes.items():
            try:
                process_info['process'].kill()
            except ProcessLookupError:
                pass  # 进程已经结束
            except Exception as e:
                self.logger.warning(f"Error killing process {pid}: {e}")
        
        self.processes.clear()
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        for temp_file in self.temp_files:
            try:
                os.remove(temp_file)
            except OSError:
                pass  # 文件可能已不存在
        
        self.temp_files.clear()


# 使用示例
if __name__ == "__main__":
    controller = SIPpController()
    
    # 创建一个注册场景
    params = {
        'registrar_host': '127.0.0.1',
        'registrar_port': '5060',
        'username': 'testuser',
        'domain': 'example.com'
    }
    
    scenario_file = controller.generate_scenario_xml('registration', params)
    
    # 运行场景
    result = controller.run_scenario(scenario_file, '127.0.0.1:5060', {
        '-i': '127.0.0.1',
        '-p': '6060',
        '-timeout': 60
    })
    
    print("Execution result:", result)
    
    # 清理资源
    controller.cleanup_temp_files()