CREATE TABLE IF NOT EXISTS doctor_info (
    doctor_id VARCHAR(20) PRIMARY KEY,  -- 医生ID（主键）
    doctor_name VARCHAR(50) NOT NULL,   -- 医生姓名
    gender CHAR(2),                     -- 性别
    department VARCHAR(50),             -- 科室（如康复科）
    phone VARCHAR(20),                  -- 手机号
    username VARCHAR(50) NOT NULL,      -- 登录账号（和姓名区分）
    pwd VARCHAR(50) NOT NULL,           -- 登录密码
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP  -- 创建时间
);