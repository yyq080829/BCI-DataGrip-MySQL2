-- =====================================================================
-- 迁移脚本：为新客户端 Kyouic 补齐字段与表（针对【已存在】的库）
-- ---------------------------------------------------------------------
-- 说明：
--   · 后端 ORM 的 db.create_all() 只会"建不存在的表"，不会给已存在的
--     patient_info 追加新列。若你的 stroke_rehab_game 库是旧版本建的，
--     直接跑本文件即可补齐，无需删库重建。
--   · 全新库直接执行 BCI.sql 即可，本文件可跳过。
--   · 所有新增表/列都用 IF NOT EXISTS / 容错写法，可反复执行。
-- =====================================================================

USE stroke_rehab_game;

-- ① 给 patient_info 追加临床字段（已存在则跳过）
ALTER TABLE patient_info
    ADD COLUMN diagnosis VARCHAR(120) COMMENT '诊断' AFTER role,
    ADD COLUMN brunnstrom_stage VARCHAR(10) COMMENT 'Brunnstrom分期' AFTER diagnosis,
    ADD COLUMN train_level VARCHAR(10) DEFAULT '初级' COMMENT '训练等级' AFTER brunnstrom_stage,
    ADD COLUMN fm_score INT DEFAULT 0 COMMENT 'Fugl-Meyer评分' AFTER train_level,
    ADD COLUMN last_train DATE COMMENT '最近训练日期' AFTER fm_score,
    ADD COLUMN adherence INT DEFAULT 0 COMMENT '训练依从率%' AFTER last_train,
    ADD COLUMN first_visit DATE COMMENT '初诊日期' AFTER adherence,
    ADD COLUMN recovery_progress TEXT COMMENT '康复进度序列(JSON)' AFTER first_visit,
    ADD COLUMN game_train_count INT DEFAULT 0 COMMENT '游戏训练次数' AFTER recovery_progress;

-- ② 新增 5 张临床表（与 BCI.sql 第 7~11 节一致）
CREATE TABLE IF NOT EXISTS scale_assessment (
    assess_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    assess_date DATE DEFAULT NULL,
    scale_key VARCHAR(20) NOT NULL,
    scale_name VARCHAR(50),
    score_text VARCHAR(30),
    result_text VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_scale_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS clinical_assessment (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    answers VARCHAR(50) NOT NULL,
    total_score INT DEFAULT 0,
    mapped_level VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_clinical_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS training_record (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    patient_name VARCHAR(50),
    level VARCHAR(10),
    game_name VARCHAR(50),
    duration_min INT DEFAULT 0,
    result_text VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_tr_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS eeg_session (
    id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(20) NOT NULL,
    session_no INT DEFAULT 0,
    alpha DECIMAL(6,2) DEFAULT 0,
    beta DECIMAL(6,2) DEFAULT 0,
    smr DECIMAL(6,2) DEFAULT 0,
    theta DECIMAL(6,2) DEFAULT 0,
    delta DECIMAL(6,2) DEFAULT 0,
    erd DECIMAL(6,2) DEFAULT 0,
    accuracy DECIMAL(6,2) DEFAULT 0,
    attention DECIMAL(6,2) DEFAULT 0,
    relaxation DECIMAL(6,2) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    KEY idx_eeg_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

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

SELECT '迁移完成：patient_info 已补临床列，并新增 scale_assessment / clinical_assessment / training_record / eeg_session / doctor_advice' AS result;
