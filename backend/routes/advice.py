"""
医生建议接口（蓝图 advice_bp，前缀 /api/advice）

对应新客户端「康复建议」（医生端）：医生给患者写建议。
  · GET /?patient_id=   某患者全部建议
  · POST /              新增建议 {doctor_id, patient_id, patient_name?, advice_text}
"""

from flask import Blueprint, request, jsonify
from models.clinical import DoctorAdvice
from extensions import db

advice_bp = Blueprint('advice', __name__, url_prefix='/api/advice')


@advice_bp.route('/', methods=['GET'])
def list_advice():
    """某患者全部建议（?patient_id=xxx）。"""
    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
    rows = DoctorAdvice.query.filter_by(patient_id=pid)\
        .order_by(DoctorAdvice.created_at.desc()).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in rows]}), 200


@advice_bp.route('/', methods=['POST'])
def add_advice():
    """新增一条医生建议。body: doctor_id, patient_id, advice_text, patient_name?"""
    try:
        d = request.get_json() or {}
        pid = d.get('patient_id')
        txt = d.get('advice_text')
        if not pid or not txt:
            return jsonify({'code': 400, 'message': '缺少patient_id或advice_text'}), 400
        rec = DoctorAdvice(
            doctor_id=d.get('doctor_id'),
            patient_id=pid,
            patient_name=d.get('patient_name'),
            advice_text=txt
        )
        db.session.add(rec)
        db.session.commit()
        return jsonify({'code': 200, 'message': '已添加建议', 'data': rec.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'添加失败: {str(e)}'}), 500
