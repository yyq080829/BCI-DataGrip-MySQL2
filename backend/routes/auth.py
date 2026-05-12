# 登录认证接口
"""
POST /api/auth/register  - 患者注册
POST /api/auth/login     - 统一登录（患者/医生/陪同人员）
GET  /api/auth/profile   - 获取个人信息（需要JWT认证）
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from models.user import Patient, Doctor, Escort
from extensions import db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    患者注册接口
    请求示例：
    {
        "patient_name": "王五",
        "gender": "男",
        "age": 62,
        "affected_side": "左",
        "stroke_type": "缺血性",
        "username": "patient_wangwu",
        "password": "Wang123456!",
        "phone": "13800138003",
        "doctor_id": "DOC2025001"
    }
    """
    try:
        data = request.get_json()

        # 1. 验证必填字段
        required_fields = ['patient_name', 'gender', 'age', 'affected_side',
                           'stroke_type', 'username', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必填字段: {field}'
                }), 400

        # 2. 检查用户名是否已存在（患者表）
        if Patient.query.filter_by(username=data['username']).first():
            return jsonify({
                'code': 400,
                'message': '该用户名已被注册'
            }), 400

        # 3. 生成患者ID（格式：自动生成年月日+序号）
        today = datetime.now().strftime('%Y%m%d')
        # 查询今天已注册的患者数量
        count = Patient.query.filter(Patient.patient_id.like(f'{today}%')).count()
        patient_id = f'{today}{count + 1:03d}'

        # 如果前端传了patient_id，使用前端的
        if 'patient_id' in data and data['patient_id']:
            # 检查ID是否已存在
            if Patient.query.get(data['patient_id']):
                return jsonify({
                    'code': 400,
                    'message': '患者ID已存在'
                }), 400
            patient_id = data['patient_id']

        # 4. 创建患者记录
        new_patient = Patient(
            patient_id=patient_id,
            patient_name=data['patient_name'],
            gender=data['gender'],
            age=data['age'],
            affected_side=data['affected_side'],
            stroke_type=data['stroke_type'],
            username=data['username'],
            pwd=data['password'],
            phone=data.get('phone', ''),
            doctor_name=data.get('doctor_name', ''),
            doctor_id=data.get('doctor_id', ''),
            remark=data.get('remark', ''),
            admission_time=datetime.now(),
            role='patient'
        )

        # 5. 保存到数据库
        db.session.add(new_patient)
        db.session.commit()

        # 6. 返回成功信息
        return jsonify({
            'code': 201,
            'message': '注册成功',
            'data': {
                'patient_id': patient_id,
                'patient_name': data['patient_name'],
                'username': data['username']
            }
        }), 201

    except Exception as e:
        # 数据库错误回滚
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'注册失败: {str(e)}'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    统一登录接口 - 支持患者、医生、陪同人员
    请求示例：
    {
        "username": "patient_zhangsan",
        "password": "Zhang123456!",
        "role": "patient"  // 可选，不传则自动识别
    }

    返回示例：
    {
        "code": 200,
        "message": "登录成功",
        "data": {
            "token": "eyJhbGciOi...",
            "user": {
                "user_id": "202505001",
                "user_name": "张三",
                "role": "patient",
                "gender": "男",
                "age": 58,
                "affected_side": "右",
                "stroke_type": "缺血性",
                "doctor_name": "李医生"
            }
        }
    }
    """
    try:
        data = request.get_json()

        # 1. 验证必填字段
        if 'username' not in data or 'password' not in data:
            return jsonify({
                'code': 400,
                'message': '缺少用户名或密码'
            }), 400

        username = data['username']
        password = data['password']
        role_hint = data.get('role', '')

        user = None
        user_role = None

        # 2. 按角色顺序查找用户（如果指定了角色，只查该角色）

        # 2.1 尝试医生登录
        if not role_hint or role_hint == 'doctor':
            doctor = Doctor.query.filter_by(username=username).first()
            if doctor and doctor.check_password(password):
                user = doctor
                user_role = 'doctor'

        # 2.2 尝试患者登录
        if not user and (not role_hint or role_hint == 'patient'):
            patient = Patient.query.filter_by(username=username).first()
            if patient and patient.check_password(password):
                user = patient
                user_role = 'patient'

        # 2.3 尝试陪同人员登录
        if not user and (not role_hint or role_hint == 'companion'):
            escort = Escort.query.filter_by(username=username).first()
            if escort and escort.check_password(password):
                user = escort
                user_role = 'companion'

        # 3. 登录失败
        if not user:
            return jsonify({
                'code': 401,
                'message': '用户名或密码错误'
            }), 401

        # 4. 生成JWT Token（包含用户ID和角色信息）
        access_token = create_access_token(
            identity=user.to_dict()['user_id'],
            additional_claims={
                'role': user_role,
                'username': username
            }
        )

        # 5. 返回登录成功信息
        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'token': access_token,
                'user': user.to_dict()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'登录失败: {str(e)}'
        }), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()  # 需要JWT认证
def get_profile():
    """
    获取当前登录用户信息
    请求头：Authorization: Bearer <token>
    """
    try:
        # 从JWT中获取用户ID和角色
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        role = claims.get('role')

        # 根据角色查询对应的表
        if role == 'patient':
            user = Patient.query.get(current_user_id)
        elif role == 'doctor':
            user = Doctor.query.get(current_user_id)
        elif role == 'companion':
            user = Escort.query.get(current_user_id)
        else:
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