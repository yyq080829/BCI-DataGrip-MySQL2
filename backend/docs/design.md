# 脑卒中上肢康复系统 · 后端设计文档（design.md）

## 1. 项目定位

一个 **Flask 后端**，同时服务两类前端：

1. **问卷系统前端**（HTML，放在 `../frontend/`）：医生/患者登录、做康复问卷、匹配训练难度。
2. **Unity 游戏**（两个康复游戏）：实时采集训练数据，存进同一个 MySQL 数据库。

它们**共用一个数据库、一个后端进程**，没有拆成两个服务（部署最简单）。

---

## 2. 整体架构

```
┌─────────────┐      HTTP(/api,/monitor)      ┌──────────────────┐
│  前端问卷页   │ ───────────────────────────▶ │                  │
│ (frontend/)  │                             │   Flask 后端      │
└─────────────┘                             │   (app.py)        │
                                           │  routes/*         │
┌─────────────┐   TCP(:9999)                │  models/*         │
│  Unity 游戏   │ ───────────────┐          │                  │
│  (两个游戏)  │ ◀─────────────┐ │          └──────────────────┘
└─────────────┘              │ │                   │ SQLAlchemy
                            │ │                   ▼
                  ┌─────────▼─▼─────────┐   ┌──────────────────┐
                  │ bci_bridge_server   │   │   MySQL           │
                  │ .py(独立进程TCP桥接) │   │ stroke_rehab_game │
                  └─────────┬───────────┘   └──────────────────┘
                        TCP(:8000)
                            │
                            ▼
                  ┌──────────────────┐
                  │ HybridBCI 平台    │
                  │ (脑机算法/实验)   │
                  └──────────────────┘
```

- 前端页面由 `routes/frontend.py` 直接托管，`python app.py` 后访问 `/` 即打开问卷页。
- Unity 通过 **TCP:9999** 连接独立桥接进程 `services/bci_bridge_server.py`（不再用 Flask/WebSocket）；
  桥接再经 **TCP:8000** 连接 HybridBCI 平台，并把结果/训练帧落库 MySQL。
- 后台监控页 `/monitor` 改为 **HTTP 轮询**（`/api/monitor/data`），不再依赖 WebSocket。

---

## 3. 后端承担的三件事（核心）

| # | 任务 | 数据路径 | 涉及模块 |
|---|------|----------|----------|
| 1 | 问卷系统（前端 ↔ 数据库） | 前端 → `/api/auth/*`、`/api/questionnaire/*` → MySQL | `routes/auth.py`、`routes/questionnaire.py`、`models/user.py`、`models/questionnaire.py` |
| 2 | 第一个游戏（Unity ↔ HybridBCI 平台 ↔ MySQL） | Unity → TCP:9999 → `bci_bridge_server.py` → 平台(TCP:8000)；平台结果回传 Unity；实验反馈落库 `experiment_record` | `services/bci_bridge_server.py` |
| 3 | 第二个游戏（Unity ↔ MySQL 直连） | Unity → TCP:9999 → `bci_bridge_server.py` → `train_real_time_data`（不经脑电平台）→ HTTP 轮询 `/monitor` | `services/bci_bridge_server.py`、`routes/monitor.py` |

> 关于“前端和游戏要不要分开”：前端与游戏共用一个数据库，不必拆两个库；但 **Unity 与平台的连接已抽成独立进程 `bci_bridge_server.py`**（TCP 桥接），避免 Flask/eventlet/WebSocket 多模块互相依赖导致平台连接超时/协议错。一个 `app.py` 仍同时提供 /api 接口 + 托管前端。

---

## 4. 目录结构与模块职责

```
backend/
├── app.py              # Flask 入口（工厂函数 create_app）：建表、注册蓝图（不再内置桥接）
├── config.py           # 配置中心：MySQL 连接、JWT、CORS、平台地址、P300 网格、桥接端口
├── extensions.py       # 扩展实例 db/jwt（socketio 已移除，避免循环导入）
├── requirements.txt    # Python 依赖清单（含中文注释）
├── models/             # ORM 模型（= 数据库表定义，db.create_all 据此自动建表）
│   ├── user.py         # Patient / Doctor（登录账号 + to_dict 字段对齐前端）
│   ├── training.py     # GameLevel / TrainingData / ExperimentRecord / StageAssessment
│   └── questionnaire.py # QuestionnaireRecord（问卷作答）
├── routes/             # 蓝图（HTTP 接口）
│   ├── auth.py         # 登录 / 注册 / 找回密码 / profile
│   ├── questionnaire.py # 问卷题目 / 提交 / 历史 / 最新 / 重测（含难度匹配算法）
│   ├── training.py     # 训练结果保存 / 历史 / 统计
│   ├── monitor.py      # 后台大臂角度实时监控页 /monitor（HTTP 轮询）
│   └── frontend.py     # 托管 frontend/ 静态文件，让 app.py 能打开前端
├── services/
│   └── bci_bridge_server.py # 独立桥接进程：Unity(TCP:9999) <-> 平台(TCP:8000) <-> MySQL
└── sql_files/          # SQL 参考/备份（详见 sql_files/README.md）
```

各模块一句话职责：
- `app.py`：把接口与前端组装起来（建表、挂路由）；Unity 连接交给独立桥接进程。
- `config.py`：所有可调参数集中在此（含桥接的 UNITY_HOST/PORT）。
- `extensions.py`：db/jwt 两个扩展的单一实例（socketio 已移除）。
- `models/*`：用 Python 类描述数据库表，改表结构改这里。
- `routes/auth.py`：账号体系，签发 JWT。
- `routes/questionnaire.py`：问卷题目与难度匹配（A/B/C/D 计数 → 初/中/高阶关）。
- `routes/training.py`：训练结果的非实时落库与统计查询。
- `routes/monitor.py`：自包含 HTML 页，前端每 500ms 轮询 `/api/monitor/data` 画大臂角度曲线。
- `routes/frontend.py`：把 `../frontend` 当静态目录托管。
- `services/bci_bridge_server.py`：独立进程；连接平台、把算法结果翻译为 Unity 指令，并把结果/训练帧落库 MySQL。

---

## 5. 关键通信协议

### 5.1 平台 IPC 协议（services/bci_bridge_server.py）
- 帧格式：`[4 字节大端长度][UTF-8 JSON]`（与官方平台一致）。
- 平台 → 桥接常见消息：`ipc_user_info`(用户信息)、`ipc_algorithm_test`(算法在线结果)、`ipc_heartbeat` 等。
- 桥接 → 平台常见消息：`ipc_user_info`(回复 window=0)、`ipc_event`(打标/事件)。
- 桥接收到 `ipc_algorithm_test` 后用 `convert_platform_to_unity()` 翻译为 Unity 指令（`{"cmd":"SELECT","param":"...","intensity":0}`）。

### 5.2 Unity TCP 协议（services/bci_bridge_server.py，端口 TCP:9999）
Unity 的 `Link.cs` 连接桥接的 TCP:9999，按行收发 JSON（`\n` 分隔）。

| 消息 | 方向 | 说明 |
|------|------|------|
| `{"type":"register","patient_id":"..."}` | Unity→桥接 | 上报当前患者，用于落库 patient_id |
| `{"type":"training_frame", ...字段}` | Unity→桥接 | 每帧角度/得分 → 写 `train_real_time_data`（第二个游戏） |
| `{"type":"training_result", ...}` | Unity→桥接 | 结束汇总，可选落库一条实验反馈 |
| `{"cmd":"SELECT","param":"...","intensity":0}` | 桥接→Unity | 平台算法结果翻译的指令（P300/SSVEP/MI 等） |

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
【游戏1】 Unity → TCP:9999 → bci_bridge_server → 平台(TCP:8000)；平台 result → 桥接翻译 → Unity 指令；
         同时每次算法结果落库 experiment_record
【游戏2】 Unity training_frame → TCP:9999 → bci_bridge_server → train_real_time_data ──HTTP轮询──▶ /monitor 实时显示
```

---

## 8. 快速开始

```bash
cd backend
pip install -r requirements.txt
# 配置 config.py 里的 MySQL 账号密码（或环境变量）

# 终端 1：启动后端（问卷系统 + API + 监控页）
python app.py
# 浏览器打开 http://localhost:5000/        （问卷系统）
# 浏览器打开 http://localhost:5000/monitor  （大臂角度实时监控，HTTP 轮询）

# 终端 2：启动独立桥接（Unity <-> 平台 <-> MySQL）
python services/bci_bridge_server.py
# 先开 HybridBCI 平台进入在线模式，再运行 Unity（Link.cs 会自动连 TCP:9999）
```

数据库由 `db.create_all()` 自动建；若用旧库，先跑 `sql_files/add_email_column.sql` 补 email 列。

---

## 9. 已知待优化（新人接手注意）

- 🔐 密码明文存储（`pwd` 字段），生产请改 werkzeug 哈希。
- 🧩 `sql_files/` 有旧碎片文件（`patient_info.sql`/`doctor.sql` 等），已标注“请勿混跑”，认准 `BCI.sql`。
- 🗑️ `train_real_time_data` 每帧一行，量大，需定期归档。
- 🔗 外键均为 CASCADE，删患者会连带删训练/评估/实验记录。
- 🧠 `bci_data` 脑电原始表当前未自动落库，仅预留（高阶脑电分析用）。
- 🔌 **Unity 连接已改为独立桥接进程** `services/bci_bridge_server.py`（TCP:9999 ↔ 平台 TCP:8000），原 `routes/unity.py`、`services/hybridbci_client.py` 已删除，Flask 侧 `socketio`/`eventlet` 已移除；平台连接超时/协议错的坑通过“独立进程 + 纯标准库 TCP”规避。
