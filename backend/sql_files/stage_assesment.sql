CREATE TABLE IF NOT EXISTS stage_assessment (
    assess_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '评估自增ID',
    patient_id VARCHAR(20) NOT NULL COMMENT '患者ID',
    assess_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '评估时间',
    assess_cycle VARCHAR(20) NOT NULL COMMENT '评估周期：第1周/康复中期等',
    avg_shoulder_angle DECIMAL(5,2) COMMENT '平均肩外展角度(°)',
    avg_elbow_angle DECIMAL(5,2) COMMENT '平均肘伸展角度(°)',
    avg_forearm_angle DECIMAL(5,2) COMMENT '平均前臂旋转角度(°)',
    qualified_rate DECIMAL(5,2) COMMENT '动作达标率(%)',
    avg_compensation_score INT COMMENT '平均代偿评分',
    FMA_UE_score INT DEFAULT 0 COMMENT 'FMA上肢量表评分(0-66)',
    ARAT_score INT DEFAULT 0 COMMENT 'ARAT上肢功能评分(0-57)',
    doctor_evaluation TEXT COMMENT '医生评估意见',
    next_train_plan TEXT COMMENT '后续训练计划',
    -- 外键约束
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脑卒中上肢康复阶段临床评估数据表';