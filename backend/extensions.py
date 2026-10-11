"""
扩展对象集中创建（避免循环导入）

为什么要单独建这个文件？
  Flask 的 db / jwt / socketio 这些“扩展”需要在创建 Flask app 之前就实例化，
  然后再在 app.py 里用 `db.init_app(app)` 绑定到 app。
  如果直接在 app.py 里 `from flask_sqlalchemy import SQLAlchemy; db = SQLAlchemy()`，
  而 models 又 `from app import db`，就会造成循环导入（circular import）。
  所以统一在这里先 new 出来（不绑 app），谁要用就 `from extensions import db`。
"""

from flask_sqlalchemy import SQLAlchemy   # ORM 框架：用 Python 类定义表、自动建表
from flask_jwt_extended import JWTManager  # JWT 登录令牌管理
from flask_socketio import SocketIO        # WebSocket（Unity 实时通信用它）

# 先创建实例，暂不绑定 app（app.py 里再 init_app）
db = SQLAlchemy()
jwt = JWTManager()
# 开启跨域（cors_allowed_origins='*'），让前端/Unity 能连上 WebSocket
# async_mode='eventlet'：使用 eventlet 作为并发引擎（见 requirements.txt）
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
