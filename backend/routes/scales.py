"""
康复量表接口（蓝图 scales_bp，前缀 /api/scales）

对应新客户端「康复量表」：5 大量表元数据 + 患者量表评分历史。
  · GET /meta          量表元数据（Fugl-Meyer/Brunnstrom/Barthel/MBI/MMSE）
  · GET /?patient_id=  该患者各量表评分历史
  · POST /             医生录入一条量表评分
"""

from datetime import datetime, date
from flask import Blueprint, request, jsonify
from models.clinical import ScaleAssessment
from extensions import db

scales_bp = Blueprint('scales', __name__, url_prefix='/api/scales')

# 与 Kyouic/app/index.html 的 SCALE_META 完全一致
SCALE_META = [
    {'key': 'fugl-meyer', 'name': 'Fugl-Meyer量表', 'sub': '运动功能评估',
     'desc': '脑卒中偏瘫肢体运动功能最常用评定量表（0-100分）'},
    {'key': 'brunnstorm', 'name': 'Brunnstrom分期', 'sub': '运动恢复分期',
     'desc': '中枢神经损伤后运动恢复6期分阶标准'},
    {'key': 'barthel', 'name': 'Barthel指数', 'sub': '日常生活能力',
     'desc': '日常生活活动能力（ADL）独立性评估（0-100分）'},
    {'key': 'adl', 'name': 'MBI量表', 'sub': '改良Barthel指数',
     'desc': 'Barthel指数改良版，五级评分更灵敏'},
    {'key': 'mmse', 'name': 'MMSE量表', 'sub': '认知功能筛查',
     'desc': '简易精神状态检查（定向/记忆/注意/语言，0-30分）'},
]


@scales_bp.route('/meta', methods=['GET'])
def meta():
    """量表元数据。"""
    return jsonify({'code': 200, 'data': SCALE_META}), 200


@scales_bp.route('/', methods=['GET'])
def list_scales():
    """某患者的量表评分历史（?patient_id=xxx）。"""
    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
    rows = ScaleAssessment.query.filter_by(patient_id=pid)\
        .order_by(ScaleAssessment.assess_date.desc()).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in rows]}), 200


@scales_bp.route('/', methods=['POST'])
def add_scale():
    """医生录入一条量表评分。body: patient_id, scale_key, scale_name?, score_text, result_text, assess_date?"""
    try:
        d = request.get_json() or {}
        pid = d.get('patient_id')
        if not pid:
            return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
        ad = d.get('assess_date')
        try:
            ad = datetime.strptime(ad, '%Y-%m-%d').date() if ad else date.today()
        except Exception:
            ad = date.today()
        rec = ScaleAssessment(
            patient_id=pid,
            assess_date=ad,
            scale_key=d.get('scale_key'),
            scale_name=d.get('scale_name'),
            score_text=d.get('score_text'),
            result_text=d.get('result_text')
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({'code': 200, 'message': '已保存量表评分', 'data': rec.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'保存失败: {str(e)}'}), 500
