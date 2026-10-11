"""
路由包（routes）—— 所有 HTTP / WebSocket 接口的“目录”

本目录下的每个 .py 是一个蓝图(Blueprint)：
  · auth.py         登录 / 注册 / 找回密码
  · questionnaire.py 问卷题目与提交（落到 questionnaire_record）
  · training.py      训练数据上传 / 查询 / 统计
  · unity.py        Unity 游戏 WebSocket 事件（实时角度、p300、结果）
  · monitor.py       后台大臂角度实时监控页 /monitor
  · frontend.py      托管 frontend/ 静态文件（让 app.py 能打开前端）
app.py 里统一用 register_blueprint 把它们挂到 Flask 上。
"""
