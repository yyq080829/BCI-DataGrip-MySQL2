# 脑卒中康复系统后端 API 文档
## 基本信息
+ 基础地址：http://localhost:5000（本地开发）或后续部署的实际 IP
+ 所有接口返回 JSON，通用响应格式：
```
{
  "code": 200,          // 200/201 成功，4xx 客户端错误，5xx 服务器错误
  "message": "success", // 提示信息
  "data": {}            // 可选，成功时返回的数据
}
```
+ 认证方式：登录成功后获得 JWT token，后续需要认证的接口需在请求头中携带：
```
Authorization: Bearer <token>
```
+ 跨域：后端已配置 CORS，前端可直接调用，无需额外配置。
### 1.用户登录
接口：POST /api/auth/login

描述：患者、医生、管理员、陪同人员统一登录入口。

| 字段名      | Type   | 说明                                            | 必填 |
|----------|--------|-----------------------------------------------|----|
| username | String | 登录账号                                          | 是  |
| password | String | 登陆密码                                          | 是  |
| userType | String | 可选值：doctor，patient，admin, companion。不传则后端自动查找 | 否  |
示例：
```
{
  "username": "patient_lisi",
  "password": "Xka061201!",
  "userType": "patient"
}
```
响应（成功）
```
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "user_id": "202505002",
      "user_name": "李四",
      "role": "patient",
      "gender": "男",
      "age": 58,
      "affected_side": "右",
      "stroke_type": "缺血性卒中",
      "doctor_name": "王医生",
      "admission_time": "2025-03-17"
    }
  }
}
```
对于医生登录，返回的 user 包含 department 等字段；陪同人员包含 relation, patient_id。

响应（失败）
```
{
  "code": 401,
  "message": "用户名或密码错误"
}
```
### 用户注册（患者/医生）
接口：POST /api/auth/register

描述：患者或医生注册新账号。陪同人员目前需由管理员在后台添加。

| 字段名                        | type   | 说明                     | 必填 |
|----------------------------|--------|------------------------|----|
| username                   | String | 登录账号，必须唯一              | 是  |
| password                   | String | 登陆密码                   | 是  |
| email                      | String | 邮箱（当前版本暂不保存）           | 否  |
| confirmPassword            | String | 确认密码，若提供会与 password 校验 | 否  |
| register-user-type         | String | patient 或 doctor       | 是  |
| patient_name / doctor_name | String | 真实姓名，默认使用 username     | 否  |
| gender                     | String | 默认 男                   | 否  |
| age                        | int    | 默认 0                   | 否  |
| affected_side              | String | 默认 左（仅患者）              | 否  |
| stroke_type                | String | 默认 缺血性（仅患者）            | 否  |

示例（患者注册，只传必填）：
```
{
  "username": "new_patient",
  "password": "123456",
  "register-user-type": "patient"
}
```
示例（完整注册）：
```
{
  "username": "wangwu",
  "password": "Wang123456!",
  "email": "wangwu@example.com",
  "confirmPassword": "Wang123456!",
  "register-user-type": "patient",
  "patient_name": "王五",
  "gender": "男",
  "age": 62,
  "affected_side": "左",
  "stroke_type": "缺血性"
}
```
响应（成功）
```
{
  "code": 201,
  "message": "患者注册成功",
  "data": {
    "patient_id": "20260520001",
    "username": "new_patient"
  }
}
```
响应（失败）
```
{
  "code": 400,
  "message": "用户名已存在"
}
```
### 3.获取当前用户信息（需认证）
接口：GET /api/auth/profile

描述：根据 JWT token 返回当前登录用户的详细信息。

请求头：Authorization: Bearer <token>

响应（患者示例）：
```
{
  "code": 200,
  "message": "获取成功",
  "data": {
    "user_id": "202505001",
    "user_name": "张三",
    "role": "patient",
    "gender": "男",
    "age": 58,
    "affected_side": "右",
    "stroke_type": "缺血性",
    "doctor_name": "李医生"
  }
}
```
### 4. 管理员获取所有用户（需 admin 权限）
接口：GET /api/admin/users

描述：获取系统中所有患者、医生、陪同人员的列表。

请求头：Authorization: Bearer <token>（必须是 admin 角色）

响应：
```
{
  "code": 200,
  "data": [
    {
      "user_id": "202505001",
      "username": "patient_zhangsan",
      "user_name": "张三",
      "role": "patient",
      "email": "",
      "status": "active",
      "register_date": "2025-11-15"
    },
    {
      "user_id": "DOC2025001",
      "username": "doctor_li",
      "user_name": "李医生",
      "role": "doctor",
      "email": "",
      "status": "active",
      "register_date": "2025-10-15"
    }
  ]
}
```
### 5. 医生获取自己负责的患者列表（需医生认证）
接口：GET /api/doctor/patients

描述：返回当前医生名下所有患者的详细信息。

请求头：Authorization: Bearer <token>

查询参数：

| 参数名       | Type   | 说明                       | 必填 |
|-----------|--------|--------------------------|----|
| doctor_id | String | 医生ID，若不传则使用 token 中的用户ID | 否  |

响应：
```
{
  "code": 200,
  "data": [
    {
      "patient_id": "202505001",
      "patient_name": "张三",
      "gender": "男",
      "age": 58,
      "affected_side": "右",
      "stroke_type": "缺血性",
      "admission_time": "2025-11-15",
      "recovery_level": "初级"
    }
  ]
}
```
### 6. 保存训练数据（需患者认证）
接口：POST /api/training/save

描述：Unity 游戏结束后，患者提交本次训练的结果。

请求头：Authorization: Bearer <token>（仅患者可用）

请求体：
| 字段名                        | type   | 说明                     | 必填 |
|----------------------------|--------|------------------------|----|
| level_id                   | int |  关卡 ID             | 是  |
| score                   | int | 游戏得分                   | 否  |
| duration                      | int | 训练时长（秒）           | 否  |
| accuracy            | float | 准确率（%） | 否  |
| shoulder_abduction         | float | 肩外展角度（°）       | 否  |
| elbow_extension | float | 肘伸展角度（°）     | 否  |
| forearm_rotation                     | float | 前臂旋转角度（°）                   | 否  |
| compensation                       | string    | 代偿动作，如 无, 耸肩                   | 否  |
| compensation_score	              | int |  代偿评分（0-100）             | 否  |
| device_type                | String | 设备类型，默认 AR手机 | 否  |

示例：
```
{
  "level_id": 1,
  "score": 85,
  "duration": 300,
  "shoulder_abduction": 58.5,
  "compensation": "无",
  "compensation_score": 100
}
```
响应：
```
{
  "code": 200,
  "message": "训练数据保存成功",
  "data": {
    "record_id": 123,
    "is_qualified": true,
    "score": 85
  }
}
```
7. 查询训练历史（需患者或医生认证）
接口：GET /api/training/history

描述：查询指定患者的训练记录。

请求头：Authorization: Bearer <token>

查询参数：
| 参数名                        | type   | 说明                     | 必填 |
|----------------------------|--------|------------------------|----|
| patient_id                  | string |  患者 ID             | 患者不需传，医生必填  |
| days                   | int | 查询最近几天，默认 30                   | 否  |
| limit                      | int |  返回条数，默认 50          | 否  |

响应：
```
{
  "code": 200,
  "message": "查询成功",
  "data": {
    "patient_id": "202505001",
    "count": 10,
    "records": [
      {
        "data_id": 1,
        "game_name": "星际翼航",
        "level_name": "航道1（入门）",
        "train_time": "2026-05-20 14:30:00",
        "shoulder_abduction": 58.5,
        "action_score": 8,
        "is_qualified": true,
        "game_score": 80,
        "compensation": "无"
      }
    ]
  }
}
```
### 8. 训练统计（需患者或医生认证）
接口：GET /api/training/stats

描述：获取患者训练的汇总统计数据。

请求头：Authorization: Bearer <token>

查询参数：

| 参数名        | Type   | 说明   | 必填         |
|------------|--------|------|------------|
| patient_id | String | 患者ID | 医生必填，患者可不填 |
响应：
```
{
  "code": 200,
  "data": {
    "total_sessions": 45,
    "avg_score": 72.5,
    "qualified_rate": 68.8,
    "by_game": [
      {
        "game_name": "星际翼航",
        "count": 20,
        "avg_score": 75.2,
        "best_score": 94
      },
      {
        "game_name": "星光舞台",
        "count": 25,
        "avg_score": 70.0,
        "best_score": 89
      }
    ]
  }
}
```
### 9. 接收脑电数据（供 HybridBCI 平台调用）
接口：POST /api/bci/receive

描述：接收脑机接口设备推送的实时脑电数据（HTTP 方式）。前端一般不调用，此接口供硬件/中间件使用。

请求体：
```
{
  "patient_id": "202505001",
  "device_id": "BCI-Device-001",
  "eeg_data": {
    "alpha_power": 8.5,
    "beta_power": 3.2,
    "attention": 65.5,
    "meditation": 40.2
  },
  "signal_quality": 85
}
```
响应：
```
{
  "code": 200,
  "message": "数据已接收"
}
```
### 10.2 Unity 获取游戏指令
接口：GET /api/unity/game-command

描述：Unity 轮询获取后端下发的控制指令（根据脑电数据动态调整难度等）。

响应：
```
{
  "code": 200,
  "data": {
    "action": "idle",    // idle / speed_up / slow_down / change_level
    "parameters": {}
  }
}
```
注：此接口当前为占位实现，实际逻辑需后续开发。
```
code	含义
200	成功
201	创建成功
400	请求参数错误
401	未认证或认证失败
403	无权限
404	资源不存在
500	服务器内部错误
```
测试账号
```
角色	用户名	密码
患者	patient_lisi	Xka061201!
患者	patient_zhangsan	Zhang123456!
医生	doctor_li	Li123456!
医生	doctor_wang	Wang123456!
管理员	yyq080829	xka061201
陪同人员	escort_lisi	Esc123456!
```

### 注意事项
1. 密码安全：当前版本密码以明文存储和传输，仅适用于开发测试。正式上线前必须改用 HTTPS 和哈希加密。

2. Token 管理：前端需将 token 保存在 localStorage 或 sessionStorage 中，并在每次请求时添加到 Authorization 头。

3. 跨域：后端已配置 CORS，可接受来自任何域的请求（开发环境）。若需要限制域名，可修改 config.py 中的 CORS_ORIGINS。

4. 时间格式：所有时间字段均返回 YYYY-MM-DD HH:MM:SS 格式。