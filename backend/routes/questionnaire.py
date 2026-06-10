"""
问卷接口
GET  /api/questionnaire/questions      - 获取问卷题目
POST /api/questionnaire/submit         - 提交问卷作答
GET  /api/questionnaire/history        - 查询问卷历史
GET  /api/questionnaire/latest         - 获取最新问卷结果
POST /api/questionnaire/retest         - 重新测评

难度匹配规则:
  初阶关（Ⅰ-Ⅱ 期）：A/B 累计 ≥ 7 题
  中阶关（Ⅲ 期）：C 累计 ≥ 4 题 且 A/B ≤ 5 题
  高阶关（Ⅳ-Ⅵ 期）：D 累计 ≥ 4 题 且 A/B ≤ 3 题
"""

from flask import Blueprint, request, jsonify
from models.questionnaire import QuestionnaireRecord
from models.training import GameLevel
from extensions import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

questionnaire_bp = Blueprint('questionnaire', __name__, url_prefix='/api/questionnaire')


# ================================================================
# 问卷题目数据（硬编码，与文档完全一致）
# ================================================================
QUESTIONNAIRE_DATA = {
    "title": "康复游戏登录问卷",
    "description": "亲爱的用户，为了给你匹配最安全、最适合的《星光舞台》训练难度，"
                   "请根据你当前上肢真实情况作答（共10题，单选，约1分钟完成）。"
                   "答案仅用于关卡适配，严格保护隐私。"
                   "康复进步后可在「个人中心-问卷测试」重新测评。",
    "questions": [
        {
            "id": 1,
            "text": "你能自主完成 前臂旋前（掌心向下）、旋后（掌心向上） 动作吗？",
            "options": [
                {"label": "A", "text": "完全转不动，需他人帮助"},
                {"label": "B", "text": "能转一点，幅度很小"},
                {"label": "C", "text": "能转到标准位置，基本稳定"},
                {"label": "D", "text": "能快速翻转，动作灵活顺畅"}
            ]
        },
        {
            "id": 2,
            "text": "手掌向上转、向下转切换时，是否顺畅？",
            "options": [
                {"label": "A", "text": "完全不顺畅，经常卡住"},
                {"label": "B", "text": "偶尔卡顿，切换缓慢"},
                {"label": "C", "text": "切换顺畅，无明显停顿"},
                {"label": "D", "text": "切换快速，连续不失误"}
            ]
        },
        {
            "id": 3,
            "text": "转动前臂时，小臂是否晃动、偏移？",
            "options": [
                {"label": "A", "text": "晃动严重，控制不住"},
                {"label": "B", "text": "偶尔晃动，方向不准"},
                {"label": "C", "text": "基本稳定，轻微晃动"},
                {"label": "D", "text": "完全稳定，不晃不偏"}
            ]
        },
        {
            "id": 4,
            "text": "做手掌翻转动作时，是否出现耸肩、抬臂、代偿？",
            "options": [
                {"label": "A", "text": "经常代偿，无法控制"},
                {"label": "B", "text": "偶尔代偿，姿势变形"},
                {"label": "C", "text": "很少代偿，姿势基本标准"},
                {"label": "D", "text": "不会代偿，姿势规范"}
            ]
        },
        {
            "id": 5,
            "text": "前臂转动时，是否有疼痛、酸胀、疲劳？",
            "options": [
                {"label": "A", "text": "一动就疼，无法坚持"},
                {"label": "B", "text": "轻微酸胀，能坚持1-3分钟"},
                {"label": "C", "text": "无疼痛，能坚持5分钟左右"},
                {"label": "D", "text": "完全舒适，可坚持8分钟以上"}
            ]
        },
        {
            "id": 6,
            "text": "你能按节奏完成手掌翻转吗？",
            "options": [
                {"label": "A", "text": "跟不上任何节奏"},
                {"label": "B", "text": "能慢节奏，经常出错"},
                {"label": "C", "text": "能跟中等节奏，较少出错"},
                {"label": "D", "text": "能跟快节奏，准确稳定"}
            ]
        },
        {
            "id": 7,
            "text": "单手保持掌心朝上/朝下，能稳定不动多久？",
            "options": [
                {"label": "A", "text": "完全稳不住"},
                {"label": "B", "text": "不到1秒"},
                {"label": "C", "text": "1秒左右，基本稳定"},
                {"label": "D", "text": "2秒以上，非常稳定"}
            ]
        },
        {
            "id": 8,
            "text": "做动作时，手腕是否用力过度、僵硬？",
            "options": [
                {"label": "A", "text": "非常僵硬，用力失控"},
                {"label": "B", "text": "偶尔僵硬，需刻意放松"},
                {"label": "C", "text": "基本自然，用力适中"},
                {"label": "D", "text": "完全放松，控制自如"}
            ]
        },
        {
            "id": 9,
            "text": "日常拧瓶盖、翻书、握笔、端碗等动作是否顺畅？",
            "options": [
                {"label": "A", "text": "完全不能，需人帮助"},
                {"label": "B", "text": "勉强完成，笨拙缓慢"},
                {"label": "C", "text": "基本独立，效率一般"},
                {"label": "D", "text": "轻松完成，灵活快速"}
            ]
        },
        {
            "id": 10,
            "text": "你更适合的训练节奏是？",
            "options": [
                {"label": "A", "text": "极慢、辅助为主、安全第一"},
                {"label": "B", "text": "较慢、温和练习、少量重复"},
                {"label": "C", "text": "中等节奏、稳定训练、适度挑战"},
                {"label": "D", "text": "较快节奏、精准强化、高效练习"}
            ]
        }
    ]
}


# ================================================================
# 难度匹配算法
# ================================================================
def calculate_difficulty(answers: list) -> dict:
    """
    根据问卷答案计算匹配难度

    规则:
      初阶关（Ⅰ-Ⅱ 期）：A/B 累计 ≥ 7 题
      中阶关（Ⅲ 期）：C 累计 ≥ 4 题 且 A/B ≤ 5 题
      高阶关（Ⅳ-Ⅵ 期）：D 累计 ≥ 4 题 且 A/B ≤ 3 题
      默认：中阶关

    返回:
      {
          "matched_level": "初阶关",
          "matched_level_id": 1,
          "count_a": 3, "count_b": 4, "count_c": 2, "count_d": 1,
          "ab_count": 7, "description": "..."
      }
    """
    count_a = answers.count('A')
    count_b = answers.count('B')
    count_c = answers.count('C')
    count_d = answers.count('D')
    ab_count = count_a + count_b

    # 匹配规则（按优先级从高到低）
    if ab_count >= 7:
        matched_level = "初阶关"
        description = "A/B累计≥7题，建议从初级难度开始，安全第一"
    elif count_d >= 4 and ab_count <= 3:
        matched_level = "高阶关"
        description = "D累计≥4题且A/B≤3题，可以挑战高级难度"
    elif count_c >= 4 and ab_count <= 5:
        matched_level = "中阶关"
        description = "C累计≥4题且A/B≤5题，适合中等难度训练"
    else:
        # 默认中阶关
        matched_level = "中阶关"
        description = "综合评估，建议中等难度训练"

    # 查找匹配的关卡ID
    level = GameLevel.query.filter_by(difficulty=matched_level).first()
    matched_level_id = level.level_id if level else None

    return {
        "matched_level": matched_level,
        "matched_level_id": matched_level_id,
        "count_a": count_a,
        "count_b": count_b,
        "count_c": count_c,
        "count_d": count_d,
        "ab_count": ab_count,
        "description": description
    }


# ================================================================
# API 路由
# ================================================================
@questionnaire_bp.route('/questions', methods=['GET'])
def get_questions():
    """
    获取问卷题目

    返回:
    {
        "code": 200,
        "data": {
            "title": "康复游戏登录问卷",
            "description": "...",
            "total_questions": 10,
            "questions": [...]
        }
    }
    """
    return jsonify({
        'code': 200,
        'data': {
            'title': QUESTIONNAIRE_DATA['title'],
            'description': QUESTIONNAIRE_DATA['description'],
            'total_questions': len(QUESTIONNAIRE_DATA['questions']),
            'questions': QUESTIONNAIRE_DATA['questions']
        }
    }), 200


@questionnaire_bp.route('/submit', methods=['POST'])
def submit_questionnaire():
    """
    提交问卷作答

    请求格式:
    {
        "patient_id": "202505001",
        "answers": ["A", "B", "C", "D", "A", "B", "C", "D", "A", "B"]
    }

    返回:
    {
        "code": 200,
        "data": {
            "matched_level": "初阶关",
            "matched_level_id": 1,
            "count_a": 3, "count_b": 4, "count_c": 2, "count_d": 1,
            "description": "...",
            "message": "问卷提交成功！已为你匹配【初阶关】难度"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'code': 400, 'message': '请求数据为空'}), 400

        patient_id = data.get('patient_id')
        answers = data.get('answers')

        if not patient_id:
            return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
        if not answers or not isinstance(answers, list):
            return jsonify({'code': 400, 'message': '缺少answers或格式错误'}), 400
        if len(answers) != 10:
            return jsonify({'code': 400, 'message': f'答案数量错误，需要10题，收到{len(answers)}题'}), 400

        # 验证答案格式
        valid_labels = {'A', 'B', 'C', 'D'}
        for i, ans in enumerate(answers):
            if ans not in valid_labels:
                return jsonify({'code': 400, 'message': f'第{i+1}题答案无效: {ans}，只支持A/B/C/D'}), 400

        # 计算难度匹配
        result = calculate_difficulty(answers)

        # 存储到数据库
        record = QuestionnaireRecord(
            patient_id=patient_id,
            answers=','.join(answers),
            count_a=result['count_a'],
            count_b=result['count_b'],
            count_c=result['count_c'],
            count_d=result['count_d'],
            matched_level=result['matched_level'],
            matched_level_id=result['matched_level_id']
        )
        db.session.add(record)
        db.session.commit()

        logger.info(f'[问卷] 患者{patient_id}提交问卷，匹配难度: {result["matched_level"]}')

        # 构造提示消息
        message = f"问卷提交成功！已为你匹配【{result['matched_level']}】难度，自动进入星光舞台。若难度不合适，可在训练中暂停调整，或前往「个人中心-问卷测试」重新测评。"

        return jsonify({
            'code': 200,
            'data': {
                'record_id': record.record_id,
                'matched_level': result['matched_level'],
                'matched_level_id': result['matched_level_id'],
                'count_a': result['count_a'],
                'count_b': result['count_b'],
                'count_c': result['count_c'],
                'count_d': result['count_d'],
                'ab_count': result['ab_count'],
                'description': result['description'],
                'message': message
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f'[问卷] 提交失败: {e}')
        return jsonify({'code': 500, 'message': f'提交失败: {str(e)}'}), 500


@questionnaire_bp.route('/history', methods=['GET'])
def get_history():
    """
    查询患者问卷历史

    请求参数: ?patient_id=202505001

    返回:
    {
        "code": 200,
        "data": {
            "total": 3,
            "records": [...]
        }
    }
    """
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify({'code': 400, 'message': '缺少patient_id参数'}), 400

    records = QuestionnaireRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(QuestionnaireRecord.submit_time.desc()).all()

    return jsonify({
        'code': 200,
        'data': {
            'total': len(records),
            'records': [r.to_dict() for r in records]
        }
    }), 200


@questionnaire_bp.route('/latest', methods=['GET'])
def get_latest():
    """
    获取患者最新问卷结果

    请求参数: ?patient_id=202505001

    返回:
    {
        "code": 200,
        "data": {
            "matched_level": "初阶关",
            "matched_level_id": 1,
            "submit_time": "2026-06-08 12:00:00",
            ...
        }
    }
    """
    patient_id = request.args.get('patient_id')
    if not patient_id:
        return jsonify({'code': 400, 'message': '缺少patient_id参数'}), 400

    record = QuestionnaireRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(QuestionnaireRecord.submit_time.desc()).first()

    if not record:
        return jsonify({'code': 404, 'message': '该患者暂无问卷记录'}), 404

    return jsonify({
        'code': 200,
        'data': record.to_dict()
    }), 200


@questionnaire_bp.route('/retest', methods=['POST'])
def retest_questionnaire():
    """
    重新测评（与提交问卷逻辑相同，只是语义不同）

    请求格式:
    {
        "patient_id": "202505001",
        "answers": ["A", "B", "C", "D", "A", "B", "C", "D", "A", "B"]
    }
    """
    # 重新测评就是重新提交问卷
    return submit_questionnaire()
