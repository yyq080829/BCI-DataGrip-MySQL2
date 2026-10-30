"""
患者接口（蓝图 patients_bp，前缀 /api/patients）

对应新客户端「患者中心 / 我的档案」：
  · GET  /                 患者列表（含临床摘要）
  · GET  /search?q=        按姓名/编号/诊断搜索
  · GET  /<patient_id>     患者详情（档案 + 量表历史 + 医生建议）
  · PUT  /<patient_id>     更新临床字段（医生完善档案）

注意：患者创建在 auth.py 的 /register；本模块负责档案的读取与完善。
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import or_
from models.user import Patient
from models.clinical import ScaleAssessment, DoctorAdvice
from extensions import db

patients_bp = Blueprint('patients', __name__, url_prefix='/api/patients')


@patients_bp.route('/', methods=['GET'])
def list_patients():
    """患者列表（医生端患者中心）。"""
    patients = Patient.query.order_by(Patient.patient_id).all()
    return jsonify({'code': 200, 'data': [p.to_dict() for p in patients]}), 200


@patients_bp.route('/search', methods=['GET'])
def search_patients():
    """按姓名/编号/诊断模糊搜索。"""
    q = (request.args.get('q') or '').strip()
    if not q:
        return list_patients()
    like = f'%{q}%'
    patients = Patient.query.filter(
        or_(Patient.patient_id.like(like),
            Patient.patient_name.like(like),
            Patient.diagnosis.like(like))
    ).all()
    return jsonify({'code': 200, 'data': [p.to_dict() for p in patients]}), 200


@patients_bp.route('/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    """患者详情：档案 + 量表评分历史 + 医生建议。"""
    p = Patient.query.get(patient_id)
    if not p:
        return jsonify({'code': 404, 'message': '患者不存在'}), 404
    scales = ScaleAssessment.query.filter_by(patient_id=patient_id)\
        .order_by(ScaleAssessment.assess_date.desc()).all()
    advices = DoctorAdvice.query.filter_by(patient_id=patient_id)\
        .order_by(DoctorAdvice.created_at.desc()).all()
    data = p.to_dict()
    data['assessmentHistory'] = [s.to_dict() for s in scales]
    data['doctorAdvices'] = [a.advice_text for a in advices]
    return jsonify({'code': 200, 'data': data}), 200


@patients_bp.route('/<patient_id>', methods=['PUT'])
def update_patient(patient_id):
    """更新患者临床字段（医生完善档案）。"""
    p = Patient.query.get(patient_id)
    if not p:
        return jsonify({'code': 404, 'message': '患者不存在'}), 404
    d = request.get_json() or {}
    for f in ['diagnosis', 'brunnstrom_stage', 'train_level', 'fm_score',
              'adherence', 'game_train_count', 'recovery_progress']:
        if f in d and d[f] is not None:
            setattr(p, f, d[f])
    for date_field in ['last_train', 'first_visit']:
        if date_field in d and d[date_field]:
            try:
                setattr(p, date_field, datetime.strptime(d[date_field], '%Y-%m-%d').date())
            except Exception:
                pass
    if 'recovery_progress' in d and isinstance(d['recovery_progress'], list):
        p.recovery_progress = json.dumps(d['recovery_progress'])
    db.session.commit()
    return jsonify({'code': 200, 'message': '更新成功', 'data': p.to_dict()}), 200
