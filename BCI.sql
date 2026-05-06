-- 创建脑卒中康复游戏数据库，不存在则创建
CREATE DATABASE IF NOT EXISTS stroke_rehab_game
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

SHOW DATABASES;

-- 使用该数据库（后续所有操作基于此库）
USE stroke_rehab_game;



-- 表1：患者基础信息表
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




-- 表2：游戏关卡配置表
CREATE TABLE IF NOT EXISTS game_level_config (
    level_id INT PRIMARY KEY AUTO_INCREMENT COMMENT '关卡自增ID',
    game_name VARCHAR(50) NOT NULL COMMENT '康复游戏名称',
    train_part VARCHAR(30) NOT NULL COMMENT '训练部位/动作',
    level_name VARCHAR(50) NOT NULL COMMENT '关卡名称',
    target_angle DECIMAL(5,2) NOT NULL COMMENT '目标关节角度(°)',
    angle_tolerance DECIMAL(5,2) DEFAULT 5.00 COMMENT '角度容错度(°)',
    train_duration INT NOT NULL COMMENT '单关训练时长(秒)',
    difficulty VARCHAR(10) NOT NULL COMMENT '难度等级：简单/中等/困难',
    game_remark VARCHAR(200) COMMENT '关卡规则说明'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='康复游戏关卡配置表';



-- 初始化3款康复游戏的关卡数据，可直接用于游戏测试
INSERT INTO game_level_config (game_name, train_part, level_name, target_angle, angle_tolerance, train_duration, difficulty, game_remark)
VALUES
('星际翼航', '肩外展+内收', '航道1（入门）', 60.00, 8.00, 300, '简单', '抬胳膊够60°，捡80%晶体解锁，干扰磁场少'),
('星际翼航', '肩外展+内收', '航道2（进阶）', 90.00, 5.00, 360, '中等', '抬胳膊够90°，弹性星云降低难度，干扰磁场增多'),
('肘伸展采水晶', '肘关节伸展', '入门关', 10.00, 10.00, 240, '简单', '水晶大且慢，肘伸展≥10°即可采集'),
('肘伸展采水晶', '肘关节伸展', '大师关', 0.00, 3.00, 300, '困难', '水晶小且晃，肘完全伸直（0°）才能采集'),
('星光舞台', '前臂旋前+旋后', '初级节奏', 90.00, 10.00, 180, '简单', '手离手机30-50cm，节拍慢，单次旋前/旋后达标即得分'),
('星光舞台', '前臂旋前+旋后', '高级节奏', 90.00, 5.00, 240, '困难', '节拍快，需快速交替旋前+旋后，姿势保持2秒才得分');






-- 表3：训练实时数据表（核心业务表，外键关联）
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
    -- 外键约束（黑马MySQL进阶版重点，关联患者表）
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
    -- 外键约束（关联关卡表）
    FOREIGN KEY (level_id) REFERENCES game_level_config(level_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='康复游戏训练实时数据表';




-- 表4：阶段临床评估数据表
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
    -- 外键约束，关联患者表
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='脑卒中上肢康复阶段临床评估数据表';




-- 插入患者基础数据
INSERT INTO patient_info (patient_id, patient_name, gender, age, affected_side, stroke_type, doctor_name, phone, remark)
VALUES
('202505001', '张三', '男', 58, '右', '缺血性', '李医生', '13800138000', '高血压病史10年，右侧肢体偏瘫，无康复禁忌');

-- 插入训练实时数据（关联患者202505001，关卡1：星际翼航航道1）
INSERT INTO train_real_time_data (patient_id, level_id, shoulder_abduction, action_score, is_qualified, compensation, compensation_score, game_score)
VALUES
('202505001', 1, 58.50, 8, 1, '无', 100, 80),
('202505001', 1, 62.00, 9, 1, '无', 100, 89),
('202505001', 1, 52.00, 5, 0, '轻微耸肩', 85, 94);


-- 插入阶段评估数据（关联患者202505001，第1周评估）
INSERT INTO stage_assessment (patient_id, assess_cycle, avg_shoulder_angle, qualified_rate, avg_compensation_score, FMA_UE_score, ARAT_score, doctor_evaluation, next_train_plan)
VALUES
('202505001', '第1周', 57.50, 66.67, 95, 30, 25, '右侧肩外展平均57.5°，达标率66.67%，仅1次轻微耸肩，康复效果良好', '继续星际翼航航道1训练，3天后解锁航道2，增加每日训练时长10分钟');


-- 查询患者张三（202505001）的所有训练数据，关联关卡表获取游戏/关卡名称
SELECT
    p.patient_name,
    g.game_name,
    g.level_name,
    t.train_time,
    t.shoulder_abduction,
    t.is_qualified,
    t.compensation,
    t.game_score
FROM
    train_real_time_data t
JOIN
    patient_info p ON t.patient_id = p.patient_id
JOIN
    game_level_config g ON t.level_id = g.level_id
WHERE
    p.patient_id = '202505001';


-- 统计张三的星际翼航游戏平均肩外展角度+动作达标率
SELECT
    p.patient_name,
    g.game_name,
    AVG(t.shoulder_abduction) AS 平均肩外展角度,
    CONCAT(ROUND(SUM(t.is_qualified)/COUNT(*)*100,2),'%') AS 动作达标率
FROM
    train_real_time_data t
JOIN
    patient_info p ON t.patient_id = p.patient_id
JOIN
    game_level_config g ON t.level_id = g.level_id
WHERE
    p.patient_id = '202505001'
    AND g.game_name = '星际翼航'
GROUP BY
    p.patient_name, g.game_name;


-- 查询星际翼航航道1（level_id=1）的所有训练数据，含患者姓名+患侧
SELECT
    p.patient_name,
    p.affected_side,
    t.train_time,
    t.shoulder_abduction,
    t.is_qualified
FROM
    train_real_time_data t
JOIN
    patient_info p ON t.patient_id = p.patient_id
WHERE
    t.level_id = 1
ORDER BY
    t.train_time DESC;


-- 查询张三的所有阶段评估数据，含FMA/ARAT量表评分
SELECT
    patient_name,
    assess_cycle,
    avg_shoulder_angle,
    qualified_rate,
    FMA_UE_score,
    ARAT_score,
    doctor_evaluation
FROM
    stage_assessment a
JOIN
    patient_info p ON a.patient_id = p.patient_id
WHERE
    p.patient_name = '张三';


-- 统计所有患者的平均FMA-UE上肢评分，按患侧分组
SELECT
    affected_side AS 患侧,
    COUNT(*) AS 患者数,
    AVG(FMA_UE_score) AS 平均FMA评分
FROM
    stage_assessment a
JOIN
    patient_info p ON a.patient_id = p.patient_id
GROUP BY
    affected_side;

-- 查询所有患者代偿动作非“无”的训练数据，含患者姓名+代偿类型
SELECT
    p.patient_name,
    g.game_name,
    t.train_time,
    t.shoulder_abduction,
    t.compensation,
    t.compensation_score
FROM
    train_real_time_data t
JOIN
    patient_info p ON t.patient_id = p.patient_id
JOIN
    game_level_config g ON t.level_id = g.level_id
WHERE
    t.compensation != '无'
    OR t.compensation_score < 90;


-- 统计张三的各游戏累计最高得分，按得分降序
SELECT
    p.patient_name,
    g.game_name,
    MAX(t.game_score) AS 累计最高得分
FROM
    train_real_time_data t
JOIN
    patient_info p ON t.patient_id = p.patient_id
JOIN
    game_level_config g ON t.level_id = g.level_id
WHERE
    p.patient_name = '张三'
GROUP BY
    p.patient_name, g.game_name
ORDER BY
    累计最高得分 DESC;


-- 查询星际翼航所有训练数据中，肩外展角度低于目标角度的记录
SELECT
    p.patient_name,
    g.game_name,
    g.target_angle AS 关卡目标角度,
    t.shoulder_abduction AS 实际角度,
    (g.target_angle - t.shoulder_abduction) AS 角度差值
FROM
    train_real_time_data t
JOIN
    patient_info p ON t.patient_id = p.patient_id
JOIN
    game_level_config g ON t.level_id = g.level_id
WHERE
    g.game_name = '星际翼航'
    AND t.shoulder_abduction < g.target_angle;


-- 为训练表建立索引
CREATE INDEX idx_patient_id ON train_real_time_data(patient_id);
CREATE INDEX idx_level_id ON train_real_time_data(level_id);
CREATE INDEX idx_train_time ON train_real_time_data(train_time);




-- 授权本地所有IP访问MySQL，密码为你的MySQL密码（如123456）
GRANT ALL PRIVILEGES ON stroke_rehab_game.* TO 'root'@'localhost' IDENTIFIED BY 'Xka061201！' WITH GRANT OPTION;
FLUSH PRIVILEGES; -- 刷新权限







INSERT INTO patient_info (
    patient_id,
    patient_name,
    gender,
    age,
    affected_side,
    stroke_type,
    admission_time,
    doctor_name,
    phone,
    remark,
    pwd
)
VALUES (
    '202505002',        -- patient_id (换个新ID，是李四)
    '李四',            -- patient_name
    '男',              -- gender
    58,                -- age
    '右侧',            -- affected_side (改短点，只填2个字)
    '缺血性卒中',      -- stroke_type
    '2025-03-17',      -- admission_time (当前日期)
    '王医生',          -- doctor_name
    '13800138001',     -- phone
    '康复训练初期',     -- remark
    'Xka061201!'       -- pwd (密码)
);





-- 创建医生信息表（含账号密码）
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





-- 插入李医生数据（账号：doctor_li，密码：Li123456!）
INSERT INTO doctor_info (
    doctor_id,
    doctor_name,
    gender,
    department,
    phone,
    username,
    pwd
)
VALUES (
    'DOC2025001',    -- 医生ID
    '李医生',        -- 姓名
    '男',            -- 性别
    '康复医学科',    -- 科室
    '13900139000',   -- 手机号
    'doctor_li',     -- 登录账号（和患者区分）
    'Li123456!'      -- 密码（复杂度足够）
);

-- 插入王医生数据（账号：doctor_wang，密码：Wang123456!）
INSERT INTO doctor_info (
    doctor_id,
    doctor_name,
    gender,
    department,
    phone,
    username,
    pwd
)
VALUES (
    'DOC2025002',    -- 医生ID
    '王医生',        -- 姓名
    '女',            -- 性别
    '康复医学科',    -- 科室
    '13900139001',   -- 手机号
    'doctor_wang',   -- 登录账号（和患者区分）
    'Wang123456!'    -- 密码（复杂度足够）
);







-- 给患者表添加主治医生ID列
ALTER TABLE patient_info ADD COLUMN doctor_id VARCHAR(20);

-- 给李四患者关联王医生
UPDATE patient_info
SET doctor_id = 'DOC2025002'
WHERE patient_id = '202505002';


-- 修改 patient_info.doctor_id 的排序规则
ALTER TABLE patient_info
MODIFY COLUMN doctor_id VARCHAR(20) COLLATE utf8mb4_unicode_ci;


-- 查询李四的主治医生信息
SELECT p.patient_name, d.doctor_name
FROM patient_info p
LEFT JOIN doctor_info d ON p.doctor_id = d.doctor_id
WHERE p.patient_id = '202505002';




SHOW CREATE TABLE stage_assessment;



-- 修改 stage_assessment 表的 patient_id（和上面保持一致）
ALTER TABLE stage_assessment
MODIFY COLUMN patient_id VARCHAR(20)
COMMENT '关联患者ID'
COLLATE utf8mb4_unicode_ci;




-- 创建陪同人员表（无外键，仅基础字段）
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




-- 给患者表补充 username 字段（登录账号，唯一）
ALTER TABLE patient_info
ADD COLUMN username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号' AFTER phone;

-- 给李四补充登录账号（示例：patient_lisi）
UPDATE patient_info
SET username = 'patient_lisi'
WHERE patient_id = '202505002';



-- 1. 先统一 patient_id 排序规则（确保两边一致）
ALTER TABLE escort_info
MODIFY COLUMN patient_id VARCHAR(20) COLLATE utf8mb4_unicode_ci COMMENT '关联患者ID（仅存储，暂不关联）';

-- 1. 先添加 username 字段（允许 NULL，不加 UNIQUE）
ALTER TABLE patient_info
ADD COLUMN username VARCHAR(50) COMMENT '登录账号' AFTER phone;

-- 2. 给已有患者设置 username（示例：给李四设置）
UPDATE patient_info
SET username = 'patient_lisi'
WHERE patient_id = '202505002';

-- 3. 给其他患者也设置 username（如果有更多数据，按实际修改）
-- UPDATE patient_info SET username = 'patient_zhangsan' WHERE patient_id = '202505001';

-- 4. 最后给 username 加 NOT NULL + UNIQUE 约束
ALTER TABLE patient_info
MODIFY COLUMN username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号';



-- 医生登录
SELECT * FROM doctor_info WHERE username = ? AND pwd = ?;

-- 患者登录
SELECT * FROM patient_info WHERE username = ? AND pwd = ?;

-- 陪同人员登录
SELECT * FROM escort_info username = ? AND pwd = ?;



-- 1. 先删除 train_real_time_data 里的旧外键（从报错看约束名是 train_real_time_data_ibfk_1）
ALTER TABLE train_real_time_data
DROP FOREIGN KEY `train_real_time_data_ibfk_1`;

-- 2. 统一 patient_info.patient_id 排序规则
ALTER TABLE patient_info
MODIFY COLUMN patient_id VARCHAR(20) COLLATE utf8mb4_unicode_ci COMMENT '患者ID（主键）';

-- 3. 统一 escort_info.patient_id 排序规则
ALTER TABLE escort_info
MODIFY COLUMN patient_id VARCHAR(20) COLLATE utf8mb4_unicode_ci COMMENT '关联患者ID';

-- 4. 统一 train_real_time_data.patient_id 排序规则
ALTER TABLE train_real_time_data
MODIFY COLUMN patient_id VARCHAR(20) COLLATE utf8mb4_unicode_ci COMMENT '关联患者ID';

-- 5. 重建 train_real_time_data 的外键
ALTER TABLE train_real_time_data
ADD CONSTRAINT `train_real_time_data_ibfk_1`
FOREIGN KEY (`patient_id`) REFERENCES `patient_info` (`patient_id`);



ALTER TABLE escort_info
ADD CONSTRAINT fk_escort_patient
FOREIGN KEY (patient_id)
REFERENCES patient_info(patient_id)
ON DELETE CASCADE;


-- 给所有未设置 username 的患者批量生成账号（格式：patient_+patient_id）
UPDATE patient_info
SET username = CONCAT('patient_', patient_id)
WHERE username IS NULL OR username = '';



-- 给张三补账号（如果他的 patient_id 是 202505001）
UPDATE patient_info
SET username = 'patient_zhangsan'
WHERE patient_id = '202505001';

-- 给李四补账号（已存在就不用再执行）
UPDATE patient_info
SET username = 'patient_lisi'
WHERE patient_id = '202505002';


-- 检查是否还有 NULL/空值
SELECT patient_id, patient_name, username
FROM patient_info
WHERE username IS NULL OR username = '';


ALTER TABLE patient_info
MODIFY COLUMN username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号';


DESC patient_info;


INSERT INTO escort_info (
    escort_id,
    escort_name,
    gender,
    relation,
    patient_id,
    phone,
    username,
    pwd
)
VALUES (
    'ESC2025001',        -- 陪同人员ID（自定义，保证唯一）
    '李母',              -- 陪同人员姓名
    '女',                -- 性别
    '母亲',              -- 与患者关系
    '202505002',         -- 关联患者ID（对应李四）
    '13800138002',       -- 手机号
    'escort_lisi',       -- 登录账号（唯一，建议用 escort_+姓名/ID）
    'Esc123456!'         -- 登录密码（建议包含大小写+数字+特殊字符）
);






INSERT INTO escort_info (
    escort_id,
    escort_name,
    gender,
    relation,
    patient_id,
    phone,
    username,
    pwd
)
VALUES (
    'ESC2025002',
    '张父',
    '男',
    '父亲',
    '202505001',  -- 对应张三的patient_id
    '13700137000',
    'escort_zhang',
    'Esc123456!'
);




ALTER TABLE patient_info
ADD COLUMN role VARCHAR(20) DEFAULT 'patient' COMMENT '角色：patient/doctor/companion';


ALTER TABLE doctor_info
ADD COLUMN role VARCHAR(20) DEFAULT 'doctor' COMMENT '角色：patient/doctor/companion';


ALTER TABLE escort_info
ADD COLUMN role VARCHAR(20) DEFAULT 'companion' COMMENT '角色：patient/doctor/companion';


DESC patient_info;
DESC doctor_info;
DESC escort_info;



SELECT
  doctor_id AS user_id,
  doctor_name AS user_name,
  role,
  pwd
FROM doctor_info
WHERE username = ? AND pwd = ?;


SELECT
  patient_id AS user_id,
  patient_name AS user_name,
  role,
  pwd
FROM patient_info
WHERE username = ? AND pwd = ?;


SELECT
  escort_id AS user_id,
  escort_name AS user_name,
  role,
  pwd
FROM escort_info
WHERE username = ? AND pwd = ?;


SELECT
  patient_id AS user_id,
  patient_name AS user_name,
  role,
  pwd
FROM patient_info
WHERE username = 'patient_lisi' AND pwd = 'Xka061201!';



-- 更新张三的密码（如果张三已经存在，用 UPDATE）
UPDATE patient_info
SET pwd = 'Zhang123456!'
WHERE patient_id = '202505001';


UPDATE patient_info
SET username = 'patient_zhangsan', pwd = 'Zhang123456!'
WHERE patient_id = '202505001';


-- 假设张三的 patient_id 是 202505001，给他分配医生 ID：DOC2025001
UPDATE patient_info
SET doctor_id = 'DOC2025001'
WHERE patient_id = '202505001';



SELECT
    patient_id,
    patient_name,
    doctor_id,
    role
FROM patient_info
WHERE patient_id = '202505001';
















SELECT patient_id, pwd, role
FROM patient_info
WHERE patient_id = 'test001' AND pwd = '123456';


SELECT doctor_id, pwd, role
FROM doctor_info
WHERE doctor_id = 'doc001' AND pwd = '123456';









select * from patient_info;






-- 替换成你实际的账号、密码、角色
SELECT * FROM patient_info
WHERE patient_id = '202505001' AND pwd = 'Zhang123456!' AND role = 'patient';








































