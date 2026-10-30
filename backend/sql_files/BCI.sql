-- =====================================================================
-- 主文件（最全）：脑卒中康复游戏数据库 完整建表 + 示例数据 + 索引
-- ---------------------------------------------------------------------
-- ⭐ 这是唯一真源(Single Source of Truth)。
--   手工建库时：直接执行本文件即可（已含 建库 + USE + 建表 + 示例数据 + 索引）。
--   email 列已随本文件建好（找回密码功能用）。
--   平台实验反馈表另见 experiment_record.sql（再补跑一份即可）。
--
-- ⚠️ 字符集/排序规则必须与 backend/config.py 完全一致，否则建外键时会报：
--      [HY000][3780] Referencing column ... and referenced column ...
--      in foreign key constraint ... are incompatible
--    原因：外键两边的列 collation 不一致（一边 general_ci、一边 unicode_ci）。
--    config.py 连接串用的是 charset=utf8mb4&collation=utf8mb4_general_ci，
--    因此本文件全部统一为 utf8mb4 + utf8mb4_general_ci。
--
-- 说明：
--   · 真实运行的库由后端 ORM（db.create_all）自动创建，本文件主要用于
--     “看表结构 / 本地手动建一套库 / 备份参考”。
--   · 改表结构请优先改 backend/models/*.py，再同步到这里。
-- =====================================================================

-- 让本次客户端连接也使用 utf8mb4，避免中文乱码
SET NAMES utf8mb4;

-- 创建数据库（已存在则保持原样；下面每张表都显式声明 COLLATE，保证彼此一致）
CREATE DATABASE IF NOT EXISTS stroke_rehab_game
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;

USE stroke_rehab_game;

-- ======================= 1. 患者表（包含所有字段） =======================
-- 患者基础信息 + 登录账号（patient_id 同时是登录后的 JWT 身份）
CREATE TABLE IF NOT EXISTS patient_info (
    patient_id VARCHAR(20) PRIMARY KEY COMMENT '患者ID',
    patient_name VARCHAR(50) NOT NULL COMMENT '患者姓名',
    gender CHAR(1) NOT NULL COMMENT '性别：男/女',
    age INT NOT NULL COMMENT '年龄',
    affected_side CHAR(1) NOT NULL COMMENT '患侧：左/右',
    stroke_type VARCHAR(30) NOT NULL COMMENT '卒中类型',
    admission_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '康复开始时间',
    doctor_name VARCHAR(50) COMMENT '主治医生姓名',
    phone VARCHAR(20) COMMENT '家属电话',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱（找回密码用）',
    remark TEXT COMMENT '备注',
    pwd VARCHAR(50) COMMENT '登录密码',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
    doctor_id VARCHAR(20) COMMENT '关联医生ID',
    role VARCHAR(20) DEFAULT 'patient' COMMENT '角色',
    -- ↓↓↓ 新客户端 Kyouic 临床康复字段（与 models/user.py.Patient 对齐）↓↓↓
    diagnosis VARCHAR(120) COMMENT '诊断，如 脑梗死后遗症（右侧偏瘫）',
    brunnstrom_stage VARCHAR(10) COMMENT 'Brunnstrom 分期：Ⅰ~Ⅵ',
    train_level VARCHAR(10) DEFAULT '初级' COMMENT '训练等级：初级/中级/高级/精细',
    fm_score INT DEFAULT 0 COMMENT 'Fugl-Meyer 上肢评分(0-66)',
    last_train DATE COMMENT '最近训练日期',
    adherence INT DEFAULT 0 COMMENT '训练依从率(%)',
    first_visit DATE COMMENT '初诊日期',
    recovery_progress TEXT COMMENT '康复进度序列(JSON 数组)',
    game_train_count INT DEFAULT 0 COMMENT '游戏训练次数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='患者信息表';

-- ======================= 2. 游戏关卡配置表 =======================
-- 每个游戏(星光舞台/星际翼航/肘伸展采水晶)的关卡：目标角度/难度/时长
CREATE TABLE IF NOT EXISTS game_level_config (
    level_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '关卡ID',
    game_name VARCHAR(50) NOT NULL COMMENT '游戏名称',
    train_part VARCHAR(30) NOT NULL COMMENT '训练部位',
    level_name VARCHAR(50) NOT NULL COMMENT '关卡名称',
    target_angle DECIMAL(5,2) NOT NULL COMMENT '目标角度',
    angle_tolerance DECIMAL(5,2) DEFAULT 5.00 COMMENT '容错度',
    train_duration INT NOT NULL COMMENT '训练时长(秒)',
    difficulty VARCHAR(10) NOT NULL COMMENT '难度',
    game_remark VARCHAR(200) COMMENT '规则说明'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- 插入关卡数据（示例）
INSERT IGNORE INTO game_level_config (game_name, train_part, level_name, target_angle, angle_tolerance, train_duration, difficulty, game_remark) VALUES
('星际翼航', '肩外展+内收', '航道1（入门）', 60.00, 8.00, 300, '简单', '抬胳膊够60°'),
('星际翼航', '肩外展+内收', '航道2（进阶）', 90.00, 5.00, 360, '中等', '抬胳膊够90°'),
('肘伸展采水晶', '肘关节伸展', '入门关', 10.00, 10.00, 240, '简单', '肘伸展≥10°'),
('肘伸展采水晶', '肘关节伸展', '大师关', 0.00, 3.00, 300, '困难', '肘完全伸直0°'),
('星光舞台', '前臂旋前+旋后', '初级节奏', 90.00, 10.00, 180, '简单', '节拍慢'),
('星光舞台', '前臂旋前+旋后', '高级节奏', 90.00, 5.00, 240, '困难', '节拍快');

-- ======================= 3. 训练实时数据表 =======================
-- Unity 每帧上报一帧(角度/难度/反馈)就插一行；量增长快，注意归档
-- 索引直接写在建表语句里（KEY ...），这样重复执行本文件也不会报
-- “Duplicate key name”（比单独的 CREATE INDEX 更安全、可反复运行）
CREATE TABLE IF NOT EXISTS train_real_time_data (
    data_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    level_id INT NOT NULL,
    train_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    shoulder_abduction DECIMAL(5,2),
    elbow_extension DECIMAL(5,2),
    forearm_rotation DECIMAL(5,2),
    action_score INT DEFAULT 0,
    is_qualified TINYINT(1) DEFAULT 0,
    compensation VARCHAR(50),
    compensation_score INT DEFAULT 100,
    device_type VARCHAR(30) DEFAULT 'AR手机',
    game_score INT DEFAULT 0,
    KEY idx_patient_id (patient_id),
    KEY idx_level_id (level_id),
    KEY idx_train_time (train_time),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (level_id) REFERENCES game_level_config(level_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 4. 阶段评估表 =======================
CREATE TABLE IF NOT EXISTS stage_assessment (
    assess_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    assess_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    assess_cycle VARCHAR(20) NOT NULL,
    avg_shoulder_angle DECIMAL(5,2),
    avg_elbow_angle DECIMAL(5,2),
    avg_forearm_angle DECIMAL(5,2),
    qualified_rate DECIMAL(5,2),
    avg_compensation_score INT,
    FMA_UE_score INT DEFAULT 0,
    ARAT_score INT DEFAULT 0,
    doctor_evaluation TEXT,
    next_train_plan TEXT,
    KEY idx_assess_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 5. 医生表 =======================
CREATE TABLE IF NOT EXISTS doctor_info (
    doctor_id VARCHAR(20) PRIMARY KEY,
    doctor_name VARCHAR(50) NOT NULL,
    gender CHAR(2),
    department VARCHAR(50),
    phone VARCHAR(20),
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱（找回密码用）',
    username VARCHAR(50) NOT NULL,
    pwd VARCHAR(50) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) DEFAULT 'doctor'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 6. 陪同人员表 =======================
CREATE TABLE IF NOT EXISTS escort_info (
    escort_id VARCHAR(20) PRIMARY KEY,
    escort_name VARCHAR(50) NOT NULL,
    gender CHAR(2),
    relation VARCHAR(30),
    patient_id VARCHAR(20),
    phone VARCHAR(20),
    username VARCHAR(50) NOT NULL UNIQUE,
    pwd VARCHAR(50) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) DEFAULT 'companion',
    KEY idx_escort_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 7. 量表评分历史表 =======================
-- 对应新客户端「康复量表」：患者各量表(Fugl-Meyer/Brunnstrom/Barthel/MBI/MMSE)评分历史
CREATE TABLE IF NOT EXISTS scale_assessment (
    assess_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    assess_date DATE DEFAULT NULL,
    scale_key VARCHAR(20) NOT NULL COMMENT 'fugl-meyer/brunnstorm/barthel/adl/mmse',
    scale_name VARCHAR(50) COMMENT '量表显示名',
    score_text VARCHAR(30) COMMENT '评分文本，如 38/100 或 III期',
    result_text VARCHAR(50) COMMENT '结果描述，如 明显运动障碍',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_scale_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 8. 临床评估记录表 =======================
-- 对应新客户端 10 题临床评估（每题 0-4 分）→ 康复等级
CREATE TABLE IF NOT EXISTS clinical_assessment (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    answers VARCHAR(50) NOT NULL COMMENT '10题作答(0-4)，逗号分隔',
    total_score INT DEFAULT 0 COMMENT '总分(0-40)',
    mapped_level VARCHAR(10) COMMENT '康复等级：初级/中级/高级/精细',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_clinical_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 9. 训练记录表（会话级） =======================
-- 对应新客户端 trainingRecords：一次训练的汇总（与逐帧 train_real_time_data 互补）
CREATE TABLE IF NOT EXISTS training_record (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    patient_name VARCHAR(50),
    level VARCHAR(10) COMMENT '初级/中级/高级/精细',
    game_name VARCHAR(50),
    duration_min INT DEFAULT 0 COMMENT '训练时长(分钟)',
    result_text VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_tr_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 10. 脑电会话数据表 =======================
-- 对应新客户端「脑电分析」：每次训练的 EEG 指标
CREATE TABLE IF NOT EXISTS eeg_session (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    session_no INT DEFAULT 0,
    alpha DECIMAL(6,2) DEFAULT 0,
    beta DECIMAL(6,2) DEFAULT 0,
    smr DECIMAL(6,2) DEFAULT 0 COMMENT 'SMR感觉运动节律(12-15Hz)',
    theta DECIMAL(6,2) DEFAULT 0,
    delta DECIMAL(6,2) DEFAULT 0,
    erd DECIMAL(6,2) DEFAULT 0 COMMENT 'ERD事件相关去同步(%)',
    accuracy DECIMAL(6,2) DEFAULT 0 COMMENT '游戏准确率(%)',
    attention DECIMAL(6,2) DEFAULT 0 COMMENT '专注度',
    relaxation DECIMAL(6,2) DEFAULT 0 COMMENT '放松度',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_eeg_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 11. 医生建议表 =======================
-- 对应新客户端「康复建议」：医生给患者写的建议
CREATE TABLE IF NOT EXISTS doctor_advice (
    advice_id INT PRIMARY KEY AUTO_INCREMENT,
    doctor_id VARCHAR(20),
    patient_id VARCHAR(20) NOT NULL,
    patient_name VARCHAR(50),
    advice_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_advice_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ======================= 插入数据 =======================
-- 患者张三
INSERT IGNORE INTO patient_info (patient_id, patient_name, gender, age, affected_side, stroke_type, doctor_name, phone, remark, pwd, username, role)
VALUES ('202505001', '张三', '男', 58, '右', '缺血性', '李医生', '13800138000', '高血压病史10年', 'Zhang123456!', 'patient_zhangsan', 'patient');

-- 患者李四
INSERT IGNORE INTO patient_info (patient_id, patient_name, gender, age, affected_side, stroke_type, admission_time, doctor_name, phone, remark, pwd, username, role)
VALUES ('202505002', '李四', '男', 58, '右', '缺血性卒中', '2025-03-17', '王医生', '13800138001', '康复训练初期', 'Xka061201!', 'patient_lisi', 'patient');

-- 医生数据
INSERT IGNORE INTO doctor_info (doctor_id, doctor_name, gender, department, phone, username, pwd) VALUES
('DOC2025001', '李医生', '男', '康复医学科', '13900139000', 'doctor_li', 'Li123456!'),
('DOC2025002', '王医生', '女', '康复医学科', '13900139001', 'doctor_wang', 'Wang123456!');

-- 关联患者与医生
UPDATE patient_info SET doctor_id = 'DOC2025002' WHERE patient_id = '202505002';
UPDATE patient_info SET doctor_id = 'DOC2025001' WHERE patient_id = '202505001';

-- 训练数据（张三，关卡1）
INSERT IGNORE INTO train_real_time_data (patient_id, level_id, shoulder_abduction, action_score, is_qualified, compensation, compensation_score, game_score) VALUES
('202505001', 1, 58.50, 8, 1, '无', 100, 80),
('202505001', 1, 62.00, 9, 1, '无', 100, 89),
('202505001', 1, 52.00, 5, 0, '轻微耸肩', 85, 94);

-- 阶段评估（张三）
INSERT IGNORE INTO stage_assessment (patient_id, assess_cycle, avg_shoulder_angle, qualified_rate, avg_compensation_score, FMA_UE_score, ARAT_score, doctor_evaluation, next_train_plan)
VALUES ('202505001', '第1周', 57.50, 66.67, 95, 30, 25, '右侧肩外展平均57.5°，达标率66.67%', '继续航道1训练');

-- 陪同人员
INSERT IGNORE INTO escort_info (escort_id, escort_name, gender, relation, patient_id, phone, username, pwd) VALUES
('ESC2025001', '李母', '女', '母亲', '202505002', '13800138002', 'escort_lisi', 'Esc123456!'),
('ESC2025002', '张父', '男', '父亲', '202505001', '13700137000', 'escort_zhang', 'Esc123456!');

-- 最终验证
SELECT * FROM patient_info;
