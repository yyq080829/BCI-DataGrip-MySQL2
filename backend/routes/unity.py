"""
Unity对接接口
POST /api/unity/send-eeg    - Unity上传EEG数据
GET  /api/unity/game-command - Unity获取游戏控制指令
WebSocket /unity             - Unity实时通信
"""

from flask import Blueprint, request, jsonify
from flask_socketio import emit
from extensions import socketio, db

unity_bp = Blueprint('unity', __name__)

# 存储患者ID与WebSocket会话ID的映射
# patient_id -> sid (socket session id)
patient_sid_map = {}

@unity_bp.route('/send-eeg', methods=['POST'])
def receive_eeg_from_unity():
    """接收Unity端传来的脑电数据(备用）"""
    try:
        data = request.get_json()

        #  处理Unity传来的脑电数据
        # 后续添加脑电处理逻辑

        return jsonify({
            'code': 200,
            'message': '数据已接收',
            'data': data
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'接收失败: {str(e)}'
        }), 500


@unity_bp.route('/game-command', methods=['GET'])
def get_game_command():
    """Unity轮询获取游戏控制指令"""
    #  根据脑电数据生成游戏指令
    return jsonify({
        'code': 200,
        'data': {
            'action': 'idle',
            'parameters': {}
        }
    }), 200


# WebSocket处理
@socketio.on('connect', namespace='/unity')
def handle_unity_connect():
    """Unity通过WebSocket连接"""
    print(f'[Unity WebSocket] 客户端 {request.sid} 已连接')
    emit('connected', {'status': 'ok', 'message': 'Connected to backend'})


@socketio.on('disconnect', namespace='/unity')
def handle_unity_disconnect():
    """Unity断开连接"""
    for pid, sid in list(patient_sid_map.items()):
        if sid == request.sid:
            del patient_sid_map[pid]
            print(f'[Unity WebSocket] 患者 {pid} 的连接已断开')
            break
    print(f'[Unity WebSocket] 客户端 {request.sid} 已断开')

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

    # 如果该患者之前有旧连接，先清理旧会话（可选）
    if patient_id in patient_sid_map:
        old_sid = patient_sid_map[patient_id]
        print(f'[Unity WebSocket] 患者 {patient_id} 已有旧连接 {old_sid}，将被覆盖')
    # 绑定新会话
    patient_sid_map[patient_id] = request.sid
    print(f'[Unity WebSocket] 患者 {patient_id} 已绑定到会话 {request.sid}')
    emit('registered', {'status': 'ok', 'patient_id': patient_id})

@socketio.on('eeg_stream', namespace='/unity')
def handle_eeg_stream(data):
    """实时脑电数据流处理"""
    print(f'[Unity WebSocket] 收到数据: {data}')

# ==================== 对外接口函数（供其他模块调用） ====================
def send_command_to_unity(patient_id: str, command: dict) -> bool:
    """
    向指定患者的Unity客户端发送游戏指令
    :param patient_id: 患者ID
    :param command: 指令字典，例如 {"cmd": "FORWARD", "intensity": 0.8}
    :return: 是否成功发送
    """
    sid = patient_sid_map.get(patient_id)
    if sid:
        emit('game_command', command, room=sid, namespace='/unity')
        print(f'[Unity WebSocket] 向患者 {patient_id} 发送指令: {command}')
        return True
    else:
        print(f'[Unity WebSocket] 未找到患者 {patient_id} 的WebSocket连接，指令丢弃')
        return False

def get_online_patients():
    """返回当前在线的患者ID列表（用于监控）"""
    return list(patient_sid_map.keys())
