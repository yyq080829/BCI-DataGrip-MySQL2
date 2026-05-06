CREATE TABLE IF NOT EXISTS patient_info (
    patient_id VARCHAR(20) PRIMARY KEY COMMENT '患者唯一标识（住院号/身份证后8位）',
    patient_name VARCHAR(50) NOT NULL COMMENT '患者姓名',
    gender CHAR(1) NOT NULL COMMENT '性别：男/女',
    age INT NOT NULL COMMENT '患者年龄',
    affected_side CHAR(1) NOT NULL COMMENT '患侧：左/右',
    stroke_type VARCHAR(30) NOT NULL COMMENT '卒中类型：缺血性/出血性',
    admission_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '康复开始时间',
    doctor_name VARCHAR(50) COMMENT '主治医生',
    phone VARCHAR(20) COMMENT '家属联系方式',
    remark TEXT COMMENT '临床备注（合并症、禁忌等）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脑卒中患者基础信息表';