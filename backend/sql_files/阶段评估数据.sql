-- ⚠️ 旧版碎片文件（仅供对照/备份），【请勿与 BCI.sql 混跑】。
--    这是往 stage_assessment 插示例数据的脚本，内容与 BCI.sql 里的一致。
--    仅作数据备份参考；建库认准 BCI.sql。

INSERT INTO stage_assessment (patient_id, assess_cycle, avg_shoulder_angle, qualified_rate, avg_compensation_score, FMA_UE_score, ARAT_score, doctor_evaluation, next_train_plan)
VALUES
('202505001', '第1周', 57.50, 66.67, 95, 30, 25, '右侧肩外展平均57.5°，达标率66.67%，仅1次轻微耸肩，康复效果良好', '继续星际翼航航道1训练，3天后解锁航道2，增加每日训练时长10分钟');
