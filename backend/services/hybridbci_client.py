"""
HybridBCI 平台客户端（IPC Socket 通信）
功能：
- 连接科创平台（默认 127.0.0.1:8000）
- 接收 ipc_algorithm_test 消息
- 解析 attention / blink / gyroscope 等算法输出
- 通过 routes.unity.send_command_to_unity 推送给对应的 Unity 客户端
"""

import socket
import json
import threading
import time
import logging
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='[HybridBCI] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HybridBCIClient:
    def __init__(self, socketio, host='127.0.0.1', port=8000, auto_reconnect=True):
        """
        初始化客户端
        :param socketio: Flask-SocketIO 实例（用于推送指令给 Unity）
        :param host: 科创平台 IP
        :param port: 端口（默认 8000，鼠标模块为 9527）
        :param auto_reconnect: 是否自动重连
        """
        self.socketio = socketio
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect
        self.sock = None
        self.running = False
        self.thread = None

        # 当前患者ID（可从平台用户信息中获取，简化起见先为 None）
        self.patient_id = None

    def start(self):
        """启动客户端（非阻塞，内部启动线程）"""
        if self.running:
            logger.warning("客户端已在运行")
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"客户端已启动，目标 {self.host}:{self.port}")

    def stop(self):
        """停止客户端"""
        self.running = False
        if self.sock:
            self.sock.close()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("客户端已停止")

    def _run(self):
        """主循环：连接并处理消息"""
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
        """建立 TCP 连接，并发送 ipc_user_info 协议（平台要求）"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)  # 设置超时
        self.sock.connect((self.host, self.port))
        logger.info(f"已连接到 {self.host}:{self.port}")

        # 发送用户信息（窗口句柄为 0，表示无图形界面）
        user_info = {
            "msg": "ipc_user_info",
            "window": 0
        }
        self._send_json(user_info)
        logger.info("已发送 ipc_user_info")

    def _send_json(self, data: dict):
        """发送 JSON 消息，每条消息以换行符结束"""
        if self.sock:
            message = json.dumps(data, ensure_ascii=False) + "\n"
            self.sock.send(message.encode('utf-8'))

    def _handle_messages(self):
        """循环接收消息，按行解析（平台每条 JSON 以换行分隔）"""
        buffer = ""
        while self.running and self.sock:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    logger.warning("连接已关闭（recv 空）")
                    break
                buffer += data
                # 按换行符拆分消息
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
        """处理单条 JSON 消息"""
        try:
            msg = json.loads(msg_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e} | 原始数据: {msg_str[:100]}")
            return

        msg_type = msg.get("msg")
        if msg_type == "ipc_algorithm_test":
            self._handle_algorithm_test(msg)
        elif msg_type == "ipc_user_info":
            # 可保存 patient_id 等（如果有）
            logger.info(f"收到用户信息: {msg.get('user_name')}, 布局模式: {msg.get('layout_type')}")
            # 如果平台提供了患者ID，可以更新 self.patient_id
            if "patient_id" in msg:
                self.patient_id = msg["patient_id"]
        elif msg_type == "ipc_set_visible":
            visible = msg.get("visible", True)
            logger.info(f"平台要求窗口可见性: {visible}")
        elif msg_type == "ipc_exit":
            logger.info("收到退出指令，客户端即将停止")
            self.stop()
        else:
            logger.debug(f"忽略未处理消息类型: {msg_type}")

    def _handle_algorithm_test(self, msg: dict):
        """
        处理 ipc_algorithm_test，转换为游戏指令并推送给 Unity
        """
        algorithm_name = msg.get("algorithm_name")
        result_args = msg.get("result_args", {})
        logger.info(f"收到算法输出: {algorithm_name} -> {result_args}")

        command = self._convert_to_command(algorithm_name, result_args)
        if command:
            self._send_to_unity(command)

    def _convert_to_command(self, algorithm_name: str, result_args: dict) -> Optional[dict]:
        """
        将 BCI 输出转换为统一的游戏指令格式
        """
        if algorithm_name == "attention":
            att = result_args.get("data")
            if att is None:
                return None
            # 映射：注意力>65 前进，<35 后退，中间 idle
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
            if abs(yaw) > 5:  # 阈值5度
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
        """通过 routes.unity 模块中的函数发送指令到对应的 Unity 客户端"""
        # 延迟导入，避免循环依赖
        from routes.unity import send_command_to_unity
        # 如果没有患者ID，尝试使用全局广播（可能无效）
        if self.patient_id:
            send_command_to_unity(self.patient_id, command)
        else:
            # 如果没有患者ID，可以广播或记录错误
            logger.warning("没有患者ID，无法定向推送指令，尝试广播")
            self.socketio.emit('game_command', command, namespace='/unity', broadcast=True)