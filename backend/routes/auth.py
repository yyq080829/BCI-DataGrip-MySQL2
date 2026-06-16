"""
登录认证接口 - 适配前端 HTML 的请求格式
前端登录请求示例：
    POST /api/auth/login
    {
        "username": "doctor1",
        "password": "Doctor123",
        "userType": "doctor"   // 可选值: doctor, patient, admin
    }

前端注册请求示例：
    POST /api/auth/register
    {
        "username": "newuser",
        "email": "new@example.com",
        "password": "123456",
        "confirmPassword": "123456",
        "register-user-type": "patient"   // patient 或 doctor
    }
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from models.user import Patient, Doctor   # 移除了 Escort
from extensions import db
from datetime import datetime
import random

auth_bp = Blueprint('auth', __name__)

def generate_patient_id():
    """生成格式为 年月日+三位序号 的患者ID，例如 20250515001"""
    today = datetime.now().strftime('%Y%m%d')
    count = Patient.query.filter(Patient.patient_id.like(f'{today}%')).count()
    return f'{today}{count + 1:03d}'

def generate_doctor_id():
    """生成简单的医生ID，格式 DOC + 时间戳后6位 + 随机数"""
    import time
    suffix = str(int(time.time()))[-6:]
    rand = random.randint(10, 99)
    return f'DOC{suffix}{rand}'

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    统一登录接口，支持患者、医生、管理员
    前端发送的 JSON 包含: username, password, userType (可选)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        username = data.get('username')
        password = data.get('password')
        user_type = data.get('userType')

        if not username or not password:
            return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400

        user = None
        role = None

        # 1. 如果前端明确指定了 userType，则只查询对应的表
        if user_type == 'doctor':
            user = Doctor.query.filter_by(username=username).first()
            if user and user.check_password(password):
                role = 'doctor'
        elif user_type == 'patient':
            user = Patient.query.filter_by(username=username).first()
            if user and user.check_password(password):
                role = 'patient'
        elif user_type == 'admin':
            # 假设管理员也存储在 doctor_info 表中，且 role 字段为 'admin'
            user = Doctor.query.filter_by(username=username).first()
            if user and user.check_password(password) and getattr(user, 'role', None) == 'admin':
                role = 'admin'
        else:
            # 2. 如果前端没有传 userType 或传了不认识的值，则自动查找（兼容旧前端）
            user = Doctor.query.filter_by(username=username).first()
            if user and user.check_password(password):
                role = 'doctor'
            else:
                user = Patient.query.filter_by(username=username).first()
                if user and user.check_password(password):
                    role = 'patient'
                # 注意：陪同人员(Escort)功能已移除，不再处理

        if not user or not role:
            return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401

        # 生成 JWT token
        access_token = create_access_token(
            identity=user.to_dict()['user_id'],
            additional_claims={
                'role': role,
                'username': username
            }
        )

        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'token': access_token,
                'user': user.to_dict()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'登录失败: {str(e)}'
        }), 500

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    患者/医生注册接口
    前端发送 JSON 格式：
    {
        "username": "zhangsan",
        "email": "zs@example.com",
        "password": "123456",
        "confirmPassword": "123456",
        "register-user-type": "patient"   // 或 "doctor"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirmPassword')
        user_type = data.get('register-user-type')

        if not all([username, email, password, confirm_password, user_type]):
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400

        if password != confirm_password:
            return jsonify({'code': 400, 'message': '两次输入的密码不一致'}), 400

        if user_type == 'patient':
            if Patient.query.filter_by(username=username).first():
                return jsonify({'code': 400, 'message': '用户名已存在'}), 400

            patient_id = generate_patient_id()
            new_patient = Patient(
                patient_id=patient_id,
                patient_name=username,
                gender='男',
                age=0,
                affected_side='左',
                stroke_type='缺血性',
                admission_time=datetime.now(),
                doctor_name='',
                phone='',
                remark='',
                username=username,
                pwd=password,
                doctor_id='',
                role='patient'
            )
            db.session.add(new_patient)
            db.session.commit()

            return jsonify({
                'code': 201,
                'message': '患者注册成功',
                'data': {
                    'patient_id': patient_id,
                    'username': username
                }
            }), 201

        elif user_type == 'doctor':
            if Doctor.query.filter_by(username=username).first():
                return jsonify({'code': 400, 'message': '用户名已存在'}), 400

            doctor_id = generate_doctor_id()
            new_doctor = Doctor(
                doctor_id=doctor_id,
                doctor_name=username,
                department='康复科',
                phone='',
                username=username,
                pwd=password,
                role='doctor'
            )
            db.session.add(new_doctor)
            db.session.commit()

            return jsonify({
                'code': 201,
                'message': '医生注册成功',
                'data': {
                    'doctor_id': doctor_id,
                    'username': username
                }
            }), 201

        else:
            return jsonify({'code': 400, 'message': '不支持的注册类型，请选择 patient 或 doctor'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'注册失败: {str(e)}'
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """返回当前登录用户的详细信息"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        role = claims.get('role')

        if role == 'patient':
            user = Patient.query.get(current_user_id)
        elif role == 'doctor':
            user = Doctor.query.get(current_user_id)
        else:
            # 移除了 companion 角色
            return jsonify({'code': 400, 'message': '未知角色'}), 400

        if not user:
            return jsonify({'code': 404, 'message': '用户不存在'}), 404

        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }), 500