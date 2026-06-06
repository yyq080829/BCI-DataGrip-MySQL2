""" HybridBCI 平台客户端 - 纯 Python 移植版（兼容官方 HNNKTcpSocketClient 协议） """
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
    def __init__(self, socketio, host='127.0.0.1', port=8000, auto_reconnect=True, window_handle=12345):
        self.socketio = socketio
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect
        self.window_handle = window_handle  # [修复4] 可配置window句柄
        self.sock = None
        self.running = False
        self.thread = None
        self._recv_buffer = b''
        self._socket_lock = threading.Lock()  # [修复3] 线程锁
        self.patient_id = None
        self._heartbeat_interval = 30  # [修复6] 心跳间隔
        self._heartbeat_thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        # [修复6] 启动心跳线程
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info(f"客户端启动，目标 {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
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
        # [修复4] 先关闭旧连接，防止资源泄漏
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
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
            with self._socket_lock:  # [修复3] 加锁
                self.sock.send(header + payload)
            logger.info(f"发送: {data}")
        except Exception as e:
            logger.error(f"发送失败: {e}")

    def send_event(self, event_id: int, extra_data: dict = None):
        """向平台发送打标事件 (ipc_event)"""
        msg = {"msg": "ipc_event", "event": event_id}
        if extra_data:
            msg.update(extra_data)  # [修复1] 实际加入消息体
            logger.info(f"发送事件 {event_id}, 附加数据: {extra_data}")
        self._send_json(msg)

        # [修复6] 心跳保活

    def _heartbeat_loop(self):
        """定期发送心跳保活"""
        while self.running:
            time.sleep(self._heartbeat_interval)
            if self.sock:
                try:
                    self._send_json({"msg": "ipc_heartbeat"})
                    logger.debug("心跳已发送")
                except Exception as e:
                    logger.warning(f"心跳发送失败: {e}")

                    # [修复7] 可靠的缓冲区读取

    def _recv_exactly(self, n: int) -> Optional[bytes]:
        """确保从缓冲区/套接字读取恰好 n 字节"""
        while len(self._recv_buffer) < n:
            try:
                with self._socket_lock:  # [修复3] 加锁
                    chunk = self.sock.recv(8192)
                if not chunk:
                    return None
                self._recv_buffer += chunk
            except socket.timeout:
                if not self.running:
                    return None
                continue
            except Exception as e:
                logger.error(f"接收异常: {e}")
                return None
        data = self._recv_buffer[:n]
        self._recv_buffer = self._recv_buffer[n:]
        return data

    def _handle_messages(self):
        """接收并解析长度前缀消息（健壮版）"""
        while self.running and self.sock:
            try:
                # 1. 读取4字节头部
                header = self._recv_exactly(4)
                if header is None:
                    logger.warning("连接已关闭（头部读取失败）")
                    break

                    # 2. 读取完整负载
                payload_len = struct.unpack('>I', header)[0]
                if payload_len > 10 * 1024 * 1024:  # 防护：超10MB视为异常
                    logger.error(f"异常负载长度: {payload_len}")
                    break

                payload = self._recv_exactly(payload_len)
                if payload is None:
                    logger.warning("连接已关闭（负载读取失败）")
                    break

                    # 3. 解析处理
                msg_str = payload.decode('utf-8')
                logger.info(f"原始消息: {msg_str}")
                msg = json.loads(msg_str)
                self._dispatch_message(msg)

            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
            except Exception as e:
                logger.error(f"处理异常: {e}")
                break

    def _dispatch_message(self, msg: dict):
        msg_type = msg.get("msg")
        if msg_type in ("ipcuser", "ipc_user_info", "ipcuserinfo"):
            groupname = msg.get("groupname") or msg.get("group_name")
            layout = msg.get("layouttype") or msg.get("layout_type")

            # [修复2] 从消息中提取 patient_id
            self.patient_id = (
                    msg.get("patient_id") or
                    msg.get("patientid") or
                    msg.get("user_id") or
                    groupname
            )
            logger.info(f"收到平台用户信息: groupname={groupname}, "
                        f"layout={layout}, patient_id={self.patient_id}")

            # [修复4] 使用可配置的 window_handle
            reply = {"msg": "ipc_user_info", "window": self.window_handle}
            self._send_json(reply)
            logger.info(f"已回复 ipc_user_info window={self.window_handle}")

        elif msg_type == "ipc_algorithm_test":
            self._handle_algorithm_test(msg)
        elif msg_type == "ipc_set_visible":
            logger.info(f"平台要求窗口可见性: {msg.get('visible')}")
        elif msg_type == "ipc_exit":
            logger.info("收到退出指令")
            self.stop()
        elif msg_type == "ipc_event":
            logger.info(f"平台确认事件: {msg.get('event')} 时间: {msg.get('start')}")
        elif msg_type == "ipc_heartbeat":
            logger.debug("收到平台心跳响应")
        else:
            logger.info(f"未处理的消息类型: {msg_type}")

    def _handle_algorithm_test(self, msg: dict):
        algorithm_name = msg.get("algorithm_name")
        result_args = msg.get("result_args", {})
        logger.info(f"算法输出: {algorithm_name} -> {result_args}")
        command = self._convert_to_command(algorithm_name, result_args)
        if command:
            self._send_to_unity(command)

            # [修复5] 支持多种算法

    def _convert_to_command(self, algorithm_name: str, result_args: dict) -> Optional[dict]:
        algorithm_name = algorithm_name.lower().strip()

        if algorithm_name == "p300":
            data = result_args.get("data")
            if data is not None:
                return {"cmd": "SELECT", "param": str(data)}

        elif algorithm_name == "ssvep":
            frequency = result_args.get("frequency") or result_args.get("data")
            if frequency is not None:
                return {"cmd": "FOCUS", "param": str(frequency)}

        elif algorithm_name in ("mi", "motor_imagery"):
            direction = result_args.get("direction") or result_args.get("data")
            if direction is not None:
                return {"cmd": "MOVE", "param": str(direction)}

        elif algorithm_name == "relax":
            return {"cmd": "RELAX", "param": "0"}

        else:
            data = result_args.get("data")
            if data is not None:
                return {"cmd": algorithm_name.upper(), "param": str(data)}

        logger.warning(f"无法转换算法结果: {algorithm_name} -> {result_args}")
        return None

    def _send_to_unity(self, command: dict):
        from routes.unity import send_command_to_unity
        if self.patient_id:
            send_command_to_unity(self.patient_id, command)
        else:
            logger.warning("无患者ID，使用默认 ID 202505001")
            send_command_to_unity("202505001", command)
