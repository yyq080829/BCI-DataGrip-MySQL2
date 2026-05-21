-- 创建数据库
CREATE DATABASE IF NOT EXISTS stroke_rehab_game
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE stroke_rehab_game;

-- ======================= 1. 患者表（包含所有字段） =======================
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
    remark TEXT COMMENT '备注',
    pwd VARCHAR(50) COMMENT '登录密码',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
    doctor_id VARCHAR(20) COMMENT '关联医生ID',
    role VARCHAR(20) DEFAULT 'patient' COMMENT '角色'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='患者信息表';

-- ======================= 2. 游戏关卡配置表 =======================
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 插入关卡数据
INSERT IGNORE INTO game_level_config (game_name, train_part, level_name, target_angle, angle_tolerance, train_duration, difficulty, game_remark) VALUES
('星际翼航', '肩外展+内收', '航道1（入门）', 60.00, 8.00, 300, '简单', '抬胳膊够60°'),
('星际翼航', '肩外展+内收', '航道2（进阶）', 90.00, 5.00, 360, '中等', '抬胳膊够90°'),
('肘伸展采水晶', '肘关节伸展', '入门关', 10.00, 10.00, 240, '简单', '肘伸展≥10°'),
('肘伸展采水晶', '肘关节伸展', '大师关', 0.00, 3.00, 300, '困难', '肘完全伸直0°'),
('星光舞台', '前臂旋前+旋后', '初级节奏', 90.00, 10.00, 180, '简单', '节拍慢'),
('星光舞台', '前臂旋前+旋后', '高级节奏', 90.00, 5.00, 240, '困难', '节拍快');

-- ======================= 3. 训练实时数据表 =======================
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
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (level_id) REFERENCES game_level_config(level_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ======================= 5. 医生表 =======================
CREATE TABLE IF NOT EXISTS doctor_info (
    doctor_id VARCHAR(20) PRIMARY KEY,
    doctor_name VARCHAR(50) NOT NULL,
    gender CHAR(2),
    department VARCHAR(50),
    phone VARCHAR(20),
    username VARCHAR(50) NOT NULL,
    pwd VARCHAR(50) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    role VARCHAR(20) DEFAULT 'doctor'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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

-- 索引
CREATE INDEX idx_patient_id ON train_real_time_data(patient_id);
CREATE INDEX idx_level_id ON train_real_time_data(level_id);
CREATE INDEX idx_train_time ON train_real_time_data(train_time);

-- 最终验证
SELECT * FROM patient_info;