"""
训练数据接口
POST /api/training/save    - 存储Unity游戏结束后的得分、时长
GET  /api/training/history - 查询训练历史
GET  /api/training/stats   - 训练数据统计
"""

from flask import Blueprint, request, jsonify
from models.training import TrainingData, GameLevel
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

training_bp = Blueprint('training', __name__, url_prefix='/api/training')


@training_bp.route('/save', methods=['POST'])
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
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        patient_id = data.get('patient_id')
        level_id = data.get('level_id')
        if not patient_id or not level_id:
            return jsonify({'code': 400, 'message': '缺少 patient_id 或 level_id'}), 400

        # 检查关卡是否存在
        level = GameLevel.query.get(data.get('level_id'))
        if not level:
            return jsonify({'code': 400, 'message': '关卡不存在'}), 400

        # 判断是否达标（根据关卡目标角度）
        is_qualified = False
        if level.game_name == '星光舞台':
            actual_angle = data.get('forearm_rotation', 0)
            is_qualified = actual_angle >= float(level.target_angle) - float(level.angle_tolerance)
        else:
            # 其他游戏（如果出现）默认不达标
            is_qualified = False

        # 创建训练记录
        training = TrainingData(
            patient_id=patient_id,
            level_id=level_id,
            train_time=datetime.now(),
            shoulder_abduction=data.get('shoulder_abduction'),
            elbow_extension=data.get('elbow_extension'),
            forearm_rotation=data.get('forearm_rotation'),
            action_score=data.get('score', 0),
            is_qualified=is_qualified,
            game_score=data.get('score', 0),
            compensation=data.get('compensation', '无'),
            compensation_score=data.get('compensation_score', 100),
            device_type=data.get('device_type', 'Unity')
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
def get_training_history():
    """
    查询训练历史

    参数：
        patient_id: 患者ID（医生查看时需要）
        days: 查询最近天数（默认30天）
        limit: 返回条数限制（默认50条）
    """
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少 patient_id'}), 400

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
def get_training_stats():
    """训练数据统计"""
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少 patient_id'}), 400

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