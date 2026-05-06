CREATE TABLE IF NOT EXISTS train_real_time_data (
    data_id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '实时数据自增ID',
    patient_id VARCHAR(20) NOT NULL COMMENT '患者ID',
    level_id INT NOT NULL COMMENT '关卡ID',
    train_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '动作采集时间',
    shoulder_abduction DECIMAL(5,2) COMMENT '肩外展角度(°)',
    elbow_extension DECIMAL(5,2) COMMENT '肘伸展角度(°)',
    forearm_rotation DECIMAL(5,2) COMMENT '前臂旋前/旋后角度(°)',
    action_score INT DEFAULT 0 COMMENT '单动作得分(0-10)',
    is_qualified TINYINT(1) DEFAULT 0 COMMENT '动作是否达标：0=否，1=是',
    compensation VARCHAR(50) COMMENT '代偿动作：耸肩/躯干侧倾/腕屈曲/无',
    compensation_score INT DEFAULT 100 COMMENT '代偿评分(100=无代偿，分数越低越严重)',
    device_type VARCHAR(30) DEFAULT 'AR手机' COMMENT '数据采集设备',
    game_score INT DEFAULT 0 COMMENT '游戏累计得分',
    -- 外键约束
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (level_id) REFERENCES game_level_config(level_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='康复游戏训练实时数据表';