# 后端
```
backend/
├── app.py              # Flask 入口
├── config.py           # 配置
├── extensions.py       扩展
├── requirements.txt    # 依赖
├── models
│   ├── __init__.py
│   ├── game.py                    # 游戏关卡配置模型
│   ├── training.py      # 训练数据模型
│   └── user.py          # 患者信息（用于患者ID关联）
├── routes/
│   ├── __init__.py
│   ├── game.py                    # 游戏关卡接口
│   ├── training.py                # 训练数据上传/查询接口
│   └── unity.py         # Unity WebSocket + 存储逻辑
├── services/
│   ├── __init__.py
│   └── hybridbci_client.py # 平台 TCP 客户端
├── logs/                          # 日志文件
│   └── app.log
└── sql_files/                     # 队友提供的SQL文件（备份参考）
    ├── 数据库初始化.sql
    ├── BCI.sql
    ├── patient_info.sql
    ├── doctor.sql
    ├── escort_info.sql
    ├── game_level_connfig.sql
    ├── train_real_time_data.sql
    ├── stage_assesment.sql
    ├── 训练数据.sql
    ├── 阶段评估数据.sql
    └── 插入游戏关卡配置数据.sql

```