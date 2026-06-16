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