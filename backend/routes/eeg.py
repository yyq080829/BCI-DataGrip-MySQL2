"""
脑电数据接口（蓝图 eeg_bp，前缀 /api/eeg）

对应新客户端「脑电分析」：导入/查询 EEG 会话，并计算统计指标
（SMR/ERD/θα/准确率/专注度/放松度，以及 ERD 与准确率的相关系数 r）。
  · GET /meta          字段说明
  · POST /import       批量导入会话（{patient_id, sessions:[...]}）或单条
  · GET /?patient_id=  会话列表
  · GET /stats?patient_id=  统计（首3/末3均值、趋势%、θ/α、相关系数r）
"""

from flask import Blueprint, request, jsonify
from models.clinical import EegSession
from extensions import db

eeg_bp = Blueprint('eeg', __name__, url_prefix='/api/eeg')

EEG_FIELDS = ['alpha', 'beta', 'smr', 'theta', 'delta', 'erd', 'accuracy', 'attention', 'relaxation']


def _norm(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def _avg(key, lst):
    return sum(x[key] for x in lst) / len(lst) if lst else 0.0


def _corr(xs, ys):
    """皮尔逊相关系数。"""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


@eeg_bp.route('/meta', methods=['GET'])
def meta():
    return jsonify({'code': 200, 'data': {
        'fields': EEG_FIELDS,
        'format': 'session_no,alpha,beta,smr,theta,delta,erd,accuracy,attention,relaxation'
    }}), 200


@eeg_bp.route('/import', methods=['POST'])
def import_eeg():
    """批量导入 EEG 会话。body: {patient_id, sessions:[{session_no,alpha,...}]} 或单条对象。"""
    try:
        d = request.get_json() or {}
        pid = d.get('patient_id')
        rows = d.get('sessions') or []
        if not pid:
            return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
        if not isinstance(rows, list) or not rows:
            rows = [d]  # 允许单条
        objs = []
        for r in rows:
            objs.append(EegSession(
                patient_id=pid,
                session_no=int(r.get('session_no', 0) or 0),
                alpha=_norm(r.get('alpha')), beta=_norm(r.get('beta')), smr=_norm(r.get('smr')),
                theta=_norm(r.get('theta')), delta=_norm(r.get('delta')), erd=_norm(r.get('erd')),
                accuracy=_norm(r.get('accuracy')), attention=_norm(r.get('attention')),
                relaxation=_norm(r.get('relaxation'))
            ))
        db.session.add_all(objs)
        db.session.commit()
        return jsonify({'code': 200, 'message': f'已导入{len(objs)}条', 'count': len(objs)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': 500, 'message': f'导入失败: {str(e)}'}), 500


@eeg_bp.route('/', methods=['GET'])
def list_eeg():
    """某患者 EEG 会话列表（?patient_id=xxx）。"""
    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
    rows = EegSession.query.filter_by(patient_id=pid).order_by(EegSession.session_no.asc()).all()
    return jsonify({'code': 200, 'data': [r.to_dict() for r in rows]}), 200


@eeg_bp.route('/stats', methods=['GET'])
def stats_eeg():
    """统计指标（与客户端 eegStats() 对齐）。"""
    pid = request.args.get('patient_id')
    if not pid:
        return jsonify({'code': 400, 'message': '缺少patient_id'}), 400
    rows = EegSession.query.filter_by(patient_id=pid).order_by(EegSession.session_no.asc()).all()
    data = [r.to_dict() for r in rows]
    n = len(data)
    if n == 0:
        return jsonify({'code': 200, 'data': {'n': 0}}), 200

    first = data[:3]
    last = data[-3:]
    smr_first = _avg('smr', first)
    smr_last = _avg('smr', last)
    erd_first = _avg('erd', first)
    erd_last = _avg('erd', last)
    theta_alpha = _avg('theta', data) / _avg('alpha', data) if _avg('alpha', data) else 0
    acc = _avg('accuracy', data)
    att = _avg('attention', data)
    rel = _avg('relaxation', data)
    r = _corr([x['erd'] for x in data], [x['accuracy'] for x in data])
    smr_trend = (smr_last - smr_first) / smr_first * 100 if smr_first else 0
    erd_trend = (erd_last - erd_first) / erd_first * 100 if erd_first else 0

    return jsonify({'code': 200, 'data': {
        'n': n,
        'smrFirst': round(smr_first, 2), 'smrLast': round(smr_last, 2), 'smrTrend': round(smr_trend, 1),
        'erdFirst': round(erd_first, 1), 'erdLast': round(erd_last, 1), 'erdTrend': round(erd_trend, 1),
        'thetaAlpha': round(theta_alpha, 2), 'accuracy': round(acc, 1),
        'attention': round(att, 0), 'relaxation': round(rel, 0),
        'corrERDAcc': round(r, 2)
    }}), 200
