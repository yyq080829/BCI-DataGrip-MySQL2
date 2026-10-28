"""
扩展对象集中创建（避免循环导入）

为什么要单独建这个文件？
  Flask 的 db / jwt 这些“扩展”需要在创建 Flask app 之前就实例化，
  然后再在 app.py 里用 `db.init_app(app)` 绑定到 app。
  如果直接在 app.py 里 `from flask_sqlalchemy import SQLAlchemy; db = SQLAlchemy()`，
  而 models 又 `from app import db`，就会造成循环导入（circular import）。
  所以统一在这里先 new 出来（不绑 app），谁要用就 `from extensions import db`。

⚠️ WebSocket(socketio) 已移除：
  · Unity 连接改为独立 TCP 桥接（services/bci_bridge_server.py），不再走 Flask/eventlet
  · 后台监控页 /monitor 改为 HTTP 轮询，也不再需要 socketio
  这样彻底避开了原方案里 Flask + eventlet + 多模块相互依赖导致平台连接超时/协议错的问题。
"""

from flask_sqlalchemy import SQLAlchemy   # ORM 框架：用 Python 类定义表、自动建表
from flask_jwt_extended import JWTManager  # JWT 登录令牌管理

# 先创建实例，暂不绑定 app（app.py 里再 init_app）
db = SQLAlchemy()
jwt = JWTManager()
