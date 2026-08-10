## 接口地址

http://61.169.217.122:10680/api/callback/recruitment


## 鉴权

请求 Header 中携带 Token：

```
Authorization: Bearer {token}
```

Token：7f3a8c2b1d6e4f598a0b7c5d3e2f1a09b6c4d2e0f8a7b5c3d1e9f0a2b4c6d8e6f

## 参数说明

| 字段             | 类型   | 必填      | 说明                                                         |
| ---------------- | ------ | --------- | ------------------------------------------------------------ |
| sessionId        | string | 是        | 对应请求时返回的会话 ID                                      |
| action           | string | 否        | 回调类型。不传或空默认为 reply。可选：request_resume / schedule_interview |
| content          | string | 视 action | reply 时为回复文本；schedule_interview 时为邀约文案          |
| interviewTime    | string | 否        | 面试开始时间，格式 yyyy-MM-dd HH:mm                          |
| interviewEndTime | string | 否        | 面试结束时间，格式 yyyy-MM-dd HH:mm                          |

## 示例

### 1. 回复消息（默认，action 可不传）

```json
{
  "sessionId": "local_test_session_005",
  "content": "你好，感谢关注我们的岗位，方便发一份简历过来吗？"
}
```

### 2. 索要简历

```json
{
  "sessionId": "local_test_session_005",
  "action": "request_resume"
}
```

### 3. 约面试

```json
{
  "sessionId": "local_test_session_005",
  "action": "schedule_interview",
  "content": "恭喜您通过初选，现邀请您参加面试。",
  "interviewTime": "2026-06-20 14:00",
  "interviewEndTime": "2026-06-20 15:00"
}
```

## 响应

```json
{
  "success": true,
  "msg": "ok"
}
```