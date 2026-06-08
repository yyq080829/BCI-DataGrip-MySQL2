"""
用户模型 - 映射数据库中的三张用户表
patient_info  - 患者表
doctor_info   - 医生表
escort_info   - 陪同人员表
"""

from datetime import datetime
from extensions import db


class Patient(db.Model):
    """患者模型"""
    __tablename__ = 'patient_info'

    patient_id = db.Column(db.String(20), primary_key=True, comment='患者唯一标识')
    patient_name = db.Column(db.String(50), nullable=False, comment='患者姓名')
    gender = db.Column(db.String(1), nullable=False, comment='性别')
    age = db.Column(db.Integer, nullable=False, comment='年龄')
    affected_side = db.Column(db.String(2), nullable=False, comment='患侧')
    stroke_type = db.Column(db.String(30), nullable=False, comment='卒中类型')
    admission_time = db.Column(db.DateTime, default=datetime.now, comment='入院时间')
    doctor_name = db.Column(db.String(50), comment='主治医生姓名')
    phone = db.Column(db.String(20), comment='联系电话')
    remark = db.Column(db.Text, comment='备注信息')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='登录账号')
    pwd = db.Column(db.String(50), comment='登录密码')
    doctor_id = db.Column(db.String(20), comment='主治医生ID')
    role = db.Column(db.String(20), default='patient', comment='角色标识')

    trainings = db.relationship('TrainingData', backref='patient', lazy=True)

    def check_password(self, password):
        return self.pwd == password

    def to_dict(self):
        return {
            'user_id': self.patient_id,
            'user_name': self.patient_name,
            'role': 'patient',
            'affected_side': self.affected_side
        }


class Doctor(db.Model):
    """医生模型"""
    __tablename__ = 'doctor_info'

    doctor_id = db.Column(db.String(20), primary_key=True, comment='医生ID')
    doctor_name = db.Column(db.String(50), nullable=False, comment='姓名')
    department = db.Column(db.String(50), comment='科室')
    phone = db.Column(db.String(20), comment='联系电话')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='登录账号')
    pwd = db.Column(db.String(50), comment='登录密码')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    role = db.Column(db.String(20), default='doctor', comment='角色标识')

    def check_password(self, password):
        return self.pwd == password

    def to_dict(self):
        return {
            'user_id': self.doctor_id,
            'user_name': self.doctor_name,
            'role': 'doctor',
            'department': self.department
        }


class Escort(db.Model):
    """陪同人员模型"""
    __tablename__ = 'escort_info'

    escort_id = db.Column(db.String(20), primary_key=True, comment='陪同人员ID')
    escort_name = db.Column(db.String(50), nullable=False, comment='姓名')
    gender = db.Column(db.String(2), comment='性别')
    relation = db.Column(db.String(30), comment='与患者关系')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), comment='关联患者ID')
    phone = db.Column(db.String(20), comment='手机号')
    username = db.Column(db.String(50), unique=True, nullable=False, comment='登录账号')
    pwd = db.Column(db.String(50), nullable=False, comment='登录密码')
    create_time = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    role = db.Column(db.String(20), default='companion', comment='角色标识')

    def check_password(self, password):
        return self.pwd == password

    def to_dict(self):
        return {
            'user_id': self.escort_id,
            'user_name': self.escort_name,
            'role': 'companion',
            'relation': self.relation,
            'patient_id': self.patient_id
        }
