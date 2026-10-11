-- ⚠️ 旧版碎片文件（仅供对照/备份），【请勿与 BCI.sql 混跑】。
--    文件名拼写有误（connfig 应为 config），且内容与 BCI.sql 里的
--    game_level_config 重复。认准 BCI.sql 当唯一真源。

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
