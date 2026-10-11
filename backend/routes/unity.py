"""
Unity 对接接口（蓝图 unity_bp，主要用 WebSocket 命名空间 /unity）

这是后端与 Unity 游戏通信的核心模块，承担两个游戏的数据接入：

  【第一个游戏 · 脑机拼写游戏】经华南脑控 HybridBCI 平台
    · Unity 通过 p300_start / p300_flash / p300_stop 把刺激事件上报后端
    · 后端转发给平台（HybridBCIBridge.send_p300_marker / send_experiment_data）
    · 平台算法结果再由桥接层翻译为游戏指令推回 Unity（见 services/hybridbci_client.py）

  【第二个游戏 · 大臂康复】Unity 直连数据库，不经过脑电平台
    · Unity 每帧 training_frame 上报肩外展等角度 -> 直接写 train_real_time_data
    · 实时广播到 /monitor 命名空间，供后台监控页实时显示

此外 training_result 是两个游戏共用的“结束汇总”事件，用 game_type 区分：
  game_type=1 平台游戏：MySQL 存一份 + 平台再存一份（导出）
  game_type=2 直连游戏：只存 MySQL
"""

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit
from extensions import socketio, db
import logging
import time

logger = logging.getLogger(__name__)

unity_bp = Blueprint('unity', __name__)

# 在线患者映射：patient_id -> WebSocket 会话ID(sid)，用于精准推送游戏指令
patient_sid_map = {}

# P300 范式运行状态（一次训练过程中的累计计数）
p300_running = False
p300_flash_count = 0          # 总闪烁次数
p300_start_time = 0           # 开始时间戳（用于算时长）
p300_target_count = 0         # 目标刺激次数（红色闪烁）
p300_nontarget_count = 0      # 非目标刺激次数（绿色频闪）


# ------------------------------------------------------------------
# HTTP 接口（降级备用，正常走下面的 WebSocket）
# ------------------------------------------------------------------
@unity_bp.route('/send-eeg', methods=['POST'])
def receive_eeg_from_unity():
    """备用：接收 Unity 传来的脑电数据（当前未做落库，仅回显）。"""
    try:
        data = request.get_json()
        return jsonify({'code': 200, 'message': '数据已接收', 'data': data}), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'接收失败: {str(e)}'}), 500


@unity_bp.route('/game-command', methods=['GET'])
def get_game_command():
    """备用：Unity 轮询获取游戏控制指令（主方案是 WebSocket 主动推送）。"""
    return jsonify({'code': 200, 'data': {'cmd': 'idle', 'param': ''}}), 200


# ------------------------------------------------------------------
# WebSocket 事件处理（命名空间 /unity）
# ------------------------------------------------------------------
@socketio.on('connect', namespace='/unity')
def on_unity_connect():
    """Unity 客户端连上 WebSocket。"""
    logger.info('[Unity] 客户端已连接')


@socketio.on('disconnect', namespace='/unity')
def on_unity_disconnect():
    """Unity 断开：从在线映射里清掉它的 sid。"""
    logger.info('[Unity] 客户端已断开')
    for pid, sid in list(patient_sid_map.items()):
        if sid == request.sid:
            del patient_sid_map[pid]
            break


@socketio.on('register_patient', namespace='/unity')
def on_register_patient(data):
    """Unity 上线时先报 patient_id，后端记下 sid 以便后续精准推送指令。"""
    patient_id = data.get('patient_id')
    if patient_id:
        patient_sid_map[patient_id] = request.sid
        logger.info(f'[Unity] 患者注册: {patient_id}')
        emit('register_ack', {'status': 'ok', 'patient_id': patient_id})
    else:
        emit('register_ack', {'status': 'error', 'message': '缺少patient_id'})


# ------------------------------------------------------------------
# P300 拼写游戏（第一个游戏，经平台）
# ------------------------------------------------------------------
@socketio.on('p300_flash', namespace='/unity')
def on_p300_flash(data):
    """Unity 上报一次闪烁刺激。

    字段：is_target(true=红色闪烁/目标, false=绿色频闪/非目标), row, col。
    后端把目标/非目标翻译成平台事件编号（1/0）转发给 HybridBCI 平台。
    """
    global p300_flash_count, p300_target_count, p300_nontarget_count

    is_target = data.get('is_target', False)
    row = data.get('row', 0)
    col = data.get('col', 0)

    p300_flash_count += 1

    # 转发打标事件给平台（0=非目标, 1=目标）
    bci_client = current_app.config.get('BCI_CLIENT')
    if bci_client and hasattr(bci_client, 'send_p300_marker'):
        bci_client.send_p300_marker(is_target=is_target, row=row, col=col)

    if is_target:
        p300_target_count += 1
    else:
        p300_nontarget_count += 1

    emit('p300_flash_ack', {'status': 'ok', 'flash_count': p300_flash_count})


@socketio.on('p300_start', namespace='/unity')
def on_p300_start(data):
    """Unity 通知 P300 范式开始：重置计数、记录开始时间、注册患者。"""
    global p300_running, p300_flash_count, p300_start_time
    global p300_target_count, p300_nontarget_count

    patient_id = data.get('patient_id')
    grid_rows = data.get('grid_rows', 3)
    grid_cols = data.get('grid_cols', 4)

    p300_running = True
    p300_flash_count = 0
    p300_target_count = 0
    p300_nontarget_count = 0
    p300_start_time = time.time()

    if patient_id:
        patient_sid_map[patient_id] = request.sid

    print("=" * 50)
    print("  P300 范式开始")
    print(f"  患者: {patient_id}")
    print(f"  网格: {grid_rows}行 x {grid_cols}列")
    print("  输出格式: 绿色频闪→0, 红色闪烁→1 (row,col)")
    print("=" * 50)

    logger.info(f'[P300] 范式开始: patient={patient_id}, grid={grid_rows}x{grid_cols}')
    emit('p300_start_ack', {'status': 'ok'})


@socketio.on('p300_stop', namespace='/unity')
def on_p300_stop(data):
    """Unity 通知 P300 范式结束：把实验结果上报平台（平台侧存一份）。"""
    global p300_running

    patient_id = data.get('patient_id')
    score = data.get('score', 0)
    accuracy = data.get('accuracy', 0.0)
    duration = int(time.time() - p300_start_time) if p300_start_time else 0

    p300_running = False

    print("=" * 50)
    print("  P300 范式结束")
    print(f"  患者: {patient_id}")
    print(f"  总闪烁次数: {p300_flash_count}")
    print(f"  目标刺激: {p300_target_count}次")
    print(f"  非目标刺激: {p300_nontarget_count}次")
    print(f"  得分: {score}")
    print(f"  准确率: {accuracy}")
    print(f"  时长: {duration}秒")
    print("=" * 50)

    # ★ 关键：向平台上报实验记录（平台侧落库；后端这边由桥接层再导出一份到 experiment_record）★
    bci_client = current_app.config.get('BCI_CLIENT')
    if bci_client and hasattr(bci_client, 'send_experiment_data'):
        bci_client.send_experiment_data(
            experiment_type="p300",
            duration=duration,
            score=score,
            accuracy=accuracy,
            extra_data={
                'patient_id': patient_id,
                'flash_count': p300_flash_count,
                'target_count': p300_target_count,
                'nontarget_count': p300_nontarget_count
            }
        )
        logger.info('[P300] 已向平台上报实验记录')
    else:
        logger.warning('[P300] BCI客户端未启动，无法上报实验记录')

    emit('p300_stop_ack', {'status': 'ok', 'duration': duration})


# ------------------------------------------------------------------
# 训练结果（两个游戏共用）
# ------------------------------------------------------------------
@socketio.on('training_result', namespace='/unity')
def on_training_result(data):
    """Unity 上传训练结果（结束汇总），用 game_type 区分两个游戏。

    game_type=1 第一个游戏(平台)：MySQL(train_real_time_data) 存一份 + 平台再存一份
    game_type=2 第二个游戏(直连)：只存 MySQL，不碰平台
    """
    patient_id = data.get('patient_id')
    level_id = data.get('level_id')
    score = data.get('score', 0)
    duration = data.get('duration', 0)
    game_type = data.get('game_type', 1)   # 默认按第一个游戏(平台)处理

    logger.info(f'[Unity] 收到训练结果: patient={patient_id}, game_type={game_type}, data={data}')

    # —— ① 两个游戏都把“汇总结果”写进 MySQL，保证数据落库 ——
    from models.training import TrainingData
    with current_app.app_context():
        try:
            summary = TrainingData(
                patient_id=patient_id,
                level_id=level_id,
                game_score=score,
                device_type='平台脑机游戏' if game_type == 1 else 'Unity直连游戏',
            )
            db.session.add(summary)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f'[Unity] 训练结果写库失败: {e}')

    # —— ② 仅第一个游戏：把结果上报/导出到 HybridBCI 平台 ——
    if game_type == 1:
        bci_client = current_app.config.get('BCI_CLIENT')
        if bci_client and hasattr(bci_client, 'send_event'):
            bci_client.send_event(100, extra_data={
                'patient_id': patient_id,
                'score': score,
                'duration': duration,
            })
            logger.info('[Unity] 已把第一个游戏结果上报 HybridBCI 平台（平台侧已存储，MySQL 副本已保存）')
        else:
            logger.warning('[Unity] BCI客户端未启动，无法上报平台；但 MySQL 副本已保存')
    else:
        logger.info('[Unity] 第二个游戏（直连），数据已直接存入 MySQL，不经过平台')

    emit('training_result_ack', {'status': 'ok', 'message': '数据已接收'})


# ------------------------------------------------------------------
# 实时训练帧（第二个游戏：Unity 直连数据库，实时角度/难度/反馈）
# ------------------------------------------------------------------
@socketio.on('training_frame', namespace='/unity')
def on_training_frame(data):
    """Unity 实时上报单帧训练数据 -> 直接写 train_real_time_data -> 广播到 /monitor。

    这是【大臂康复】的直连路径，完全不经过脑电平台。
    """
    from flask import current_app
    from extensions import db, socketio
    from models.training import TrainingData, GameLevel

    patient_id = data.get('patient_id')
    level_id = data.get('level_id')
    if not patient_id or level_id is None:
        emit('training_frame_ack', {'status': 'error', 'message': '缺少patient_id或level_id'})
        return

    with current_app.app_context():
        try:
            # 落库：一帧 = 一行 train_real_time_data
            row = TrainingData(
                patient_id=patient_id,
                level_id=level_id,
                shoulder_abduction=data.get('shoulder_abduction'),
                elbow_extension=data.get('elbow_extension'),
                forearm_rotation=data.get('forearm_rotation'),
                action_score=data.get('action_score', 0),
                is_qualified=data.get('is_qualified', False),
                compensation=data.get('compensation'),
                compensation_score=data.get('compensation_score', 100),
                game_score=data.get('game_score', 0),
                device_type=data.get('device_type', 'AR手机'),
            )
            db.session.add(row)
            db.session.commit()

            # 查该关卡目标角度，便于后台对比显示“患者角度 vs 目标角度”
            level = GameLevel.query.get(level_id)
            target_angle = float(level.target_angle) if level and level.target_angle is not None else None

            # 回 ack 给 Unity（同一 /unity 会话）
            emit('training_frame_ack', {'status': 'ok', 'data_id': row.data_id})

            # ★ 大臂康复数据：直接 Unity -> 数据库，不经过脑电平台 ★
            # 实时广播给后台监控页（/monitor 命名空间），用于实时显示大臂抬起角度
            socketio.emit('arm_angle_update', {
                'patient_id': patient_id,
                'level_id': level_id,
                'level_name': level.level_name if level else None,
                'shoulder_abduction': float(row.shoulder_abduction) if row.shoulder_abduction is not None else None,
                'target_angle': target_angle,
                'is_qualified': row.is_qualified,
                'train_time': row.train_time.strftime('%Y-%m-%d %H:%M:%S') if row.train_time else None,
            }, namespace='/monitor')
        except Exception as e:
            db.session.rollback()
            emit('training_frame_ack', {'status': 'error', 'message': str(e)})


# ------------------------------------------------------------------
# 对外接口函数（供 services/hybridbci_client.py 调用，把平台指令推给 Unity）
# ------------------------------------------------------------------
def send_command_to_unity(patient_id: str, command: dict) -> bool:
    """把平台翻译好的游戏指令推送给指定患者的 Unity 客户端。"""
    sid = patient_sid_map.get(patient_id)
    if sid:
        emit('game_command', command, room=sid, namespace='/unity')
        logger.info(f'[Unity] 向患者 {patient_id} 发送指令: {command}')
        return True
    else:
        logger.warning(f'[Unity] 未找到患者 {patient_id} 的连接，指令丢弃')
        return False


def get_online_patients():
    """返回当前在线的患者ID列表。"""
    return list(patient_sid_map.keys())
