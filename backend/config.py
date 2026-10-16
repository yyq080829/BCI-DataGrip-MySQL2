"""
配置模块（Config）—— 整个后端唯一的“设置中心”

作用：
  把数据库账号、密钥、平台地址、JWT 参数等集中放在这里，
  其他模块通过 `from config import Config` 读取，方便统一管理和部署切换。
  改配置只改这一个文件，不用满世界找。

新手最常改的地方：
  · MYSQL_USER / MYSQL_PASSWORD / MYSQL_HOST / MYSQL_PORT / MYSQL_DATABASE
    —— 你的 MySQL 真实账号密码（当前写死在代码里，正式部署应改用环境变量）。
  · BCI_HOST / BCI_PORT —— 华南脑控 HybridBCI 平台 TCP 服务地址（默认本机 8000）。
  · CORS_ORIGINS —— 允许跨域访问的前端地址；开发期设 '*' 表示全部允许。
"""

import os
from datetime import timedelta


class Config:
    """Flask 应用配置类，所有配置项都是类属性。"""

    # ---------- 基础安全 ----------
    # Flask 会话签名密钥（生产环境务必改成随机长字符串，或用环境变量注入）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hand-to-guess-string'

    # ---------- 数据库（只用 MySQL，已彻底移除 SQLite）----------
    # 下面 5 个变量拼成数据库连接串，必须与你的 MySQL 实际配置一致
    MYSQL_USER = 'root'                 # MySQL 用户名
    MYSQL_PASSWORD = 'Ljy18718957842'   # MySQL 密码（⚠️ 明文写在代码里，仅限本地开发）
    MYSQL_HOST = '127.0.0.1'            # MySQL 主机（本机）
    MYSQL_PORT = '3306'                 # MySQL 端口
    MYSQL_DATABASE = 'stroke_rehab_game'  # 数据库名（要和 sql_files 里的一致）

    # SQLAlchemy 连接串：mysql+pymysql://用户:密码@主机:端口/库?字符集
    # pymysql 是纯 Python 的 MySQL 驱动（见 requirements.txt）
    # ⚠️ 这里的 collation 必须与 sql_files/BCI.sql 里的 COLLATE 完全一致
    #    （当前都是 utf8mb4_general_ci）。若两边不一致，SQL 建表时的外键会报
    #    [HY000][3780] ... are incompatible。
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4&collation=utf8mb4_general_ci"
    )

    # SQLAlchemy 性能/稳定性开关
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # 关闭事件追踪，省内存（官方推荐）
    SQLALCHEMY_ECHO = False                 # 设为 True 会在控制台打印每条 SQL，调试用
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 3600,     # 连接超过 1 小时自动重连，避免 MySQL 8 小时空闲断连
        'pool_pre_ping': True,    # 每次取连接前先 ping 一下，确保连接可用
    }

    # ---------- 登录鉴权（JWT）----------
    JWT_SECRET_KEY = 'jwt-secret-key-2025'                 # 签发/校验 token 的密钥
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)         # token 24 小时过期
    CORS_ORIGINS = '*'                                     # 允许跨域的来源（开发期全开）
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024                  # 单次请求最大 16MB

    # ---------- 华南脑控 HybridBCI 平台 ----------
    BCI_HOST = '127.0.0.1'   # 平台 TCP 服务地址
    BCI_PORT = 8000          # 平台 TCP 服务端口

    # ---------- P300 拼写游戏网格（第一个游戏用）----------
    P300_GRID_ROWS = 3       # 网格行数
    P300_GRID_COLS = 4       # 网格列数
    P300_EVENT_NON_TARGET = 0  # 非目标刺激的事件编号
    P300_EVENT_TARGET = 1     # 目标刺激的事件编号
