"""
Flask 后端主入口

本服务承担 3 件事（新手先看这里）：
  1. 问卷系统（前端 <-> 数据库）
     · 医生/患者登录、注册、找回密码：/api/auth/*
     · 问卷题目 / 提交：/api/questionnaire/*（落到 questionnaire_record）
     · 同时托管 frontend/ 静态文件，访问 / 即可打开问卷页（康游智创）
  2. 第一个游戏（Unity <-> HybridBCI 平台 <-> MySQL）
     · 脑机游戏经 HybridBCIBridge 与平台 TCP 通信
     · 游戏结束后平台存一份，后端再"导出"一份到 MySQL（experiment_record + train_real_time_data）
  3. 第二个游戏（Unity <-> MySQL 直连）
     · 大臂康复数据由 Unity 每帧 training_frame 直接写 train_real_time_data
     · 并经 /monitor 后台页实时显示，不经过脑电平台

关于"前端和游戏要不要分开"：
  · 它们共用一个数据库，没必要拆成两个后端。
  · 这里用同一个 app.py 既提供 /api 接口、又托管前端静态文件，
    启动一个进程即可同时服务前端与 Unity，部署最简单。
"""

from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt, socketio


def create_app():
    """创建并配置 Flask 应用（工厂函数）。"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展（db/jwt/socketio 在 extensions.py 里先 new 出来，这里绑定到 app）
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)  # 允许跨域
    socketio.init_app(app, cors_allowed_origins="*")                          # 允许 WebSocket 跨域

    # 在应用上下文里建表 + 初始化默认数据
    with app.app_context():
        import models.user
        import models.training
        import models.questionnaire
        db.create_all()   # 根据 models/ 里的类自动建表（SQL 文件只是参考/备份）

        # 如果游戏关卡表为空，插入默认 3 个关卡（星光舞台 初/中/高阶）
        from models.training import GameLevel
        if GameLevel.query.count() == 0:
            levels = [
                GameLevel(game_name='星光舞台', train_part='前臂旋前+旋后', level_name='初级节奏',
                          target_angle=90.00, angle_tolerance=15.00, train_duration=180,
                          difficulty='初阶关', game_remark='节拍慢，适合I-II期康复'),
                GameLevel(game_name='星光舞台', train_part='前臂旋前+旋后', level_name='中级节奏',
                          target_angle=90.00, angle_tolerance=10.00, train_duration=240,
                          difficulty='中阶关', game_remark='节拍中等，适合III期康复'),
                GameLevel(game_name='星光舞台', train_part='前臂旋前+旋后', level_name='高级节奏',
                          target_angle=90.00, angle_tolerance=5.00, train_duration=300,
                          difficulty='高阶关', game_remark='节拍快，适合IV-VI期强化'),
            ]
            db.session.add_all(levels)
            db.session.commit()
            print("已插入默认游戏关卡（初阶关、中阶关、高阶关）")

    # 注册蓝图（把各路由模块挂到 Flask 上）
    from routes.training import training_bp
    from routes.questionnaire import questionnaire_bp
    from routes.auth import auth_bp
    from routes.unity import unity_bp
    from routes.monitor import monitor_bp
    from routes.frontend import frontend_bp   # 托管前端静态文件（让 app.py 能打开前端）

    app.register_blueprint(training_bp, url_prefix='/api/training')
    app.register_blueprint(questionnaire_bp, url_prefix='/api/questionnaire')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(unity_bp)        # WebSocket 事件使用 /unity 命名空间
    app.register_blueprint(monitor_bp)      # 后台实时监控页 /monitor
    app.register_blueprint(frontend_bp)     # 前端静态文件：/ 打开问卷页，/<file> 托管资源

    # 启动 HybridBCI 平台桥接（平台 <-> Unity <-> 数据库）
    from services.hybridbci_client import HybridBCIBridge
    bridge = HybridBCIBridge(
        socketio=socketio,
        app=app,
        host=app.config['BCI_HOST'],
        port=app.config['BCI_PORT'],
        p300_grid_rows=app.config.get('P300_GRID_ROWS', 3),
        p300_grid_cols=app.config.get('P300_GRID_COLS', 4),
    )
    bridge.start()                       # 开启后台线程连平台（平台没开则每 3 秒重连，不阻塞）
    app.config['BCI_CLIENT'] = bridge    # 存到 app 上，供 unity.py 调用（current_app.config['BCI_CLIENT']）

    return app


if __name__ == '__main__':
    # 直接运行 python app.py 时启动服务
    app = create_app()
    print("=" * 60)
    print("  后端服务已启动（前端 + Unity + HybridBCI 平台已接入）")
    print(f"  Flask Web服务 : 0.0.0.0:5000")
    print(f"  HybridBCI平台 : {app.config['BCI_HOST']}:{app.config['BCI_PORT']}")
    print("  可用接口:")
    print("    GET  /                      -> 打开前端问卷页")
    print("    GET  /index.html            -> Unity WebGL 入口")
    print("    POST /api/auth/login")
    print("    POST /api/auth/register")
    print("    POST /api/auth/forgot-password")
    print("    POST /api/auth/reset-password")
    print("    GET  /api/auth/profile")
    print("    POST /api/training/save")
    print("    GET  /api/training/history")
    print("    GET  /api/training/stats")
    print("    WS   /unity  (register_patient / training_frame / p300_*)")
    print("    WS   /monitor (后台实时大臂角度监控页 /monitor)")
    print("    GET  /monitor (大臂康复实时角度后台显示)")
    print("    GET  /api/questionnaire/questions")
    print("    POST /api/questionnaire/submit")
    print("=" * 60)
    # 用 socketio.run 而不是 app.run，因为要用 eventlet 跑 WebSocket
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
