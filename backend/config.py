"""
配置文件（数据库连接，密钥等）
"""

import os
from datetime import timedelta


class Config:
    """应用配置类"""

    # Flask密钥（用于session加密）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hand-to-guess-string'

    # 数据库连接（MySQL）
    # 格式: mysql+pymysql://用户名:密码@主机地址:端口/数据库名
    # 请根据实际MySQL配置修改以下参数
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '123456')     # ← 改成你的MySQL密码
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'kangyou_zhichuang')  # ← 改成你的数据库名

    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@'
        f'{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT配置（用于登录认证）
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-2025')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    # CORS跨域配置（允许前端、Unity和问卷页面访问）
    CORS_ORIGINS = '*'

    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # ==================== P300 执行器配置 ====================
    # HybridBCI 平台 TCP 连接配置
    #    重要：BCI_HOST 必须是平台运行的IP，不是后端自己的IP！
    #    如果后端和平台在同一台电脑，用 127.0.0.1
    #    如果平台在另一台电脑，用那台电脑的IP
    BCI_HOST = os.environ.get('BCI_HOST', '127.0.0.1')
    BCI_PORT = int(os.environ.get('BCI_PORT', 8000))

    # P300 范式网格配置（行数×列数）
    P300_GRID_ROWS = int(os.environ.get('P300_GRID_ROWS', 3))
    P300_GRID_COLS = int(os.environ.get('P300_GRID_COLS', 4))

    # 打标事件ID配置
    P300_EVENT_NON_TARGET = 0
    P300_EVENT_TARGET = 1
