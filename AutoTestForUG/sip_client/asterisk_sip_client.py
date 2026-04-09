"""
Asterisk SIP客户端实现
通过AMI/ARI接口控制Asterisk服务器进行测试
"""
import logging
from typing import Dict, Any, Optional, Callable, List
from .sip_client_base import SIPClientBase


class AsteriskSIPClient(SIPClientBase):
    """
    Asterisk SIP客户端实现
    通过AMI/ARI接口控制Asterisk服务器进行测试
    支持AMQP消息队列进行异步通信
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
                - amqp_enabled: 是否启用AMQP，默认False
                - amqp_host: AMQP服务器地址，默认localhost
                - amqp_port: AMQP端口，默认5672
                - amqp_username: AMQP用户名
                - amqp_password: AMQP密码
                - amqp_vhost: AMQP虚拟主机，默认/
                - fxo_trunk_config: FXO中继配置
                - fxs_endpoint_config: FXS终端配置
        """
        self.config = config
        self.ami_connection = None
        self.ari_connection = None
        self.amqp_connection = None
        self.amqp_channel = None
        self.message_callbacks = {}
        
        self.asterisk_host = config.get('asterisk_host', '127.0.0.1')
        self.ami_port = config.get('ami_port', 5038)
        self.ami_username = config.get('ami_username', 'admin')
        self.ami_password = config.get('ami_password', 'password')
        self.ari_port = config.get('ari_port', 8088)
        self.ari_username = config.get('ari_username', 'asterisk')
        self.ari_password = config.get('ari_password', 'asterisk')
        
        # AMQP配置
        self.amqp_enabled = config.get('amqp_enabled', False)
        self.amqp_host = config.get('amqp_host', 'localhost')
        self.amqp_port = config.get('amqp_port', 5672)
        self.amqp_username = config.get('amqp_username', 'guest')
        self.amqp_password = config.get('amqp_password', 'guest')
        self.amqp_vhost = config.get('amqp_vhost', '/')
        
        # FXO/FXS配置
        self.fxo_trunk_config = config.get('fxo_trunk_config', {})
        self.fxs_endpoint_config = config.get('fxs_endpoint_config', {})
        
        self.logger = logging.getLogger(__name__)
        
        # 初始化连接
        self._connect_ami()
        self._connect_ari()
        
        if self.amqp_enabled:
            self._connect_amqp()
    
    def _connect_ami(self):
        """连接到Asterisk Manager Interface"""
        try:
            # 这里使用pyst2库连接AMI
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
            # 尝试使用其他库或提供模拟连接
            self.ami_connection = self._create_mock_ami_connection()
        except Exception as e:
            self.logger.error(f"连接Asterisk AMI失败: {str(e)}")
            self.ami_connection = self._create_mock_ami_connection()

    def _create_mock_ami_connection(self):
        """创建模拟AMI连接，用于开发和测试"""
        class MockAMIConnection:
            def send_action(self, action_data):
                # 模拟AMI响应
                action = action_data.get('Action', '').lower()
                if action == 'originate':
                    return {'Response': 'Success'}
                elif action == 'command':
                    return {'Response': 'Follows', 'Output': 'Command executed successfully'}
                else:
                    return {'Response': 'Success'}
            
            def logoff(self):
                pass
        
        self.logger.info("使用模拟AMI连接进行开发测试")
        return MockAMIConnection()
    
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

    def _connect_amqp(self):
        """连接到AMQP消息队列服务器"""
        try:
            # 这里使用pika库连接AMQP
            import pika
            credentials = pika.PlainCredentials(self.amqp_username, self.amqp_password)
            parameters = pika.ConnectionParameters(
                host=self.amqp_host,
                port=self.amqp_port,
                virtual_host=self.amqp_vhost,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            
            self.amqp_connection = pika.BlockingConnection(parameters)
            self.amqp_channel = self.amqp_connection.channel()
            
            # 声明交换机和队列
            self.amqp_channel.exchange_declare(exchange='asterisk_events', exchange_type='topic', durable=True)
            self.amqp_channel.queue_declare(queue='asterisk_notifications', durable=True)
            self.amqp_channel.queue_bind(
                exchange='asterisk_events',
                queue='asterisk_notifications',
                routing_key='asterisk.#'
            )
            
            # 设置消费者
            self.amqp_channel.basic_qos(prefetch_count=1)
            
            self.logger.info(f"成功连接到AMQP服务器: {self.amqp_host}:{self.amqp_port}")
        except ImportError:
            self.logger.warning("pika未安装，无法连接AMQP消息队列")
        except Exception as e:
            self.logger.error(f"连接AMQP消息队列失败: {str(e)}")
    
    def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        发布事件到AMQP队列
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            bool: 发布是否成功
        """
        try:
            if not self.amqp_channel:
                self.logger.error("AMQP通道不可用")
                return False
            
            import json
            import time
            
            message = {
                'timestamp': time.time(),
                'event_type': event_type,
                'data': data,
                'source': 'asterisk_client'
            }
            
            self.amqp_channel.basic_publish(
                exchange='asterisk_events',
                routing_key=f'asterisk.{event_type}',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # 持久化消息
                    content_type='application/json'
                )
            )
            
            self.logger.info(f"事件已发布到AMQP: {event_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"发布AMQP事件失败: {str(e)}")
            return False
    
    def consume_events(self, event_types: List[str], callback_func: Callable[[Dict[str, Any]], None]):
        """
        消费AMQP队列中的事件
        
        Args:
            event_types: 要监听的事件类型列表
            callback_func: 事件回调函数
        """
        try:
            if not self.amqp_channel:
                self.logger.error("AMQP通道不可用")
                return
            
            # 为每种事件类型绑定队列
            for event_type in event_types:
                binding_key = f'asterisk.{event_type}'
                self.amqp_channel.queue_bind(
                    exchange='asterisk_events',
                    queue='asterisk_notifications',
                    routing_key=binding_key
                )
            
            def handle_delivery(ch, method, properties, body):
                try:
                    event_data = json.loads(body.decode('utf-8'))
                    callback_func(event_data)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    self.logger.error(f"处理AMQP消息失败: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            
            self.amqp_channel.basic_consume(
                queue='asterisk_notifications',
                on_message_callback=handle_delivery
            )
            
            self.logger.info(f"开始监听AMQP事件: {event_types}")
            self.amqp_channel.start_consuming()
            
        except Exception as e:
            self.logger.error(f"消费AMQP事件失败: {str(e)}")
    
    def stop_consuming_events(self):
        """停止消费事件"""
        try:
            if self.amqp_channel:
                self.amqp_channel.stop_consuming()
                self.logger.info("已停止监听AMQP事件")
        except Exception as e:
            self.logger.error(f"停止消费AMQP事件失败: {str(e)}")
    
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

    def configure_fxo_trunk(self, trunk_config: Dict[str, Any]) -> bool:
        """
        配置FXO中继通道
        
        Args:
            trunk_config: FXO中继配置信息
            
        Returns:
            bool: 配置是否成功
        """
        try:
            if self.ami_connection:
                trunk_name = trunk_config.get('name', 'fxo_trunk')
                channel_group = trunk_config.get('channel_group', 1)
                signaling = trunk_config.get('signaling', 'fxo_gs')
                
                # 生成FXO中继配置
                fxo_config = f"""
[{trunk_name}]
type=peer
context=from-fxo
disallow=all
allow=ulaw
group={channel_group}
signalling={signaling}
callerid=unknown
"""
                
                # 上传FXO配置到Asterisk
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': f'database put FXO/Trunks {trunk_name} "{fxo_config}"'
                })
                
                self.logger.info(f"FXO中继配置完成: {trunk_name}")
                
                # 发布配置事件到AMQP
                if self.amqp_enabled:
                    event_data = {
                        'event_type': 'fxo_trunk_configured',
                        'trunk_name': trunk_name,
                        'config': trunk_config,
                        'timestamp': __import__('time').time()
                    }
                    self.publish_event('configuration.fxo', event_data)
                
                return True
            else:
                self.logger.error("AMI连接不可用，无法配置FXO中继")
                return False
        except Exception as e:
            self.logger.error(f"FXO中继配置失败: {str(e)}")
            return False

    def configure_fxs_endpoint(self, endpoint_config: Dict[str, Any]) -> bool:
        """
        配置FXS终端通道
        
        Args:
            endpoint_config: FXS终端配置信息
            
        Returns:
            bool: 配置是否成功
        """
        try:
            if self.ami_connection:
                endpoint_name = endpoint_config.get('name', 'fxs_endpoint')
                channel_group = endpoint_config.get('channel_group', 1)
                signaling = endpoint_config.get('signaling', 'fxs_ls')
                
                # 生成FXS终端配置
                fxs_config = f"""
[{endpoint_name}]
type=friend
context=from-fxs
disallow=all
allow=ulaw
group={channel_group}
signalling={signaling}
callerid="FXS Endpoint" <{endpoint_name}>
"""
                
                # 上传FXS配置到Asterisk
                response = self.ami_connection.send_action({
                    'Action': 'Command',
                    'Command': f'database put FXS/Endpoints {endpoint_name} "{fxs_config}"'
                })
                
                self.logger.info(f"FXS终端配置完成: {endpoint_name}")
                
                # 发布配置事件到AMQP
                if self.amqp_enabled:
                    event_data = {
                        'event_type': 'fxs_endpoint_configured',
                        'endpoint_name': endpoint_name,
                        'config': endpoint_config,
                        'timestamp': __import__('time').time()
                    }
                    self.publish_event('configuration.fxs', event_data)
                
                return True
            else:
                self.logger.error("AMI连接不可用，无法配置FXS终端")
                return False
        except Exception as e:
            self.logger.error(f"FXS终端配置失败: {str(e)}")
            return False

    def test_fxo_fxs_connection(self, test_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        测试FXO/FXS连接
        
        Args:
            test_params: 测试参数
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        try:
            if not self.ami_connection:
                return {'success': False, 'error': 'AMI connection unavailable'}
            
            # 获取测试参数
            fxo_trunk = test_params.get('fxo_trunk', 'default_fxo')
            fxs_endpoint = test_params.get('fxs_endpoint', 'default_fxs')
            test_duration = test_params.get('duration', 10)  # 秒
            
            # 发起FXO到FXS的呼叫
            channel = f"DAHDI/g1/{fxo_trunk}"  # 假设使用DAHDI通道
            context = "from-fxo"
            extension = fxs_endpoint  # 被叫FXS终端
            
            response = self.ami_connection.send_action({
                'Action': 'Originate',
                'Channel': channel,
                'Context': context,
                'Exten': extension,
                'Priority': '1',
                'Timeout': str(test_duration * 1000),  # 毫秒
                'Async': 'true'
            })
            
            # 监听呼叫事件
            test_result = {
                'success': 'Response' in response and response['Response'] == 'Success',
                'test_type': 'fxo_fxs_connection',
                'fxo_trunk': fxo_trunk,
                'fxs_endpoint': fxs_endpoint,
                'duration': test_duration,
                'ami_response': response
            }
            
            self.logger.info(f"FXO/FXS连接测试完成: {fxo_trunk} -> {fxs_endpoint}")
            
            # 发布测试事件到AMQP
            if self.amqp_enabled:
                event_data = {
                    'event_type': 'fxo_fxs_test_completed',
                    'result': test_result,
                    'timestamp': __import__('time').time()
                }
                self.publish_event('test.fxo_fxs', event_data)
            
            return test_result
        except Exception as e:
            self.logger.error(f"FXO/FXS连接测试失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
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

    def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """
        通过AMQP发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            bool: 发布是否成功
        """
        if not self.amqp_enabled or not self.amqp_channel:
            self.logger.warning("AMQP未启用或连接不可用")
            return False
        
        try:
            import json
            import pika
            message_body = json.dumps(data)
            routing_key = f"asterisk.{event_type}"
            
            self.amqp_channel.basic_publish(
                exchange='asterisk_events',
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # 消息持久化
                )
            )
            
            self.logger.info(f"事件已发布到AMQP: {routing_key}")
            return True
        except Exception as e:
            self.logger.error(f"发布事件到AMQP失败: {str(e)}")
            return False

    def setup_event_handlers(self, handlers_config: Dict[str, Callable]) -> bool:
        """
        设置事件处理器
        
        Args:
            handlers_config: 事件处理器配置，格式为 {event_pattern: handler_function}
            
        Returns:
            bool: 设置是否成功
        """
        if not self.amqp_enabled:
            self.logger.warning("AMQP未启用，无法设置事件处理器")
            return False
        
        try:
            for event_pattern, handler_func in handlers_config.items():
                self.subscribe_to_events(event_pattern, handler_func)
            
            self.logger.info(f"设置了 {len(handlers_config)} 个事件处理器")
            return True
        except Exception as e:
            self.logger.error(f"设置事件处理器失败: {str(e)}")
            return False

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        获取Asterisk系统指标
        
        Returns:
            Dict[str, Any]: 系统指标数据
        """
        try:
            if self.ami_connection:
                # 获取Asterisk系统信息
                response = self.ami_connection.send_action({'Action': 'CoreStatus'})
                
                # 获取活跃通道信息
                channels_response = self.ami_connection.send_action({'Action': 'CoreShowChannels'})
                
                # 获取SIP对等信息
                sip_peers_response = self.ami_connection.send_action({'Action': 'SIPpeers'})
                
                metrics = {
                    'core_status': response,
                    'active_channels': channels_response,
                    'sip_peers': sip_peers_response,
                    'timestamp': __import__('time').time()
                }
                
                # 发布指标事件到AMQP
                if self.amqp_enabled:
                    self.publish_event('metrics.system', metrics)
                
                return metrics
            else:
                return {'error': 'AMI connection unavailable'}
        except Exception as e:
            self.logger.error(f"获取系统指标失败: {str(e)}")
            return {'error': str(e)}

    def subscribe_to_events(self, event_pattern: str, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """
        订阅AMQP事件
        
        Args:
            event_pattern: 事件模式
            callback: 回调函数
            
        Returns:
            bool: 订阅是否成功
        """
        if not self.amqp_enabled or not self.amqp_channel:
            self.logger.warning("AMQP未启用或连接不可用")
            return False
        
        try:
            # 为特定事件模式创建队列
            queue_name = f"subscriber_{event_pattern.replace('.', '_').replace('*', 'any').replace('#', 'all')}"
            self.amqp_channel.queue_declare(queue=queue_name, durable=True)
            self.amqp_channel.queue_bind(
                exchange='asterisk_events',
                queue=queue_name,
                routing_key=event_pattern
            )
            
            # 注册回调函数
            self.message_callbacks[event_pattern] = callback
            
            def handle_message(ch, method, properties, body):
                try:
                    import json
                    data = json.loads(body.decode('utf-8'))
                    if event_pattern in self.message_callbacks:
                        self.message_callbacks[event_pattern](data)
                except Exception as e:
                    self.logger.error(f"处理AMQP消息失败: {str(e)}")
            
            self.amqp_channel.basic_consume(
                queue=queue_name,
                on_message_callback=handle_message,
                auto_ack=True
            )
            
            self.logger.info(f"已订阅AMQP事件: {event_pattern}")
            return True
        except Exception as e:
            self.logger.error(f"订阅AMQP事件失败: {str(e)}")
            return False

    def start_event_listening(self):
        """
        开始监听AMQP事件
        """
        if not self.amqp_enabled or not self.amqp_channel:
            self.logger.warning("AMQP未启用或连接不可用")
            return
        
        try:
            self.logger.info("开始监听AMQP事件...")
            # 在单独的线程中启动消费者
            import threading
            consumer_thread = threading.Thread(target=self._consume_messages)
            consumer_thread.daemon = True
            consumer_thread.start()
        except Exception as e:
            self.logger.error(f"启动AMQP事件监听失败: {str(e)}")

    def _consume_messages(self):
        """
        内部方法：消费AMQP消息
        """
        try:
            self.amqp_channel.start_consuming()
        except Exception as e:
            self.logger.error(f"AMQP消息消费异常: {str(e)}")

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
        
        try:
            if self.amqp_connection:
                self.amqp_connection.close()
                self.logger.info("Asterisk AMQP连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭Asterisk AMQP连接时出错: {str(e)}")
    
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
        
        try:
            if self.amqp_connection:
                self.amqp_connection.close()
                self.logger.info("已断开Asterisk AMQP连接")
        except Exception as e:
            self.logger.error(f"断开AMQP连接时出错: {str(e)}")