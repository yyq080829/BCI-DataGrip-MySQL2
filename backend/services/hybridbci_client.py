"""
HybridBCI 平台客户端 - 使用长度前缀协议（兼容官方 HNNKTcpSocketClient）
"""
import socket
import struct
import json
import threading
import time
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format='[HybridBCI] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HybridBCIClient:
    def __init__(self, socketio, host='127.0.0.1', port=8000, auto_reconnect=True):
        self.socketio = socketio
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect
        self.sock = None
        self.running = False
        self.thread = None
        self._recv_buffer = b''
        self.patient_id = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"客户端启动，目标 {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self):
        while self.running:
            try:
                self._connect()
                self._handle_messages()
            except Exception as e:
                logger.error(f"连接异常: {e}")
                if not self.auto_reconnect:
                    break
                time.sleep(3)

    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((self.host, self.port))
        self._recv_buffer = b''
        logger.info(f"已连接到 {self.host}:{self.port}")

    def _send_json(self, data: dict):
        """发送JSON消息，格式：4字节大端长度 + JSON字符串"""
        if not self.sock:
            return
        json_str = json.dumps(data, ensure_ascii=False)
        payload = json_str.encode('utf-8')
        header = struct.pack('>I', len(payload))
        try:
            self.sock.send(header + payload)
            logger.info(f"发送: {data}")
        except Exception as e:
            logger.error(f"发送失败: {e}")

    def send_event(self, event_id: int, extra_data: dict = None):
        """向平台发送打标事件 (ipc_event)"""
        msg = {"msg": "ipc_event", "event": event_id}
        if extra_data:
            logger.info(f"发送事件 {event_id}, 附加数据: {extra_data} (平台可能忽略)")
        self._send_json(msg)

    def _handle_messages(self):
        while self.running and self.sock:
            try:
                if len(self._recv_buffer) < 4:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        logger.warning("连接已关闭（recv 空）")
                        break
                    self._recv_buffer += chunk
                    continue

                payload_len = struct.unpack('>I', self._recv_buffer[:4])[0]
                total_needed = 4 + payload_len
                if len(self._recv_buffer) < total_needed:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        logger.warning("连接已关闭（recv 空）")
                        break
                    self._recv_buffer += chunk
                    continue

                payload = self._recv_buffer[4:total_needed]
                self._recv_buffer = self._recv_buffer[total_needed:]

                try:
                    msg = json.loads(payload.decode('utf-8'))
                    self._dispatch_message(msg)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e} -> {payload[:100]}")
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"接收异常: {e}")
                break

    def _dispatch_message(self, msg: dict):
        msg_type = msg.get("msg")
        if msg_type in ("ipcuser", "ipc_user_info"):
            groupname = msg.get("groupname") or msg.get("group_name")
            layout = msg.get("layouttype") or msg.get("layout_type")
            logger.info(f"收到平台用户信息: {groupname}, 布局类型: {layout}")
            # 回复相同的 msg 类型
            reply = {"msg": msg_type, "window": 0}
            self._send_json(reply)
            logger.info(f"已回复 {msg_type} window=0")
        elif msg_type == "ipc_algorithm_test":
            self._handle_algorithm_test(msg)
        elif msg_type == "ipc_set_visible":
            logger.info(f"平台要求窗口可见性: {msg.get('visible')}")
        elif msg_type == "ipc_exit":
            logger.info("收到退出指令")
            self.stop()
        elif msg_type == "ipc_event":
            logger.info(f"平台确认事件: {msg.get('event')} 时间: {msg.get('start')}")
        else:
            logger.info(f"未处理的消息类型: {msg_type}")

    def _handle_algorithm_test(self, msg: dict):
        algorithm_name = msg.get("algorithm_name")
        result_args = msg.get("result_args", {})
        logger.info(f"算法输出: {algorithm_name} -> {result_args}")

        command = self._convert_to_command(algorithm_name, result_args)
        if command:
            self._send_to_unity(command)

    def _convert_to_command(self, algorithm_name: str, result_args: dict) -> Optional[dict]:
        if algorithm_name == "p300":
            data = result_args.get("data")
            if data is not None:
                return {"cmd": "SELECT", "param": str(data)}
        return None

    def _send_to_unity(self, command: dict):
        from routes.unity import send_command_to_unity
        if self.patient_id:
            send_command_to_unity(self.patient_id, command)
        else:
            logger.warning("无患者ID，使用默认 ID 202505001")
            send_command_to_unity("202505001", command)