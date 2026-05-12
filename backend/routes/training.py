"""
训练数据接口
POST /api/training/save    - 存储Unity游戏结束后的得分、时长
POST /api/training/upload  - 上传训练实时数据
GET  /api/training/history - 查询训练历史
GET  /api/training/stats   - 训练数据统计
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models.training import TrainingData, GameLevel
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

training_bp = Blueprint('training', __name__)


@training_bp.route('/save', methods=['POST'])
@jwt_required()
def save_training_result():
    """
    存储Unity游戏结束后的结果（得分、时长等）

    请求格式：
    {
        "level_id": 1,
        "score": 85,
        "duration": 300,
        "accuracy": 75.5,
        "shoulder_abduction": 58.5,
        "elbow_extension": 10.2,
        "forearm_rotation": 85.0,
        "compensation": "无",
        "compensation_score": 100
    }
    """
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()

        # 只有患者可以保存训练数据
        if claims.get('role') != 'patient':
            return jsonify({'code': 403, 'message': '只有患者可以保存训练数据'}), 403

        data = request.get_json()

        # 检查关卡是否存在
        level = GameLevel.query.get(data.get('level_id'))
        if not level:
            return jsonify({'code': 400, 'message': '关卡不存在'}), 400

        # 判断是否达标（根据关卡目标角度）
        is_qualified = False
        if level.game_name == '星际翼航':
            actual_angle = data.get('shoulder_abduction', 0)
            is_qualified = actual_angle >= float(level.target_angle) - float(level.angle_tolerance)
        elif level.game_name == '肘伸展采水晶':
            actual_angle = data.get('elbow_extension', 0)
            is_qualified = actual_angle >= float(level.target_angle) - float(level.angle_tolerance)
        elif level.game_name == '星光舞台':
            actual_angle = data.get('forearm_rotation', 0)
            is_qualified = actual_angle >= float(level.target_angle) - float(level.angle_tolerance)

        # 创建训练记录
        training = TrainingData(
            patient_id=current_user_id,
            level_id=data.get('level_id'),
            train_time=datetime.now(),
            shoulder_abduction=data.get('shoulder_abduction'),
            elbow_extension=data.get('elbow_extension'),
            forearm_rotation=data.get('forearm_rotation'),
            action_score=data.get('score', 0),
            is_qualified=is_qualified,
            game_score=data.get('score', 0),
            compensation=data.get('compensation', '无'),
            compensation_score=data.get('compensation_score', 100),
            device_type=data.get('device_type', 'AR手机')
        )

        db.session.add(training)
        db.session.commit()

        return jsonify({
            'code': 200,
            'message': '训练数据保存成功',
            'data': {
                'record_id': training.data_id,
                'is_qualified': is_qualified,
                'score': data.get('score')
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'保存失败: {str(e)}'}), 500


@training_bp.route('/history', methods=['GET'])
@jwt_required()
def get_training_history():
    """
    查询训练历史

    参数：
        patient_id: 患者ID（医生查看时需要）
        days: 查询最近天数（默认30天）
        limit: 返回条数限制（默认50条）
    """
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        role = claims.get('role')

        # 确定查询的患者ID
        if role == 'patient':
            patient_id = current_user_id
        elif role == 'doctor':
            patient_id = request.args.get('patient_id')
            if not patient_id:
                return jsonify({'code': 400, 'message': '请指定患者ID'}), 400
        else:
            return jsonify({'code': 403, 'message': '无权访问'}), 403

        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 50, type=int)

        since = datetime.now() - timedelta(days=days)

        trainings = TrainingData.query.filter(
            TrainingData.patient_id == patient_id,
            TrainingData.train_time >= since
        ).order_by(
            TrainingData.train_time.desc()
        ).limit(limit).all()

        return jsonify({
            'code': 200,
            'message': '查询成功',
            'data': {
                'patient_id': patient_id,
                'count': len(trainings),
                'records': [t.to_dict() for t in trainings]
            }
        }), 200

    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败: {str(e)}'}), 500


@training_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_training_stats():
    """训练数据统计"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()

        if claims.get('role') == 'patient':
            patient_id = current_user_id
        else:
            patient_id = request.args.get('patient_id')
            if not patient_id:
                return jsonify({'code': 400, 'message': '请指定患者ID'}), 400

        # 总训练次数
        total = TrainingData.query.filter_by(patient_id=patient_id).count()

        # 平均得分
        avg_score = db.session.query(
            func.avg(TrainingData.game_score)
        ).filter_by(patient_id=patient_id).scalar()

        # 达标率
        qualified = TrainingData.query.filter_by(
            patient_id=patient_id,
            is_qualified=True
        ).count()
        qualified_rate = (qualified / total * 100) if total > 0 else 0

        # 按游戏统计
        game_stats = db.session.query(
            GameLevel.game_name,
            func.count(TrainingData.data_id),
            func.avg(TrainingData.game_score),
            func.max(TrainingData.game_score)
        ).join(
            TrainingData
        ).filter(
            TrainingData.patient_id == patient_id
        ).group_by(GameLevel.game_name).all()

        return jsonify({
            'code': 200,
            'data': {
                'total_sessions': total,
                'avg_score': round(float(avg_score), 2) if avg_score else 0,
                'qualified_rate': round(qualified_rate, 2),
                'by_game': [{
                    'game_name': g[0],
                    'count': g[1],
                    'avg_score': round(float(g[2]), 2) if g[2] else 0,
                    'best_score': int(g[3]) if g[3] else 0
                } for g in game_stats]
            }
        }), 200

    except Exception as e:
        return jsonify({'code': 500, 'message': f'统计失败: {str(e)}'}), 500