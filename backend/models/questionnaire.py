"""
问卷数据模型
questionnaire_record - 问卷记录表
"""

from datetime import datetime
from extensions import db


class QuestionnaireRecord(db.Model):
    """问卷记录模型 - 存储患者问卷作答和难度匹配结果"""
    __tablename__ = 'questionnaire_record'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='记录ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')

    # 10道题的答案（A/B/C/D），用逗号分隔存储，如 "A,B,C,D,A,B,C,D,A,B"
    answers = db.Column(db.String(50), nullable=False, comment='作答结果(逗号分隔)')

    # 统计各选项数量
    count_a = db.Column(db.Integer, default=0, comment='A选项数量')
    count_b = db.Column(db.Integer, default=0, comment='B选项数量')
    count_c = db.Column(db.Integer, default=0, comment='C选项数量')
    count_d = db.Column(db.Integer, default=0, comment='D选项数量')

    # 难度匹配结果
    matched_level = db.Column(db.String(50), nullable=False, comment='匹配难度等级')
    matched_level_id = db.Column(db.Integer, comment='匹配关卡ID')

    # 时间
    submit_time = db.Column(db.DateTime, default=datetime.now, comment='提交时间')

    def to_dict(self):
        return {
            'record_id': self.record_id,
            'patient_id': self.patient_id,
            'answers': self.answers.split(',') if self.answers else [],
            'count_a': self.count_a,
            'count_b': self.count_b,
            'count_c': self.count_c,
            'count_d': self.count_d,
            'matched_level': self.matched_level,
            'matched_level_id': self.matched_level_id,
            'submit_time': self.submit_time.strftime('%Y-%m-%d %H:%M:%S') if self.submit_time else None
        }