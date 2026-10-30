"""
Flask 后端主入口

本服务承担 3 件事（新手先看这里）：
  1. 问卷系统（前端 <-> 数据库）
     · 医生/患者登录、注册、找回密码：/api/auth/*
     · 问卷题目 / 提交：/api/questionnaire/*（落到 questionnaire_record）
     · 同时托管 frontend/ 静态文件，访问 / 即可打开问卷页（康游智创）
  2. 第一个游戏（Unity <-> HybridBCI 平台 <-> MySQL）
   · 脑机游戏由【独立进程 services/bci_bridge_server.py】负责：
     平台结果翻译后发给 Unity，并把结果落库 experiment_record。
     （命令行另开一个终端 `python services/bci_bridge_server.py` 跑，不在本 app 内）
  3. 第二个游戏（Unity <-> MySQL 直连）
   · 大臂康复数据由 Unity 每帧发往桥接，桥接写 train_real_time_data
   · 后台 /monitor 页改为 HTTP 轮询实时显示，不经过脑电平台

  关于"前端和游戏要不要分开"：
  · 它们共用一个数据库，没必要拆成两个后端。
  · 本 app.py 只负责 /api 接口 + 托管前端静态文件（问卷系统）。
  · Unity 与脑电平台的连接交给独立桥接进程 bci_bridge_server.py，
  这样避开了原 Flask + eventlet + WebSocket 多模块互相依赖导致的平台超时/协议错。
  """

from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt


def create_app():
    """创建并配置 Flask 应用（工厂函数）。"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展（db/jwt/socketio 在 extensions.py 里先 new 出来，这里绑定到 app）
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)  # 允许跨域

    # 在应用上下文里建表 + 初始化默认数据
    with app.app_context():
        import models.user
        import models.training
        import models.questionnaire
        import models.clinical   # 新客户端领域模型：量表/临床评估/训练记录/脑电/建议
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
    from routes.monitor import monitor_bp
    from routes.frontend import frontend_bp   # 托管前端静态文件（让 app.py 能打开前端）
    from routes.patients import patients_bp
    from routes.assessment import assessment_bp
    from routes.scales import scales_bp
    from routes.eeg import eeg_bp
    from routes.advice import advice_bp

    app.register_blueprint(training_bp, url_prefix='/api/training')
    app.register_blueprint(questionnaire_bp, url_prefix='/api/questionnaire')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(monitor_bp)      # 后台实时监控页 /monitor（HTTP 轮询）
    app.register_blueprint(frontend_bp)     # 前端静态文件：/ 打开问卷页，/<file> 托管资源
    app.register_blueprint(patients_bp, url_prefix='/api/patients')
    app.register_blueprint(assessment_bp, url_prefix='/api/assessment')
    app.register_blueprint(scales_bp, url_prefix='/api/scales')
    app.register_blueprint(eeg_bp, url_prefix='/api/eeg')
    app.register_blueprint(advice_bp, url_prefix='/api/advice')

    # ⚠️ Unity 与脑电平台的连接已交给独立进程 bci_bridge_server.py，
    #    请用另一个终端运行：python services/bci_bridge_server.py
    #    本 app 只负责 /api 接口与前端静态托管，不再内置桥接。

    return app


if __name__ == '__main__':
    # 直接运行 python app.py 时启动服务
    app = create_app()
    print("=" * 60)
    print("  后端服务已启动（前端问卷系统 + API）")
    print(f"  Flask Web服务 : 0.0.0.0:5000")
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
    print("    GET  /monitor (大臂康复实时角度后台显示，HTTP 轮询)")
    print("    GET  /api/monitor/data (最新一帧训练数据 JSON)")
    print("    GET  /api/questionnaire/questions")
    print("    POST /api/questionnaire/submit")
    print("    GET  /api/patients/  (列表/搜索/详情)")
    print("    POST /api/assessment/submit  (10题临床评估→分级)")
    print("    GET  /api/scales/meta  (5大量表元数据)")
    print("    POST /api/eeg/import  (脑电会话导入)")
    print("    POST /api/advice/  (医生建议增/查)")
    print("=" * 60)
    print("  ⚠️ Unity 与脑电平台连接请另开终端运行:")
    print("     python services/bci_bridge_server.py")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
