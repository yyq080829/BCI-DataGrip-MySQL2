CREATE TABLE IF NOT EXISTS bci_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    patient_id VARCHAR(20) NOT NULL COMMENT '患者ID',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据接收时间',
    delta_power FLOAT COMMENT 'Delta波功率(0.5-4Hz)',
    theta_power FLOAT COMMENT 'Theta波功率(4-8Hz)',
    alpha_power FLOAT COMMENT 'Alpha波功率(8-13Hz)',
    beta_power FLOAT COMMENT 'Beta波功率(13-30Hz)',
    gamma_power FLOAT COMMENT 'Gamma波功率(30-50Hz)',
    attention FLOAT COMMENT '注意力指数(0-100)',
    meditation FLOAT COMMENT '放松度指数(0-100)',
    signal_quality INT COMMENT '信号质量(0-100)',
    raw_mean FLOAT COMMENT '原始数据均值',
    raw_std FLOAT COMMENT '原始数据标准差',
    device_id VARCHAR(50) COMMENT '脑电设备ID',
    --FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='脑电数据存储表';