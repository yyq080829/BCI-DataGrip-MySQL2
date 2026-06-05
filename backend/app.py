"""
Flask后端主入口
功能：
- 创建Flask应用
- 初始化数据库、JWT、跨域等扩展
- 注册所有API蓝图
- 启动WebSocket服务
- 自动创建表并插入默认游戏关卡（SQLite）
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
        db.create_all()   # 自动创建所有表

        # 插入默认游戏关卡（如果表为空）
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

    app.register_blueprint(training_bp, url_prefix='/api/training')
    app.register_blueprint(unity_bp, url_prefix='/api/unity')
    return app


if __name__ == '__main__':
    app = create_app()
    # 启动服务器，监听所有网络接口，方便局域网内的设备访问
    from services.hybridbci_client import HybridBCIClient

    bci_client = HybridBCIClient(socketio, host='127.0.0.1', port=8000)
    bci_client.start()
    app.config['BCI_CLIENT'] = bci_client
    print("[后端] HybridBCI 客户端已启动，等待平台数据...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)