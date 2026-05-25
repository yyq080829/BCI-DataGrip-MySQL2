"""
Unity对接接口
POST /api/unity/send-eeg    - Unity上传EEG数据
GET  /api/unity/game-command - Unity获取游戏控制指令
WebSocket /unity             - Unity实时通信
"""

from flask import Blueprint, request, jsonify
from flask_socketio import emit
from app import db, socketio

unity_bp = Blueprint('unity', __name__)


@unity_bp.route('/send-eeg', methods=['POST'])
def receive_eeg_from_unity():
    """接收Unity端传来的脑电数据"""
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
    print('[Unity WebSocket] Unity已连接')
    emit('connected', {'status': 'ok'})


@socketio.on('disconnect', namespace='/unity')
def handle_unity_disconnect():
    """Unity断开连接"""
    print('[Unity WebSocket] Unity已断开')


@socketio.on('eeg_stream', namespace='/unity')
def handle_eeg_stream(data):
    """实时脑电数据流处理"""
    print(f'[Unity WebSocket] 收到数据: {data}')
    emit('game_command', {
        'action': 'idle',
        'parameters': {}
    })