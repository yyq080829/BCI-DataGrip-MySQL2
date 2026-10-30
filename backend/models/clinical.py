"""
临床康复领域模型（新客户端 Kyouic 领域模型）

对应新客户端 app/index.html 的数据结构：
  · scale_assessment     量表评分历史（Fugl-Meyer / Brunnstrom / Barthel / MBI / MMSE）
  · clinical_assessment  10 题临床评估（每题 0-4 分）→ 康复等级（对应 assessmentQuestions + submitAssess）
  · training_record      训练记录（会话级，对应 trainingRecords：time/patient/level/game/dur/result）
  · eeg_session          脑电会话数据（对应 EEG demo 格式：session/alpha/beta/smr/theta/delta/erd/accuracy/attention/relaxation）
  · doctor_advice        医生建议（对应 doctorAdvices / submitAdvice）

这些表由后端启动时 db.create_all() 自动创建；改表结构改这里，并同步 sql_files/。
"""

from datetime import datetime, date
from extensions import db


class ScaleAssessment(db.Model):
    """量表评分记录 —— 对应 scale_assessment 表（患者各量表评分历史）。"""

    __tablename__ = 'scale_assessment'

    assess_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='评估ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    assess_date = db.Column(db.Date, default=date.today, comment='评估日期')
    scale_key = db.Column(db.String(20), nullable=False, comment='量表key: fugl-meyer/brunnstorm/barthel/adl/mmse')
    scale_name = db.Column(db.String(50), comment='量表显示名，如 Fugl-Meyer')
    score_text = db.Column(db.String(30), comment='评分文本，如 38/100 或 III期')
    result_text = db.Column(db.String(50), comment='结果描述，如 明显运动障碍')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'assess_id': self.assess_id,
            'patient_id': self.patient_id,
            'assess_date': self.assess_date.strftime('%Y-%m-%d') if self.assess_date else None,
            'scale_key': self.scale_key,
            'scale_name': self.scale_name,
            'score_text': self.score_text,
            'result_text': self.result_text,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class ClinicalAssessment(db.Model):
    """临床评估记录 —— 对应 clinical_assessment 表（10 题 0-4 分问卷）。"""

    __tablename__ = 'clinical_assessment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='记录ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    answers = db.Column(db.String(50), nullable=False, comment='10题作答(0-4)，逗号分隔')
    total_score = db.Column(db.Integer, default=0, comment='总分(0-40)')
    mapped_level = db.Column(db.String(10), comment='康复等级：初级/中级/高级/精细')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='提交时间')

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'answers': [int(x) for x in self.answers.split(',') if x != ''] if self.answers else [],
            'total_score': self.total_score,
            'mapped_level': self.mapped_level,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class TrainingRecord(db.Model):
    """训练记录（会话级）—— 对应 training_record 表（客户端 trainingRecords）。"""

    __tablename__ = 'training_record'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='记录ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    patient_name = db.Column(db.String(50), comment='患者姓名')
    level = db.Column(db.String(10), comment='训练等级：初级/中级/高级/精细')
    game_name = db.Column(db.String(50), comment='游戏名，如 星际翼航')
    duration_min = db.Column(db.Integer, default=0, comment='训练时长(分钟)')
    result_text = db.Column(db.String(200), comment='训练结果描述')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'record_id': self.record_id,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'level': self.level,
            'game_name': self.game_name,
            'duration_min': self.duration_min,
            'result_text': self.result_text,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class EegSession(db.Model):
    """脑电会话数据 —— 对应 eeg_session 表（客户端 EEG demo 格式）。"""

    __tablename__ = 'eeg_session'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='记录ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    session_no = db.Column(db.Integer, default=0, comment='会话序号')
    alpha = db.Column(db.Numeric(6, 2), default=0, comment='α波')
    beta = db.Column(db.Numeric(6, 2), default=0, comment='β波')
    smr = db.Column(db.Numeric(6, 2), default=0, comment='SMR感觉运动节律(12-15Hz)')
    theta = db.Column(db.Numeric(6, 2), default=0, comment='θ波')
    delta = db.Column(db.Numeric(6, 2), default=0, comment='δ波')
    erd = db.Column(db.Numeric(6, 2), default=0, comment='ERD事件相关去同步(%)')
    accuracy = db.Column(db.Numeric(6, 2), default=0, comment='游戏准确率(%)')
    attention = db.Column(db.Numeric(6, 2), default=0, comment='专注度')
    relaxation = db.Column(db.Numeric(6, 2), default=0, comment='放松度')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        def f(v):
            return float(v) if v is not None else 0
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'session_no': self.session_no,
            'alpha': f(self.alpha), 'beta': f(self.beta), 'smr': f(self.smr),
            'theta': f(self.theta), 'delta': f(self.delta), 'erd': f(self.erd),
            'accuracy': f(self.accuracy), 'attention': f(self.attention), 'relaxation': f(self.relaxation),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class DoctorAdvice(db.Model):
    """医生建议 —— 对应 doctor_advice 表（客户端 doctorAdvices / submitAdvice）。"""

    __tablename__ = 'doctor_advice'

    advice_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='建议ID')
    doctor_id = db.Column(db.String(20), comment='医生ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    patient_name = db.Column(db.String(50), comment='患者姓名')
    advice_text = db.Column(db.Text, nullable=False, comment='建议内容')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')

    def to_dict(self):
        return {
            'advice_id': self.advice_id,
            'doctor_id': self.doctor_id,
            'patient_id': self.patient_id,
            'patient_name': self.patient_name,
            'advice_text': self.advice_text,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }
