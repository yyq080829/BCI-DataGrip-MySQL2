"""
华南脑控 HybridBCI 平台连接模块（纯 Python，无 Qt 依赖）

参考官方 ipc_socket 协议：
    帧格式: [4 字节大端长度][UTF-8 JSON 负载]
    平台(服务端) <-> 控制器(本后端) 双向通信

按官方「3 个 class」思路拆分（对应官方 HNNKTcpSocketClient + MainWindow）：
    1. IpcCodec             —— 帧编解码（对应官方 QDataStream 打包/解包）
    2. HybridBCIConnection  —— TCP 传输层（对应官方 HNNKTcpSocketClient）
    3. HybridBCIBridge      —— 业务桥接层（对应官方 MainWindow 的协议处理）
       · 平台 -> Unity：把算法结果翻译为游戏指令，经 WebSocket 推送给在线 Unity
       · Unity  -> 平台：把 p300 打标 / 实验记录上报给平台
       · 反馈落库：训练与实验反馈参数写入数据库
"""

import json
import struct
import socket
import threading
import logging
import time

logger = logging.getLogger(__name__)


class IpcCodec:
    """IPC 帧编解码：帧 = 4 字节大端长度 + JSON 负载。

    对应官方 HNNKTcpSocketClient 中用 QDataStream 写 uint32 长度再写负载的逻辑，
    这里用纯 Python 的 struct 实现，且支持「多个包合并在一起」的情况。
    """

    _HEADER = 4
    _MAX_PAYLOAD = 10 * 1024 * 1024  # 安全上限 10MB

    @staticmethod
    def encode(msg: dict) -> bytes:
        """把 dict 编码为一帧字节。"""
        payload = json.dumps(msg, ensure_ascii=False).encode('utf-8')
        return struct.pack('>I', len(payload)) + payload

    @staticmethod
    def decode(buffer: bytes):
        """尝试从 buffer 中解析出一个完整帧。

        返回 (msg_dict, remaining_bytes)；数据不足一帧时返回 (None, buffer)。
        """
        if len(buffer) < IpcCodec._HEADER:
            return None, buffer
        (length,) = struct.unpack('>I', buffer[:IpcCodec._HEADER])
        if length > IpcCodec._MAX_PAYLOAD:
            raise ValueError(f'IPC 负载过大: {length}')
        if len(buffer) < IpcCodec._HEADER + length:
            return None, buffer
        raw = buffer[IpcCodec._HEADER:IpcCodec._HEADER + length]
        msg = json.loads(raw.decode('utf-8'))
        return msg, buffer[IpcCodec._HEADER + length:]


class HybridBCIConnection:
    """TCP 传输层：连接平台、收发包、断线重连。

    对应官方 HNNKTcpSocketClient：只负责「连上 / 收发字节 / 断线重连」，
    收到完整帧后通过 on_message 回调上抛，连接与断开通过回调通知业务层。
    """

    def __init__(self, host='127.0.0.1', port=8000, auto_reconnect=True,
                 on_message=None, on_connect=None, on_disconnect=None):
        self.host = host
        self.port = port
        self.auto_reconnect = auto_reconnect
        self._on_message = on_message
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect

        self._sock = None
        self._running = False
        self._connected = False
        self._buffer = b''
        self._lock = threading.Lock()
        self._thread = None

    @property
    def connected(self):
        return self._connected

    def start(self):
        """启动连接线程（守护线程，随主进程退出）。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info('[HybridBCI] 连接线程已启动 -> %s:%s', self.host, self.port)

    def stop(self):
        self._running = False
        self._close()

    # ------------------------------------------------------------------
    # 内部主循环
    # ------------------------------------------------------------------
    def _run(self):
        while self._running:
            try:
                self._connect()
                if self._on_connect:
                    self._on_connect()
                self._recv_loop()
            except Exception as e:  # 连接异常，进入重连
                logger.error('[HybridBCI] 连接异常: %s', e)
            finally:
                self._close()
                if self._on_disconnect:
                    self._on_disconnect()
            if self.auto_reconnect and self._running:
                logger.info('[HybridBCI] 3 秒后重连...')
                time.sleep(3)

    def _connect(self):
        self._buffer = b''
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((self.host, self.port))
        self._sock = sock
        self._connected = True
        logger.info('[HybridBCI] 已连接到 %s:%s', self.host, self.port)

    def _close(self):
        self._connected = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _recv_loop(self):
        while self._running and self._connected:
            try:
                chunk = self._sock.recv(8192)
            except socket.timeout:
                continue
            except OSError:
                break
            if not chunk:
                break  # 对端关闭
            self._buffer += chunk
            self._drain()

    def _drain(self):
        """从缓冲区中尽可能多地解包完整帧并上抛。"""
        while True:
            msg, self._buffer = IpcCodec.decode(self._buffer)
            if msg is None:
                break
            if self._on_message:
                try:
                    self._on_message(msg)
                except Exception as e:
                    logger.exception('[HybridBCI] 消息处理出错: %s', e)

    def send(self, msg: dict) -> bool:
        """发送一帧 JSON 消息，成功返回 True。"""
        if not self._connected or not self._sock:
            return False
        with self._lock:
            try:
                self._sock.sendall(IpcCodec.encode(msg))
                return True
            except OSError as e:
                logger.error('[HybridBCI] 发送失败: %s', e)
                self._connected = False
                return False


class HybridBCIBridge:
    """业务桥接层：连接 平台 <-> Unity <-> 数据库。

    对应官方 MainWindow 的协议处理（on_server_data）：
    · 平台 -> Unity：把算法在线结果翻译为游戏指令推送给在线 Unity 客户端
    · Unity  -> 平台：把 p300 打标 / 实验记录上报给平台
    · 反馈落库：训练与实验反馈参数写入数据库
    """

    def __init__(self, socketio, app=None, host='127.0.0.1', port=8000,
                 p300_grid_rows=3, p300_grid_cols=4):
        self.socketio = socketio
        self.app = app  # Flask app，用于离线线程里获取 db 上下文
        self.p300_grid_rows = p300_grid_rows
        self.p300_grid_cols = p300_grid_cols
        self.patient_id = None   # 平台下发的 user_id
        self.layout_type = 0

        self._conn = HybridBCIConnection(
            host=host, port=port,
            on_message=self._handle_message,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self):
        self._conn.start()

    def stop(self):
        self._conn.stop()

    def _on_connect(self):
        logger.info('[HybridBCI] 平台链路已建立')

    def _on_disconnect(self):
        logger.info('[HybridBCI] 平台链路已断开')

    # ------------------------------------------------------------------
    # 平台 -> 后端 消息分发
    # ------------------------------------------------------------------
    def _handle_message(self, msg: dict):
        msg_type = msg.get('msg', '')
        handler = {
            'ipc_user_info': self._on_user_info,
            'ipc_algorithm_test': self._on_algorithm_test,
            'ipc_set_visible': self._on_set_visible,
            'ipc_heartbeat': lambda m: None,   # 平台心跳，不需回复
            'ipc_device_info': self._on_device_info,
            'ipc_device_data': self._on_device_data,
            'ipc_device_gyroscope': self._on_gyroscope,
        }.get(msg_type)
        if handler:
            handler(msg)
        else:
            logger.info('[HybridBCI] 未处理消息类型: %s', msg_type)

    def _on_user_info(self, msg):
        """平台下发用户信息：记录 patient_id，回复 window=0（后端无 GUI 窗口）。"""
        self.patient_id = str(msg.get('user_id') or msg.get('user_name') or '')
        self.layout_type = msg.get('layout_type', 0)
        logger.info('[HybridBCI] 用户: id=%s layout=%s', self.patient_id, self.layout_type)
        # 始终回复 window=0，告诉平台本进程没有需要嵌入的 GUI 窗口
        self._conn.send({'msg': 'ipc_user_info', 'window': 0})

    def _on_algorithm_test(self, msg):
        """平台算法在线输出 -> 翻译为 Unity 游戏指令 -> 推送给 Unity。"""
        algorithm = msg.get('algorithm_name', '')
        result = msg.get('result_args', {})
        logger.info('[HybridBCI] 算法结果: %s %s', algorithm, result)
        command = self._to_unity_command(algorithm, result)
        if command:
            self._send_to_unity(command)

    def _on_set_visible(self, msg):
        logger.info('[HybridBCI] 窗口可见性: %s', msg.get('visible'))

    def _on_device_info(self, msg):
        logger.info('[HybridBCI] 设备信息: device_id=%s', msg.get('device_id'))

    def _on_device_data(self, msg):
        """高阶篇：平台实时脑电数据流。如需落库可在此转发到 bci_data 表。"""
        pass

    def _on_gyroscope(self, msg):
        logger.debug('[HybridBCI] 陀螺仪: %s', msg)

    # ------------------------------------------------------------------
    # 平台 -> Unity 指令翻译
    # ------------------------------------------------------------------
    def _to_unity_command(self, algorithm, result):
        if algorithm in ('p300', 'p300_ssvep', 'p300_mi'):
            data = result.get('data')
            if data is not None:
                return {'cmd': 'SELECT', 'param': str(data)}
        if algorithm == 'ssvep':
            freq = result.get('frequency') or result.get('data')
            if freq is not None:
                return {'cmd': 'FOCUS', 'param': str(freq)}
        if algorithm in ('mi', 'motor_imagery'):
            direction = result.get('direction') or result.get('data')
            if direction is not None:
                return {'cmd': 'MOVE', 'param': str(direction)}
        if algorithm == 'relax':
            return {'cmd': 'RELAX', 'param': '0'}
        data = result.get('data')
        if data is not None:
            return {'cmd': algorithm.upper(), 'param': str(data)}
        logger.warning('[HybridBCI] 无法翻译算法结果: %s -> %s', algorithm, result)
        return None

    def _send_to_unity(self, command):
        from routes.unity import send_command_to_unity
        target = self.patient_id or '202505001'
        send_command_to_unity(target, command)

    # ------------------------------------------------------------------
    # Unity -> 平台 上报接口（供 routes/unity.py 调用）
    # ------------------------------------------------------------------
    def send_p300_marker(self, is_target, row=0, col=0):
        """向平台发送 p300 打标事件（0=非目标, 1=目标）。"""
        event = 1 if is_target else 0
        logger.info('[HybridBCI] p300 打标: %s', event)
        return self._conn.send({'msg': 'ipc_event', 'event': event})

    def send_event(self, event_id, extra_data=None):
        data = {'msg': 'ipc_event', 'event': event_id}
        if extra_data:
            data.update(extra_data)
        return self._conn.send(data)

    def send_experiment_data(self, experiment_type='p300', duration=0,
                             score=0, accuracy=0.0, extra_data=None):
        """向平台上报实验记录（平台「实验记录」页面依赖此协议），并落库。"""
        data = {
            'msg': 'ipc_experiment_data',
            'experiment_type': experiment_type,
            'duration': duration,
            'score': score,
            'accuracy': accuracy,
            'patient_id': self.patient_id or 'unknown',
        }
        if extra_data:
            data.update(extra_data)
        ok = self._conn.send(data)
        if ok:
            self._save_experiment(data)
        return ok

    # ------------------------------------------------------------------
    # 反馈参数落库
    # ------------------------------------------------------------------
    def _save_experiment(self, data):
        """将平台实验反馈记录写入 experiment_record 表。"""
        if self.app is None:
            return
        try:
            with self.app.app_context():
                from extensions import db
                from models.training import ExperimentRecord
                rec = ExperimentRecord(
                    patient_id=data.get('patient_id'),
                    experiment_type=data.get('experiment_type'),
                    duration=data.get('duration'),
                    score=data.get('score'),
                    accuracy=data.get('accuracy'),
                    extra_data=json.dumps(data.get('extra_data') or {}, ensure_ascii=False),
                )
                db.session.add(rec)
                db.session.commit()
                logger.info('[HybridBCI] 实验反馈已落库')
        except Exception as e:
            logger.exception('[HybridBCI] 实验反馈落库失败: %s', e)
