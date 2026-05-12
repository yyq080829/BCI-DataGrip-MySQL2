"""
训练数据模型
train_real_time_data - 训练实时数据表
game_level_config - 游戏关卡配置表
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
            'target_angle': float(self.target_angle),
            'angle_tolerance': float(self.angle_tolerance),
            'train_duration': self.train_duration,
            'difficulty': self.difficulty,
            'game_remark': self.game_remark
        }


class TrainingData(db.Model):
    """训练实时数据模型"""
    __tablename__ = 'train_real_time_data'

    # 主键和关联字段
    data_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True, comment='数据ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'),
                           nullable=False, comment='患者ID')
    level_id = db.Column(db.Integer, db.ForeignKey('game_level_config.level_id'),
                         nullable=False, comment='关卡ID')

    # 时间戳
    train_time = db.Column(db.DateTime, default=datetime.now, comment='训练时间')

    # 关节角度数据（MediaPipe采集）
    shoulder_abduction = db.Column(db.Numeric(5, 2), comment='肩外展角度')
    elbow_extension = db.Column(db.Numeric(5, 2), comment='肘伸展角度')
    forearm_rotation = db.Column(db.Numeric(5, 2), comment='前臂旋转角度')

    # 评分数据
    action_score = db.Column(db.Integer, default=0, comment='动作得分(0-10)')
    is_qualified = db.Column(db.Boolean, default=False, comment='是否达标')
    game_score = db.Column(db.Integer, default=0, comment='游戏累计得分')

    # 代偿检测
    compensation = db.Column(db.String(50), comment='代偿动作类型')
    compensation_score = db.Column(db.Integer, default=100, comment='代偿评分')

    # 其他
    device_type = db.Column(db.String(30), default='AR手机', comment='采集设备')

    # 关联关系（可通过training.level获取关卡信息）
    level = db.relationship('GameLevel', backref='training_data')

    def to_dict(self):
        """转为字典格式返回给前端"""
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