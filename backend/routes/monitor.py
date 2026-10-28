"""
后台实时监控页面（蓝图 monitor_bp，页面 /monitor）

用途：实时显示 Unity 第二个游戏（大臂康复）上报的「肩外展(大臂抬起)角度」。
数据链路：Unity --training_frame--> 桥接(bci_bridge_server.py) --落库--> train_real_time_data

与旧版区别：
  旧版用 Flask-SocketIO 的 /monitor WebSocket 命名空间广播（依赖 eventlet + WebSocket）。
  新版改为【HTTP 轮询】：前端每 500ms 拉一次 /api/monitor/data 取最新一帧。
  这样彻底去掉了 WebSocket，监控页与桥接进程解耦，部署更简单。

页面 HTML 直接内联，部署最简单（无外部 CDN 依赖）。
"""

from flask import Blueprint, Response, jsonify
from extensions import db
from models.training import TrainingData, GameLevel

monitor_bp = Blueprint('monitor', __name__)

# 页面 HTML 直接内联，部署最简单（无需额外模板引擎）。
HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大臂康复 · 实时角度监控</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Microsoft YaHei", sans-serif; background:#0f1420; color:#e6edf3; margin:0; padding:24px; }
  h1 { font-size:20px; margin:0 0 4px; }
  .sub { color:#8b98a5; font-size:13px; margin-bottom:20px; }
  .card { background:#1b2333; border-radius:12px; padding:20px; margin-bottom:16px; }
  .big { font-size:64px; font-weight:700; line-height:1; }
  .unit { font-size:20px; color:#8b98a5; }
  .row { display:flex; gap:16px; flex-wrap:wrap; }
  .stat { flex:1; min-width:180px; }
  .label { color:#8b98a5; font-size:13px; margin-bottom:6px; }
  .ok { color:#3fb950; font-weight:600; } .no { color:#f85149; font-weight:600; }
  canvas { width:100%; height:240px; background:#0f1420; border-radius:8px; display:block; }
  .log { max-height:160px; overflow:auto; font-size:12px; color:#8b98a5; line-height:1.7; }
  .dot { display:inline-block; width:10px; height:10px; border-radius:50%; background:#f85149; margin-right:8px; vertical-align:middle; }
</style>
</head>
<body>
  <h1><span class="dot" id="status"></span>大臂康复 · 实时角度监控</h1>
  <div class="sub">数据来源：Unity → 桥接脚本 → 数据库(train_real_time_data) · 不经过脑电平台 · HTTP 轮询</div>

  <div class="row">
    <div class="card stat">
      <div class="label">当前大臂(肩外展)角度</div>
      <div><span class="big" id="angle">--</span><span class="unit"> °</span></div>
      <div id="qual" class="label">等待数据…</div>
    </div>
    <div class="card stat">
      <div class="label">目标角度</div>
      <div><span class="big" id="target">--</span><span class="unit"> °</span></div>
      <div class="label">关卡：<span id="level">--</span></div>
    </div>
    <div class="card stat">
      <div class="label">患者 / 采集时间</div>
      <div id="pid" style="font-size:18px;">--</div>
      <div id="time" class="label">--</div>
    </div>
  </div>

  <div class="card">
    <div class="label">实时角度曲线（最近 60 帧，橙色虚线为目标角度）</div>
    <canvas id="chart"></canvas>
  </div>

  <div class="card">
    <div class="label">实时日志</div>
    <div class="log" id="log"></div>
  </div>

<script>
  const status = document.getElementById('status');
  const points = [];
  const canvas = document.getElementById('chart');
  const ctx = canvas.getContext('2d');
  let lastTime = null;

  async function poll() {
    try {
      const resp = await fetch('/api/monitor/data');
      const d = await resp.json();
      if (d.has_data) {
        status.style.background = '#3fb950';

        document.getElementById('angle').textContent =
          d.shoulder_abduction != null ? d.shoulder_abduction.toFixed(1) : '--';
        document.getElementById('target').textContent =
          d.target_angle != null ? d.target_angle.toFixed(1) : '--';
        document.getElementById('level').textContent = d.level_name || d.level_id || '--';
        document.getElementById('pid').textContent = d.patient_id || '--';
        document.getElementById('time').textContent = d.train_time || '--';

        const q = document.getElementById('qual');
        if (d.is_qualified) { q.textContent = '✓ 达标'; q.className = 'ok'; }
        else { q.textContent = '✗ 未达标'; q.className = 'no'; }

        if (d.shoulder_abduction != null) {
          // 同一帧不要重复记日志（按采集时间去重）
          if (d.train_time !== lastTime) {
            lastTime = d.train_time;
            points.push(d.shoulder_abduction);
            if (points.length > 60) points.shift();
            const log = document.getElementById('log');
            const line = document.createElement('div');
            line.textContent = `[${d.train_time}] 患者 ${d.patient_id} | 大臂=${d.shoulder_abduction}° 目标=${d.target_angle}° ${d.is_qualified ? '达标' : '未达标'}`;
            log.prepend(line);
          }
          drawChart(d.target_angle);
        }
      } else {
        status.style.background = '#f85149';
      }
    } catch (e) {
      status.style.background = '#f85149';
    }
    setTimeout(poll, 500);   // 每 500ms 拉一次（轮询）
  }

  // 简易折线图：蓝线=实时角度，橙虚线=目标角度
  function drawChart(target) {
    const w = canvas.width = canvas.clientWidth;
    const h = canvas.height = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const max = Math.max(180, ...points, target || 0) * 1.1;
    const min = 0;
    if (target != null) {
      const ty = h - (target - min) / (max - min) * h;
      ctx.strokeStyle = '#f0883e'; ctx.setLineDash([5, 5]); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(0, ty); ctx.lineTo(w, ty); ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.strokeStyle = '#58a6ff'; ctx.lineWidth = 2; ctx.beginPath();
    points.forEach((v, i) => {
      const x = points.length > 1 ? i / (points.length - 1) * w : w / 2;
      const y = h - (v - min) / (max - min) * h;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
  }

  poll();
</script>
</body>
</html>
"""


@monitor_bp.route('/monitor')
def monitor_page():
    """后台实时监控页：实时显示大臂抬起角度。"""
    return Response(HTML, mimetype='text/html')


@monitor_bp.route('/api/monitor/data')
def monitor_data():
    """返回 train_real_time_data 最新一帧（含对应关卡目标角度），供前端轮询。"""
    try:
        row = (TrainingData.query
               .order_by(TrainingData.train_time.desc())
               .first())
        if not row:
            return jsonify({'has_data': False})

        target_angle = None
        level_name = None
        if row.level:
            target_angle = float(row.level.target_angle) if row.level.target_angle is not None else None
            level_name = row.level.level_name

        return jsonify({
            'has_data': True,
            'patient_id': row.patient_id,
            'level_id': row.level_id,
            'level_name': level_name,
            'shoulder_abduction': float(row.shoulder_abduction) if row.shoulder_abduction is not None else None,
            'target_angle': target_angle,
            'is_qualified': row.is_qualified,
            'train_time': row.train_time.strftime('%Y-%m-%d %H:%M:%S') if row.train_time else None,
        })
    except Exception as e:
        return jsonify({'has_data': False, 'error': str(e)})
