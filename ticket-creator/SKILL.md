---
name: ticket-creator
description: 用于在工商变更系统中自动化创建/新增聚合工单（包含工单主信息、变更登记事项明细列表、经办人列表）。
user-invocable: true
metadata: {
  "openclaw": {
    "emoji": "🎫"
  }
}
---

# 工商变更工单创建助手

你作为专业的前置助手，负责将用户的自然语言业务诉求（如企业改名、换法人、股份变更、改经营范围等）转化为标准的系统工商变更聚合工单。

## 调用指南

### 1. 触发时机
当客户明确表达需要"申请工商变更"、"新增变更工单"、"登记工商变更事项"或"指派经办人办理工商业务"时，调用此工具。

### 2. 前置交互
在调用前，大模型需要通过多轮对话或上下文分析，确保获取到以下**核心三要素**：
* **企业信息**：企业名称、统一社会信用代码（18位）
* **变更事项**：要变更什么（如法定代表人、注册资本等），以及变更前后对比
* **经办人**：负责跑流程的经办人姓名及联系电话

### 3. 字段处理规则
* **格式对齐**：只需输出 `workOrder`、`itemList`、`agentList` 三个根节点，嵌套由脚本自动完成
* **自动忽略审计字段**：不生成 `id`、`createBy`、`createTime`、`updateBy`、`updateTime`、`sysOrgCode`、`tenantId`、`delFlag`、`orderNo`、`orderId` 等后端填充字段
* **JSON 节点**：`beforeChange` 和 `afterChange` 必须是明确的 K-V 对象
* **可选字段**：如用户提供身份证照片URL、身份证号等，应一并传入

---

## 输入参数

大模型提取后的 JSON 传入 `ticket_creator.py` 执行：

```json
{
  "workOrder": {
    "enterpriseName": "企业名称",
    "creditCode": "统一社会信用代码",
    "matterType": "事项类型",
    "objectType": "对象类型（可选）",
    "orderType": "工单类型（可选）",
    "orderStatus": "工单状态（可选）"
  },
  "itemList": [
    {
      "itemName": "变更事项名称",
      "beforeChange": {"原字段": "原值"},
      "afterChange": {"新字段": "新值"}
    }
  ],
  "agentList": [
    {
      "agentName": "经办人姓名",
      "agentPhone": "手机号",
      "agentIdentityType": "身份类型（默认1）",
      "agentType": "经办人类型（可选）",
      "agentIdCard": "身份证号（可选）",
      "idCardFrontUrl": "身份证正面URL（可选）",
      "idCardBackUrl": "身份证反面URL（可选）"
    }
  ]
}
```

### 字段说明

#### workOrder 工单主信息
| 字段 | 必填 | 说明 |
|------|------|------|
| enterpriseName | ✅ | 企业名称/对象名称 |
| creditCode | ✅ | 企业统一信用代码（18位） |
| matterType | ✅ | 事项类型，如：法定代表人变更、注册资本变更、经营范围变更、住所变更、名称变更、股东股权变更等 |
| objectType | ❌ | 对象类型，默认空 |
| orderType | ❌ | 工单类型，默认空 |
| orderStatus | ❌ | 工单状态，默认空 |

#### itemList 变更登记事项列表（数组）
| 字段 | 必填 | 说明 |
|------|------|------|
| itemName | ✅ | 事项名称，如：住所、法定代表人、注册资本等 |
| beforeChange | ✅ | 变更前信息，K-V对象 |
| afterChange | ✅ | 变更后信息，K-V对象 |

#### agentList 经办人列表（数组）
| 字段 | 必填 | 说明 |
|------|------|------|
| agentName | ✅ | 经办人姓名 |
| agentPhone | ✅ | 经办人手机号 |
| agentIdentityType | ❌ | 经办人身份类型，默认"1" |
| agentType | ❌ | 经办人类型 |
| agentIdCard | ❌ | 经办人身份证号码 |
| idCardFrontUrl | ❌ | 身份证正面图片URL |
| idCardBackUrl | ❌ | 身份证反面图片URL |

### 常见事项类型参考
- 住所变更 → matterType: "住所变更"，itemName: "住所"
- 法定代表人变更 → matterType: "法定代表人变更"，itemName: "法定代表人"
- 注册资本变更 → matterType: "注册资本变更"，itemName: "注册资本"
- 经营范围变更 → matterType: "经营范围变更"，itemName: "经营范围"
- 企业名称变更 → matterType: "企业名称变更"，itemName: "企业名称"
- 股东/股权变更 → matterType: "股东股权变更"，itemName: "股东"
