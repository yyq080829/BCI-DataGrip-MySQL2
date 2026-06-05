"""
Unity对接接口
- POST /api/unity/send-eeg    : Unity上传EEG数据（备用）
- GET  /api/unity/game-command: Unity轮询获取游戏控制指令（降级方案）
- WebSocket /unity            : Unity实时通信（主要方式）
- WebSocket /unity            : Unity实时通信（主要方式)
"""

from flask import Blueprint, request, jsonify, current_app
from flask_socketio import emit
from extensions import socketio, db
import logging

logger = logging.getLogger(__name__)

unity_bp = Blueprint('unity', __name__)

# 存储患者ID与WebSocket会话ID的映射
patient_sid_map = {}

# ------------------------------------------------------------------
# HTTP 接口（降级备用）
# ------------------------------------------------------------------
@unity_bp.route('/send-eeg', methods=['POST'])
def receive_eeg_from_unity():
    """接收Unity端传来的脑电数据（备用）"""
    try:
        data = request.get_json()
        # 这里可以处理Unity直接上传的EEG数据（若需要）
        return jsonify({'code': 200, 'message': '数据已接收', 'data': data}), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'接收失败: {str(e)}'}), 500


@unity_bp.route('/game-command', methods=['GET'])
def get_game_command():
    """Unity轮询获取游戏控制指令（降级方案）"""
    # 简单返回idle，实际使用中推荐WebSocket推送
    return jsonify({
        'code': 200,
        'data': {'action': 'idle', 'parameters': {}}
    }), 200


# ------------------------------------------------------------------
# WebSocket 事件处理
# ------------------------------------------------------------------
@socketio.on('connect', namespace='/unity')
def handle_unity_connect():
    """Unity WebSocket 连接建立"""
    logger.info(f'[Unity] 客户端 {request.sid} 已连接')
    emit('connected', {'status': 'ok', 'message': 'Connected to backend'})


@socketio.on('disconnect', namespace='/unity')
def handle_unity_disconnect():
    """Unity WebSocket 断开连接，清理映射"""
    for pid, sid in list(patient_sid_map.items()):
        if sid == request.sid:
            del patient_sid_map[pid]
            logger.info(f'[Unity] 患者 {pid} 的连接已断开')
            break
    logger.info(f'[Unity] 客户端 {request.sid} 已断开')


@socketio.on('register', namespace='/unity')
def handle_register(data):
    """
    Unity 连接后必须发送注册消息，绑定患者ID
    消息格式: { "patient_id": "202505001" }
    """
    patient_id = data.get('patient_id')
    if not patient_id:
        emit('error', {'message': 'Missing patient_id'})
        return

    # 如果该患者之前有旧连接，覆盖
    if patient_id in patient_sid_map:
        old_sid = patient_sid_map[patient_id]
        logger.info(f'[Unity] 患者 {patient_id} 已有旧连接 {old_sid}，将被覆盖')
    patient_sid_map[patient_id] = request.sid
    logger.info(f'[Unity] 患者 {patient_id} 已绑定到会话 {request.sid}')
    emit('registered', {'status': 'ok', 'patient_id': patient_id})


@socketio.on('eeg_stream', namespace='/unity')
def handle_eeg_stream(data):
    """Unity 主动上传的实时脑电数据流（可选）"""
    logger.info(f'[Unity] 收到EEG数据流: {data}')
    # 可在此处将数据转发给平台（如 ipc_device_data 协议），目前仅记录


# ==================== 新增：接收训练结果并反馈给平台 ====================
@socketio.on('training_result', namespace='/unity')
def handle_training_result(data):
    """
    Unity 游戏结束时发送训练结果
    消息格式示例:
    {
        "patient_id": "202505001",
        "level_id": 1,
        "score": 85,
        "duration": 300,
        "accuracy": 92.5,
        "is_qualified": true
    }
    """
    patient_id = data.get('patient_id')
    if not patient_id:
        emit('error', {'message': 'Missing patient_id'})
        return

    # 1. 保存到数据库（调用已有的 training/save 逻辑或直接存储）
    # 注意：save_training_result 是一个需要 JWT 认证的接口，这里简化调用
    # 实际我们可以直接创建 TrainingData 记录
    try:
        from models.training import TrainingData, GameLevel
        level_id = data.get('level_id')
        level = GameLevel.query.get(level_id) if level_id else None
        if level:
            new_record = TrainingData(
                patient_id=patient_id,
                level_id=level_id,
                game_score=data.get('score', 0),
                action_score=data.get('score', 0),  # 简化
                is_qualified=data.get('is_qualified', False),
                compensation=data.get('compensation', '无'),
                compensation_score=data.get('compensation_score', 100),
                device_type='Unity'
            )
            db.session.add(new_record)
            db.session.commit()
            logger.info(f'[Unity] 训练结果已保存: patient={patient_id}, score={data.get("score")}')
        else:
            logger.warning(f'[Unity] 关卡不存在: level_id={level_id}')
    except Exception as e:
        logger.error(f'[Unity] 保存训练结果失败: {e}')
        db.session.rollback()

    # 2. 通过 HybridBCI 客户端向平台发送事件（如果客户端已连接）
    try:
        bci_client = current_app.config.get('BCI_CLIENT')
        if bci_client and hasattr(bci_client, 'send_event'):
            # 自定义事件编号：例如 100 表示训练完成，可携带额外数据
            # 注意平台只接受整数 event id
            event_id = 100
            bci_client.send_event(event_id, extra_data={
                'patient_id': patient_id,
                'score': data.get('score'),
                'duration': data.get('duration')
            })
            logger.info(f'[Unity] 已向平台发送事件 {event_id}')
        else:
            logger.warning('[Unity] BCI客户端未启动或不支持send_event')
    except Exception as e:
        logger.error(f'[Unity] 向平台发送事件失败: {e}')

    # 3. 回复 Unity 确认
    emit('training_result_ack', {'status': 'ok', 'message': '数据已接收'})


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