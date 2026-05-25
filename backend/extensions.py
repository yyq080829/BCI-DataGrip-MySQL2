"""
扩展对象 - 避免循环导入
所有扩展都在这里统一创建
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

# 创建扩展实例（不绑定app）
db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")