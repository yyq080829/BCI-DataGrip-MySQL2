"""
纯 MySQL 配置文件（已彻底移除 SQLite 相关代码）
"""

import os
from datetime import timedelta


class Config:
    """应用配置类 - 仅使用 MySQL"""

    # Flask 密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hand-to-guess-string'

    # ==================== 严格只用 MySQL 的配置 ====================
    # 必须确保以下参数与你的 MySQL 实际配置一致
    MYSQL_USER = 'root'  # 你的 MySQL 用户名
    MYSQL_PASSWORD = 'Ljy18718957842'  # 你的 MySQL 密码
    MYSQL_HOST = '127.0.0.1'
    MYSQL_PORT = '3306'
    MYSQL_DATABASE = 'stroke_rehab_game'  # 你的数据库名

    # 强制指定纯 MySQL 连接（关键！移除了所有 SQLite 可能）
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4&collation=utf8mb4_general_ci"
    )

    # SQLAlchemy 引擎配置
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }

    # ==================== 其他配置保持不变 ====================
    JWT_SECRET_KEY = 'jwt-secret-key-2025'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    CORS_ORIGINS = '*'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    BCI_HOST = '127.0.0.1'
    BCI_PORT = 8000
    P300_GRID_ROWS = 3
    P300_GRID_COLS = 4
    P300_EVENT_NON_TARGET = 0
    P300_EVENT_TARGET = 1