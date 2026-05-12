def init_models():
    """延迟导入所有模型"""
    from models.user import Patient, Doctor, Escort
    from models.training import TrainingData, GameLevel
    from models.bci_data import BCIData
    from models.assessment import StageAssessment
    return {
        'Patient': Patient,
        'Doctor': Doctor,
        'Escort': Escort,
        'TrainingData': TrainingData,
        'GameLevel': GameLevel,
        'BCIData': BCIData,
        'StageAssessment': StageAssessment
    }