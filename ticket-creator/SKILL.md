---
name: ticket-creator
description: 用于在工商变更系统中自动化创建/新增聚合工单（包含工单主信息、变更登记事项明细列表）。
user-invocable: true
metadata: {
  "openclaw": {
    "emoji": "🎫"
  }
}
---

# 工商变更工单创建助手

你作为专业的前置助手，负责将用户的自然语言业务诉求（如企业改名、换法人、股份变更、改经营范围等）转化为标准的系统工商变更聚合工单。

## 配置要求
- 必填环境变量：
  - `TICKET_CREATOR_BASE_URL`
  - `TICKET_CREATOR_OPEN_TOKEN`

## 调用指南

### 1. 触发时机
当客户明确表达需要"申请工商变更"、"新增变更工单"或"登记工商变更事项"时，调用此工具。

### 2. 前置交互
在调用前，大模型需要通过多轮对话或上下文分析，确保获取到以下**核心要素**：
* **企业信息**：企业名称、统一社会信用代码（18位）
* **变更事项**：要变更什么（如法定代表人、注册资本等），以及变更前后对比
* **会话路由（微信会话 Key）**：如果在当前微信会话中，**必须**先调用 `session_status` 工具并提取其返回结果中的 `Session` 字段值作为 `sessionKey` 传入（或填入 `workOrder.wechatMappingKey`），以绑定聊天通道。

### 3. 字段处理规则
* **格式对齐**：只需输出 `workOrder`、`itemList` 两个根节点，嵌套由脚本自动完成
* **严格对照接口示例**：优先严格对照 `工商变更工单API.md` 第 8.1 节“新增工单”请求体生成参数；如果字段与自然语言描述冲突，以第 8.1 节示例和第 7 节 JSON 结构规范为准
* **字典值优先**：优先传接口字典 `item_value`，如 `objectType=ENTERPRISE`、`matterType=CHANGE`、`orderType=BIZ_CHANGE`、`orderStatus=CONFIRM_BY_C`、`itemName=EQUITY`；常见中文别名脚本会自动归一化
* **自动忽略审计字段**：不生成 `id`、`createBy`、`createTime`、`updateBy`、`updateTime`、`sysOrgCode`、`tenantId`、`delFlag`、`orderNo`、`orderId` 等后端填充字段
* **JSON 节点**：`beforeChange` 和 `afterChange` 必须是明确的 K-V 对象
* **默认值**：未提供时默认 `objectType=ENTERPRISE`、`matterType=CHANGE`、`orderType=BIZ_CHANGE`、`orderStatus=CONFIRM_BY_C`
* **可选字段**：如用户提供身份证照片URL、身份证号等，应一并传入

---

## 输入参数

大模型提取后的 JSON 作为参数，通过运行 `python3 skills/ticket-creator/ticket_creator.py '<JSON_PARAMS>'` 执行：

```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "matterType": "CHANGE",
    "objectType": "ENTERPRISE",
    "orderType": "BIZ_CHANGE",
    "orderStatus": "CONFIRM_BY_C"
  },
  "itemList": [
    {
      "itemName": "CAPITAL",
      "beforeChange": {
        "amount": 1000000,
        "currency": "CNY",
        "shareholders": [
          { "name": "张三", "amount": 600000, "ratio": 0.60 },
          { "name": "李四", "amount": 400000, "ratio": 0.40 }
        ]
      },
      "afterChange": {
        "amount": 5000000,
        "currency": "CNY",
        "shareholders": [
          { "name": "张三", "amount": 3000000, "ratio": 0.60 },
          { "name": "李四", "amount": 2000000, "ratio": 0.40 }
        ]
      }
    },
    {
      "itemName": "SCOPE",
      "beforeChange": {
        "scope": "计算机软件开发；技术咨询。"
      },
      "afterChange": {
        "scope": "计算机软件开发；技术咨询；信息系统集成服务；数据处理服务。"
      }
    },
    {
      "itemName": "EQUITY",
      "beforeChange": {
        "shareholders": [
          { "name": "王五", "amount": 3000000, "ratio": 0.60, "certType": "ID_CARD", "certNumber": "310101199001011234" },
          { "name": "赵六", "amount": 2000000, "ratio": 0.40, "certType": "ID_CARD", "certNumber": "310101198501012345" }
        ]
      },
      "afterChange": {
        "shareholders": [
          { "name": "王五", "amount": 2550000, "ratio": 0.51, "certType": "ID_CARD", "certNumber": "310101199001011234", "certFrontUrl": "https://example.com/files/wangwu_front.jpg", "certBackUrl": "https://example.com/files/wangwu_back.jpg" },
          { "name": "赵六", "amount": 1500000, "ratio": 0.30, "certType": "ID_CARD", "certNumber": "310101198501012345" },
          { "name": "孙七", "amount": 950000, "ratio": 0.19, "certType": "ID_CARD", "certNumber": "440300198001011234" }
        ]
      }
    }
  ]
}
```

### 字段说明

#### 顶层参数 (Root Parameters)
| 字段 | 必填 | 说明 |
|------|------|------|
| sessionKey | ❌ | 微信会话唯一 Key。调用 `session_status` 接口后从中提取 `Session` 字段值传入，用于静默匹配聊天通道。 |

#### workOrder 工单主信息
| 字段 | 必填 | 说明 |
|------|------|------|
| enterpriseName | ✅ | 企业名称/对象名称 |
| creditCode | ✅ | 企业统一信用代码（18位） |
| matterType | ✅ | 事项类型代码，通常传 `CHANGE` |
| objectType | ❌ | 对象类型，默认空 |
| orderType | ❌ | 工单类型，默认空 |
| orderStatus | ❌ | 工单状态，默认空（开放接口新增默认为 `CONFIRM_BY_C`） |
| wechatMappingKey | ❌ | 微信路由凭证键（可选，若传入 sessionKey 则程序会自动将其作为 wechatMappingKey 注入，不需人工传值） |

#### itemList 变更登记事项列表（数组）
| 字段 | 必填 | 说明 |
|------|------|------|
| itemName | ✅ | 事项名称代码，如：`ADDR`、`LEGAL`、`CAPITAL`、`SCOPE`、`NAME`、`EQUITY`、`PERIOD` |
| beforeChange | ✅ | 必须严格使用第 7 节定义的 JSON 结构，如 `CAPITAL.amount` 单位为元、`EQUITY.ratio` 为 0~1 小数 |
| afterChange | ✅ | 必须严格使用第 7 节定义的 JSON 结构 |

### 常见事项类型参考
- 住所变更 → `matterType: "CHANGE"`，`itemName: "ADDR"`
- 法定代表人变更 → `matterType: "CHANGE"`，`itemName: "LEGAL"`
- 注册资本变更 → `matterType: "CHANGE"`，`itemName: "CAPITAL"`
- 经营范围变更 → `matterType: "CHANGE"`，`itemName: "SCOPE"`
- 企业名称变更 → `matterType: "CHANGE"`，`itemName: "NAME"`
- 股东/股权变更 → `matterType: "CHANGE"`，`itemName: "EQUITY"`

### 事项 JSON 结构要求
- `CAPITAL`：`{"amount": 5000000, "currency": "CNY", "shareholders": [{"name": "张三", "amount": 2500000, "ratio": 0.50}]}`
- `SCOPE`：`{"scope": "经营范围全文"}`
- `ADDR`：`{"address": "完整经营地址"}`
- `NAME` / `LEGAL`：`{"name": "名称或姓名"}`
- `PERIOD`：固定期限传 `{"type": "fixed", "date": "2030-12-31"}`，长期传 `{"type": "forever"}`
- `EQUITY`：`{"shareholders":[{"name":"王五","amount":2550000,"ratio":0.51,"certType":"ID_CARD","certNumber":"310101...","certFrontUrl":"https://...","certBackUrl":"https://..."}]}`。证件字段均为可选，`certType` 取值：`ID_CARD`（身份证）、`BUSINESS_LICENSE`（营业执照）、`PASSPORT`（护照）
