"""
Flask后端主入口 - 纯API版本（无Unity/BCI平台连接）
"""

from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import db, jwt, socketio

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    socketio.init_app(app, cors_allowed_origins="*")

    with app.app_context():
        import models.user
        import models.training
        import models.questionnaire
        db.create_all()

        # 插入默认游戏关卡（如果表为空）
        from models.training import GameLevel
        if GameLevel.query.count() == 0:
            levels = [
                GameLevel(
                    game_name='星光舞台',
                    train_part='前臂旋前+旋后',
                    level_name='初级节奏',
                    target_angle=90.00,
                    angle_tolerance=15.00,
                    train_duration=180,
                    difficulty='初阶关',
                    game_remark='节拍慢，适合I-II期康复'
                ),
                GameLevel(
                    game_name='星光舞台',
                    train_part='前臂旋前+旋后',
                    level_name='中级节奏',
                    target_angle=90.00,
                    angle_tolerance=10.00,
                    train_duration=240,
                    difficulty='中阶关',
                    game_remark='节拍中等，适合III期康复'
                ),
                GameLevel(
                    game_name='星光舞台',
                    train_part='前臂旋前+旋后',
                    level_name='高级节奏',
                    target_angle=90.00,
                    angle_tolerance=5.00,
                    train_duration=300,
                    difficulty='高阶关',
                    game_remark='节拍快，适合IV-VI期强化'
                )
            ]
            db.session.add_all(levels)
            db.session.commit()
            print("已插入默认游戏关卡（初阶关、中阶关、高阶关）")

    # 注册蓝图（仅保留前端需要的API）
    from routes.training import training_bp
    from routes.questionnaire import questionnaire_bp
    from routes.auth import auth_bp

    app.register_blueprint(training_bp, url_prefix='/api/training')
    app.register_blueprint(questionnaire_bp, url_prefix='/api/questionnaire')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    return app


if __name__ == '__main__':
    app = create_app()
    print("=" * 60)
    print("  后端API服务已启动（无BCI/Unity连接）")
    print(f"  Flask Web服务: 0.0.0.0:5000")
    print("  可用接口:")
    print("    POST /api/auth/login")
    print("    POST /api/auth/register")
    print("    GET  /api/auth/profile")
    print("    POST /api/training/save")
    print("    GET  /api/training/history")
    print("    GET  /api/training/stats")
    print("    GET  /api/questionnaire/questions")
    print("    POST /api/questionnaire/submit")
    print("    GET  /api/questionnaire/history")
    print("    GET  /api/questionnaire/latest")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)