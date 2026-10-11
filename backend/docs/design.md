# 脑卒中上肢康复系统 · 后端设计文档（design.md）

## 1. 项目定位

一个 **Flask 后端**，同时服务两类前端：

1. **问卷系统前端**（HTML，放在 `../frontend/`）：医生/患者登录、做康复问卷、匹配训练难度。
2. **Unity 游戏**（两个康复游戏）：实时采集训练数据，存进同一个 MySQL 数据库。

它们**共用一个数据库、一个后端进程**，没有拆成两个服务（部署最简单）。

---

## 2. 整体架构

```
┌─────────────┐        HTTP/WS(/api,/unity,/monitor)        ┌──────────────────┐
│  前端问卷页   │ ─────────────────────────────────────────▶ │                  │
│ (frontend/)  │                                            │   Flask 后端      │
└─────────────┘                                            │   (app.py)        │
                                                          │                  │
┌─────────────┐   WebSocket(/unity)   ┌──────────────┐     │  routes/*         │
│  Unity 游戏   │ ───────────────────▶ │  unity.py    │     │  models/*         │
│  (两个游戏)  │ ◀─────────────────── │  (实时帧/指令) │     │  services/*        │
└─────────────┘                      └──────┬───────┘     │                  │
                                           │              └──────────────────┘
                              TCP(:8000)    │                     │ SQLAlchemy
                                           ▼                     ▼
                                  ┌──────────────────┐      ┌──────────────────┐
                                  │ HybridBCI 平台    │      │   MySQL           │
                                  │ (脑机算法/实验)   │      │ stroke_rehab_game │
                                  └──────────────────┘      └──────────────────┘
```

- 前端页面由 `routes/frontend.py` 直接托管，`python app.py` 后访问 `/` 即打开问卷页。
- Unity 通过 WebSocket（`/unity` 命名空间）与后端通信；后台监控页在 `/monitor`（`/monitor` 命名空间）。

---

## 3. 后端承担的三件事（核心）

| # | 任务 | 数据路径 | 涉及模块 |
|---|------|----------|----------|
| 1 | 问卷系统（前端 ↔ 数据库） | 前端 → `/api/auth/*`、`/api/questionnaire/*` → MySQL | `routes/auth.py`、`routes/questionnaire.py`、`models/user.py`、`models/questionnaire.py` |
| 2 | 第一个游戏（Unity ↔ HybridBCI 平台 ↔ MySQL） | Unity → `/unity`(p300_*) → `HybridBCIBridge` → 平台；平台结果回传 → Unity；实验反馈导出到 `experiment_record` + `train_real_time_data` | `routes/unity.py`、`services/hybridbci_client.py` |
| 3 | 第二个游戏（Unity ↔ MySQL 直连） | Unity → `/unity`(training_frame) → `train_real_time_data`（不经脑电平台）→ 实时广播 `/monitor` | `routes/unity.py`、`routes/monitor.py` |

> 关于“前端和游戏要不要分开”：**不用分开**。它们共用一个数据库，拆开反而要处理跨库/跨服务，没必要。一个 `app.py` 同时提供接口 + 托管前端即可。

---

## 4. 目录结构与模块职责

```
backend/
├── app.py              # Flask 入口（工厂函数 create_app）：建表、注册蓝图、启动平台桥接
├── config.py           # 配置中心：MySQL 连接、JWT、CORS、平台地址、P300 网格
├── extensions.py       # 扩展实例 db/jwt/socketio（先创建，避免循环导入）
├── requirements.txt    # Python 依赖清单（含中文注释）
├── models/             # ORM 模型（= 数据库表定义，db.create_all 据此自动建表）
│   ├── user.py         # Patient / Doctor（登录账号 + to_dict 字段对齐前端）
│   ├── training.py     # GameLevel / TrainingData / ExperimentRecord / StageAssessment
│   └── questionnaire.py # QuestionnaireRecord（问卷作答）
├── routes/             # 蓝图（HTTP/WebSocket 接口）
│   ├── auth.py         # 登录 / 注册 / 找回密码 / profile
│   ├── questionnaire.py # 问卷题目 / 提交 / 历史 / 最新 / 重测（含难度匹配算法）
│   ├── training.py     # 训练结果保存 / 历史 / 统计
│   ├── unity.py        # Unity WebSocket 事件（register/training_frame/p300_*/training_result）
│   ├── monitor.py      # 后台大臂角度实时监控页 /monitor
│   └── frontend.py     # 托管 frontend/ 静态文件，让 app.py 能打开前端
├── services/
│   └── hybridbci_client.py # HybridBCI 平台 TCP 桥接（IpcCodec + HybridBCIConnection + HybridBCIBridge）
└── sql_files/          # SQL 参考/备份（详见 sql_files/README.md）
```

各模块一句话职责：
- `app.py`：把一切组装起来（建表、挂路由、连平台）。
- `config.py`：所有可调参数集中在此。
- `extensions.py`：db/jwt/socketio 三个扩展的单一实例。
- `models/*`：用 Python 类描述数据库表，改表结构改这里。
- `routes/auth.py`：账号体系，签发 JWT。
- `routes/questionnaire.py`：问卷题目与难度匹配（A/B/C/D 计数 → 初/中/高阶关）。
- `routes/training.py`：训练结果的非实时落库与统计查询。
- `routes/unity.py`：Unity 实时通信核心；区分两个游戏，第二个游戏直连写库并广播监控。
- `routes/monitor.py`：一个自包含 HTML 页，实时画大臂角度曲线（订阅 `/monitor`）。
- `routes/frontend.py`：把 `../frontend` 当静态目录托管。
- `services/hybridbci_client.py`：与华南脑控平台 TCP 通信，翻译平台算法结果为 Unity 指令，导出实验反馈到 MySQL。

---

## 5. 关键通信协议

### 5.1 平台 IPC 协议（services/hybridbci_client.py）
- 帧格式：`[4 字节大端长度][UTF-8 JSON]`。
- 平台 → 后端常见消息：`ipc_user_info`(用户信息)、`ipc_algorithm_test`(算法在线结果)、`ipc_heartbeat` 等。
- 后端 → 平台常见消息：`ipc_event`(打标/事件)、`ipc_experiment_data`(实验记录)。
- 三个 class：`IpcCodec`(编解码) / `HybridBCIConnection`(TCP 传输+重连) / `HybridBCIBridge`(业务桥接)。

### 5.2 Unity WebSocket 事件（routes/unity.py，命名空间 `/unity`）
| 事件 | 方向 | 说明 |
|------|------|------|
| `register_patient` | Unity→后端 | 上报 patient_id，建立 sid 映射 |
| `training_frame` | Unity→后端 | 每帧角度/得分 → 写 `train_real_time_data` → 广播 `/monitor`（第二个游戏） |
| `p300_start/flash/stop` | Unity→后端 | 第一个游戏刺激事件，转发平台 |
| `training_result` | Unity→后端 | 结束汇总，`game_type` 区分两个游戏 |
| `game_command` | 后端→Unity | 平台算法结果翻译的指令（SELECT/FOCUS/MOVE…） |

---

## 6. 数据库表总览（由 models 自动建）

| 表 | 模型 | 用途 |
|----|------|------|
| `patient_info` | Patient | 患者 + 登录账号（含 email） |
| `doctor_info` | Doctor | 医生 + 登录账号 |
| `game_level_config` | GameLevel | 游戏关卡（目标角度/难度） |
| `train_real_time_data` | TrainingData | Unity 实时训练数据（量最大） |
| `stage_assessment` | StageAssessment | 阶段临床评估 |
| `questionnaire_record` | QuestionnaireRecord | 问卷作答 + 难度匹配 |
| `experiment_record` | ExperimentRecord | 平台实验反馈落库 |

仅在 SQL 里的表（需手动建）：`bci_data`、`questionnaire`、`question`。详见 `sql_files/README.md`。

---

## 7. 数据流速览

```
【问卷】 前端提交 answers → calculate_difficulty → questionnaire_record（匹配难度）
【游戏1】 Unity p300_* → HybridBCIBridge → 平台；平台 result → Unity 指令；
         p300_stop → send_experiment_data → 平台(存) + experiment_record(导出) + train_real_time_data(汇总)
【游戏2】 Unity training_frame → train_real_time_data(直连) ──广播──▶ /monitor 实时显示
```

---

## 8. 快速开始

```bash
cd backend
pip install -r requirements.txt
# 配置 config.py 里的 MySQL 账号密码（或环境变量）
python app.py
# 浏览器打开 http://localhost:5000/        （问卷系统）
# 浏览器打开 http://localhost:5000/monitor  （大臂角度实时监控）
```

数据库由 `db.create_all()` 自动建；若用旧库，先跑 `sql_files/add_email_column.sql` 补 email 列。

---

## 9. 已知待优化（新人接手注意）

- 🔐 密码明文存储（`pwd` 字段），生产请改 werkzeug 哈希。
- 🧩 `sql_files/` 有旧碎片文件（`patient_info.sql`/`doctor.sql` 等），已标注“请勿混跑”，认准 `BCI.sql`。
- 🗑️ `train_real_time_data` 每帧一行，量大，需定期归档。
- 🔗 外键均为 CASCADE，删患者会连带删训练/评估/实验记录。
- 🧠 `bci_data` 脑电原始表当前未自动落库，仅预留（高阶脑电分析用）。
