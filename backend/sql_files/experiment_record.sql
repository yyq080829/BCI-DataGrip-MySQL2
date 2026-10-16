-- =====================================================================
-- 平台实验反馈记录表（HybridBCI 平台实验记录落库）
-- ---------------------------------------------------------------------
-- 作用：华南脑控 HybridBCI 平台在脑机实验(P300/SSVEP/MI)结束后返回结果，
--       后端把结果“导出”一份写进本表（见 services/hybridbci_client.py）。
-- 用法：在跑完 BCI.sql 之后，再 source 本文件即可建表。
--       后端启动时也会由 ORM 自动建（models/training.py 的 ExperimentRecord）。
-- ⚠️ 本表有外键指向 patient_info，CHARSET/COLLATE 必须与 BCI.sql、config.py
--    一致（都是 utf8mb4 + utf8mb4_general_ci），否则报 [HY000][3780]。
-- =====================================================================

-- 选中数据库（在“未选库”的执行窗口里必须先选中，否则报 [3D000][1046] No database selected）
USE stroke_rehab_game;

CREATE TABLE IF NOT EXISTS experiment_record (
    id             INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    patient_id     VARCHAR(20) NOT NULL COMMENT '患者ID',
    experiment_type VARCHAR(30) COMMENT '实验类型: p300/ssvep/mi...',
    duration       INT DEFAULT 0 COMMENT '实验时长(秒)',
    score          INT DEFAULT 0 COMMENT '得分',
    accuracy       FLOAT DEFAULT 0 COMMENT '准确率(0-1)',
    extra_data     TEXT COMMENT '附加信息(JSON)',
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_exp_patient (patient_id),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='HybridBCI平台实验反馈记录表';
