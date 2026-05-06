INSERT INTO patient_info (patient_id, patient_name, gender, age, affected_side, stroke_type, doctor_name, phone, remark)
VALUES ('202505001', '张三', '男', 58, '右', '缺血性', '李医生', '13800138000', '高血压病史10年，右侧肢体偏瘫，无康复禁忌');

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
    '202505002',
    '李四',
    '男',
    58,
    '右侧',
    '缺血性卒中',
    '2025-03-17',
    '王医生',
    '13800138001',
    '康复训练初期',
    'Xka061201!'
);