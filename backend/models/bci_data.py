"""
脑电数据模型 - 存储HybridBCI平台推送的脑电数据
注意：这个表需要创建
"""

from datetime import datetime
from extensions import db

class BCIData(db.Model):
    """脑电数据存储表"""
    __tablename__ = 'bci_data'

    # 主键
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # 关联患者
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'),
                           nullable=False, comment='患者ID')

    # 时间戳
    timestamp = db.Column(db.DateTime, default=datetime.now, comment='数据接收时间')

    # 脑电频段功率（HybridBCI推送的核心数据）
    delta_power = db.Column(db.Float, comment='Delta波功率(0.5-4Hz)')
    theta_power = db.Column(db.Float, comment='Theta波功率(4-8Hz)')
    alpha_power = db.Column(db.Float, comment='Alpha波功率(8-13Hz)')
    beta_power = db.Column(db.Float, comment='Beta波功率(13-30Hz)')
    gamma_power = db.Column(db.Float, comment='Gamma波功率(30-50Hz)')

    # 注意力相关指标
    attention = db.Column(db.Float, comment='注意力指数(0-100)')
    meditation = db.Column(db.Float, comment='放松度指数(0-100)')

    # 信号质量
    signal_quality = db.Column(db.Integer, comment='信号质量(0-100)')

    # 原始数据摘要（不存完整原始数据，只存关键统计值）
    raw_mean = db.Column(db.Float, comment='原始数据均值')
    raw_std = db.Column(db.Float, comment='原始数据标准差')

    # 设备信息
    device_id = db.Column(db.String(50), comment='脑电设备ID')

    def to_dict(self):
        """转为字典"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f') if self.timestamp else None,
            'delta_power': self.delta_power,
            'theta_power': self.theta_power,
            'alpha_power': self.alpha_power,
            'beta_power': self.beta_power,
            'gamma_power': self.gamma_power,
            'attention': self.attention,
            'meditation': self.meditation,
            'signal_quality': self.signal_quality
        }