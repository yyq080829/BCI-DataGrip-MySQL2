# 后端
```
backend/
│
├── app.py                          # Flask应用入口，启动服务器
├── config.py                       # 配置文件（数据库连接、密钥等）
├── requirements.txt                # Python依赖包列表
├── .env                           # 环境变量（敏感信息，不提交到git）
├── .gitignore                     # Git忽略文件                 
├── extensions.py                     
│
├── models/                        # 数据库模型（映射已有表）
│   ├── __init__.py
│   ├── bci_data.py
│   ├── user.py                    # 患者、医生、陪同人员模型
│   ├── game.py                    # 游戏关卡配置模型
│   ├── training.py                # 训练数据模型/游戏关卡表结构
│   └── assessment.py              # 阶段评估模型
│
├── routes/                        # 路由蓝图（API接口）
│   ├── __init__.py
│   ├── auth.py                    # 登录认证接口（前端网页调用）
│   ├── training.py                # 训练数据上传/查询接口
│   ├── game.py                    # 游戏关卡接口
│   ├── bci.py                     # HybridBCI平台调用
│   └── unity.py                   # Unity通信接口（Unity游戏调用）
│
├── services/                      # 业务逻辑层
│   ├── __init__.py
│   ├── eeg_processing.py          # 脑电信号处理
│   ├── mediapipe_service.py       # MediaPipe姿态估计
│   ├── angle_calculator.py        # 关节角度计算
│   └── compensation_detector.py   # 代偿动作检测
│
├── utils/                         # 工具函数
│   └── __init__.py
│
├── socket_handlers/               # WebSocket事件处理
│   ├── __init__.py
│   └── unity_handler.py           # Unity实时通信处理
│
├── migrations/                    # 数据库迁移（可选，暂不需要）
│   └── README.md
│
├── sql_files/                     # 队友提供的SQL文件（备份参考）
│   ├── 数据库初始化.sql
│   ├── BCI.sql
│   ├── patient_info.sql
│   ├── doctor.sql
│   ├── escort_info.sql
│   ├── game_level_connfig.sql
│   ├── train_real_time_data.sql
│   ├── stage_assesment.sql
│   ├── 患者数据.sql
│   ├── 医生数据.sql
│   ├── 陪同人员数据.sql
│   ├── 训练数据.sql
│   ├── 阶段评估数据.sql
│   ├── 插入游戏关卡配置数据.sql
│   ├── 索引创建.sql
│   └── 权限设置.sql
│
├── logs/                          # 日志文件
│   └── app.log
│
└── tests/                         # 测试文件
    ├── __init__.py
    ├── test_auth.py
    └── test_training.py
```