"""
Unity对接接口
- POST /api/unity/send-eeg       : Unity上传EEG数据（备用）
- GET  /api/unity/game-command   : Unity轮询获取游戏控制指令（降级方案）
- WebSocket /unity               : Unity实时通信（主要方式）

P300 新增事件:
- p300_flash : Unity上报闪烁事件（绿色频闪/红色闪烁）
- p300_start : Unity通知P300范式开始
- p300_stop  : Unity通知P300范式结束

实验记录上报:
- p300_stop 时自动向平台上报实验记录数据

大臂康复实时数据（直连，不经平台/脑电）:
- training_frame : Unity 每帧上报肩外展等角度 -> 直接写 train_real_time_data -> 实时广播到 /monitor 后台
"""

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit
from extensions import socketio, db
import logging
import time

logger = logging.getLogger(__name__)

unity_bp = Blueprint('unity', __name__)

# 存储患者ID与WebSocket会话ID的映射
patient_sid_map = {}

# P300 范式运行状态
p300_running = False
p300_flash_count = 0
p300_start_time = 0
p300_target_count = 0
p300_nontarget_count = 0


# ------------------------------------------------------------------
# HTTP 接口（降级备用）
# ------------------------------------------------------------------
@unity_bp.route('/send-eeg', methods=['POST'])
def receive_eeg_from_unity():
    """接收Unity端传来的脑电数据（备用）"""
    try:
        data = request.get_json()
        return jsonify({'code': 200, 'message': '数据已接收', 'data': data}), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'接收失败: {str(e)}'}), 500


@unity_bp.route('/game-command', methods=['GET'])
def get_game_command():
    """Unity轮询获取游戏控制指令（降级方案）"""
    return jsonify({'code': 200, 'data': {'cmd': 'idle', 'param': ''}}), 200


# ------------------------------------------------------------------
# WebSocket 事件处理
# ------------------------------------------------------------------
@socketio.on('connect', namespace='/unity')
def on_unity_connect():
    """Unity客户端连接"""
    logger.info('[Unity] 客户端已连接')


@socketio.on('disconnect', namespace='/unity')
def on_unity_disconnect():
    """Unity客户端断开"""
    logger.info('[Unity] 客户端已断开')
    # 清理映射
    for pid, sid in list(patient_sid_map.items()):
        if sid == request.sid:
            del patient_sid_map[pid]
            break


@socketio.on('register_patient', namespace='/unity')
def on_register_patient(data):
    """
    Unity注册患者ID

    请求格式: {"patient_id": "202505001"}
    """
    patient_id = data.get('patient_id')
    if patient_id:
        patient_sid_map[patient_id] = request.sid
        logger.info(f'[Unity] 患者注册: {patient_id}')
        emit('register_ack', {'status': 'ok', 'patient_id': patient_id})
    else:
        emit('register_ack', {'status': 'error', 'message': '缺少patient_id'})


# ------------------------------------------------------------------
# P300 闪烁事件
# ------------------------------------------------------------------
@socketio.on('p300_flash', namespace='/unity')
def on_p300_flash(data):
    """
    Unity上报P300闪烁事件

    请求格式:
    {
        "is_target": true,     // true=红色闪烁(目标), false=绿色频闪(非目标)
        "row": 2,              // 行号(1-based)
        "col": 3               // 列号(1-based)
    }

    后端终端输出:
    - 绿色频闪 → 0
    - 红色闪烁 → 1 (row,col)
    """
    global p300_flash_count, p300_target_count, p300_nontarget_count

    is_target = data.get('is_target', False)
    row = data.get('row', 0)
    col = data.get('col', 0)

    p300_flash_count += 1

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
    """
    Unity通知P300范式开始

    请求格式:
    {
        "patient_id": "202505001",
        "grid_rows": 3,
        "grid_cols": 4
    }
    """
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

    # 注册患者
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
    """
    Unity通知P300范式结束

    请求格式:
    {
        "patient_id": "202505001",
        "score": 85,
        "accuracy": 0.75
    }

    同时向平台上报实验记录数据
    """
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

    # ★ 关键：向平台上报实验记录 ★
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
        logger.info(f'[P300] 已向平台上报实验记录')
    else:
        logger.warning('[P300] BCI客户端未启动，无法上报实验记录')

    emit('p300_stop_ack', {'status': 'ok', 'duration': duration})


# ------------------------------------------------------------------
# 训练结果
# ------------------------------------------------------------------
@socketio.on('training_result', namespace='/unity')
def on_training_result(data):
    """
    Unity上传训练结果

    请求格式:
    {
        "patient_id": "202505001",
        "level_id": 1,
        "score": 85,
        "duration": 300
    }
    """
    patient_id = data.get('patient_id')
    logger.info(f'[Unity] 收到训练结果: patient={patient_id}, data={data}')

    # 向平台发送事件
    bci_client = current_app.config.get('BCI_CLIENT')
    if bci_client and hasattr(bci_client, 'send_event'):
        event_id = 100
        bci_client.send_event(event_id, extra_data={
            'patient_id': patient_id,
            'score': data.get('score'),
            'duration': data.get('duration')
        })
        logger.info(f'[Unity] 已向平台发送事件 {event_id}')
    else:
        logger.warning('[Unity] BCI客户端未启动或不支持send_event')

    emit('training_result_ack', {'status': 'ok', 'message': '数据已接收'})


# ------------------------------------------------------------------
# 实时训练帧（接通 Unity 实时角度 / 难度 / 反馈 -> 数据库）
# ------------------------------------------------------------------
@socketio.on('training_frame', namespace='/unity')
def on_training_frame(data):
    """
    Unity 实时上报单帧训练数据

    请求格式:
    {
        "patient_id": "202505001",
        "level_id": 1,                 // 关卡(决定目标角度/难度)
        "shoulder_abduction": 58.5,    // 肩外展角度
        "elbow_extension": 0.0,        // 肘伸展角度
        "forearm_rotation": 90.0,      // 前臂旋转角度
        "action_score": 8,             // 单动作得分
        "is_qualified": true,          // 是否达标
        "compensation": "无",          // 代偿动作
        "compensation_score": 100,     // 代偿评分
        "game_score": 80,              // 当前游戏得分
        "device_type": "AR手机"        // 采集设备
    }
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

            # 查询关卡目标角度，便于后台对比显示
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
# 对外接口函数（供其他模块调用）
# ------------------------------------------------------------------
def send_command_to_unity(patient_id: str, command: dict) -> bool:
    """向指定患者的Unity客户端发送游戏指令"""
    sid = patient_sid_map.get(patient_id)
    if sid:
        emit('game_command', command, room=sid, namespace='/unity')
        logger.info(f'[Unity] 向患者 {patient_id} 发送指令: {command}')
        return True
    else:
        logger.warning(f'[Unity] 未找到患者 {patient_id} 的连接，指令丢弃')
        return False


def get_online_patients():
    """返回当前在线的患者ID列表"""
    return list(patient_sid_map.keys())
