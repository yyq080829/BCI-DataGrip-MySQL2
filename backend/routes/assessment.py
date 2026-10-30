"""
临床评估接口（蓝图 assessment_bp，前缀 /api/assessment）

对应新客户端 10 题临床评估（每题 0-4 分 → 总分 → 康复等级）。
题目维度与选项见 ASSESSMENT_QUESTIONS（与 Kyouic/app/index.html 的 assessmentQuestions 完全一致）。

分级阈值（与客户端 submitAssess 对齐）：
  · 总分 ≤ 10   → 初级
  · 11 ~ 25    → 中级
  · 26 ~ 35    → 高级
  · 36 ~ 40    → 精细
"""

from flask import Blueprint, request, jsonify
from models.clinical import ClinicalAssessment
from models.user import Patient
from extensions import db

assessment_bp = Blueprint('assessment', __name__, url_prefix='/api/assessment')

# 题目来源：Kyouic/app/index.html 的 assessmentQuestions（不可改前端，故后端对齐同一份）
ASSESSMENT_QUESTIONS = [
    {'dimension': '肩主动控制 · Brunnstrom上肢分期',
     'question': '1. 坐位放松状态下，您的患侧手臂能否主动抬起（肩前屈）？',
     'options': ['完全不能，上肢松软无力', '仅出现轻微肌肉收缩或联合反应，手臂不能抬起',
                 '可屈肘但肩不能主动前屈，抬臂需极大努力', '可将手臂抬起至肩水平，动作缓慢费力',
                 '可自如抬起超过肩水平，接近正常']},
    {'dimension': '肘关节运动 · Brunnstrom Ⅰ~Ⅲ期',
     'question': '2. 您的患侧肘部能否主动弯曲和伸展？',
     'options': ['完全不能', '仅在打哈欠或用力时随身体连带弯曲（联合反应）',
                 '可主动屈肘，但伸肘困难、前臂僵硬', '屈伸肘基本自如，但速度和准确度差', '屈伸肘正常自如']},
    {'dimension': '手到腰动作 · Brunnstrom Ⅳ期标志',
     'question': '3. 您的患侧手能否摸到自己同侧的腰？',
     'options': ['完全不能', '需另一只手帮助才能放到腰上', '能做到但需缓慢努力、动作分解',
                 '可以完成但稍显笨拙', '轻松完成']},
    {'dimension': '前臂旋转 · Brunnstrom Ⅴ期',
     'question': '4. 您的患侧前臂能否旋转（如翻掌、拧钥匙动作）？',
     'options': ['完全不能，手掌固定朝下', '只能轻微翻转（不足四分之一圈）', '可翻转但范围受限、明显僵硬',
                 '基本完成旋转但缓慢', '旋转自如']},
    {'dimension': '抓握功能 · Fugl-Meyer / ARAT',
     'question': '5. 您的患侧手能否抓握物体（如水杯）？',
     'options': ['手完全松软，或紧握无法张开', '仅能勾住物体，不能主动抓握',
                 '可抓握大物体（如水杯）但握力弱、松开困难', '可稳定抓握并主动松开', '抓握有力，握放自如']},
    {'dimension': '手部精细动作 · Fugl-Meyer腕指功能',
     'question': '6. 您的患侧手能否完成精细动作（如捏起硬币、系扣子）？',
     'options': ['完全不能', '手指仅有轻微屈伸', '可用整个手掌简单配合（如扒拢硬币）',
                 '可捏起较大物品（如瓶盖）', '可捏起硬币、系扣子等精细动作']},
    {'dimension': '肌张力 · 改良Ashworth导向',
     'question': '7. 您患侧上肢及手的肌肉紧张程度（僵硬/痉挛）如何？',
     'options': ['松软无力，没有任何肌张力', '轻度紧张，快速活动时才感到阻力',
                 '中度僵硬，已影响穿衣等日常动作', '明显僵硬，关节被动活动严重受限', '肌张力正常，不紧不僵']},
    {'dimension': '肩部并发症筛查',
     'question': '8. 您的患侧肩部是否有疼痛或半脱位（肩关节"脱出"的感觉）？',
     'options': ['剧烈疼痛，完全不能活动', '明显疼痛伴半脱位，被动活动受限', '活动时疼痛，休息可缓解',
                 '偶尔轻微疼痛', '无疼痛，肩部活动正常']},
    {'dimension': '日常活动参与 · Barthel指数导向',
     'question': '9. 日常生活中（穿衣、进食、洗漱），患侧上肢的实际使用程度？',
     'options': ['完全不使用', '仅作为辅助按压或固定物体', '可参与双手配合活动（如双手拧毛巾）',
                 '可独立完成简单任务（如用勺子进食）', '已恢复日常使用，动作流畅']},
    {'dimension': '双手协同 · 上肢实用功能',
     'question': '10. 双手配合活动时（如拧瓶盖、系鞋带），您的患手表现如何？',
     'options': ['患手完全不能参与', '仅能固定物体供健手操作', '可简单配合但物体易掉落',
                 '可配合完成大部分双手任务', '可灵活配合复杂双手任务']},
]


def calc_level(score):
    if score <= 10:
        return '初级'
    if score <= 25:
        return '中级'
    if score <= 35:
        return '高级'
    return '精细'


@assessment_bp.route('/questions', methods=['GET'])
def questions():
    """返回 10 道临床评估题（前端渲染用）。"""
    return jsonify({'code': 200, 'data': {
        'total': len(ASSESSMENT_QUESTIONS),
        'questions': ASSESSMENT_QUESTIONS
    }}), 200


@assessment_bp.route('/submit', methods=['POST'])
def submit():
    """提交 10 题作答（每题 0-4）→ 算总分 → 匹配康复等级 → 落库并更新患者训练等级。"""
    try:
        data = request.get_json() or {}
        pid = data.get('patient_id')
        answers = data.get('answers')
        if not pid or not isinstance(answers, list) or len(answers) != 10:
            return jsonify({'code': 400, 'message': '缺少patient_id或answers(需10题)'}), 400
        try:
            answers = [int(x) for x in answers]
        except Exception:
            return jsonify({'code': 400, 'message': 'answers 必须为0-4的整数'}), 400
        if any(a < 0 or a > 4 for a in answers):
            return jsonify({'code': 400, 'message': '每题分值应在0-4之间'}), 400

        total = sum(answers)
        level = calc_level(total)

        rec = ClinicalAssessment(
            patient_id=pid,
            answers=','.join(str(a) for a in answers),
            total_score=total,
            mapped_level=level
        )
        db.session.add(rec)

        # 同步更新患者的训练等级（train_level），供游戏关卡解锁使用
        p = Patient.query.get(pid)
        if p:
            p.train_level = level

        db.session.commit()
        return jsonify({'code': 200, 'data': {
            'record_id': rec.id,
            'total_score': total,
            'mapped_level': level,
            'answers': answers,
            'message': f'评估完成 · 康复等级：{level}'
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'提交失败: {str(e)}'}), 500


@assessment_bp.route('/history', methods=['GET'])
def history():
    """某患者全部临床评估历史（?patient_id=xxx）。"""
    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
    recs = ClinicalAssessment.query.filter_by(patient_id=pid)\
        .order_by(ClinicalAssessment.created_at.desc()).all()
    return jsonify({'code': 200, 'data': {'total': len(recs), 'records': [r.to_dict() for r in recs]}}), 200


@assessment_bp.route('/latest', methods=['GET'])
def latest():
    """某患者最新一次临床评估（?patient_id=xxx）。"""
    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
    rec = ClinicalAssessment.query.filter_by(patient_id=pid)\
        .order_by(ClinicalAssessment.created_at.desc()).first()
    if not rec:
        return jsonify({'code': 404, 'message': '暂无评估记录'}), 404
    return jsonify({'code': 200, 'data': rec.to_dict()}), 200
