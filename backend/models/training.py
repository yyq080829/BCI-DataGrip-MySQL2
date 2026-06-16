"""
训练与评估数据模型
train_real_time_data - 训练实时数据表
game_level_config - 游戏关卡配置表
stage_assessment - 阶段评估表 (新增补全)
"""

from datetime import datetime
from extensions import db


class GameLevel(db.Model):
    """游戏关卡配置模型"""
    __tablename__ = 'game_level_config'

    level_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='关卡ID')
    game_name = db.Column(db.String(50), nullable=False, comment='游戏名称')
    train_part = db.Column(db.String(30), nullable=False, comment='训练部位')
    level_name = db.Column(db.String(50), nullable=False, comment='关卡名称')
    target_angle = db.Column(db.Numeric(5, 2), nullable=False, comment='目标角度')
    angle_tolerance = db.Column(db.Numeric(5, 2), default=5.00, comment='角度容错')
    train_duration = db.Column(db.Integer, nullable=False, comment='训练时长(秒)')
    difficulty = db.Column(db.String(10), nullable=False, comment='难度等级')
    game_remark = db.Column(db.String(200), comment='关卡说明')

    def to_dict(self):
        return {
            'level_id': self.level_id,
            'game_name': self.game_name,
            'train_part': self.train_part,
            'level_name': self.level_name,
            'target_angle': float(self.target_angle) if self.target_angle else None,
            'angle_tolerance': float(self.angle_tolerance) if self.angle_tolerance else None,
            'train_duration': self.train_duration,
            'difficulty': self.difficulty,
            'game_remark': self.game_remark
        }


class TrainingData(db.Model):
    """训练实时数据模型"""
    __tablename__ = 'train_real_time_data'

    data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='数据ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    level_id = db.Column(db.Integer, db.ForeignKey('game_level_config.level_id'), nullable=False, comment='关卡ID')
    train_time = db.Column(db.DateTime, default=datetime.now, comment='训练时间')

    # 运动数据
    shoulder_abduction = db.Column(db.Numeric(5, 2), comment='肩外展角度')
    elbow_extension = db.Column(db.Numeric(5, 2), comment='肘伸展角度')
    forearm_rotation = db.Column(db.Numeric(5, 2), comment='前臂旋转角度')
    action_score = db.Column(db.Integer, default=0, comment='动作得分(0-10)')
    is_qualified = db.Column(db.Boolean, default=False, comment='是否达标')
    game_score = db.Column(db.Integer, default=0, comment='游戏累计得分')
    compensation = db.Column(db.String(50), comment='代偿动作类型')
    compensation_score = db.Column(db.Integer, default=100, comment='代偿评分')
    device_type = db.Column(db.String(30), default='AR手机', comment='采集设备')

    level = db.relationship('GameLevel', backref='training_data')

    def to_dict(self):
        return {
            'data_id': self.data_id,
            'patient_id': self.patient_id,
            'game_name': self.level.game_name if self.level else None,
            'level_name': self.level.level_name if self.level else None,
            'train_time': self.train_time.strftime('%Y-%m-%d %H:%M:%S') if self.train_time else None,
            'shoulder_abduction': float(self.shoulder_abduction) if self.shoulder_abduction else None,
            'elbow_extension': float(self.elbow_extension) if self.elbow_extension else None,
            'forearm_rotation': float(self.forearm_rotation) if self.forearm_rotation else None,
            'action_score': self.action_score,
            'is_qualified': self.is_qualified,
            'game_score': self.game_score,
            'compensation': self.compensation,
            'compensation_score': self.compensation_score
        }


class StageAssessment(db.Model):
    """阶段评估模型 (对应 stage_assessment 表)"""
    __tablename__ = 'stage_assessment'

    assess_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='评估ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')
    assess_time = db.Column(db.DateTime, default=datetime.now, comment='评估时间')
    assess_cycle = db.Column(db.String(20), nullable=False, comment='评估周期(如: 第1周)')

    # 角度 averages
    avg_shoulder_angle = db.Column(db.Numeric(5, 2), comment='平均肩外展角度')
    avg_elbow_angle = db.Column(db.Numeric(5, 2), comment='平均肘伸展角度')
    avg_forearm_angle = db.Column(db.Numeric(5, 2), comment='平均前臂旋转角度')

    # 评分指标
    qualified_rate = db.Column(db.Numeric(5, 2), comment='达标率(%)')
    avg_compensation_score = db.Column(db.Integer, comment='平均代偿评分')
    FMA_UE_score = db.Column(db.Integer, default=0, comment='FMA-UE评分')
    ARAT_score = db.Column(db.Integer, default=0, comment='ARAT评分')

    # 医生结论
    doctor_evaluation = db.Column(db.Text, comment='医生评价')
    next_train_plan = db.Column(db.Text, comment='下一步训练计划')

    def to_dict(self):
        return {
            'assess_id': self.assess_id,
            'patient_id': self.patient_id,
            'assess_time': self.assess_time.strftime('%Y-%m-%d %H:%M:%S') if self.assess_time else None,
            'assess_cycle': self.assess_cycle,
            'avg_shoulder_angle': float(self.avg_shoulder_angle) if self.avg_shoulder_angle else None,
            'avg_elbow_angle': float(self.avg_elbow_angle) if self.avg_elbow_angle else None,
            'avg_forearm_angle': float(self.avg_forearm_angle) if self.avg_forearm_angle else None,
            'qualified_rate': float(self.qualified_rate) if self.qualified_rate else None,
            'avg_compensation_score': self.avg_compensation_score,
            'FMA_UE_score': self.FMA_UE_score,
            'ARAT_score': self.ARAT_score,
            'doctor_evaluation': self.doctor_evaluation,
            'next_train_plan': self.next_train_plan
        }