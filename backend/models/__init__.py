def init_models():
    """延迟导入所有模型"""
    from models.user import Patient, Doctor, Escort
    from models.training import TrainingData, GameLevel
    from models.questionnaire import QuestionnaireRecord
    return {
        'Patient': Patient,
        'Doctor': Doctor,
        'Escort': Escort,
        'TrainingData': TrainingData,
        'GameLevel': GameLevel,
        'QuestionnaireRecord': QuestionnaireRecord
    }