"""
HybridBCI 平台客户端 - 纯 Python 移植版（兼容官方 HNNKTcpSocketClient 协议）

v5 修复清单（基于4轮终端测试 + 平台源码深度分析）：

  [致命修复1] 端口冲突：Flask和BCI客户端都用8000端口
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    app.py: socketio.run(app, host='172.17.37.19', port=8000)
    BCI客户端: connect(172.17.37.19, 8000)
    → Flask自己监听8000，BCI客户端也连8000，连的是自己不是平台！
    → 修复：Flask用5000端口，BCI客户端连平台8000端口

  [致命修复2] 心跳导致平台断连
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    终端日志：连接成功 → 30秒后发心跳 → 立刻断连
    原因：官方Demo不发心跳，平台不期望收到客户端心跳
    → 修复：完全禁用主动心跳

  [致命修复3] 缺少实验记录上报机制
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    平台"实验记录"需要客户端通过 ipc_experiment_data 协议上报
    当前代码没有实现此协议，所以平台不会出现实验记录
    → 修复：新增 send_experiment_data 方法

  [修复4] ipc_user_info 回复：始终回复 window=0
  [修复5] sock.send → sock.sendall
  [修复6] _handle_messages 缩进错误
  [修复7] _recv_exactly 缓冲区模式

新增功能：
  - P300 闪烁事件处理：绿色频闪输出0，红色闪烁输出1+坐标
  - send_p300_marker：向平台发送P300打标事件
  - send_experiment_data：向平台上报实验记录数据
"""

import socket
import struct
import json
import threading
import time
import logging
from typing import Optional, Callable

logging.basicConfig(level=logging.INFO, format='[HybridBCI] %(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class HybridBCIClient:
    """
    HybridBCI 平台 TCP 客户端

    协议格式：[4字节大端长度][JSON负载]
    与官方 HNNKTcpSocketClient 完全兼容

    P300 新增功能：
    - 绿色频闪（非目标刺激）→ 终端输出 0
    - 红色闪烁（目标刺激）  → 终端输出 1 和坐标 (row, col)
    """

    def __init__(self, socketio, host='127.0.0.1', port=8000,
                 auto_reconnect=True, window_handle=0,
                 p300_grid_rows=3, p300_grid_cols=4):
        self.socketio = socketio
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect
        self.window_handle = window_handle
        self.p300_grid_rows = p300_grid_rows
        self.p300_grid_cols = p300_grid_cols
        self.sock = None
        self.running = False
        self._connected = False
        self._recv_thread = None
        self._recv_buffer = b''
        self._send_lock = threading.Lock()
        self.patient_id = None
        self.layout_type = 0
        self._user_info_received = False

    # ================================================================
    # 启动 / 停止
    # ================================================================

    def start(self):
        """启动客户端连接线程"""
        if self.running:
            return
        self.running = True
        self._recv_thread = threading.Thread(target=self._run, daemon=True)
        self._recv_thread.start()
        logger.info(f"客户端启动，目标 {self.host}:{self.port}")

    def stop(self):
        """停止客户端"""
        self.running = False
        self._close_socket()

    # ================================================================
    # 连接管理
    # ================================================================

    def _run(self):
        """主循环：连接 → 接收消息 → 断线重连"""
        while self.running:
            try:
                self._connect()
                self._handle_messages()
            except Exception as e:
                logger.error(f"连接异常: {e}")
            finally:
                self._close_socket()

            if self.auto_reconnect and self.running:
                logger.info("等待 3 秒后重连...")
                time.sleep(3)

    def _connect(self):
        """建立TCP连接"""
        self._recv_buffer = b''
        self._user_info_received = False
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((self.host, self.port))
        self.sock = sock
        self._connected = True
        logger.info(f"已连接到 {self.host}:{self.port}")

    def _close_socket(self):
        """关闭连接"""
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    # ================================================================
    # 数据收发
    # ================================================================

    def _recv_exactly(self, n: int) -> Optional[bytes]:
        """缓冲区模式：从缓冲区/套接字读取恰好 n 字节"""
        while len(self._recv_buffer) < n:
            if not self.sock:
                return None
            try:
                chunk = self.sock.recv(8192)
                if not chunk:
                    return None
                self._recv_buffer += chunk
            except socket.timeout:
                if not self.running:
                    return None
                continue
            except (ConnectionError, OSError) as e:
                logger.debug(f"接收异常: {e}")
                return None

        result = self._recv_buffer[:n]
        self._recv_buffer = self._recv_buffer[n:]
        return result

    def _send_json(self, msg: dict) -> bool:
        """发送JSON消息到平台（协议：4字节大端长度 + 负载）"""
        if not self._connected or not self.sock:
            return False

        with self._send_lock:
            try:
                payload = json.dumps(msg, ensure_ascii=False).encode('utf-8')
                header = struct.pack('>I', len(payload))
                self.sock.sendall(header + payload)
                logger.info(f"发送: {msg}")
                return True
            except (ConnectionError, OSError) as e:
                logger.error(f"发送失败: {e}")
                self._connected = False
                return False

    # ================================================================
    # 消息处理主循环
    # ================================================================

    def _handle_messages(self):
        """持续接收并处理平台消息"""
        while self.running and self._connected:
            # 1. 读取4字节头部
            header = self._recv_exactly(4)
            if header is None:
                if self.running:
                    logger.warning("连接已关闭（头部读取失败）")
                break

            # 2. 读取负载（修复：必须在 if header is None 块外部！）
            payload_len = struct.unpack('>I', header)[0]
            if payload_len > 10 * 1024 * 1024:  # 安全限制10MB
                logger.error(f"异常负载长度: {payload_len}")
                break

            payload = self._recv_exactly(payload_len)
            if payload is None:
                if self.running:
                    logger.warning("连接已关闭（负载读取失败）")
                break

            # 3. 解析JSON
            try:
                raw_str = payload.decode('utf-8')
                logger.info(f"原始消息: {raw_str}")
                msg_data = json.loads(raw_str)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"JSON解析失败: {e}")
                continue

            # 4. 分发处理
            self._dispatch(msg_data)

    # ================================================================
    # 消息分发
    # ================================================================

    def _dispatch(self, msg_data: dict):
        """根据 msg 字段分发到对应处理函数"""
        msg_type = msg_data.get("msg", "")

        if msg_type == "ipc_user_info":
            self._on_user_info(msg_data)
        elif msg_type == "ipc_algorithm_test":
            self._on_algorithm_test(msg_data)
        elif msg_type == "ipc_set_visible":
            self._on_set_visible(msg_data)
        elif msg_type == "ipc_heartbeat":
            # 平台发来的心跳，不需要回复（官方Demo不回复）
            logger.debug("收到平台心跳")
        else:
            logger.info(f"未处理的消息类型: {msg_type} - {msg_data}")

    # ================================================================
    # 协议处理
    # ================================================================

    def _on_user_info(self, msg_data: dict):
        """
        处理 ipc_user_info 协议

        关键逻辑（与官方Demo一致）：
        - 始终回复 ipc_user_info，window=0 表示后端无GUI窗口
        - 提取 patient_id 用于后续数据关联
        """
        self.layout_type = msg_data.get("layout_type", 0)
        nick_name = msg_data.get("nick_name", "")
        user_id = msg_data.get("user_id", "")
        group_name = msg_data.get("group_name", "")

        # 用 user_id 作为 patient_id
        self.patient_id = str(user_id)
        self._user_info_received = True

        logger.info(f"收到平台用户信息: groupname={group_name}, "
                     f"layout={self.layout_type}, patient_id={self.patient_id}, "
                     f"nick_name={nick_name}")

        # 始终回复 ipc_user_info，window=0 表示无GUI窗口
        reply = {"msg": "ipc_user_info", "window": 0}
        self._send_json(reply)
        logger.info(f"已回复 ipc_user_info window=0（后端无GUI模式）")

    def _on_algorithm_test(self, msg_data: dict):
        """
        处理 ipc_algorithm_test 协议（平台算法在线输出）

        P300 算法结果处理：
        - 进阶篇: data 为 int 索引(1~N)，转换为 (row,col) 坐标
        - 基础篇: data 为 string 指令名称
        """
        algorithm_name = msg_data.get("algorithm_name", "")
        result_args = msg_data.get("result_args", {})

        logger.info(f"收到算法结果: algorithm={algorithm_name}, result_args={result_args}")

        # P300 特殊处理
        if algorithm_name in ("p300", "p300_ssvep", "p300_mi"):
            self._handle_p300_result(algorithm_name, result_args)

        # 转换为Unity指令并转发
        command = self._convert_to_unity_command(algorithm_name, result_args)
        if command:
            self._send_to_unity(command)

    def _on_set_visible(self, msg_data: dict):
        """处理 ipc_set_visible 协议"""
        visible = msg_data.get("visible", True)
        logger.info(f"收到窗口可见性设置: visible={visible}")

    # ================================================================
    # P300 闪烁事件处理
    # ================================================================

    def _handle_p300_result(self, algorithm_name: str, result_args: dict):
        """
        处理P300算法结果，输出坐标到终端

        进阶篇: data 为 int 索引(1~N)
        基础篇: data 为 string 指令名称
        """
        data = result_args.get("data")

        if isinstance(data, int):
            # 进阶篇：索引转坐标
            row, col = self._index_to_coord(data)
            print(f"1 ({row},{col})")
            logger.info(f"[P300] 目标刺激: 1 ({row},{col})")
        elif isinstance(data, str):
            # 基础篇：字符串指令
            print(f"1 {data}")
            logger.info(f"[P300] 目标刺激: 1 {data}")
        else:
            logger.warning(f"[P300] 未知数据格式: {data}")

    def _index_to_coord(self, index: int):
        """将1-based索引转换为(row, col)坐标"""
        if index < 1:
            return 1, 1
        row = (index - 1) // self.p300_grid_cols + 1
        col = (index - 1) % self.p300_grid_cols + 1
        return row, col

    def _coord_to_index(self, row: int, col: int) -> int:
        """将(row, col)坐标转换为1-based索引"""
        return (row - 1) * self.p300_grid_cols + col

    def send_p300_marker(self, is_target: bool, row: int = 0, col: int = 0):
        """
        向平台发送P300打标事件

        参数:
            is_target: True=目标刺激(红色闪烁), False=非目标刺激(绿色频闪)
            row: 行号(1-based)
            col: 列号(1-based)
        """
        event_id = 1 if is_target else 0

        if is_target:
            print(f"1 ({row},{col})")
            logger.info(f"[P300闪烁] 目标刺激(红色): 1 ({row},{col})")
        else:
            print("0")
            logger.info("[P300闪烁] 非目标刺激(绿色): 0")

        # 向平台发送打标事件
        self._send_json({
            "msg": "ipc_event",
            "event": event_id
        })

    # ================================================================
    # 实验记录上报（关键！平台"实验记录"依赖此协议）
    # ================================================================

    def send_experiment_data(self, experiment_type: str = "p300",
                             duration: int = 0, score: int = 0,
                             accuracy: float = 0.0,
                             extra_data: dict = None):
        """
        向平台上报实验记录数据

        平台通过 ipc_experiment_data 协议接收实验数据，
        收到后会在平台的"实验记录"页面显示。

        参数:
            experiment_type: 实验类型（如 "p300"）
            duration: 实验时长（秒）
            score: 得分
            accuracy: 准确率(0.0~1.0)
            extra_data: 额外数据字典
        """
        data = {
            "msg": "ipc_experiment_data",
            "experiment_type": experiment_type,
            "duration": duration,
            "score": score,
            "accuracy": accuracy,
            "patient_id": self.patient_id or "unknown"
        }
        if extra_data:
            data.update(extra_data)

        success = self._send_json(data)
        if success:
            logger.info(f"[实验记录] 已上报: type={experiment_type}, "
                         f"duration={duration}s, score={score}, accuracy={accuracy}")
        else:
            logger.warning("[实验记录] 上报失败：连接未建立")
        return success

    # ================================================================
    # 通用事件发送
    # ================================================================

    def send_event(self, event_id: int, extra_data: dict = None):
        """
        向平台发送事件

        参数:
            event_id: 事件ID（0=非目标, 1=目标, 100+=自定义）
            extra_data: 额外数据
        """
        data = {"msg": "ipc_event", "event": event_id}
        if extra_data:
            data.update(extra_data)
        self._send_json(data)

    # ================================================================
    # 算法结果 → Unity指令转换
    # ================================================================

    def _convert_to_unity_command(self, algorithm_name: str, result_args: dict) -> Optional[dict]:
        """将平台算法结果转换为Unity游戏指令"""
        if algorithm_name in ("p300", "p300_ssvep", "p300_mi"):
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

    # ================================================================
    # Unity 通信
    # ================================================================

    def _send_to_unity(self, command: dict):
        """向 Unity 客户端发送游戏控制指令"""
        from routes.unity import send_command_to_unity
        if self.patient_id:
            send_command_to_unity(self.patient_id, command)
        else:
            logger.warning("无患者ID，使用默认 ID 202505001")
            send_command_to_unity("202505001", command)
