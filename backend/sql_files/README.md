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
| 数据库名 | `stroke_rehab_game` |
| 字符集 | `utf8mb4` |
| 排序规则 | `utf8mb4_general_ci`（必须与 `config.py` 一致，否则外键报 3780） |
| 引擎 | `InnoDB` |
| 连接方式 | MySQL（`backend/config.py` 里配置账号密码） |

---

## 2. 这些 SQL 文件分别是干什么的

> 建议：**手工建库只跑 `BCI.sql` 一个主文件即可**（它已含 `CREATE DATABASE + USE`、所有业务表、示例数据与索引）。其余文件是可选的扩展/迁移，按需单独跑，不要重复执行。

| 文件名 | 作用 | 备注 |
|--------|------|------|
| ⭐ `BCI.sql` | **【唯一主文件·最全】** 建库 + USE + 完整建表 + 示例数据 + 索引 | 认准它当唯一真源，包含 patient/doctor/escort/关卡/实时训练/阶段评估 |
| `experiment_record.sql` | 平台实验反馈记录表 | 配合后端连接华南脑控平台（BCI.sql 未含，需另跑） |
| `add_email_column.sql` | **已有库补 email 列**（找回密码用） | 仅老库需要；新库由 BCI.sql 已带 email，不用跑 |
| `bci_data.sql` | 脑电数据表（无外键、无 ORM 模型） | 可选，仅在 SQL 里有，需手动建 |
| `questionnaire.sql` | 问卷**模板**主表 + 问题表，并插入 10 道题 | 可选，问卷题目来自这里（运行时后端硬编码，不查此表） |

> 🗑️ 已删除的冗余碎片文件（`patient_info.sql` / `doctor.sql` / `escort_info.sql` / `game_level_connfig.sql` / `train_real_time_data.sql` / `stage_assesment.sql` / `插入游戏关卡配置数据.sql` / `阶段评估数据.sql` / `训练数据.sql` / `数据库初始化.sql`）：它们的内容都已被 `BCI.sql` 覆盖，且部分是缺字段的旧版或文件名拼写错误的重复表，混跑会与主文件冲突、缺字段。现已删除，避免建表时搞错。

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

```
                 WebSocket(/unity)                  TCP(8000)
   Unity  ── training_frame ──▶ train_real_time_data    （实时角度/难度/反馈落库）
     │
     ├── p300_start / p300_flash / p300_stop ─┐
     │                                        ▼
     └── training_result ───────────▶  后端(HybridBCIBridge)  ──▶  华南脑控平台
                                            │  platform 返回实验结果
                                            ▼
                                      experiment_record（平台反馈落库）

   前端 ── 提交问卷 ──▶ questionnaire_record       题目来自 questionnaire / question
   医生 ── 录入评估 ──▶ stage_assessment
```

一句话：**Unity 负责采角度、平台负责脑机算法、后端负责把两边的数据都收进 MySQL。**

---

## 6. 快速上手（本地手工建一套库看数据）

```sql
-- 1) 用 MySQL 客户端执行（按顺序）
source BCI.sql;              -- 建库 + USE + 主表 + 示例数据 + 索引（唯一主文件）
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

- 🔐 **密码明文存储**：`patient_info.pwd` / `doctor_info.pwd` / `escort_info.pwd` 目前是明文，生产环境务必改密码哈希（如 werkzeug `generate_password_hash`）。
- 🧩 **SQL 已精简**：原 `patient_info.sql` / `doctor.sql` / `escort_info.sql` / `game_level_connfig.sql` / `train_real_time_data.sql` / `stage_assesment.sql` 等碎片文件（重复/旧版）已删除，业务表一律以 `BCI.sql` 为准，避免混跑冲突。
- 🔠 **字符集/排序规则必须统一为 `utf8mb4` + `utf8mb4_general_ci`**，且要与 `config.py` 连接串里的 `collation=utf8mb4_general_ci` 一致。两边不一致时，建外键会报 `[HY000][3780] Referencing column ... are incompatible`（典型：`escort_info`/`stage_assessment`/`train_real_time_data` 指向 `patient_info` 的外键）。改 collation 时 `config.py` 与所有 `.sql` 一起改。
- 🔤 **个别类型不一致**：模型里 `affected_side` 是 `String(2)` 而 SQL 是 `CHAR(1)`，纯显示层面，统一即可。
- 🗑️ **实时表会很大**：`train_real_time_data` 每帧一行，量增长快，建议定期备份/归档。
- 🔗 **外键都是 CASCADE**：删除患者会连带删除其训练/评估/实验记录，操作前确认。
- 🕒 所有时间字段默认取当前时间戳。

---

## 8. 与前端 / Unity 对接的 3 件事（后端职责速查）

1. **问卷系统（前端 ↔ 数据库）**：医生/患者登录用 `/api/auth/*`；问卷题目 `/api/questionnaire/questions`、提交 `/api/questionnaire/submit`（落到 `questionnaire_record`）。`app.py` 同时托管 `frontend/` 静态文件，访问 `/` 直接打开问卷页 `康游智创(5).html`。
2. **第一个游戏（Unity ↔ HybridBCI 平台 ↔ MySQL）**：脑机游戏经 `HybridBCIBridge` 与平台 TCP 通信；游戏结束后平台存一份，后端再"导出"一份到 `experiment_record` + `train_real_time_data`。
3. **第二个游戏（Unity ↔ MySQL 直连）**：大臂康复数据由 Unity 每帧 `training_frame` 直接写 `train_real_time_data`，并经 `/monitor` 实时显示，**不经过脑电平台**。

> ⚠️ 新增 `email` 字段用于找回密码：新建库会由 ORM 自动建列；**已有库请先执行 `sql_files/add_email_column.sql`**（ALTER）否则注册/找回密码会报 `Unknown column 'email'`。
