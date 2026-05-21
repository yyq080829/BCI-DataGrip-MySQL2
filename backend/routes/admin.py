from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from models.user import Patient, Doctor, Escort

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    # 检查当前用户是否是管理员
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'code': 403, 'message': '无权限访问'}), 403

    # 获取所有患者
    patients = Patient.query.all()
    # 获取所有医生
    doctors = Doctor.query.all()
    # 获取所有陪同人员
    escorts = Escort.query.all()

    users = []
    for p in patients:
        users.append({
            'user_id': p.patient_id,
            'username': p.username,
            'user_name': p.patient_name,
            'role': 'patient',
            'email': getattr(p, 'email', ''),  # 如果表有 email 字段
            'status': 'active',
            'register_date': p.admission_time.strftime('%Y-%m-%d') if p.admission_time else ''
        })
    for d in doctors:
        users.append({
            'user_id': d.doctor_id,
            'username': d.username,
            'user_name': d.doctor_name,
            'role': 'doctor',
            'email': '',
            'status': 'active',
            'register_date': d.create_time.strftime('%Y-%m-%d') if hasattr(d, 'create_time') else ''
        })
    for e in escorts:
        users.append({
            'user_id': e.escort_id,
            'username': e.username,
            'user_name': e.escort_name,
            'role': 'companion',
            'email': '',
            'status': 'active',
            'register_date': e.create_time.strftime('%Y-%m-%d') if hasattr(e, 'create_time') else ''
        })

    return jsonify({'code': 200, 'data': users}), 200