"""
模型包初始化

作用：提供一个 `init_models()` 把本项目所有 ORM 模型集中导入并返回字典。
这样在其他地方想“拿到所有表”时（比如建表、打印表名）一行就能拿到，
而不用到处 `from models.user import ...`。

注意：app.py 实际是用 `import models.user` 等方式直接导入来触发建表，
这个 init_models 更多是一个“模型清单”工具函数。
"""


def init_models():
    """延迟导入所有模型，确保 Flask-SQLAlchemy 能识别所有表"""
    from models.user import Patient, Doctor
    from models.training import TrainingData, GameLevel, StageAssessment
    from models.questionnaire import QuestionnaireRecord

    return {
        'Patient': Patient,
        'Doctor': Doctor,
        'TrainingData': TrainingData,
        'GameLevel': GameLevel,
        'StageAssessment': StageAssessment,
        'QuestionnaireRecord': QuestionnaireRecord
    }
