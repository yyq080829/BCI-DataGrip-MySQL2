"""
用户模型 - 映射数据库中的用户表
patient_info  - 患者表
doctor_info   - 医生表
（escort_info 陪同人员表当前未建模，仅保留说明）

说明（新手看这里）：
  · 前端登录成功后会读取 result.data.user.username / patient_id / doctor_id / role，
    所以 Patient/Doctor 的 to_dict() 必须返回这些字段名（见下方实现），否则前端拿不到。
  · email 字段用于“找回密码”功能（/api/auth/forgot-password、/reset-password）。
  · pwd 当前是【明文】存储，仅限开发；上线前请改成 werkzeug 密码哈希。
"""

import json
from datetime import datetime
from extensions import db


def _parse_list(text):
    """把数据库里存的 JSON 数组文本还原成列表（康复进度序列等）。"""
    if not text:
        return []
    try:
        return json.loads(text)
    except Exception:
        return []


class Patient(db.Model):
    """患者模型 —— 对应 patient_info 表"""

    __tablename__ = 'patient_info'

    # ---- 基础信息 ----
    patient_id = db.Column(db.String(20), primary_key=True, comment='患者唯一标识（住院号/身份证后8位）')
    patient_name = db.Column(db.String(50), nullable=False, comment='患者姓名')
    gender = db.Column(db.String(1), nullable=False, comment='性别：男/女')
    age = db.Column(db.Integer, nullable=False, comment='年龄')
    affected_side = db.Column(db.String(2), nullable=False, comment='患侧：左/右')
    stroke_type = db.Column(db.String(30), nullable=False, comment='卒中类型：缺血性/出血性')
    admission_time = db.Column(db.DateTime, default=datetime.now, comment='入院/康复开始时间')
    doctor_name = db.Column(db.String(50), comment='主治医生姓名')
    phone = db.Column(db.String(20), comment='家属电话')
    email = db.Column(db.String(100), comment='邮箱（用于找回密码）')

    # ---- 登录相关 ----
    remark = db.Column(db.Text, comment='备注信息')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='登录账号（唯一）')
    pwd = db.Column(db.String(50), nullable=False, comment='登录密码（开发阶段明文，生产请改哈希）')
    doctor_id = db.Column(db.String(20), comment='主治医生ID（仅存储，非外键）')
    role = db.Column(db.String(20), default='patient', comment='角色标识：patient/doctor/admin')

    # ---- 临床康复摘要（新客户端 Kyouic 领域模型，对应 patientsData 字段）----
    diagnosis = db.Column(db.String(120), comment='诊断，如 脑梗死后遗症（右侧偏瘫）')
    brunnstrom_stage = db.Column(db.String(10), comment='Brunnstrom 分期：Ⅰ~Ⅵ')
    train_level = db.Column(db.String(10), default='初级', comment='训练等级：初级/中级/高级/精细')
    fm_score = db.Column(db.Integer, default=0, comment='Fugl-Meyer 上肢评分(0-66)')
    last_train = db.Column(db.Date, comment='最近训练日期')
    adherence = db.Column(db.Integer, default=0, comment='训练依从率(%)')
    first_visit = db.Column(db.Date, comment='初诊日期')
    recovery_progress = db.Column(db.Text, comment='康复进度序列(JSON 数组，如 [38,40,42,44,45])')
    game_train_count = db.Column(db.Integer, default=0, comment='游戏训练次数')

    # ---- 关联关系（ORM 自动关联训练/问卷记录）----
    trainings = db.relationship('TrainingData', backref='patient', lazy=True)
    questionnaires = db.relationship('QuestionnaireRecord', backref='patient', lazy=True)

    def check_password(self, password):
        """校验登录密码（当前为明文比较，后续建议改为 werkzeug 哈希）"""
        return self.pwd == password

    def to_dict(self):
        """序列化为 dict。

        注意：字段名必须与前端 login 读取的字段保持一致：
          前端读取 result.data.user.username / patient_id / doctor_id / role
        user_id 是给后端 JWT 用的内部标识（= patient_id）。
        """
        return {
            'user_id': self.patient_id,        # JWT 身份标识（后端内部使用）
            'patient_id': self.patient_id,     # ★ 前端读取
            'username': self.username,         # ★ 前端读取
            'patient_name': self.patient_name,
            'user_name': self.patient_name,
            'role': self.role or 'patient',    # ★ 前端读取
            'affected_side': self.affected_side,
            'doctor_name': self.doctor_name,
            'doctor_id': self.doctor_id,       # ★ 前端读取
            'email': self.email,
            # ---- 临床康复摘要（新客户端 Kyouic 领域模型）----
            'diagnosis': self.diagnosis,
            'brunnstrom_stage': self.brunnstrom_stage,
            'train_level': self.train_level or '初级',
            'fm_score': self.fm_score,
            'last_train': self.last_train.strftime('%Y-%m-%d') if self.last_train else None,
            'adherence': self.adherence,
            'first_visit': self.first_visit.strftime('%Y-%m-%d') if self.first_visit else None,
            'recovery_progress': _parse_list(self.recovery_progress),
            'game_train_count': self.game_train_count,
            'patientId': self.patient_id,       # ★ 客户端 localStorage 用 patientId
        }


class Doctor(db.Model):
    """医生模型 —— 对应 doctor_info 表"""

    __tablename__ = 'doctor_info'

    # ---- 基础信息 ----
    doctor_id = db.Column(db.String(20), primary_key=True, comment='医生ID（主键）')
    doctor_name = db.Column(db.String(50), nullable=False, comment='姓名')
    gender = db.Column(db.String(2), comment='性别')
    department = db.Column(db.String(50), comment='科室')

    # ---- 登录相关 ----
    phone = db.Column(db.String(20), comment='联系电话')
    email = db.Column(db.String(100), comment='邮箱（用于找回密码）')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='登录账号（唯一）')
    pwd = db.Column(db.String(50), nullable=False, comment='登录密码（开发阶段明文，生产请改哈希）')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    role = db.Column(db.String(20), default='doctor', comment='角色标识：doctor/admin')

    def check_password(self, password):
        """校验登录密码"""
        return self.pwd == password

    def to_dict(self):
        """序列化为 dict（字段名需与前端 login 读取的保持一致）"""
        return {
            'user_id': self.doctor_id,
            'doctor_id': self.doctor_id,       # ★ 前端读取
            'username': self.username,         # ★ 前端读取
            'doctor_name': self.doctor_name,
            'user_name': self.doctor_name,
            'role': self.role or 'doctor',     # ★ 前端读取
            'department': self.department,
            'email': self.email,
        }


# 注意：Escort（陪同人员）模型已删除，若以后需要可参考 patient_info 自行补回。
