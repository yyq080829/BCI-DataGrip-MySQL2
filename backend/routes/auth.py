"""
登录认证接口（蓝图 auth_bp，前缀 /api/auth）

本模块对接前端「康游智创(5).html」的登录/注册/找回密码页面，提供 4 个接口：
  · POST /api/auth/login           统一登录（自动判断患者/医生/管理员）
  · POST /api/auth/register         患者/医生注册（同时保存 email）
  · GET  /api/auth/profile          获取当前登录用户信息（需带 JWT）
  · POST /api/auth/forgot-password  找回密码第 1 步：按邮箱发验证码（开发期直接返回）
  · POST /api/auth/reset-password   找回密码第 2 步：校验验证码并重置密码

JWT 说明：
  登录成功后下发 access_token（24h 有效）。token 里记录了：
    - identity = 用户主键（patient_id 或 doctor_id）
    - claims.role = 角色；claims.username = 账号
  需要鉴权的接口用 @jwt_required() 后，通过 get_jwt_identity() / get_jwt() 取回。
"""

import logging
import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from models.user import Patient, Doctor   # 患者表 / 医生表（无陪同人员）
from extensions import db
from datetime import datetime

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


def generate_patient_id():
    """生成患者ID：格式为 年月日 + 三位当日序号，例如 20250515001。"""
    today = datetime.now().strftime('%Y%m%d')
    count = Patient.query.filter(Patient.patient_id.like(f'{today}%')).count()
    return f'{today}{count + 1:03d}'


def generate_doctor_id():
    """生成医生ID：DOC + 时间戳后6位 + 2 位随机数，保证不重复。"""
    import time
    suffix = str(int(time.time()))[-6:]
    rand = random.randint(10, 99)
    return f'DOC{suffix}{rand}'


@auth_bp.route('/login', methods=['POST'])
def login():
    """统一登录接口，支持患者、医生、管理员。前端 JSON 含 username/password/userType(可选)。"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        username = data.get('username')
        password = data.get('password')
        user_type = data.get('userType')   # 前端可选：doctor / patient / admin

        if not username or not password:
            return jsonify({'code': 400, 'message': '用户名和密码不能为空'}), 400

        user = None
        role = None

        # 1) 前端明确指定了角色，则只查对应表（更快、更准确）
        if user_type == 'doctor':
            user = Doctor.query.filter_by(username=username).first()
            if user and user.check_password(password):
                role = 'doctor'
        elif user_type == 'patient':
            user = Patient.query.filter_by(username=username).first()
            if user and user.check_password(password):
                role = 'patient'
        elif user_type == 'admin':
            # 管理员也存 doctor_info 表，role 字段标记为 'admin'
            user = Doctor.query.filter_by(username=username).first()
            if user and user.check_password(password) and getattr(user, 'role', None) == 'admin':
                role = 'admin'
        else:
            # 2) 前端没传 userType（兼容旧前端）：先试医生，再试患者
            user = Doctor.query.filter_by(username=username).first()
            if user and user.check_password(password):
                role = 'doctor'
            else:
                user = Patient.query.filter_by(username=username).first()
                if user and user.check_password(password):
                    role = 'patient'

        if not user or not role:
            return jsonify({'code': 401, 'message': '用户名或密码错误'}), 401

        # 签发 JWT：identity 用主键，claims 带上 role 和 username 供接口直接读取
        access_token = create_access_token(
            identity=user.to_dict()['user_id'],
            additional_claims={'role': role, 'username': username}
        )

        return jsonify({
            'code': 200,
            'message': '登录成功',
            'data': {
                'token': access_token,
                'user': user.to_dict()   # 前端读取 username / patient_id / doctor_id / role
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'登录失败: {str(e)}'}), 500


@auth_bp.route('/register', methods=['POST'])
def register():
    """患者/医生注册。前端 JSON 含 username/email/password/confirmPassword/register-user-type。"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        username = data.get('username')
        email = data.get('email')          # 保存邮箱，用于找回密码
        password = data.get('password')
        confirm_password = data.get('confirmPassword')
        user_type = data.get('register-user-type')   # patient 或 doctor

        if not all([username, email, password, confirm_password, user_type]):
            return jsonify({'code': 400, 'message': '缺少必要参数'}), 400
        if password != confirm_password:
            return jsonify({'code': 400, 'message': '两次输入的密码不一致'}), 400

        if user_type == 'patient':
            if Patient.query.filter_by(username=username).first():
                return jsonify({'code': 400, 'message': '用户名已存在'}), 400

            patient_id = generate_patient_id()
            # 备注：新患者用默认值（性别男/年龄0/患侧左）占位，后续由医生完善档案
            new_patient = Patient(
                patient_id=patient_id,
                patient_name=username,
                gender='男', age=0, affected_side='左', stroke_type='缺血性',
                admission_time=datetime.now(),
                doctor_name='', phone='',
                email=email,
                remark='',
                username=username,
                pwd=password,           # ⚠️ 明文存储，生产请改哈希
                doctor_id='',
                role='patient'
            )
            db.session.add(new_patient)
            db.session.commit()
            return jsonify({
                'code': 201, 'message': '患者注册成功',
                'data': {'patient_id': patient_id, 'username': username}
            }), 201

        elif user_type == 'doctor':
            if Doctor.query.filter_by(username=username).first():
                return jsonify({'code': 400, 'message': '用户名已存在'}), 400

            doctor_id = generate_doctor_id()
            new_doctor = Doctor(
                doctor_id=doctor_id,
                doctor_name=username,
                department='康复科', phone='',
                email=email,
                username=username,
                pwd=password,           # ⚠️ 明文存储，生产请改哈希
                role='doctor'
            )
            db.session.add(new_doctor)
            db.session.commit()
            return jsonify({
                'code': 201, 'message': '医生注册成功',
                'data': {'doctor_id': doctor_id, 'username': username}
            }), 201

        else:
            return jsonify({'code': 400, 'message': '不支持的注册类型，请选择 patient 或 doctor'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'注册失败: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()   # 必须带有效 JWT 才能访问
def get_profile():
    """返回当前登录用户的详细信息（按 JWT 里的 role 去对应表查）。"""
    try:
        current_user_id = get_jwt_identity()   # 登录时写入的主键
        claims = get_jwt()
        role = claims.get('role')

        if role == 'patient':
            user = Patient.query.get(current_user_id)
        elif role == 'doctor':
            user = Doctor.query.get(current_user_id)
        else:
            return jsonify({'code': 400, 'message': '未知角色'}), 400

        if not user:
            return jsonify({'code': 404, 'message': '用户不存在'}), 404

        return jsonify({'code': 200, 'message': '获取成功', 'data': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'code': 500, 'message': f'获取失败: {str(e)}'}), 500


# ================================================================
# 找回密码（开发版：验证码直接返回在响应里，生产请改为发送邮件）
# ================================================================
# 简单的内存验证码存储（key=email, value=code）。
# ⚠️ 仅适合开发调试：重启进程即丢失、多进程不共享。生产应改 Redis/数据库 + 邮件服务。
_reset_codes = {}


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """找回密码第 1 步：按邮箱生成 6 位验证码，开发期直接返回 dev_code。"""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        if not email:
            return jsonify({'code': 400, 'message': '缺少email'}), 400

        # 在患者表或医生表里查找该邮箱
        user = Patient.query.filter_by(email=email).first() or Doctor.query.filter_by(email=email).first()
        if not user:
            return jsonify({'code': 400, 'message': '该邮箱未注册'}), 400

        code = f'{random.randint(100000, 999999)}'
        _reset_codes[email] = code
        logger.info(f'[找回密码] 邮箱 {email} 验证码: {code}')

        return jsonify({
            'code': 200,
            'message': '验证码已发送（开发模式验证码见返回）',
            'data': {'dev_code': code}
        }), 200
    except Exception as e:
        return jsonify({'code': 500, 'message': f'发送失败: {str(e)}'}), 500


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """找回密码第 2 步：校验验证码并重置密码（明文写入，与注册一致）。"""
    try:
        data = request.get_json() or {}
        email = data.get('email')
        code = data.get('verificationCode')
        new_password = data.get('newPassword')

        if not all([email, code, new_password]):
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        if _reset_codes.get(email) != code:
            return jsonify({'code': 400, 'message': '验证码错误或已过期'}), 400

        user = Patient.query.filter_by(email=email).first() or Doctor.query.filter_by(email=email).first()
        if not user:
            return jsonify({'code': 400, 'message': '该邮箱未注册'}), 400

        user.pwd = new_password
        db.session.commit()
        _reset_codes.pop(email, None)   # 验证码用完即作废，防止重放
        return jsonify({'code': 200, 'message': '密码重置成功，请登录'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'重置失败: {str(e)}'}), 500
