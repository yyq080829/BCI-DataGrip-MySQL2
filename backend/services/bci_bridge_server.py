"""
bci_bridge_server.py —— 独立 BCI 桥接服务（最简方案，纯标准库 + SQLAlchemy）

通信架构（替代原 Flask + WebSocket 方案）：
    HybridBCI平台(TCP:8000)  <-->  本脚本(独立进程)  <-->  Unity3D Link.cs(TCP:9999)

为什么改成独立进程、不用 Flask/WebSocket？
  原方案里 HybridBCIBridge / routes/unity / services 互相依赖，eventlet 跑 WebSocket
  时在连平台频繁出现超时、协议错。本脚本只做一件事：把平台的 ipc_algorithm_test
  结果翻译成 Unity 指令，并可选地把结果/训练帧落库，职责单一、无循环依赖。

相比 datum/6.14 111.txt 原始版本做的“部分优化”：
  1. 配置化：IP/端口/MySQL 全部取自 config.py，不再写死
  2. 落库优化：平台每次算法结果写入 experiment_record；
                Unity 每帧训练数据写入 train_real_time_data（第二个游戏，大臂康复）
  3. 双向：既向 Unity 推命令（平台->Unity），也接收 Unity 上报（register / training_frame）
  4. 更稳的日志、断线重连、优雅退出

启动方式（单独一个终端，不要放进 app.py）：
    cd backend
    python services/bci_bridge_server.py

依赖：Python 标准库 + SQLAlchemy + PyMySQL（项目 requirements 已含）。
注意：本脚本是独立进程，和 python app.py 各跑各的；两个都要开着，游戏才能联调。
"""

import os
import sys
import socket
import struct
import json
import threading
import time
import logging
import signal

# 把 backend 目录加入 sys.path，便于直接 `python services/bci_bridge_server.py` 运行
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config import Config                              # noqa: E402
from sqlalchemy import create_engine                   # noqa: E402
from sqlalchemy.orm import sessionmaker                # noqa: E402
from models.training import ExperimentRecord, TrainingData  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('BCIBridge')


# ============================================================
# 配置（取自 config.py，可用命令行参数覆盖）
# ============================================================
PLATFORM_IP = Config.BCI_HOST
PLATFORM_PORT = Config.BCI_PORT
UNITY_HOST = getattr(Config, 'UNITY_HOST', '127.0.0.1')
UNITY_PORT = getattr(Config, 'UNITY_PORT', 9999)
DEFAULT_PATIENT_ID = getattr(Config, 'BRIDGE_DEFAULT_PATIENT_ID', '202505001')
LOG_EVERY_RESULT = getattr(Config, 'BRIDGE_LOG_EVERY_RESULT', True)

# SQLAlchemy 引擎（独立进程，用 config 里的连接串，与 app.py 同一库）
_engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True, pool_recycle=3600)
_Session = sessionmaker(bind=_engine)


# ============================================================
# 数据库写入（落库优化）
# ============================================================
def save_experiment_record(patient_id, experiment_type, extra_data,
                            duration=0, score=0, accuracy=0.0):
    """把平台一次算法结果写入 experiment_record 表。失败仅记日志，不影响转发。"""
    try:
        with _Session() as s:
            rec = ExperimentRecord(
                patient_id=patient_id or DEFAULT_PATIENT_ID,
                experiment_type=experiment_type,
                duration=duration,
                score=score,
                accuracy=accuracy,
                extra_data=json.dumps(extra_data, ensure_ascii=False),
            )
            s.add(rec)
            s.commit()
            logger.info('[DB] 实验记录已落库 patient=%s type=%s', patient_id, experiment_type)
    except Exception as e:
        logger.exception('[DB] experiment_record 落库失败: %s', e)


def save_training_frame(data):
    """把 Unity 上报的一帧训练数据写入 train_real_time_data 表（第二个游戏）。"""
    try:
        with _Session() as s:
            row = TrainingData(
                patient_id=data.get('patient_id') or DEFAULT_PATIENT_ID,
                level_id=data.get('level_id'),
                shoulder_abduction=data.get('shoulder_abduction'),
                elbow_extension=data.get('elbow_extension'),
                forearm_rotation=data.get('forearm_rotation'),
                action_score=data.get('action_score', 0),
                is_qualified=bool(data.get('is_qualified', False)),
                compensation=data.get('compensation'),
                compensation_score=data.get('compensation_score', 100),
                game_score=data.get('game_score', 0),
                device_type=data.get('device_type', 'AR手机'),
            )
            s.add(row)
            s.commit()
            logger.info('[DB] 训练帧已落库 patient=%s level=%s',
                        row.patient_id, row.level_id)
    except Exception as e:
        logger.exception('[DB] train_real_time_data 落库失败: %s', e)


# ============================================================
# 平台通信 - 连接 HybridBCI 平台，接收算法输出（TCP，长度头+JSON）
# ============================================================
class PlatformClient:
    """连接 HybridBCI 平台，按 [4字节大端长度][UTF-8 JSON] 协议收发。"""

    HEADER = 4

    def __init__(self, on_data_callback, on_userinfo_callback=None):
        self.on_data_callback = on_data_callback
        self.on_userinfo_callback = on_userinfo_callback
        self.sock = None
        self.running = False
        self._buffer = b''
        self._lock = threading.Lock()

    def connect(self, ip, port):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.connect((ip, port))
            self.sock.settimeout(None)
            self.running = True
            logger.info('[平台] 已连接 %s:%s', ip, port)
            return True
        except Exception as e:
            logger.error('[平台] 连接失败: %s', e)
            self.sock = None
            return False

    def disconnect(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send(self, data_dict):
        """发送一帧（4字节长度头 + JSON）。"""
        if not self.sock:
            return
        try:
            payload = json.dumps(data_dict, ensure_ascii=False).encode('utf-8')
            frame = struct.pack('>I', len(payload)) + payload
            with self._lock:
                self.sock.sendall(frame)
        except Exception as e:
            logger.error('[平台] 发送失败: %s', e)

    def receive_loop(self):
        while self.running and self.sock:
            try:
                data = self.sock.recv(4096)
                if not data:
                    logger.warning('[平台] 连接已断开')
                    break
                self._buffer += data
                while len(self._buffer) >= self.HEADER:
                    payload_len = struct.unpack('>I', self._buffer[:self.HEADER])[0]
                    total = self.HEADER + payload_len
                    if len(self._buffer) < total:
                        break
                    payload = self._buffer[self.HEADER:total]
                    self._buffer = self._buffer[total:]
                    try:
                        msg = json.loads(payload.decode('utf-8'))
                    except json.JSONDecodeError as e:
                        logger.error('[平台] JSON解析失败: %s', e)
                        continue
                    self._dispatch(msg)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error('[平台] 接收异常: %s', e)
                break
        self.running = False
        logger.info('[平台] 接收线程结束')

    def _dispatch(self, msg):
        msg_type = msg.get('msg', '')
        if msg_type == 'ipc_user_info':
            logger.info('[平台] 用户信息: %s', msg)
            if self.on_userinfo_callback:
                self.on_userinfo_callback(msg)
            # 始终回复 window=0，告诉平台本进程没有需要嵌入的 GUI 窗口
            self.send({'msg': 'ipc_user_info', 'window': 0})
        elif msg_type == 'ipc_algorithm_test':
            self.on_data_callback(msg)
        else:
            # ipc_heartbeat / ipc_set_visible / ipc_device_* 等：打印但不处理
            logger.debug('[平台] 收到 %s', msg_type)


# ============================================================
# Unity 通信 - TCP 服务器，向 Unity3D 转发指令 + 接收 Unity 上报
# ============================================================
class UnityServer:
    """监听 TCP:9999，向 Unity 的 Link.cs 转发命令；并接收 Unity 上报的数据。"""

    def __init__(self, on_unity_message=None):
        self.on_unity_message = on_unity_message
        self.server_sock = None
        self.client_sock = None
        self.client_addr = None
        self._lock = threading.Lock()
        self.running = False
        self._recv_buffer = b''

    def start(self, host, port):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen(1)
        self.server_sock.settimeout(1.0)
        self.running = True
        logger.info('[Unity] TCP 服务器启动: %s:%s', host, port)
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
        with self._lock:
            if self.client_sock:
                try:
                    self.client_sock.close()
                except Exception:
                    pass
                self.client_sock = None
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

    def send_to_unity(self, message):
        """向 Unity 发一条 JSON + 换行符（Link.cs 按行读取）。"""
        with self._lock:
            if self.client_sock:
                try:
                    self.client_sock.sendall((message + '\n').encode('utf-8'))
                    return True
                except Exception as e:
                    logger.error('[Unity] 发送失败: %s', e)
                    return False
            return False

    def _accept_loop(self):
        while self.running:
            try:
                client, addr = self.server_sock.accept()
                client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                with self._lock:
                    if self.client_sock:
                        try:
                            self.client_sock.close()
                        except Exception:
                            pass
                    self.client_sock = client
                    self.client_addr = addr
                logger.info('[Unity] Unity3D 已连接: %s:%s', addr[0], addr[1])
                # 为每个连接起一个接收线程，读 Unity 上报的数据
                t = threading.Thread(target=self._recv_loop, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error('[Unity] 监听异常: %s', e)
                break

    def _recv_loop(self, client):
        """读取 Unity 发来的 JSON 行（每条以 \\n 结尾）。"""
        buffer = b''
        while self.running:
            try:
                chunk = client.recv(4096)
            except Exception:
                break
            if not chunk:
                break
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode('utf-8'))
                except json.JSONDecodeError as e:
                    logger.error('[Unity] 上报 JSON 解析失败: %s', e)
                    continue
                if self.on_unity_message:
                    self.on_unity_message(msg)
        logger.info('[Unity] 连接 %s 已关闭', self.client_addr)


# ============================================================
# 协议转换 - 平台 ipc_algorithm_test -> Unity GameCommand
# ============================================================
def convert_platform_to_unity(msg_dict):
    """把平台算法结果翻译成 Unity 指令 JSON 字符串（或 None 表示不转发）。"""
    msg = msg_dict.get('msg', '')
    if msg != 'ipc_algorithm_test':
        return None

    algorithm_name = msg_dict.get('algorithm_name', '')
    result_args = msg_dict.get('result_args', {})
    result_data = result_args.get('data', '')

    if algorithm_name in ('p300', 'ssvep', 'p300_ssvep', 'p300_mi', 'mi'):
        # 基础篇 data=方格文字(如"DJ开")，进阶篇 data=索引(int)
        return json.dumps({'cmd': 'SELECT', 'param': str(result_data), 'intensity': 0})

    if algorithm_name == 'attention':
        try:
            val = int(result_data)
        except (ValueError, TypeError):
            val = 0
        return json.dumps({'cmd': 'FORWARD' if val > 50 else 'BACKWARD',
                           'param': '', 'intensity': val})

    if algorithm_name == 'blink':
        if str(result_data) == '1':
            return json.dumps({'cmd': 'JUMP', 'param': '', 'intensity': 0})
        return None

    if algorithm_name == 'gyroscope':
        if isinstance(result_data, dict):
            gyro_x = result_data.get('gyroscope_x', 0)
            if abs(gyro_x) > 0.1:
                return json.dumps({'cmd': 'RIGHT' if gyro_x > 0 else 'LEFT',
                                   'param': '', 'intensity': int(abs(gyro_x) * 100)})
        return None

    # 未知算法，原样转发
    return json.dumps({'cmd': 'ACTION', 'param': str(result_data), 'intensity': 0})


# ============================================================
# 桥接主逻辑
# ============================================================
class BCIBridge:
    """把平台结果转发给 Unity，并把结果/训练帧落库。"""

    def __init__(self):
        self.current_patient_id = None

        self.unity_server = UnityServer(on_unity_message=self._on_unity_message)
        self.platform_client = PlatformClient(
            on_data_callback=self._on_platform_data,
            on_userinfo_callback=self._on_platform_userinfo,
        )

    # ---- 平台侧 ----
    def _on_platform_userinfo(self, msg):
        # 平台下发的用户信息（可能带 patient_id / user_name），优先于 Unity register 使用
        pid = msg.get('user_id') or msg.get('user_name')
        if pid:
            self.current_patient_id = str(pid)
            logger.info('[平台] 设定患者ID=%s', self.current_patient_id)

    def _on_platform_data(self, msg_dict):
        unity_msg = convert_platform_to_unity(msg_dict)
        if unity_msg:
            ok = self.unity_server.send_to_unity(unity_msg)
            if ok:
                logger.info('  --> 转发到 Unity: %s', unity_msg)
            else:
                logger.info('  [等待Unity连接] 数据: %s', unity_msg)

        # 落库优化：每次算法结果都记一条 experiment_record
        if LOG_EVERY_RESULT:
            algorithm = msg_dict.get('algorithm_name', '')
            save_experiment_record(
                patient_id=self.current_patient_id,
                experiment_type=algorithm,
                extra_data=msg_dict,
            )

    # ---- Unity 侧 ----
    def _on_unity_message(self, msg):
        mtype = msg.get('type') or msg.get('msg')
        if mtype == 'register':
            self.current_patient_id = str(msg.get('patient_id') or self.current_patient_id)
            logger.info('[Unity] 注册患者: %s', self.current_patient_id)
        elif mtype == 'training_frame':
            save_training_frame(msg)
        elif mtype == 'training_result':
            # 第二个游戏结束汇总（可选落库为一条实验反馈记录）
            save_experiment_record(
                patient_id=msg.get('patient_id') or self.current_patient_id,
                experiment_type='unity_direct',
                extra_data=msg,
                duration=msg.get('duration', 0),
                score=msg.get('score', 0),
            )
        else:
            logger.debug('[Unity] 未处理消息类型: %s', mtype)

    # ---- 生命周期 ----
    def start(self, platform_ip, platform_port, unity_host, unity_port):
        self.unity_server.start(unity_host, unity_port)
        if self.platform_client.connect(platform_ip, platform_port):
            t = threading.Thread(target=self.platform_client.receive_loop, daemon=True)
            t.start()
        else:
            logger.warning('[提示] 平台未连接，将自动重试（见主循环）')

    def ensure_platform(self, platform_ip, platform_port):
        """主循环里保证平台连接；断线则重连。"""
        if not self.platform_client.running:
            logger.info('[BCIBridge] 尝试连接平台...')
            if self.platform_client.connect(platform_ip, platform_port):
                self.platform_client.send({'msg': 'ipc_user_info', 'window': 0})
                t = threading.Thread(target=self.platform_client.receive_loop, daemon=True)
                t.start()
            else:
                time.sleep(5)


def main():
    print('=' * 50)
    print('  BCI Bridge Server - 独立桥接（平台 <-> Unity <-> MySQL）')
    print('=' * 50)
    print(f'  平台 : {PLATFORM_IP}:{PLATFORM_PORT}')
    print(f'  Unity: {UNITY_HOST}:{UNITY_PORT}')
    print(f'  落库 : experiment_record / train_real_time_data')
    print('  请在 Unity 中确保 Link 脚本已挂到 GameManager 上')
    print('=' * 50)

    bridge = BCIBridge()
    bridge.start(PLATFORM_IP, PLATFORM_PORT, UNITY_HOST, UNITY_PORT)

    stop = threading.Event()

    def _signal_handler(signum, frame):
        logger.info('收到退出信号，正在关闭...')
        stop.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        while not stop.is_set():
            bridge.ensure_platform(PLATFORM_IP, PLATFORM_PORT)
            time.sleep(1)
    finally:
        bridge.platform_client.disconnect()
        bridge.unity_server.stop()
        _engine.dispose()
        logger.info('[BCIBridge] 已退出')


if __name__ == '__main__':
    main()
