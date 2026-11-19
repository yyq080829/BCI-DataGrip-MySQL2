"""
配置模块（Config）—— 整个后端唯一的“设置中心”

作用：
  把数据库账号、密钥、平台地址、JWT 参数等集中放在这里，
  其他模块通过 `from config import Config` 读取，方便统一管理和部署切换。
  改配置只改这一个文件，不用满世界找。

新手必读：
  · 数据库的主机/端口/用户/密码/库名【一律不写在代码里】，
    统一由 .vscode/launch.json 的 env 在启动时注入（按 F5 调试后端/桥接服务）。
    这样代码里不会出现任何真实连接信息。
  · 若你不用 VS Code 调试、而是在 cmd 直接运行 python app.py，
    则需要自己先 set 同名环境变量（MYSQL_HOST / MYSQL_USER / ...），否则连不上库。
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

    # ---------- 数据库（MariaDB/MySQL）----------
    # 私密信息不落代码：主机/端口/用户/密码/库名全部由环境变量提供（见 .vscode/launch.json）。
    # 未设置时不给任何默认值，连接会明确失败，避免误连到别的库。
    MYSQL_USER = os.environ.get('MYSQL_USER', '')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '')
    MYSQL_PORT = os.environ.get('MYSQL_PORT', '3306')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', '')

    # SQLAlchemy 连接串：mysql+pymysql://用户:密码@主机:端口/库?字符集
    # pymysql 是纯 Python 的 MySQL 驱动（见 requirements.txt）
    # 注意：URL 里的 charset 只影响客户端连接，不决定 CREATE TABLE 的表级字符集。
    # 表级 utf8mb4/utf8mb4_general_ci 由 app.py 里的 before_create 事件统一注入，
    # 否则新建表会继承服务器默认排序规则，外键指向 patient_info 时报 errno 150。
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
        f"?charset=utf8mb4"
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

    # ---------- Unity ↔ 桥接服务（独立进程 services/bci_bridge_server.py）----------
    # Unity3D 的 Link.cs 通过 TCP 连接本桥接（不再走 Flask/WebSocket）。
    # 平台连接用上面的 BCI_HOST / BCI_PORT。
    UNITY_HOST = '127.0.0.1'   # 桥接监听 Unity 的地址
    UNITY_PORT = 9999          # 桥接监听 Unity 的端口（Link.cs 连接此端口）
    # 当 Unity 未主动上报 patient_id 时，落库用的默认患者ID（开发期用，正式需 Unity 上报）
    BRIDGE_DEFAULT_PATIENT_ID = '202505001'
    # 是否把平台每次算法结果都落库到 experiment_record（细化日志；不需要可改 False）
    BRIDGE_LOG_EVERY_RESULT = True
