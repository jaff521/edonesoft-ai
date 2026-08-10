# 企业微信 × OpenClaw 网关：第三方集成 API 说明文档

本网关对外提供了一组轻量级的 HTTP REST API，支持第三方系统（如工单系统、自定义 AI Skill 脚本、监控报警系统等）与企业微信进行深度的消息和会话交互。

---

## 1. 全局配置

- **基础 URL**: `http://<gateway-host>:<port>` (默认端口为 `8081`，可在 `config.json` 中的 `server.port` 修改)
- **Content-Type**: `application/json` (对于所有的 `POST` 请求)

---

## 2. 认证机制 (Authentication)

网关的所有 `/api/` 接口均受 API Token 保护，支持以下两种鉴权方式（二选一即可）：

### 2.1 方式 A：Bearer Token 头 (推荐)
在 HTTP 请求的 Headers 中添加 `Authorization` 头：
```http
Authorization: Bearer <your_api_token>
```
*示例：*
`Authorization: Bearer qwert12345`

### 2.2 方式 B：URL 查询参数 (适用于简单脚本/Webhook)
在 URL 请求路径后追加 `apiToken` 参数：
```http
GET /api/session?session_key=xxxx&apiToken=qwert12345
```

> [!NOTE]
> 默认的 API Token 在网关的 `config.json` 文件中配置于 `server.apiToken` 字段下。

---

## 3. 接口列表

### 3.1 查询会话上下文 (GET /api/session)

当第三方系统或 AI Skill 脚本需要定位当前对话底层的企业微信群聊 ID、机器人 ID 时，可以通过此接口查询。支持通过 `session_key` 或 `mapping_key` 查询。

#### 3.1.1 请求信息
- **请求方式**: `GET`
- **请求路径**: `/api/session`
- **请求参数**:
  
| 参数名 | 类型 | 是否必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `session_key` | `string` | 否 (与 `mapping_key` 二选一) | OpenClaw 会话 Key (格式如 `agent:main:dashboard:...`) |
| `mapping_key` | `string` | 否 (与 `session_key` 二选一) | 路由映射 Key (格式为 `robot_wxid:chat_type:target_wxid`) |
| `apiToken` | `string` | 否 | 如果 Header 未携带 Authorization，需填入此参数 |

#### 3.1.2 响应示例 (成功 - HTTP 200)
```json
{
  "mapping_key": "1688857086919052:group:10698454991379777",
  "session_key": "agent:main:dashboard:39b2ef0a-dd62-49ce-9023-672511acf795",
  "robot_wxid": "1688857086919052",
  "contact_wxid": "7881300390925677",
  "chatroom_id": "10698454991379777",
  "chat_type": "group",
  "created_at": 1779078259675,
  "last_active_at": 1779770847469
}
```

#### 3.1.3 字段说明
- `mapping_key`: 该会话发回微信所使用的路由唯一 Key。
- `robot_wxid`: 当前服务会话的微信机器人微信号 (WxID)。
- `contact_wxid`: 当前发起对话的客户/成员微信微信号 (WxID)。
- `chatroom_id`: 微信群聊 ID (仅群聊场景 `chat_type` 为 `group` 时存在，单聊下为 `null`)。
- `chat_type`: 对话类型，可选值有 `group`（群聊）或 `contact`（单聊）。

---

### 3.2 发送消息到企微群/个人 (POST /api/send)

第三方系统在处理完工单、触发报警或自动流转后，可通过此接口将消息异步/同步推送到指定的企业微信群聊或成员个人。

#### 3.2.1 请求信息
- **请求方式**: `POST`
- **请求路径**: `/api/send`
- **请求体格式**: `JSON`
- **请求体字段**:

| 字段名 | 类型 | 是否必选 | 说明 |
| :--- | :--- | :--- | :--- |
| `mapping_key` | `string` | 是 | 对应会话的映射 Key，格式为 `robot_wxid:chat_type:target_wxid` |
| `text` | `string` | 否 | 待发送的消息文本内容 (若未提供 `image_url`，则此项必选) |
| `image_url` | `string` | 否 | 待发送的图片链接。支持直接传入私有网络/带鉴权的图片流地址 (若未提供 `text`，则此项必选) |
| `image_headers` | `object` | 否 | 获取图片链接时所需的额外 HTTP 头部，例如 `{"X-API-Key": "..."}`。网关会使用此头部下载图片流并代理上传到微信平台发送 |

#### 3.2.2 响应示例 (成功 - HTTP 200)
```json
{
  "ok": true,
  "msg_id": "send_1779770848011",
  "mapping_key": "1688857086919052:group:10698454991379777"
}
```

#### 3.2.3 响应示例 (失败 - HTTP 400/401/500)
```json
{
  "error": "Failed to download image: HTTP status 403"
}
```

---

## 4. 典型集成场景调用示例 (Python 3)

以下示例演示了在一个自定义的 AI Skill (Python 脚本) 中如何自动获取当前会话的 IDs，并通过接口提交工单，最后模拟第三方系统调用 API 回复微信。

```python
import requests
import json

# 配置参数
GATEWAY_URL = "http://localhost:8081"
API_TOKEN = "qwert12345"
HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# 1. 模拟 AI 脚本在运行中，获取到 OpenClaw 的 session_key
session_key = "agent:main:dashboard:39b2ef0a-dd62-49ce-9023-672511acf795"

# 2. 查询该 session 对应的底层微信信息
session_resp = requests.get(
    f"{GATEWAY_URL}/api/session",
    params={"session_key": session_key},
    headers=HEADERS
)

if session_resp.status_code == 200:
    session_data = session_resp.json()
    mapping_key = session_data.get("mapping_key")
    chatroom_id = session_data.get("chatroom_id")
    print(f"解析成功，Mapping Key: {mapping_key}, 群聊 ID: {chatroom_id}")
    
    # 3. 将工单信息提交给第三方工单系统，并附带 mapping_key 字段
    ticket_payload = {
        "title": "测试工商变更工单",
        "description": "客户需要修改经营范围",
        "wechat_mapping_key": mapping_key  # 第三方工单系统将其妥善存储
    }
    # 模拟提交给第三方工单系统
    # requests.post("https://third-party.ticket-system/api/tickets", json=ticket_payload)
    
    # 4. 模拟第三方工单系统在后台处理完成后，调用网关发消息 API 回复群聊
    send_payload = {
        "mapping_key": mapping_key,
        "text": "您的工单已创建成功！处理结果将在此群内实时同步。"
    }
    send_resp = requests.post(
        f"{GATEWAY_URL}/api/send",
        headers=HEADERS,
        json=send_payload
    )
    if send_resp.status_code == 200:
        print("消息发送成功！")
    else:
        print(f"消息发送失败: {send_resp.text}")
else:
    print(f"获取会话信息失败: {session_resp.text}")
```

```shell
curl "http://8.130.75.243:8081/api/session?session_key=agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad&apiToken=qwert12345"
{"mapping_key":"1688857086919052:group:10698454991379777","session_key":"agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad","robot_wxid":"1688857086919052","contact_wxid":"7881300390925677","chatroom_id":"10698454991379777","chat_type":"group","created_at":1779328205293,"last_active_at":1779772129630}

curl http://8.130.75.243:8081/api/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer qwert12345" \
  -d '{
    "mapping_key": "1688857086919052:group:10698454991379777",
    "text": "这是一条来自第三方系统的测试消息"
  }'

curl -X POST http://8.130.75.243:8081/api/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer qwert12345" \
  -d '{
    "mapping_key": "1688857086919052:group:10698454991379777",
    "text": "以下是获取到的最新验证码：",
    "image_url": "http://61.169.217.122:8088/api/v1/task/captcha?company_name=%E4%B8%8A%E6%B5%B7%E9%9B%B6%E4%BA%A6%E7%BD%91%E7%BB%9C%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8",
    "image_headers": {
      "X-API-Key": "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6"
    }
  }'

  ```