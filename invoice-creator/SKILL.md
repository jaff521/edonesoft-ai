---
name: invoice-creator
description: 用于在工商变更系统中自动化创建开票工单（含购方信息与开票明细行）。
user-invocable: true
metadata: {
  "openclaw": {
    "emoji": "🧾"
  }
}
---

# 发票开票工单创建助手

你作为专业的前置助手，负责将用户的开票诉求转化为标准的系统开票工单。

## 配置要求
- 必填环境变量：
  - `TICKET_CREATOR_BASE_URL`（复用工商变更的后端地址）
  - `RPA_API_KEY`（复用，用于 `X-Open-Token` 鉴权）

## 调用指南

### 1. 触发时机
当客户明确表达需要"开发票"、"开票"、"新增开票工单"、"申请开票"时，调用此工具。

### 2. 前置交互
在调用前，大模型需要通过多轮对话或上下文分析，确保获取到以下**核心要素**：
* **销方企业信息**：企业名称、统一社会信用代码
* **购方信息**：购买方名称（必填）、购买方信用代码（可选）、发票类型（蓝字/红字）、发票类别（专票/普票）、开票备注（可选）
* **开票明细行**：至少一行，包含项目名称、数量、单价、税率
* **会话路由**：如在微信会话中，须先调用 `session_status` 提取 `Session` 字段值作为 `sessionKey`

### 3. 字段处理规则
* **格式对齐**：输出 `workOrder`、`invoiceOrder`、`invoiceDetailList` 三个根节点
* **自动忽略审计字段**：不生成 `id`、`createBy`、`createTime`、`updateBy`、`updateTime`、`sysOrgCode`、`tenantId`、`delFlag`、`orderNo`、`orderId` 等后端填充字段
* **字典值优先**：优先传接口字典值，如 `invoiceType=BLUE_INVOICE`、`invoiceCategory=SPECIAL_VAT_INVOICE`；脚本也支持中文自动归一化
* **税收编码自动搜索**：若明细行中未提供 `goodsServiceTaxCode`（19位编码），可传入 `taxKeyword` 字段，脚本会自动调用 `/taxCategory/search` 接口匹配最佳编码
* **购方信用代码自动补全**：若购方为公司且未传入 `buyerCreditCode`，脚本底层会自动联动企信查接口自动检索并填充其 18 位统一社会信用代码

---

## 输入参数

大模型提取后的 JSON 作为参数，通过运行 `python3 {baseDir}/scripts/invoice_creator.py '<JSON_PARAMS>'` 执行：

```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "agentId": "2059454092242161666",
    "isFinalSubmit": 0
  },
  "invoiceOrder": {
    "buyerName": "北京某科技有限公司",
    "buyerCreditCode": "91110108MA01XXXXX",
    "invoiceType": "BLUE_INVOICE",
    "invoiceCategory": "SPECIAL_VAT_INVOICE",
    "invoiceRemark": "项目一期开发费"
  },
  "invoiceDetailList": [
    {
      "itemName": "软件开发服务",
      "taxKeyword": "软件开发",
      "unit": "项",
      "quantity": 1,
      "unitPrice": 100000,
      "taxRate": "6%"
    },
    {
      "itemName": "技术咨询服务",
      "goodsServiceTaxCode": "1090601020000000000",
      "unit": "次",
      "quantity": 2,
      "unitPrice": 5000,
      "taxRate": "6%"
    }
  ]
}
```

### 字段说明

#### 顶层参数 (Root Parameters)
| 字段 | 必填 | 说明 |
|------|------|------|
| sessionKey | ❌ | 微信会话唯一 Key。调用 `session_status` 接口后从中提取 `Session` 字段值传入。 |

#### workOrder 工单主信息
| 字段 | 必填 | 说明 |
|------|------|------|
| enterpriseName | ✅ | 销方企业名称 |
| creditCode | ❌ | 销方统一社会信用代码（18位） |
| agentId | ❌ | 经办人 ID |
| isFinalSubmit | ❌ | 是否最终提交，1=是 0=否，默认 0 |
| orderStatus | ❌ | 工单状态，默认 `PREPARING` |

#### invoiceOrder 发票扩展信息
| 字段 | 必填 | 说明 |
|------|------|------|
| buyerName | ✅ | 购买方名称 |
| buyerCreditCode | ❌ | 购买方统一社会信用代码 |
| invoiceType | ✅ | `BLUE_INVOICE`(蓝字发票) / `RED_INVOICE`(红字发票)。也支持传中文"蓝字"、"红字"，脚本自动归一化 |
| invoiceCategory | ✅ | `SPECIAL_VAT_INVOICE`(增值税专用发票) / `NORMAL_INVOICE`(普通发票)。也支持传中文"专票"、"普票"，脚本自动归一化 |
| invoiceRemark | ❌ | 开票备注 |

#### invoiceDetailList 开票明细行（数组，至少一行）
| 字段 | 必填 | 说明 |
|------|------|------|
| itemName | ✅ | 项目名称 |
| goodsServiceTaxCode | ❌ | 商品和服务税收分类编码（19位）。若未提供，可传 `taxKeyword` 自动搜索 |
| taxKeyword | ❌ | 用于自动搜索税收分类编码的关键词。仅当 `goodsServiceTaxCode` 未提供时生效 |
| spec | ❌ | 规格型号 |
| unit | ❌ | 单位（如"项"、"次"、"套"等） |
| quantity | ✅ | 数量 |
| unitPrice | ✅ | 单价（元） |
| amount | ❌ | 金额（可不传，服务端自动 = 数量×单价） |
| taxRate | ✅ | 税率，如 `13%`、`6%`、`0%` |

### 常见税率参考
| 值 | 适用范围 |
|----|---------|
| 13% | 一般货物/劳务 |
| 9% | 不动产/运输 |
| 6% | 现代服务业（软件开发、咨询等） |
| 3% | 简易征收 |
| 0% | 免税/零税率 |

---

## 工单创建后的回复规范

脚本执行成功后，返回 JSON 中会包含以下额外字段：

| 字段          | 说明 |
|--------------|------|
| `ticket_id`  | 工单在系统中的唯一 ID |

### ✅ 回复模板（工单创建成功）

当脚本返回 `success=true` 且包含 `ticket_id` 字段时，**必须**按如下格式回复用户：

> ✅ 开票工单已创建，工单号：`{ticket_id}`。
>
> 请等待经办人确认后进行后续开票操作。如有疑问，请联系客服。

### ❌ 回复模板（工单创建失败）

> ⚠️ 开票工单创建失败：{error_message}。请核实信息后重试。
