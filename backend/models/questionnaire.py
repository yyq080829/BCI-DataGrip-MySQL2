"""
问卷数据模型 —— 对应 questionnaire_record 表

作用：保存患者填写的《康复游戏登录问卷》作答结果，以及根据答案匹配出的训练难度。
题目本身（10 道题）硬编码在 routes/questionnaire.py 的 QUESTIONNAIRE_DATA 里，
同时在 sql_files/questionnaire.sql 里也有一份模板表（questionnaire / question）。

注意：questionnaire_record 这张表【没有】对应的 .sql 文件，完全由 ORM 自动建表。
"""

from datetime import datetime
from extensions import db


class QuestionnaireRecord(db.Model):
    """问卷记录模型 - 存储患者问卷作答和难度匹配结果"""

    __tablename__ = 'questionnaire_record'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='记录ID')
    patient_id = db.Column(db.String(20), db.ForeignKey('patient_info.patient_id'), nullable=False, comment='患者ID')

    # 10 道题的答案（A/B/C/D），用逗号分隔存储，如 "A,B,C,D,A,B,C,D,A,B"
    answers = db.Column(db.String(50), nullable=False, comment='作答结果(逗号分隔)')

    # 统计各选项数量（方便医生/算法快速看分布，不必每次再数）
    count_a = db.Column(db.Integer, default=0, comment='A选项数量')
    count_b = db.Column(db.Integer, default=0, comment='B选项数量')
    count_c = db.Column(db.Integer, default=0, comment='C选项数量')
    count_d = db.Column(db.Integer, default=0, comment='D选项数量')

    # 难度匹配结果（由 routes/questionnaire.py 的 calculate_difficulty 算出）
    matched_level = db.Column(db.String(50), nullable=False, comment='匹配难度等级（初阶关/中阶关/高阶关）')
    matched_level_id = db.Column(db.Integer, comment='匹配关卡ID（对应 game_level_config.level_id）')

    submit_time = db.Column(db.DateTime, default=datetime.now, comment='提交时间')

    def to_dict(self):
        """转 dict（answers 还原成列表，方便前端直接用）"""
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
