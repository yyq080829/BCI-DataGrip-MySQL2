# 配置文件（数据库连接，密钥等）

import os
from datetime import timedelta


class Config:
    """应用配置类"""

    # Flask密钥（用于session加密）
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bci-stroke-rehab-secret-key-2025')

    # MySQL数据库连接（连接队友已创建的stroke_rehab_game数据库）
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:Xka061201!@localhost:3306/stroke_rehab_game'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT配置（用于登录认证）
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-2025')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # CORS跨域配置（允许前端和Unity访问）
    CORS_ORIGINS = ['http://localhost:3000', 'http://localhost:8080', 'http://localhost:5000']

    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024