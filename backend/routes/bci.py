"""
脑电数据接口 - 接收HybridBCI平台推送的数据
POST /api/bci/receive  - 接收脑电实时数据（HTTP方式）
WebSocket /bci         - 接收脑电实时数据（WebSocket方式）
GET  /api/bci/history  - 查询历史脑电数据
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import emit
from models.bci_data import BCIData
from extensions import db, socketio
from datetime import datetime, timedelta

bci_bp = Blueprint('bci', __name__)


@bci_bp.route('/receive', methods=['POST'])
def receive_bci_data():
    """
    接收HybridBCI平台推送的脑电数据（HTTP POST方式）

    HybridBCI推送的JSON格式示例：
    {
        "patient_id": "202505001",
        "device_id": "BCI-Device-001",
        "timestamp": "2025-05-10 14:30:25.123",
        "eeg_data": {
            "delta_power": 0.5,
            "theta_power": 1.2,
            "alpha_power": 8.5,
            "beta_power": 3.2,
            "gamma_power": 0.8,
            "attention": 65.5,
            "meditation": 40.2
        },
        "signal_quality": 85,
        "raw_statistics": {
            "mean": 0.02,
            "std": 1.5
        }
    }
    """
    try:
        data = request.get_json()

        # 1. 验证必要字段
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        patient_id = data.get('patient_id')
        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少患者ID'}), 400

        # 2. 提取脑电数据
        eeg_data = data.get('eeg_data', {})
        raw_statistics = data.get('raw_statistics', {})

        # 3. 创建脑电数据记录
        bci_record = BCIData(
            patient_id=patient_id,
            timestamp=datetime.now(),

            # 各频段功率
            delta_power=eeg_data.get('delta_power'),
            theta_power=eeg_data.get('theta_power'),
            alpha_power=eeg_data.get('alpha_power'),
            beta_power=eeg_data.get('beta_power'),
            gamma_power=eeg_data.get('gamma_power'),

            # 注意力和放松度
            attention=eeg_data.get('attention'),
            meditation=eeg_data.get('meditation'),

            # 信号质量
            signal_quality=data.get('signal_quality'),

            # 原始数据统计
            raw_mean=raw_statistics.get('mean') if isinstance(raw_statistics, dict) else None,
            raw_std=raw_statistics.get('std') if isinstance(raw_statistics, dict) else None,

            # 设备ID
            device_id=data.get('device_id')
        )

        # 4. 保存到数据库
        db.session.add(bci_record)
        db.session.commit()

        # 5. 通过WebSocket实时推送给前端（如果前端已连接）
        socketio.emit('bci_data_update', {
            'patient_id': patient_id,
            'attention': eeg_data.get('attention'),
            'meditation': eeg_data.get('meditation'),
            'alpha_power': eeg_data.get('alpha_power'),
            'beta_power': eeg_data.get('beta_power'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, namespace='/bci')

        return jsonify({
            'code': 200,
            'message': '脑电数据接收成功',
            'data': {
                'record_id': bci_record.id,
                'timestamp': bci_record.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'数据接收失败: {str(e)}'
        }), 500


@bci_bp.route('/batch_receive', methods=['POST'])
def receive_bci_batch_data():
    """
    批量接收脑电数据（一次接收多条数据，减少请求次数）

    请求格式：
    {
        "patient_id": "202505001",
        "device_id": "BCI-Device-001",
        "records": [
            {
                "timestamp": "2025-05-10 14:30:25.123",
                "eeg_data": {...},
                "signal_quality": 85
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or 'patient_id' not in data:
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400

        patient_id = data['patient_id']
        device_id = data.get('device_id', '')
        records = data.get('records', [])

        # 批量创建记录
        bci_records = []
        for record in records:
            eeg_data = record.get('eeg_data', {})
            raw_stats = record.get('raw_statistics', {})

            bci_record = BCIData(
                patient_id=patient_id,
                timestamp=record.get('timestamp', datetime.now()),
                delta_power=eeg_data.get('delta_power'),
                theta_power=eeg_data.get('theta_power'),
                alpha_power=eeg_data.get('alpha_power'),
                beta_power=eeg_data.get('beta_power'),
                gamma_power=eeg_data.get('gamma_power'),
                attention=eeg_data.get('attention'),
                meditation=eeg_data.get('meditation'),
                signal_quality=record.get('signal_quality'),
                raw_mean=raw_stats.get('mean') if isinstance(raw_stats, dict) else None,
                raw_std=raw_stats.get('std') if isinstance(raw_stats, dict) else None,
                device_id=device_id
            )
            bci_records.append(bci_record)

        # 批量保存
        db.session.add_all(bci_records)
        db.session.commit()

        return jsonify({
            'code': 200,
            'message': f'成功接收{len(bci_records)}条脑电数据',
            'data': {
                'count': len(bci_records)
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'批量接收失败: {str(e)}'
        }), 500


@bci_bp.route('/history', methods=['GET'])
@jwt_required()
def get_bci_history():
    """
    查询脑电历史数据
    参数：
        patient_id: 患者ID（必填）
        minutes: 查询最近多少分钟的数据（默认60分钟）
        limit: 返回条数限制（默认100条）

    请求示例：
        GET /api/bci/history?patient_id=202505001&minutes=30&limit=50
    """
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少患者ID'}), 400

        # 查询参数
        minutes = request.args.get('minutes', 60, type=int)
        limit = request.args.get('limit', 100, type=int)

        # 计算时间范围
        since = datetime.now() - timedelta(minutes=minutes)

        # 查询数据
        records = BCIData.query.filter(
            BCIData.patient_id == patient_id,
            BCIData.timestamp >= since
        ).order_by(
            BCIData.timestamp.desc()
        ).limit(limit).all()

        # 转为字典列表
        data_list = [r.to_dict() for r in records]

        return jsonify({
            'code': 200,
            'message': '查询成功',
            'data': {
                'patient_id': patient_id,
                'count': len(data_list),
                'time_range': f'最近{minutes}分钟',
                'records': data_list
            }
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'查询失败: {str(e)}'
        }), 500


# ============ WebSocket处理脑电数据流 ============

@socketio.on('connect', namespace='/bci')
def handle_bci_connect():
    """HybridBCI平台通过WebSocket连接"""
    print('[BCI WebSocket] HybridBCI平台已连接')
    emit('connected', {'status': 'ok', 'message': '脑电数据通道已建立'})


@socketio.on('disconnect', namespace='/bci')
def handle_bci_disconnect():
    """HybridBCI平台断开连接"""
    print('[BCI WebSocket] HybridBCI平台已断开')


@socketio.on('bci_data', namespace='/bci')
def handle_bci_data_stream(data):
    """
    通过WebSocket实时接收脑电数据（推荐方式，延迟更低）

    HybridBCI推送格式：
    {
        "patient_id": "202505001",
        "eeg_data": {
            "alpha_power": 8.5,
            "beta_power": 3.2,
            "attention": 65.5,
            ...
        },
        "signal_quality": 85
    }
    """
    try:
        patient_id = data.get('patient_id')
        eeg_data = data.get('eeg_data', {})

        # 保存到数据库
        bci_record = BCIData(
            patient_id=patient_id,
            timestamp=datetime.now(),
            delta_power=eeg_data.get('delta_power'),
            theta_power=eeg_data.get('theta_power'),
            alpha_power=eeg_data.get('alpha_power'),
            beta_power=eeg_data.get('beta_power'),
            gamma_power=eeg_data.get('gamma_power'),
            attention=eeg_data.get('attention'),
            meditation=eeg_data.get('meditation'),
            signal_quality=data.get('signal_quality'),
            device_id=data.get('device_id')
        )

        db.session.add(bci_record)
        db.session.commit()

        # 实时转发给前端（前端订阅了bci_data_update事件）
        emit('bci_data_update', {
            'patient_id': patient_id,
            'attention': eeg_data.get('attention'),
            'meditation': eeg_data.get('meditation'),
            'alpha_power': eeg_data.get('alpha_power'),
            'beta_power': eeg_data.get('beta_power'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        }, broadcast=True)  # broadcast=True 广播给所有连接的客户端

    except Exception as e:
        print(f'[BCI WebSocket] 数据处理错误: {str(e)}')
        emit('error', {'message': str(e)})