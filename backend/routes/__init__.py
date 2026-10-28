"""
路由包（routes）—— 所有 HTTP / WebSocket 接口的“目录”

本目录下的每个 .py 是一个蓝图(Blueprint)：
  · auth.py         登录 / 注册 / 找回密码
  · questionnaire.py 问卷题目与提交（落到 questionnaire_record）
  · training.py      训练数据上传 / 查询 / 统计
  · monitor.py       后台大臂角度实时监控页 /monitor（HTTP 轮询）
  · frontend.py      托管 frontend/ 静态文件（让 app.py 能打开前端）
app.py 里统一用 register_blueprint 把它们挂到 Flask 上。

⚠️ Unity 与脑电平台的连接已不在本目录：交给独立进程
   services/bci_bridge_server.py（TCP 桥接，平台<->Unity<->MySQL）。
"""
