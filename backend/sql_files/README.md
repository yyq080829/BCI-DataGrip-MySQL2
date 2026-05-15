# BCI-DataGrip-MySQL2
AR脑卒中上肢康复系统数据库

一.项目概述
本项目是一个基于游戏化设计的脑卒中上肢康复训练系统，通过AR技术监测患者关节活动角度，结合趣味性游戏提升康复训练效果。数据库采用MySQL，主要用于存储患者信息、游戏关卡配置、训练数据、临床评估结果等。
数据库基本信息
数据库名称: stroke_rehab_game
字符集: utf8mb4
排序规则: utf8mb4_unicode_ci
引擎: InnoDB


二.数据表结构
1. patient_info (患者基础信息表)
   | 字段 | 类型 | 是否为空 | 默认值 | 说明 |
|------|------|----------|--------|------|
| patient_id | VARCHAR(20) | NOT NULL | - | 患者唯一标识（住院号/身份证后8位） |
| patient_name | VARCHAR(50) | NOT NULL | - | 患者姓名 |
| gender | CHAR(1) | NOT NULL | - | 性别：男/女 |
| age | INT | NOT NULL | - | 患者年龄 |
| affected_side | CHAR(1) | NOT NULL | - | 患侧：左/右 |
| stroke_type | VARCHAR(30) | NOT NULL | - | 卒中类型：缺血性/出血性 |
| admission_time | DATETIME | - | CURRENT_TIMESTAMP | 康复开始时间 |
| doctor_name | VARCHAR(50) | - | NULL | 主治医生 |
| phone | VARCHAR(20) | - | NULL | 家属联系方式 |
| remark | TEXT | - | NULL | 临床备注（合并症、禁忌等） |
| pwd | VARCHAR(50) | - | NULL | 登录密码 |
| doctor_id | VARCHAR(20) | - | NULL | 医生ID |
| username | VARCHAR(50) | - | NULL | 登录账号（唯一） |
| role | VARCHAR(20) | - | NULL | 角色 |


2. game_level_config (游戏关卡配置表)
| 字段 | 类型 | 是否为空 | 默认值 | 说明 |
|------|------|----------|--------|------|
| level_id | INT | NOT NULL | - | 关卡自增ID（主键） |
| game_name | VARCHAR(50) | NOT NULL | - | 康复游戏名称 |
| train_part | VARCHAR(30) | NOT NULL | - | 训练部位/动作 |
| level_name | VARCHAR(50) | NOT NULL | - | 关卡名称 |
| target_angle | DECIMAL(5,2) | NOT NULL | - | 目标关节角度(°) |
| angle_tolerance | DECIMAL(5,2) | - | 5.00 | 角度容错度(°) |
| train_duration | INT | NOT NULL | - | 单关训练时长(秒) |
| difficulty | VARCHAR(10) | NOT NULL | - | 难度等级：简单/中等/困难 |
| game_remark | VARCHAR(200) | - | NULL | 关卡规则说明 |


3. train_real_time_data (训练实时数据表)
| 字段 | 类型 | 是否为空 | 默认值 | 说明 |
|------|------|----------|--------|------|
| data_id | BIGINT | NOT NULL | - | 实时数据自增ID |
| patient_id | VARCHAR(20) | NOT NULL | - | 患者ID |
| level_id | INT | NOT NULL | - | 关卡ID |
| train_time | DATETIME | - | CURRENT_TIMESTAMP | 动作采集时间 |
| shoulder_abduction | DECIMAL(5,2) | - | NULL | 肩外展角度(°) |
| elbow_extension | DECIMAL(5,2) | - | NULL | 肘伸展角度(°) |
| forearm_rotation | DECIMAL(5,2) | - | NULL | 前臂旋前/旋后角度(°) |
| action_score | INT | - | 0 | 单动作得分(0-10) |
| is_qualified | TINYINT(1) | - | 0 | 动作是否达标：0=否，1=是 |
| compensation | VARCHAR(50) | - | NULL | 代偿动作：耸肩/躯干侧倾/腕屈曲/无 |
| compensation_score | INT | - | 100 | 代偿评分(100=无代偿，分数越低越严重) |
| device_type | VARCHAR(30) | - | 'AR手机' | 数据采集设备 |
| game_score | INT | - | 0 | 游戏累计得分 |


4. stage_assessment (阶段临床评估数据表)
| 字段 | 类型 | 是否为空 | 默认值 | 说明 |
|------|------|----------|--------|------|
| assess_id | INT | NOT NULL | - | 评估自增ID（主键） |
| patient_id | VARCHAR(20) | NOT NULL | - | 患者ID |
| assess_time | DATETIME | - | CURRENT_TIMESTAMP | 评估时间 |
| assess_cycle | VARCHAR(20) | NOT NULL | - | 评估周期：第1周/康复中期等 |
| avg_shoulder_angle | DECIMAL(5,2) | - | NULL | 平均肩外展角度(°) |
| avg_elbow_angle | DECIMAL(5,2) | - | NULL | 平均肘伸展角度(°) |
| avg_forearm_angle | DECIMAL(5,2) | - | NULL | 平均前臂旋转角度(°) |
| qualified_rate | DECIMAL(5,2) | - | NULL | 动作达标率(%) |
| avg_compensation_score | INT | - | NULL | 平均代偿评分 |
| FMA_UE_score | INT | - | 0 | FMA上肢量表评分(0-66) |
| ARAT_score | INT | - | 0 | ARAT上肢功能评分(0-57) |
| doctor_evaluation | TEXT | - | NULL | 医生评估意见 |
| next_train_plan | TEXT | - | NULL | 后续训练计划 |


5. doctor_info (医生信息表)
| 字段 | 类型 | 是否为空 | 默认值 | 说明 |
|------|------|----------|--------|------|
| doctor_id | VARCHAR(20) | NOT NULL | - | 医生ID（主键） |
| doctor_name | VARCHAR(50) | NOT NULL | - | 医生姓名 |
| gender | CHAR(2) | - | NULL | 性别 |
| department | VARCHAR(50) | - | NULL | 科室（如康复科） |
| phone | VARCHAR(20) | - | NULL | 手机号 |
| username | VARCHAR(50) | NOT NULL | - | 登录账号（和姓名区分） |
| pwd | VARCHAR(50) | NOT NULL | - | 登录密码 |
| create_time | DATETIME | - | CURRENT_TIMESTAMP | 创建时间 |
| role | VARCHAR(20) | - | NULL | 角色 |


6. escort_info (陪同人员表)
| 字段 | 类型 | 是否为空 | 默认值 | 说明 |
|------|------|----------|--------|------|
| escort_id | VARCHAR(20) | NOT NULL | - | 陪同人员ID（主键） |
| escort_name | VARCHAR(50) | NOT NULL | - | 陪同人员姓名 |
| gender | CHAR(2) | - | NULL | 性别 |
| relation | VARCHAR(30) | - | NULL | 与患者关系（家属/护工等） |
| patient_id | VARCHAR(20) | - | NULL | 关联患者ID（仅存储，暂不关联） |
| phone | VARCHAR(20) | - | NULL | 手机号 |
| username | VARCHAR(50) | NOT NULL | - | 登录账号（唯一） |
| pwd | VARCHAR(50) | NOT NULL | - | 登录密码 |
| create_time | DATETIME | - | CURRENT_TIMESTAMP | 创建时间 |
| role | VARCHAR(20) | - | NULL | 角色 |


7.外键关系
train_real_time_data.patient_id → patient_info.patient_id
train_real_time_data.level_id → game_level_config.level_id
stage_assessment.patient_id → patient_info.patient_id


8.索引
idx_patient_id: 在 train_real_time_data 表上的 patient_id 列
idx_level_id: 在 train_real_time_data 表上的 level_id 列
idx_train_time: 在 train_real_time_data 表上的 train_time 列


9.使用示例
(1)查询特定患者的训练历史
SELECT * FROM train_real_time_data 
WHERE patient_id = '202505001' 
ORDER BY train_time DESC LIMIT 10;

(2)获取某关卡的平均成绩
SELECT AVG(action_score) as avg_score, 
       COUNT(*) as total_attempts 
FROM train_real_time_data 
WHERE level_id = 1;

（3）查看患者阶段评估结果
SELECT * FROM stage_assessment 
WHERE patient_id = '202505001' 
ORDER BY assess_time DESC;



三.注意事项
所有时间字段默认为当前时间戳
患者ID建议使用住院号或身份证后8位确保唯一性
训练数据表包含大量实时数据，建议定期备份和清理
外键约束使用CASCADE模式，删除患者信息时会自动删除相关数据
密码字段应使用加密存储，生产环境注意安全



















