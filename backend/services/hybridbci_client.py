"""
HybridBCI 平台客户端（IPC Socket 通信）
功能：
- 连接科创平台（默认 127.0.0.1:8000）
- 遵循协议：先等待平台发送 ipc_user_info，再回复窗口句柄
- 接收 ipc_algorithm_test 消息
- 解析 attention / blink / gyroscope 等算法输出
- 通过 routes.unity.send_command_to_unity 推送给对应的 Unity 客户端
- 新增：向平台发送 ipc_event 事件（例如游戏结果反馈）
"""

import socket
import json
import threading
import time
import logging
from typing import Optional, Dict, Any

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
        self.patient_id = None  # 可从平台信息中获取
        self._send_lock = threading.Lock()  # 发送锁，避免多线程同时写

    def start(self):
        if self.running:
            logger.warning("客户端已在运行")
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"客户端已启动，目标 {self.host}:{self.port}")

    def stop(self):
        self.running = False
        with self._send_lock:
            if self.sock:
                self.sock.close()
                self.sock = None
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("客户端已停止")

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
        """建立 TCP 连接，但不主动发送任何消息（等待平台先发）"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((self.host, self.port))
        with self._send_lock:
            self.sock = sock
        logger.info(f"已连接到 {self.host}:{self.port}")

    def _send_json(self, data: dict):
        """发送 JSON 消息，每条消息以换行符结束"""
        with self._send_lock:
            if not self.sock:
                logger.warning("socket 未连接，无法发送")
                return False
            try:
                message = json.dumps(data, ensure_ascii=False) + "\n"
                self.sock.send(message.encode('utf-8'))
                logger.debug(f"发送: {data}")
                return True
            except Exception as e:
                logger.error(f"发送失败: {e}")
                return False

    def send_event(self, event_id: int, extra_data: Optional[Dict] = None):
        """
        向平台发送打标事件 (ipc_event)
        :param event_id: 整数事件ID，例如 100 表示训练完成
        :param extra_data: 可选，但平台标准协议只接受 event 字段，extra 不会解析，仅用于日志
        """
        msg = {"msg": "ipc_event", "event": event_id}
        if extra_data:
            logger.info(f"发送事件 {event_id}, 附加数据: {extra_data} (平台可能不接收额外字段)")
        return self._send_json(msg)

    def _handle_messages(self):
        """循环接收消息，按行解析"""
        buffer = ""
        while self.running:
            with self._send_lock:
                sock = self.sock
            if not sock:
                break
            try:
                data = sock.recv(4096).decode('utf-8')
                if not data:
                    logger.warning("连接已关闭（recv 空）")
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    self._process_message(line)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"接收消息异常: {e}")
                break

    def _process_message(self, msg_str: str):
        try:
            msg = json.loads(msg_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e} | 原始数据: {msg_str[:100]}")
            return

        msg_type = msg.get("msg")
        if msg_type == "ipc_user_info":
            logger.info(f"收到平台用户信息: {msg.get('user_name')}, 布局模式: {msg.get('layout_type')}")
            if "patient_id" in msg:
                self.patient_id = msg["patient_id"]
            # 回复窗口句柄
            reply = {"msg": "ipc_user_info", "window": 0}
            self._send_json(reply)
            logger.info("已回复 window=0")

        elif msg_type == "ipc_algorithm_test":
            self._handle_algorithm_test(msg)

        elif msg_type == "ipc_set_visible":
            visible = msg.get("visible", True)
            logger.info(f"平台要求窗口可见性: {visible}")
            # 无需回复

        elif msg_type == "ipc_exit":
            logger.info("收到退出指令，客户端即将停止")
            self.stop()

        elif msg_type == "ipc_event":
            # 平台回复的打标成功确认
            event_id = msg.get("event")
            start_time = msg.get("start")
            logger.info(f"平台确认事件 {event_id} 已处理, 时间: {start_time}")

        else:
            logger.debug(f"忽略未处理消息类型: {msg_type}")

    def _handle_algorithm_test(self, msg: dict):
        algorithm_name = msg.get("algorithm_name")
        result_args = msg.get("result_args", {})
        logger.info(f"收到算法输出: {algorithm_name} -> {result_args}")

        command = self._convert_to_command(algorithm_name, result_args)
        if command:
            self._send_to_unity(command)

    def _convert_to_command(self, algorithm_name: str, result_args: dict) -> Optional[dict]:
        if algorithm_name == "attention":
            att = result_args.get("data")
            if att is None:
                return None
            if att > 65:
                action = "FORWARD"
                intensity = min(1.0, (att - 65) / 35)
            elif att < 35:
                action = "BACKWARD"
                intensity = min(1.0, (35 - att) / 35)
            else:
                action = "IDLE"
                intensity = 0.0
            return {"cmd": action, "intensity": round(intensity, 2)}

        elif algorithm_name == "blink":
            blink_val = result_args.get("data")
            if blink_val == "1":
                return {"cmd": "JUMP", "intensity": 1.0}
            return None

        elif algorithm_name == "gyroscope":
            data = result_args.get("data", {})
            yaw = data.get("gyroscope_x", 0.0)
            if abs(yaw) > 5:
                direction = "RIGHT" if yaw > 0 else "LEFT"
                intensity = min(1.0, abs(yaw) / 30.0)
                return {"cmd": direction, "intensity": round(intensity, 2)}
            return None

        elif algorithm_name in ("p300", "ssvep"):
            cmd_char = result_args.get("data")
            if cmd_char:
                return {"cmd": "SELECT", "param": str(cmd_char)}
            return None

        elif algorithm_name == "mi":
            cmd = result_args.get("data")
            if cmd:
                return {"cmd": "ACTION", "param": str(cmd)}
            return None

        else:
            logger.warning(f"未支持的算法: {algorithm_name}")
            return None

    def _send_to_unity(self, command: dict):
        from routes.unity import send_command_to_unity
        if self.patient_id:
            send_command_to_unity(self.patient_id, command)
        else:
            logger.warning("没有患者ID，尝试广播")
            self.socketio.emit('game_command', command, namespace='/unity', broadcast=True)