from flask import Blueprint, jsonify
from models.assessment_question import Question, Questionnaire

assessment_bp = Blueprint('assessment', __name__, url_prefix='/api/assessment')


@assessment_bp.route('/questions', methods=['GET'])
def get_questions():
    """获取当前激活的问卷的所有问题"""
    active_q = Questionnaire.query.filter_by(is_active=True).first()
    if not active_q:
        return jsonify({'code': 404, 'message': '没有找到激活的问卷'}), 404

    questions = Question.query.filter_by(questionnaire_id=active_q.id).order_by(Question.sort_order).all()
    result = [{'question': q.question_text, 'options': q.options} for q in questions]
    return jsonify({'code': 200, 'data': result}), 200