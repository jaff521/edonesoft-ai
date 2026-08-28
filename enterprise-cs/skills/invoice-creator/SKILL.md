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
  - `TICKET_CREATOR_BASE_URL`（后端服务地址）
  - `TICKET_CREATOR_OPEN_TOKEN`（`X-Open-Token` 鉴权令牌，未配置时回退读取 `RPA_API_KEY`）

## 调用指南

### 1. 触发时机
当客户明确表达需要"开发票"、"开票"、"新增开票工单"等意图时触发。

### 2. 前置条件
* **销方信息**：企业名称 + 信用代码（**v1.2 强约束**：销方企业必须已存在于本系统客户信息中，否则后端接口将直接拒绝建单）
* **购方信息**：购方名称（必填）、购方信用代码（可选，可自动查询）
* **开票明细行**：至少一行，包含项目名称、金额、税率
* **会话路由**：如在微信会话中，须先调用 `session_status` 提取 `Session` 字段值作为 `sessionKey`

### 3. 字段处理规则
* **格式对齐**：输出 `workOrder`、`invoiceOrder`、`invoiceDetailList` 三个根节点
* **自动忽略审计字段**：不生成 `id`、`createBy`、`createTime`、`updateBy`、`updateTime`、`sysOrgCode`、`tenantId`、`delFlag`、`orderNo`、`orderId` 等后端填充字段
* **字典值优先**：优先传接口字典值，如 `invoiceType=BLUE_INVOICE`、`invoiceCategory=SPECIAL_VAT_INVOICE`；脚本也支持中文自动归一化
* **默认蓝字与类别自动匹配**：默认固定 `invoiceType=BLUE_INVOICE`（蓝字发票）免去询问；发票类别结合销方企业纳税人身份自动匹配（小规模纳税人默认 `NORMAL_INVOICE` 普票、默认税率 `1%`；一般纳税人默认 `SPECIAL_VAT_INVOICE` 专票）
* **项目名称格式**：`itemName` 必须按 `*{税收分类编码简称}*{客户货物名称}` 格式填写（如 `*鉴证咨询服务*法律服务`），其中简称来自 `tax_query.py` 返回的 `shortName`
* **税收编码交互确认（仅展示简称）**：`goodsServiceTaxCode`（19位纯数字）为**必填项**。前置助手**必须**先调用 `tax_query.py` 检索候选列表，按简称 `shortName` 呈献给用户选择确认
* **购方信用代码处理规则**：客户已提供则直接使用；未提供且购方为企业，**必须**调用 `unified_query.py` 自动查询确认；查询不到则留空提交
* **含税金额与税率规范（OpenAPI v1.2）**：客户提供的金额填入 `taxInclusiveAmount`（含税金额/价税合计），`taxRate` 传字符串形式（如 `"0.06"`、`"0.01"`，脚本自动转化归一化）。后端不再接收 `unitPrice`、`amount`、`taxAmount` 字段，含税单价由后端按 `含税金额 / 数量` 自动计算并保留13位小数
* **数量默认为1**：客户未明确说明数量时，默认 `quantity = 1`
* **明细行单位（unit）精准提取**：当客户提及数量和单位时须准确提取填入；未提取到则留空即可
* **二次确认方可建单**：助手整理出完整开票汇总后，**必须获得客户明确回复"确认"后**方可调用脚本创建工单
* **默认值**：未提供时默认 `orderType=BIZ_INVOICE`、`matterType=CHANGE`、`orderStatus=CONFIRM_BY_A`

---

## 输入参数

大模型提取后的 JSON 作为参数，通过运行 `python3 {baseDir}/scripts/invoice_creator.py '<JSON_PARAMS>'` 执行：

```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
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
      "itemName": "*信息技术服务*软件技术服务费",
      "goodsServiceTaxCode": "3040201020000000000",
      "unit": "项",
      "quantity": 1,
      "taxRate": "0.06",
      "taxInclusiveAmount": 10000
    }
  ]
}
```

### 字段说明

#### 顶层参数 (Root Parameters)
| 字段 | 必填 | 说明 |
|------|------|------|
| sessionKey | ❌ | 微信会话唯一 Key。调用 `session_status` 接口后从中提取 `Session` 字段值传入 |

#### workOrder 工单主信息
| 字段 | 必填 | 说明 |
|------|------|------|
| enterpriseName | ✅ | 销方企业名称 |
| creditCode | ❌ | 销方统一社会信用代码（18位） |
| agentId | ❌ | 经办人 ID |
| isFinalSubmit | ❌ | 是否最终提交，1=是 0=否，默认 0 |
| orderType | ❌ | 工单类型，默认 `BIZ_INVOICE`（脚本自动填充） |
| orderStatus | ❌ | 工单状态，默认 `CONFIRM_BY_A`（待经办人确认） |

#### invoiceOrder 发票扩展信息
| 字段 | 必填 | 说明 |
|------|------|------|
| buyerName | ✅ | 购买方名称 |
| buyerCreditCode | ❌ | 购买方统一社会信用代码 |
| invoiceType | ✅ | `BLUE_INVOICE`(蓝字) / `RED_INVOICE`(红字)。也支持传中文 |
| invoiceCategory | ✅ | `SPECIAL_VAT_INVOICE`(专票) / `NORMAL_INVOICE`(普票)。也支持传中文 |
| invoiceRemark | ❌ | 开票备注 |

#### invoiceDetailList 开票明细行（数组，至少一行）
| 字段 | 必填 | 说明 |
|------|------|------|
| itemName | ✅ | 项目名称，格式：`*{税收分类编码简称}*{客户货物名称}` |
| goodsServiceTaxCode | ✅ | **商品和服务税收分类编码（19位纯数字）** |
| spec | ❌ | 规格型号 |
| unit | ❌ | 单位（如"项"、"次"、"套"等） |
| quantity | ✅ | 数量。**客户未说明时默认为 1** |
| taxRate | ✅ | 税率字符串，如 `"0.06"`、`"0.01"`、`"0"` |
| taxInclusiveAmount | ✅ | **含税金额（元，价税合计）**。后端按 `含税金额 / 数量` 自动计算含税单价，不再接收 `unitPrice` / `amount` / `taxAmount` |

### 常见税率参考
| 值 | 适用范围 |
|----|---------|
| 0.13 (13%) | 一般货物/劳务 |
| 0.09 (9%) | 不动产/运输 |
| 0.06 (6%) | 现代服务业（软件开发、咨询等） |
| 0.01 (1%) | 小规模征收率 |
| 0 (0%) | 免税/零税率 |

---

## 工单创建后的回复规范

脚本执行成功后，返回 JSON 中会包含以下额外字段：

| 字段 | 说明 |
|------|------|
| `ticket_id` | 工单在系统中的唯一 ID |

### 回复模板（工单创建成功）

当脚本返回 `success=true` 且包含 `ticket_id` 字段时，**必须**按如下格式回复用户：

> ✅ 开票工单已创建，工单号：`{ticket_id}`。请等待经办人确认后进行后续开票操作。

### 回复模板（工单创建失败）

> ⚠️ 开票工单创建失败：{error_message}。请核实信息后重试。
