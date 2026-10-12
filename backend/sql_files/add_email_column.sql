-- =====================================================================
-- 给【已有数据库】补 email 列（找回密码功能用）
-- ---------------------------------------------------------------------
-- 场景：后端代码已给 patient_info / doctor_info 增加 email 列，
--       但 SQLAlchemy 的 db.create_all() 只会“建缺失的表”，
--       不会给已存在的表加列。
-- 如果你的 stroke_rehab_game 库是早期创建的，请先执行本文件再启动后端，
-- 否则注册 / 找回密码会因 "Unknown column 'email'" 报错。
-- 新建库（直接跑 BCI.sql）无需本文件，BCI.sql 已包含 email 列。
-- =====================================================================

USE stroke_rehab_game;

-- 患者表补 email（放在 phone 之后）
ALTER TABLE patient_info
    ADD COLUMN email VARCHAR(100) DEFAULT NULL COMMENT '邮箱（找回密码用）'
    AFTER phone;

-- 医生表补 email（放在 phone 之后）
ALTER TABLE doctor_info
    ADD COLUMN email VARCHAR(100) DEFAULT NULL COMMENT '邮箱（找回密码用）'
    AFTER phone;
