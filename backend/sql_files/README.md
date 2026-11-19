# 脑卒中上肢康复系统 · 数据库 SQL 说明（新手必读）

> 这个文件夹里是一堆 `.sql` 文件，是**数据库结构参考 + 初始示例数据**

---

## 0. 先看这一节（最重要）

- **实际运行的数据库不是靠这些 `.sql` 建出来的。**
  后端启动时由 Python 代码（SQLAlchemy ORM，见 `backend/models/*.py`）自动建表，核心代码是 `db.create_all()`。
  所以这些 `.sql` 主要用于：**① 给人看表结构 / 写文档；② 本地想手动建一套库看数据。**

- **改表结构的正确姿势**
  1. 改 `backend/models/` 下的模型类（表名、字段、类型都在那里）；
  2. 后端一启动就自动同步；
  3. 再顺手把这里的 `.sql` 同步更新，保持人和代码看到的一致。

- **手工建库时只跑“主文件”，别乱跑碎片文件**（详见第 2 节），否则会与主文件冲突、缺字段。

---

## 1. 数据库基本信息

| 项目 | 值 |
|------|-----|
| 数据库名 | 远程 1Panel `BCI`（SQL 文件里 `USE BCI;`）/ 本地 `stroke_rehab_game`（执行前改掉库名） |
| 字符集 | `utf8mb4` |
| 排序规则 | `utf8mb4_general_ci`（必须与 `config.py` 一致，否则外键报 3780） |
| 引擎 | `InnoDB` |
| 连接方式 | MariaDB/MySQL；账号密码走环境变量（见 `backend/config.py` 顶部说明），不写进代码/SQL |

---

## 2. 这些 SQL 文件分别是干什么的

> 建议：**手工建库只跑 `BCI.sql` 一个主文件即可**（它已含所有业务表、示例数据与索引；开头 `USE BCI;` 切库，远程执行前请勿改动，本地执行请把 `BCI` 改成 `stroke_rehab_game`）。其余文件是可选的扩展，按需单独跑，不要重复执行。

| 文件名 | 作用 | 备注 |
|--------|------|------|
| ⭐ `BCI.sql` | **【唯一主文件·最全】** 建库 + USE + 完整建表 + 示例数据 + 索引 | 认准它当唯一真源，包含 patient/doctor/escort/关卡/实时训练/阶段评估，以及新增的 5 张临床表(量表/临床评估/训练记录/脑电/建议) |
| `experiment_record.sql` | 平台实验反馈记录表 | 配合后端连接华南脑控平台（BCI.sql 未含，需另跑） |
| `bci_data.sql` | 脑电数据表（无外键、无 ORM 模型） | 可选，仅在 SQL 里有，需手动建 |
| `questionnaire.sql` | 问卷**模板**主表 + 问题表，并插入 10 道题 | 可选，问卷题目来自这里（运行时后端硬编码，不查此表） |

> 🗑️ 已删除的冗余碎片文件（`patient_info.sql` / `doctor.sql` / `escort_info.sql` / `game_level_connfig.sql` / `train_real_time_data.sql` / `stage_assesment.sql` / `插入游戏关卡配置数据.sql` / `阶段评估数据.sql` / `训练数据.sql` / `数据库初始化.sql` / `add_email_column.sql` / `add_clinical_2026.sql`）：它们的内容都已被 `BCI.sql` 覆盖；后两个是早期「已有库补列」迁移脚本，现在本地库与远程库均已建全，不再需要。混跑旧脚本会与主文件冲突、缺字段，故删除避免搞错。

---

## 3. 数据表总览（哪些由代码建，哪些只在 SQL 里）

后端 ORM 会自动建这些表（改结构请去 `models/`）：

| 表名 | 对应模型 | 说明 |
|------|----------|------|
| `patient_info` | `Patient` | 患者信息 + 登录账号 |
| `doctor_info` | `Doctor` | 医生信息 |
| `game_level_config` | `GameLevel` | 游戏关卡配置（目标角度/难度） |
| `train_real_time_data` | `TrainingData` | **Unity 实时训练数据**（角度/难度/反馈） |
| `stage_assessment` | `StageAssessment` | 阶段临床评估 |
| `questionnaire_record` | `QuestionnaireRecord` | 患者问卷作答记录（⚠️ **只有 ORM 建表，本文件夹没有它的 .sql**） |
| `experiment_record` | `ExperimentRecord` | 平台实验反馈记录（P300/SSVEP/MI 等） |
| `scale_assessment` | `ScaleAssessment` | 量表评分历史（Fugl-Meyer/Brunnstrom/Barthel/MBI/MMSE） |
| `clinical_assessment` | `ClinicalAssessment` | 10 题临床评估记录（0-4 分 → 康复等级） |
| `training_record` | `TrainingRecord` | 训练记录（会话级汇总，对应前端 trainingRecords） |
| `eeg_session` | `EegSession` | 脑电会话数据（α/β/SMR/θ/δ/ERD/准确率…） |
| `doctor_advice` | `DoctorAdvice` | 医生给患者写的建议 |

只在 SQL 里有、代码没建模的表（需手动执行对应 `.sql` 才会有）：

| 表名 | 来源文件 | 说明 |
|------|----------|------|
| `bci_data` | `bci_data.sql` | 脑电原始/频带功率数据 |
| `questionnaire` | `questionnaire.sql` | 问卷模板主表 |
| `question` | `questionnaire.sql` | 问卷题目表（含 `options` JSON） |

---

## 4. 各表字段说明

### 4.1 patient_info（患者表）
| 字段 | 类型 | 说明 |
|------|------|------|
| patient_id | VARCHAR(20) PK | 患者唯一标识（住院号/身份证后8位） |
| patient_name | VARCHAR(50) | 姓名 |
| gender | CHAR(1) | 性别：男/女 |
| age | INT | 年龄 |
| affected_side | CHAR(1) | 患侧：左/右 |
| stroke_type | VARCHAR(30) | 卒中类型：缺血性/出血性 |
| admission_time | DATETIME | 康复开始时间（默认当前时间） |
| doctor_name | VARCHAR(50) | 主治医生姓名 |
| phone | VARCHAR(20) | 家属电话 |
| remark | TEXT | 临床备注（合并症、禁忌等） |
| pwd | VARCHAR(50) | 登录密码（⚠️ 当前明文，待改哈希） |
| username | VARCHAR(50) UNIQUE | 登录账号 |
| doctor_id | VARCHAR(20) | 主治医生 ID（仅存储，**不是外键**） |
| role | VARCHAR(20) | 角色，默认 `patient` |
| email | VARCHAR(100) | 邮箱（找回密码用，新增） |
| diagnosis | VARCHAR(120) | 诊断（新增，新客户端临床字段） |
| brunnstrom_stage | VARCHAR(10) | Brunnstrom 分期（新增） |
| train_level | VARCHAR(10) | 训练等级：初级/中级/高级/精细（新增） |
| fm_score | INT | Fugl-Meyer 上肢评分 0-66（新增） |
| last_train | DATE | 最近训练日期（新增） |
| adherence | INT | 训练依从率 %（新增） |
| first_visit | DATE | 初诊日期（新增） |
| recovery_progress | TEXT | 康复进度序列(JSON 数组)（新增） |
| game_train_count | INT | 游戏训练次数（新增） |

### 4.2 doctor_info（医生表）/ escort_info（陪同人员表）
结构类似患者：各自有 `*_id`(主键)、`*_name`、`gender`、`phone`、`username`(唯一)、`pwd`、`create_time`、`role`，并新增 `email`（找回密码用）。
陪同表额外有 `relation`（与患者关系）、`patient_id`（关联患者）。

### 4.3 game_level_config（游戏关卡配置表）
| 字段 | 类型 | 说明 |
|------|------|------|
| level_id | INT PK 自增 | 关卡 ID |
| game_name | VARCHAR(50) | 游戏名称，如 `星光舞台` |
| train_part | VARCHAR(30) | 训练部位，如 `前臂旋前+旋后` |
| level_name | VARCHAR(50) | 关卡名称，如 `初级节奏` |
| target_angle | DECIMAL(5,2) | **目标关节角度(°)** —— Unity 据它对达标判定 |
| angle_tolerance | DECIMAL(5,2) | 角度容错度(°)，默认 5 |
| train_duration | INT | 单关训练时长(秒) |
| difficulty | VARCHAR(10) | 难度：简单/中等/困难 |
| game_remark | VARCHAR(200) | 关卡规则说明 |

### 4.4 train_real_time_data（Unity 实时训练数据表）⭐
| 字段 | 类型 | 说明 |
|------|------|------|
| data_id | BIGINT PK 自增 | 记录 ID |
| patient_id | VARCHAR(20) FK | 患者 ID |
| level_id | INT FK | 关卡 ID（决定本次训练的目标角度/难度） |
| train_time | DATETIME | 采集时间（默认当前时间） |
| shoulder_abduction | DECIMAL(5,2) | 肩外展角度(°) |
| elbow_extension | DECIMAL(5,2) | 肘伸展角度(°) |
| forearm_rotation | DECIMAL(5,2) | 前臂旋前/旋后角度(°) |
| action_score | INT | 单动作得分(0-10) |
| is_qualified | TINYINT(1) | 是否达标：0=否，1=是 |
| compensation | VARCHAR(50) | 代偿动作：耸肩/躯干侧倾/腕屈曲/无 |
| compensation_score | INT | 代偿评分(100=无代偿，越低越严重) |
| device_type | VARCHAR(30) | 采集设备，默认 `AR手机` |
| game_score | INT | 游戏得分 |

> 💡 Unity 每次实时上报一帧（WebSocket 事件 `training_frame`），就往这张表插一行。

### 4.5 stage_assessment（阶段临床评估表）
| 字段 | 类型 | 说明 |
|------|------|------|
| assess_id | INT PK 自增 | 评估 ID |
| patient_id | VARCHAR(20) FK | 患者 ID |
| assess_time | DATETIME | 评估时间 |
| assess_cycle | VARCHAR(20) | 评估周期，如 `第1周` |
| avg_shoulder_angle / avg_elbow_angle / avg_forearm_angle | DECIMAL(5,2) | 各关节平均角度 |
| qualified_rate | DECIMAL(5,2) | 动作达标率(%) |
| avg_compensation_score | INT | 平均代偿评分 |
| FMA_UE_score | INT | FMA 上肢量表评分(0-66) |
| ARAT_score | INT | ARAT 上肢功能评分(0-57) |
| doctor_evaluation | TEXT | 医生评估意见 |
| next_train_plan | TEXT | 后续训练计划 |

### 4.6 experiment_record（平台实验反馈记录表，新增）⭐
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT PK 自增 | 记录 ID |
| patient_id | VARCHAR(20) FK | 患者 ID |
| experiment_type | VARCHAR(30) | 实验类型：p300 / ssvep / mi … |
| duration | INT | 实验时长(秒) |
| score | INT | 得分 |
| accuracy | FLOAT | 准确率(0-1) |
| extra_data | TEXT | 附加信息（JSON 文本） |
| created_at | DATETIME | 创建时间 |

> 💡 后端与华南脑控 HybridBCI 平台通信时，平台返回的实验结果会自动写进这张表。

### 4.7 questionnaire_record（问卷作答记录表，ORM 建表）
| 字段 | 类型 | 说明 |
|------|------|------|
| record_id | INT PK 自增 | 记录 ID |
| patient_id | VARCHAR(20) FK | 患者 ID |
| answers | VARCHAR(50) | 10 题答案，逗号分隔，如 `A,B,C,D,...` |
| count_a / count_b / count_c / count_d | INT | 各选项数量 |
| matched_level | VARCHAR(50) | 匹配出的难度等级 |
| matched_level_id | INT | 匹配出的关卡 ID |
| submit_time | DATETIME | 提交时间 |

> ⚠️ 本文件夹**没有** `questionnaire_record` 的 `.sql`，它由后端 ORM 自动建。题目模板在 `questionnaire` / `question` 表里。

### 4.8 其余表（仅 SQL）
- `bci_data`：脑电数据（delta/theta/alpha/beta/gamma 功率、attention、meditation、signal_quality、device_id 等），外键被注释掉。
- `questionnaire`：问卷模板主表（title / description / is_active）。
- `question`：题目表（question_text / options(JSON) / sort_order），通过 `questionnaire_id` 关联模板。

---

## 5. 数据流（这张图一看就懂）

> 注意：架构已升级——Unity **不再连 Flask 的 WebSocket**，而是连独立进程
> `services/bci_bridge_server.py`（**TCP:9999**）；脑电平台也由这个桥接进程去连（**TCP:8000**）。
> Flask 只做 HTTP 接口和 `/monitor` 轮询（每 500ms 拉一次），不再有 socketio / eventlet。

```
   Unity(Link.cs)
      │  TCP :9999
      ▼
   bci_bridge_server.py  ──TCP :8000──▶  HybridBCI 脑电平台
      │  ▲                                   │
      │  │ 平台算法结果(ipc_algorithm_test)    │ 拼写/控制指令(SELECT/FORWARD/...)
      │  ▼                                   │
      │  train_real_time_data   experiment_record
      │
      │  (监控页数据流) HTTP 轮询 /api/monitor/data 每 500ms
      ▼
   Flask app.py(:5000) ──▶ MySQL
      ├─ /api/patients /assessment /scales /eeg /advice /training  (新客户端 Kyouic 后端)
      └─ /api/auth /questionnaire /training(逐帧) /monitor

   前端/医生 ── 提交问卷 ──▶ questionnaire_record   题目来自 questionnaire / question
   医生     ── 录入评估 ──▶ stage_assessment
```
一句话：**Unity 负责采角度、平台负责脑机算法、独立桥接进程负责把两边的数据收进 MySQL，Flask 只做网页接口和监控页轮询。**

---

## 6. 快速上手（本地手工建一套库看数据）

```sql
-- 0) SQL 文件开头用 USE BCI; 切到远程 1Panel 的库；
--    若在本地 MySQL 执行，请先把各文件里的 BCI 改成 stroke_rehab_game。
--    库需预先创建好（utf8mb4 / utf8mb4_general_ci），账号需有该库权限。
-- 1) 用 MySQL/MariaDB 客户端执行（按顺序）
source BCI.sql;              -- 主表 + 示例数据 + 索引（唯一主文件）
source experiment_record.sql;-- 平台实验反馈表（可选，BCI.sql 未含）
source bci_data.sql;         -- （可选）脑电数据表
source questionnaire.sql;    -- （可选）问卷模板 + 10 道题
```

或者用后端代码自动建（推荐，最省事）：
```bash
# 配好 backend/config.py 里的 MySQL 账号密码后直接启动后端
python app.py
# db.create_all() 会自动建好 models 里定义的所有表
```

---

## 7. 注意事项 / 已知待优化

- 🔐 **密码明文存储**：`patient_info.pwd` / `doctor_info.pwd` 目前是明文，生产环境务必改密码哈希（如 werkzeug `generate_password_hash`）。（陪同人员 `escort_info` 模型已移除，仅作遗留表，不再有对应代码读写。）
- 🧩 **SQL 已精简**：原 `patient_info.sql` / `doctor.sql` / `escort_info.sql` / `game_level_connfig.sql` / `train_real_time_data.sql` / `stage_assesment.sql` 等碎片文件（重复/旧版）已删除，业务表一律以 `BCI.sql` 为准，避免混跑冲突。
- 🔠 **字符集/排序规则必须统一为 `utf8mb4` + `utf8mb4_general_ci`**，且要与 `config.py` 连接串里的 `collation=utf8mb4_general_ci` 一致。两边不一致时，建外键会报 `[HY000][3780] Referencing column ... are incompatible`（典型：`escort_info`/`stage_assessment`/`train_real_time_data` 指向 `patient_info` 的外键）。改 collation 时 `config.py` 与所有 `.sql` 一起改。
- 🔤 **个别类型不一致**：模型里 `affected_side` 是 `String(2)` 而 SQL 是 `CHAR(1)`，纯显示层面，统一即可。
- 🗑️ **实时表会很大**：`train_real_time_data` 每帧一行，量增长快，建议定期备份/归档。
- 🔗 **外键都是 CASCADE**：删除患者会连带删除其训练/评估/实验记录，操作前确认。
- 🕒 所有时间字段默认取当前时间戳。

---

## 8. 与前端 / Unity 对接的 4 件事（后端职责速查）

1. **问卷系统（前端 ↔ 数据库）**：医生/患者登录用 `/api/auth/*`；问卷题目 `/api/questionnaire/questions`、提交 `/api/questionnaire/submit`（落到 `questionnaire_record`）。
   > ⚠️ 原 `frontend/` 静态目录已移除，`routes/frontend.py` 仍指向它（访问 `/` 会 404）。如需托管前端页面，把 `frontend.py` 的目录改指向实际前端（如 `Kyouic/app/`）。
2. **第一个游戏（Unity ↔ 桥接进程 ↔ HybridBCI 平台）**：Unity 的 `Link.cs` 通过 **TCP:9999** 连独立进程 `services/bci_bridge_server.py`（不再是 Flask WebSocket / `HybridBCIBridge`）；桥接进程再连脑电平台 **TCP:8000**。平台每次算法结果由桥接进程写进 `experiment_record`，拼写/控制指令由桥接翻译成 `SELECT`/`FORWARD` 等推回 Unity。
3. **第二个游戏（大臂康复，Unity ↔ 桥接进程 ↔ MySQL）**：Unity 每帧 `training_frame`（肩外展等角度）经 TCP:9999 发给桥接进程，落库 `train_real_time_data`，**不经过脑电平台**；Flask 的 `/monitor` 页面通过 HTTP 轮询 `/api/monitor/data`（每 500ms 一次）读出最新一帧显示。
4. **新客户端 Kyouic 后端（患者档案 / 临床评估 / 量表 / 脑电 / 建议 / 训练记录）**：本次新增 5 张表 + 一组接口（详见 `docs/Kyouic_后端对接清单.md`）：
   - 患者：`/api/patients`（列表/搜索/详情/更新档案）→ `patient_info`(+临床列) / `scale_assessment` / `doctor_advice`
   - 临床评估：`/api/assessment`（10 题 0-4 → 分级）→ `clinical_assessment`
   - 量表：`/api/scales`（5 大量表元数据 + 评分历史）→ `scale_assessment`
   - 脑电：`/api/eeg`（会话导入 / 列表 / 统计）→ `eeg_session`
   - 建议：`/api/advice`（增/查）→ `doctor_advice`
   - 训练：在原有 `/api/training` 下新增 `/record`、`/records`（会话级）→ `training_record`

> ⚠️ `email` 字段与临床字段（`diagnosis`/`train_level`/…）及 5 张临床表均已包含在 `BCI.sql` 中，新库直接跑 `BCI.sql` 即可建全，无需额外迁移脚本。
> 💡 若以后遇到「早期旧库缺列」的场景：ORM 的 `db.create_all()` 只会建表不会补列，需手工 `ALTER TABLE ... ADD COLUMN` 补齐（原则：先查列是否存在再补，避免重复报错）。原迁移脚本已删除。
