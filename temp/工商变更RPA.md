# 工商变更RPA

## **认证方式**



### 接口地址：

- 外网地址：http://61.169.217.122:8088

- 内网地址：http://192.168.77.47:8080

### **API密钥认证**



所有接口都需要在请求头中携带 `X-API-Key` 进行认证。



#### **请求头**



```HTTP
X-API-Key: a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6
```



#### **配置API密钥**



可以通过环境变量 `API_KEY` 配置，默认值为：



```Plain Text
a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6
```



**注意：生产环境请务必修改默认密钥！**




## **快速开始**



### **减资变更流程**



1. **获取登录二维码**：调用 '/api/v1/task/captcha' 获取电子营业执照登录二维码

2. **扫码登录**：用户使用电子营业执照APP扫码登录

3. **验证登录**：调用 '/api/v1/task/verify' 验证登录状态

4. **开始变更**：调用 '/api/v1/task/capital-reduction/start' 开始减资变更流程（异步执行）

5. **查询状态**：调用 '/api/v1/task/capital-reduction/status/{sequence_id}' 查询任务状态



---



## **接口列表**



### **1. 首页**



#### **接口信息**



|项|值|
|---|---|
|接口路径|`GET /`|
|标签|首页|
|认证|不需要|



#### **请求示例**



```Bash
curl -X GET "http://61.169.217.122:8088/"
```



#### **响应示例**



```JSON
{
  "service": "工商变更服务API",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```



---



### **2. 健康检查**



#### **接口信息**



|项|值|
|---|---|
|接口路径|`GET /health`|
|标签|健康检查|
|认证|不需要|



#### **请求示例**



```Bash
curl -X GET "http://61.169.217.122:8088/health"
```



#### **响应示例**



```JSON
{
  "status": "healthy",
  "timestamp": "2026-05-27T10:00:00.000000"
}
```



---



### **3. 获取电子营业执照验证码截图**



#### **接口信息**



|项|值|
|---|---|
|接口路径|`GET`` /api/v1/task/captcha`|
|标签|任务管理|
|认证|需要|



#### **请求参数**



|参数名|类型|必填|默认值|说明|
|---|---|---|---|---|
|company_name|string|否|default|公司名称，用于创建独立的Chromium账号|



#### **请求示例**


company_name为 上海零亦网络科技有限公司
```C#
curl  "http://61.169.217.122:8088/api/v1/task/captcha?company_name=%E4%B8%8A%E6%B5%B7%E9%9B%B6%E4%BA%A6%E7%BD%91%E7%BB%9C%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8" \
  -H "X-API-Key: a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6" \
  -o qrcode.png
```



#### **响应说明**



- **成功**：返回PNG格式的二维码图片文件流

- **失败**：返回JSON格式的错误信息



**失败响应示例**



```Python
{
  "detail": "获取二维码截图失败"
}
```



---



### **4. 验证登录状态**



#### **接口信息**



|项|值|
|---|---|
|接口路径|`GET`` /api/v1/task/verify`|
|标签|任务管理|
|认证|需要|



#### **请求参数**



|参数名|类型|必填|默认值|说明|
|---|---|---|---|---|
|company_name|string|否|default|公司名称，用于识别对应的浏览器会话|
|timeout|integer|否|120|等待超时时间（秒），仅 check_only=False 时有效|
|check_only|boolean|否|false|是否只检查登录状态，不等待扫码|



#### **功能说明**



- **check_only=true**：只检查当前是否已登录，立即返回结果

- **check_only=false**：轮询检查登录状态，直到登录成功或超时



#### **请求示例**



**检查登录状态（快速）**



```Bash
curl  "http://61.169.217.122:8088/api/v1/task/verify?company_name=%E4%B8%8A%E6%B5%B7%E9%9B%B6%E4%BA%A6%E7%BD%91%E7%BB%9C%E7%A7%91%E6%8A%80%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8&check_only=true" \
  -H "X-API-Key: a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6"
```



**等待扫码登录**



```Bash
curl -X POST "http://61.169.217.122:8088/api/v1/task/verify?company_name=公司A&timeout=120" \
  -H "X-API-Key: a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6"
```



#### **响应示例**



**登录成功**



```JSON
{
  "code": 200,
  "message": "已登录",
  "data": {
    "login_time": "2026-05-27T10:00:00.000000"
  }
}
```



**登录失败**



```JSON
{
  "code": 401,
  "message": "未登录",
  "data": null
}
```



**等待超时**



```JSON
{
  "code": 401,
  "message": "等待扫码超时 (120 秒)",
  "data": null
}
```



---



### **5. 开始注册资本变更流程**



#### **接口信息**



|项|值|
|---|---|
|接口路径|`POST ``/api/v1/task/capital-reduction/start`|
|标签|任务管理|
|认证|需要|



#### **功能说明**



输入减资变更信息，完成注册资本变更的整个流程。



**重要说明：**

- 接口会首先验证登录状态

- 如果未登录，直接返回未登录错误

- 如果已登录，生成序列ID并异步执行减资变更流程

- 支持回调通知，通过 callback_url 参数指定回调地址

#### **请求参数**



**Query参数**



|参数名|类型|必填|默认值|说明|
|---|---|---|---|---|
|company_name|string|是|default|公司名称，用于识别对应的浏览器会话|
|callback_url|string|是|-|回调地址，用于异步执行过程中通知任务状态|



**Body参数**



|参数名|类型|必填|说明|
|---|---|---|---|
|original_capital|string|否|原注册资本|
|new_capital|string|是|减资后注册资本|
|reduction_method|string|否|减资方式|
|reason|string|否|减资原因|
|notice_date|string|否|公告日期|
|debt_settlement|string|否|债权债务处理情况|
|agent_delegate|object|否|经办人信息|



**agent_delegate 参数说明**



|参数名|类型|必填|默认值|说明|
|---|---|---|---|---|
|id_card_front_path|string|是||身份证人像面图片路径（url）|
|id_card_back_path|string|是||身份证国徽面图片路径（url）|
|name|string|否||经办人姓名|
|fixed_telephone|string|否||固定电话|
|mobile_phone|string|是||移动电话|
|cert_type|string|否|中华人民共和国居民身份证|证件类型|
|cert_number|string|否||证件号码|
|agent_type|string|否|经营主体登记注册代理人|经办人类型|
|is_agent|string|否|否|是否代理机构（是/否）|
|begin_date|string|否|当前日期|代表或接受委托的有效期限开始日期|
|end_date|string|否|当前日期\+180天|代表或接受委托的有效期限结束日期|
|company_telephone|string|否||企业联系电话|



#### **请求示例**



```Bash
curl -X POST "http://61.169.217.122:8088/api/v1/task/capital-reduction/start?company_name=公司A&callback_url=http://your-server.com/webhook" \
  -H "X-API-Key: a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6" \
  -H "Content-Type: application/json" \
  -d '{
    "new_capital": "50",
    "agent_delegate": {
      "name": "张三",
      "mobile_phone": "13800138000",
      "agent_type": "经营主体登记注册代理人",
      "is_agent": "否"
    }
  }'
```



#### **响应示例**



**场景1：未登录**



```JSON
{
  "code": 401,
  "message": "请先扫码登录",
  "data": {
    "success": false,
    "message": "请先扫码登录"
  }
}
```



**场景2：已登录，工单创建成功**



```JSON
{
  "code": 200,
  "message": "工单接收成功，已进入执行状态",
  "data": {
    "success": true,
    "sequence_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running",
    "message": "工单接收成功，已进入执行状态",
    "created_at": "2026-05-27T10:00:00.000000"
  }
}
```



#### **回调通知**



当指定 callback_url 时，系统会在任务执行过程中发送回调通知：



**回调数据格式**



```JSON
{
    "sequence_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "running/completed/failed",
    "message": "状态描述消息",
    "result": {},
    "timestamp": "2026-05-27T10:00:00.000000"
}
```



**回调状态说明**



|状态|说明|
|---|---|
|running|任务开始执行|
|completed|任务成功完成|
|failed|任务执行失败或异常|



---



### 



### **6. 开始股东变更（开发中）**



#### **接口信息**



|项|值|
|---|---|
|接口路径|`POST /api/v1/task/shareholder-change/start`|
|标签|任务管理|
|认证|需要|



#### **请求参数**



|参数名|类型|必填|说明|
|---|---|---|---|
|company_name|string|是|公司名称|
|original_capital|string|否|原注册资本|
|new_capital|string|否|新注册资本|
|change_type|string|是|变更类型（新增股东/退出股东/修改股权比例）|
|shareholders|array|否|股东信息列表|
|agent_delegate|object|否|经办人信息|



#### **请求示例**



```Bash
curl -X POST "http://61.169.217.122:8088/api/v1/task/shareholder-change/start" \
  -H "X-API-Key: a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8s9T0u1V2w3X4y5Z6" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "公司A",
    "change_type": "新增股东",
    "shareholders": []
  }'
```



#### **响应示例**



```JSON
{
  "code": 200,
  "message": "股东变更流程开发中",
  "data": {
    "status": "pending"
  }
}
```



---



## **数据模型**



### **ApiResponse（通用响应模型）**



```JSON
{
  "code": 200,
  "message": "success",
  "data": {}
}
```



|字段|类型|说明|
|---|---|---|
|code|integer|状态码|
|message|string|响应消息|
|data|object/null|响应数据|



### **CapitalReductionRequest（减资变更请求模型）**



```JSON
{
  "original_capital": "",
  "new_capital": "50",
  "reduction_method": "",
  "reason": "",
  "notice_date": "",
  "debt_settlement": "",
  "agent_delegate": {}
}
```



### **AgentDelegateRequest（经办人信息模型）**



```JSON
{
  "id_card_front_path": "",
  "id_card_back_path": "",
  "name": "张三",
  "fixed_telephone": "",
  "mobile_phone": "13800138000",
  "cert_type": "中华人民共和国居民身份证",
  "cert_number": "",
  "agent_type": "经营主体登记注册代理人",
  "is_agent": "否",
  "begin_date": "2026-05-27",
  "end_date": "2026-11-23"
}
```



---



## **错误码说明**



|HTTP状态码|说明|
|---|---|
|200|请求成功|
|400|请求参数错误|
|401|认证失败（缺少API密钥或API密钥无效）|
|404|接口不存在|
|500|服务器内部错误|



### **错误响应示例**



**缺少API密钥**



```JSON
{
  "detail": "缺少API密钥，请在请求头中添加 X-API-Key"
}
```



**无效的API密钥**



```JSON
{
  "detail": "无效的API密钥"
}
```



---



## **完整示例**



### **启动服务**



```Bash
# 进入项目目录
cd /Users/zhujun/Documents/ProjectCode/AiQifu_Aiagents/ai_ICChange_rpa/icc_change_rpa/ICC_change

# 启动服务
python main.py
```





