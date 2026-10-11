-- =====================================================================
-- 平台实验反馈记录表（HybridBCI 平台实验记录落库）
-- ---------------------------------------------------------------------
-- 作用：华南脑控 HybridBCI 平台在脑机实验(P300/SSVEP/MI)结束后返回结果，
--       后端把结果“导出”一份写进本表（见 services/hybridbci_client.py）。
-- 用法：在跑完 BCI.sql 之后，再 source 本文件即可建表。
--       后端启动时也会由 ORM 自动建（models/training.py 的 ExperimentRecord）。
-- =====================================================================

CREATE TABLE IF NOT EXISTS experiment_record (
    id             INT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    patient_id     VARCHAR(20) NOT NULL COMMENT '患者ID',
    experiment_type VARCHAR(30) COMMENT '实验类型: p300/ssvep/mi...',
    duration       INT DEFAULT 0 COMMENT '实验时长(秒)',
    score          INT DEFAULT 0 COMMENT '得分',
    accuracy       FLOAT DEFAULT 0 COMMENT '准确率(0-1)',
    extra_data     TEXT COMMENT '附加信息(JSON)',
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='HybridBCI平台实验反馈记录表';
