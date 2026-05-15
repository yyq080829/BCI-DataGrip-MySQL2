CREATE TABLE IF NOT EXISTS escort_info (
    escort_id        VARCHAR(20) PRIMARY KEY COMMENT '陪同人员ID（主键）',
    escort_name      VARCHAR(50) NOT NULL COMMENT '陪同人员姓名',
    gender           CHAR(2) COMMENT '性别',
    relation         VARCHAR(30) COMMENT '与患者关系（家属/护工等）',
    patient_id       VARCHAR(20) COMMENT '关联患者ID（仅存储，暂不关联）',
    phone            VARCHAR(20) COMMENT '手机号',
    username         VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号（唯一）',
    pwd              VARCHAR(50) NOT NULL COMMENT '登录密码',
    create_time      DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;