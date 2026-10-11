-- =====================================================================
-- 数据库初始化（入口文件）
-- ---------------------------------------------------------------------
-- 作用：创建数据库 stroke_rehab_game 并 USE 它。
-- 用法：手动建库时第一个执行；之后紧接着 source BCI.sql 等。
--       后端自动建库时不依赖本文件（config.py 的连接串已指定库名）。
-- =====================================================================

-- 创建脑卒中康复游戏数据库
CREATE DATABASE IF NOT EXISTS stroke_rehab_game
DEFAULT CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE stroke_rehab_game;
