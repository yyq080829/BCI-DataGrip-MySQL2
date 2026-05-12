"""
阶段评估数据模型
stage_assessment - 阶段临床评估数据表
"""

from datetime import datetime
from extensions import db

class StageAssessment(db.Model):
    """阶段临床评估模型"""
    __tablename__ = 'stage_assessment'

    assess_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='评估ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'),
                           nullable=False, comment='患者ID')
    assess_time = db.Column(db.DateTime, default=datetime.now, comment='评估时间')
    assess_cycle = db.Column(db.String(20), nullable=False, comment='评估周期')
    avg_shoulder_angle = db.Column(db.Numeric(5, 2), comment='平均肩外展角度')
    avg_elbow_angle = db.Column(db.Numeric(5, 2), comment='平均肘伸展角度')
    avg_forearm_angle = db.Column(db.Numeric(5, 2), comment='平均前臂旋转角度')
    qualified_rate = db.Column(db.Numeric(5, 2), comment='动作达标率(%)')
    avg_compensation_score = db.Column(db.Integer, comment='平均代偿评分')
    FMA_UE_score = db.Column(db.Integer, default=0, comment='FMA上肢量表评分')
    ARAT_score = db.Column(db.Integer, default=0, comment='ARAT上肢功能评分')
    doctor_evaluation = db.Column(db.Text, comment='医生评估意见')
    next_train_plan = db.Column(db.Text, comment='后续训练计划')

    def to_dict(self):
        return {
            'assess_id': self.assess_id,
            'patient_id': self.patient_id,
            'assess_time': self.assess_time.strftime('%Y-%m-%d %H:%M:%S') if self.assess_time else None,
            'assess_cycle': self.assess_cycle,
            'avg_shoulder_angle': float(self.avg_shoulder_angle) if self.avg_shoulder_angle else None,
            'qualified_rate': float(self.qualified_rate) if self.qualified_rate else None,
            'FMA_UE_score': self.FMA_UE_score,
            'ARAT_score': self.ARAT_score,
            'doctor_evaluation': self.doctor_evaluation
        }