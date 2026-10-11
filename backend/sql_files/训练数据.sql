-- ⚠️ 旧版碎片文件（仅供对照/备份），【请勿与 BCI.sql 混跑】。
--    这是往 train_real_time_data 插示例数据的脚本，内容与 BCI.sql 里的一致。
--    仅作数据备份参考；建库认准 BCI.sql。

INSERT INTO train_real_time_data (patient_id, level_id, shoulder_abduction, action_score, is_qualified, compensation, compensation_score, game_score)
VALUES
('202505001', 1, 58.50, 8, 1, '无', 100, 80),
('202505001', 1, 62.00, 9, 1, '无', 100, 89),
('202505001', 1, 52.00, 5, 0, '轻微耸肩', 85, 94);
