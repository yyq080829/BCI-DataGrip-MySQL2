"""
Flask后端主入口 - P300执行器定制版 v5
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

        from models.training import GameLevel
        if GameLevel.query.count() == 0:
            default_level = GameLevel(
                game_name='星光舞台',
                train_part='前臂旋前+旋后',
                level_name='初级节奏',
                target_angle=90.00,
                angle_tolerance=10.00,
                train_duration=180,
                difficulty='简单',
                game_remark='节拍慢'
            )
            db.session.add(default_level)
            db.session.commit()
            print("已插入默认游戏关卡（星光舞台）")

    # 注册蓝图（API路由）
    from routes.training import training_bp
    from routes.unity import unity_bp
    from routes.questionnaire import questionnaire_bp
    from routes.auth import auth_bp

    app.register_blueprint(training_bp, url_prefix='/api/training')
    app.register_blueprint(unity_bp, url_prefix='/api/unity')
    app.register_blueprint(questionnaire_bp, url_prefix='/api/questionnaire')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    return app


if __name__ == '__main__':
    app = create_app()

    # 启动HybridBCI客户端
    from services.hybridbci_client import HybridBCIClient

    bci_client = HybridBCIClient(
        socketio,
        host=Config.BCI_HOST,          # 平台的IP
        port=Config.BCI_PORT,          # 平台的端口（8000）
        window_handle=0,               # 后端无GUI窗口，必须传0
        p300_grid_rows=Config.P300_GRID_ROWS,
        p300_grid_cols=Config.P300_GRID_COLS
    )
    bci_client.start()
    app.config['BCI_CLIENT'] = bci_client

    print("=" * 60)
    print("  P300 执行器后端已启动 (v5)")
    print(f"  Flask Web服务: 0.0.0.0:5000")
    print(f"  HybridBCI 平台连接: {Config.BCI_HOST}:{Config.BCI_PORT}")
    print(f"  P300 网格配置: {Config.P300_GRID_ROWS}行 x {Config.P300_GRID_COLS}列")
    print("  输出格式:")
    print("    绿色频闪 → 0")
    print("    红色闪烁 → 1 (row,col)  例如: 1 (2,3)")
    print("=" * 60)

    #   关键：Flask 监听 5000 端口，不是 8000！
    #    8000 是平台端口，BCI客户端连的是平台的8000
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
