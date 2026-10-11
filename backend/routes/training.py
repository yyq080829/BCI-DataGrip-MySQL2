"""
训练数据接口（蓝图 training_bp，前缀 /api/training）

这是给【游戏结束后】或【非实时场景】用的 HTTP 接口；真正的实时角度流走
routes/unity.py 的 WebSocket training_frame 事件（每帧一条，高频）。

提供：
  · POST /api/training/save    保存一次训练结果（单条，兼容旧 Unity 调用）
  · GET  /api/training/history 分页查询某患者训练历史
  · GET  /api/training/stats   统计：总次数、平均分、达标率、各游戏细分

注意：save 和 unity 的 training_frame 都会写 train_real_time_data，
所以 /stats 的总次数把两种来源都算进去了。
"""

from flask import Blueprint, request, jsonify
from models.training import TrainingData, GameLevel
from extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func

training_bp = Blueprint('training', __name__, url_prefix='/api/training')


@training_bp.route('/save', methods=['POST'])
def save_training_result():
    """保存一次训练结果（Unity 游戏结束时调用）。"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        patient_id = data.get('patient_id')
        level_id = data.get('level_id')
        if not patient_id or not level_id:
            return jsonify({'code': 400, 'message': '缺少patient_id或level_id'}), 400

        # 把前端传来的字段直接建一行训练记录
        training = TrainingData(
            patient_id=patient_id,
            level_id=level_id,
            shoulder_abduction=data.get('shoulder_abduction'),
            elbow_extension=data.get('elbow_extension'),
            forearm_rotation=data.get('forearm_rotation'),
            action_score=data.get('action_score', 0),
            is_qualified=data.get('is_qualified', False),
            game_score=data.get('game_score', 0),
            compensation=data.get('compensation'),
            compensation_score=data.get('compensation_score', 100)
        )
        db.session.add(training)
        db.session.commit()
        return jsonify({'code': 200, 'message': '保存成功', 'data_id': training.data_id}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'保存失败: {str(e)}'}), 500


@training_bp.route('/history', methods=['GET'])
def get_training_history():
    """分页查询训练历史（?patient_id=xxx&page=1&per_page=20）。"""
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少patient_id'}), 400

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # paginate 是 Flask-SQLAlchemy 自带的分页工具
        pagination = TrainingData.query.filter_by(patient_id=patient_id)\
            .order_by(TrainingData.train_time.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'code': 200,
            'data': {
                'records': [t.to_dict() for t in pagination.items],
                'total': pagination.total,
                'page': page,
                'per_page': per_page
            }
        }), 200

    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败: {str(e)}'}), 500


@training_bp.route('/stats', methods=['GET'])
def get_training_stats():
    """训练数据统计：总次数、平均分、达标率，以及按游戏细分（计数/均分/最佳）。"""
    try:
        patient_id = request.args.get('patient_id')
        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少patient_id'}), 400

        total = TrainingData.query.filter_by(patient_id=patient_id).count()
        avg_score = db.session.query(func.avg(TrainingData.game_score))\
            .filter_by(patient_id=patient_id).scalar()

        qualified = TrainingData.query.filter_by(patient_id=patient_id, is_qualified=True).count()
        qualified_rate = (qualified / total * 100) if total > 0 else 0

        # 按游戏名分组聚合：count / avg / max
        game_stats = db.session.query(
            GameLevel.game_name,
            func.count(TrainingData.data_id),
            func.avg(TrainingData.game_score),
            func.max(TrainingData.game_score)
        ).join(TrainingData).filter(TrainingData.patient_id == patient_id)\
            .group_by(GameLevel.game_name).all()

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
