-- ======================= 康复评估问卷表 =======================

-- 1. 问卷主表
CREATE TABLE IF NOT EXISTS questionnaire (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '问卷ID',
    title VARCHAR(100) NOT NULL COMMENT '问卷标题',
    description TEXT COMMENT '问卷描述/引导语',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    is_active TINYINT(1) DEFAULT 1 COMMENT '是否当前激活的问卷'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='康复评估问卷主表';

-- 2. 问题表
CREATE TABLE IF NOT EXISTS question (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '问题ID',
    questionnaire_id INT NOT NULL COMMENT '所属问卷ID',
    question_text TEXT NOT NULL COMMENT '问题文本',
    options JSON NOT NULL COMMENT '选项数组',
    sort_order INT DEFAULT 0 COMMENT '显示顺序',
    FOREIGN KEY (questionnaire_id) REFERENCES questionnaire(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评估问题表';

-- 3. 插入问卷主记录（激活状态）
INSERT INTO questionnaire (title, description, is_active) VALUES 
('康复游戏登录问卷', '亲爱的用户，为了给你匹配最安全、最适合的《星光舞台》训练难度，请根据你当前上肢真实情况作答（共10题，单选，约1分钟完成）。答案仅用于关卡适配，严格保护隐私。康复进步后可在「个人中心-问卷测试」重新测评。', 1);

-- 4. 插入 10 个问题（假设上一步插入的 questionnaire id 为 1）
INSERT INTO question (questionnaire_id, question_text, options, sort_order) VALUES
(1, '1. 你能自主完成前臂旋前（掌心向下）、旋后（掌心向上）动作吗？', 
 '["A 完全转不动，需他人帮助","B 能转一点，幅度很小","C 能转到标准位置，基本稳定","D 能快速翻转，动作灵活顺畅"]', 1),
(1, '2. 手掌向上转、向下转切换时，是否顺畅？', 
 '["A 完全不顺畅，经常卡住","B 偶尔卡顿，切换缓慢","C 切换顺畅，无明显停顿","D 切换快速，连续不失误"]', 2),
(1, '3. 转动前臂时，小臂是否晃动、偏移？', 
 '["A 晃动严重，控制不住","B 偶尔晃动，方向不准","C 基本稳定，轻微晃动","D 完全稳定，不晃不偏"]', 3),
(1, '4. 做手掌翻转动作时，是否出现耸肩、抬臂、代偿？', 
 '["A 经常代偿，无法控制","B 偶尔代偿，姿势变形","C 很少代偿，姿势基本标准","D 不会代偿，姿势规范"]', 4),
(1, '5. 前臂转动时，是否有疼痛、酸胀、疲劳？', 
 '["A 一动就疼，无法坚持","B 轻微酸胀，能坚持1-3分钟","C 无疼痛，能坚持5分钟左右","D 完全舒适，可坚持8分钟以上"]', 5),
(1, '6. 你能按节奏完成手掌翻转吗？', 
 '["A 跟不上任何节奏","B 能慢节奏，经常出错","C 能跟中等节奏，较少出错","D 能跟快节奏，准确稳定"]', 6),
(1, '7. 单手保持掌心朝上/朝下，能稳定不动多久？', 
 '["A 完全稳不住","B 不到1秒","C 1秒左右，基本稳定","D 2秒以上，非常稳定"]', 7),
(1, '8. 做动作时，手腕是否用力过度、僵硬？', 
 '["A 非常僵硬，用力失控","B 偶尔僵硬，需刻意放松","C 基本自然，用力适中","D 完全放松，控制自如"]', 8),
(1, '9. 日常拧瓶盖、翻书、握笔、端碗等动作是否顺畅？', 
 '["A 完全不能，需人帮助","B 勉强完成，笨拙缓慢","C 基本独立，效率一般","D 轻松完成，灵活快速"]', 9),
(1, '10. 你更适合的训练节奏是？', 
 '["A 极慢、辅助为主、安全第一","B 较慢、温和练习、少量重复","C 中等节奏、稳定训练、适度挑战","D 较快节奏、精准强化、高效练习"]', 10);

-- 验证插入
SELECT * FROM questionnaire;
SELECT * FROM question;