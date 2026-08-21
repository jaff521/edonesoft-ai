---
name: hr-creator
description: 用于在系统中自动化创建人事业务工单（参保登记、参保转出、公积金转入、公积金封存）。
user-invocable: true
metadata: {
  "openclaw": {
    "emoji": "👥"
  }
}
---

# 人事业务工单创建助手 (HR Creator)

你作为专业的前置助手，负责将用户的参保登记、参保转出、公积金转入、公积金封存等人事诉求转化为标准的系统人事工单。

## 配置要求
- 必填环境变量：
  - `TICKET_CREATOR_BASE_URL`（后端服务地址）
  - `TICKET_CREATOR_OPEN_TOKEN`（`X-Open-Token` 鉴权令牌，未配置时回退读取 `RPA_API_KEY`）

## 调用指南

### 1. 触发时机
当客户表达以下人事诉求之一时触发：
- **参保登记** (`orderType=BIZ_INSURANCE`)：员工新参保、社保开户登记。
- **参保转出** (`orderType=BIZ_INSURANCE_OUT`)：员工社保停保、参保转出。
- **公积金转入** (`orderType=BIZ_HOUSING_FUND_IN`)：员工公积金账户转入、封存户启封转入。
- **公积金封存** (`orderType=BIZ_HOUSING_FUND_SEAL`)：员工离职公积金封存、停缴封存。

### 2. 前置条件与数据收集
* **企业信息**：企业名称（`enterpriseName`）、统一社会信用代码（`creditCode`，可选）。
* **员工身份证信息**：支持从文本获取或通过 `image_processor.py`（DashScope OCR 视觉识别）从客户发送的身份证正反面照片中自动提取姓名和身份证号。
* **业务扩展明细**：根据具体 `orderType` 收集必填明细字段（见下表）。
* **会话路由**：如在微信会话中，须先调用 `session_status` 提取 `Session` 字段值作为 `sessionKey`。

### 3. 字段处理规则
* **自动映射 orderType**：支持中文自动归一化（如 "参保登记" -> `BIZ_INSURANCE`）。
* **日期格式标准化**：所有日期字段统一转换为 `yyyy-MM-dd` 格式（如 `2026-08-01`）。
* **二阶段确认建单**：助手收集完全部信息后，须在微信群展示逐字段标注的确认信息，**获得客户回复“确认”后**方可调用本 Skill 创建工单。

---

## 输入参数

大模型提取后的 JSON 作为参数，通过运行 `python3 {baseDir}/scripts/hr_creator.py '<JSON_PARAMS>'` 执行：

### 示例 1：参保登记工单
```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "orderType": "BIZ_INSURANCE"
  },
  "insuranceDetail": {
    "employeeName": "张三",
    "idCard": "310101199001011234",
    "employmentStartDate": "2026-08-01",
    "contractSignType": "初签",
    "contractTerm": "固定期限劳动合同",
    "contractStartDate": "2026-08-01",
    "contractEndDate": "2029-07-31",
    "employmentForm": "全日制",
    "isDispatch": "否"
  }
}
```

### 示例 2：参保转出工单
```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "orderType": "BIZ_INSURANCE_OUT"
  },
  "insuranceOutDetail": {
    "employeeName": "李四",
    "idCard": "310101199203031234"
  }
}
```

### 示例 3：公积金转入工单
```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "orderType": "BIZ_HOUSING_FUND_IN"
  },
  "housingFundInDetail": {
    "employeeName": "王五",
    "idCard": "310101199405051234",
    "fundAccount": "310000000012345",
    "fundBase": 15000.00
  }
}
```

### 示例 4：公积金封存工单
```json
{
  "sessionKey": "agent:main:dashboard:2cfd8ac5-0664-451a-a5f1-8d620b9da1ad",
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "orderType": "BIZ_HOUSING_FUND_SEAL"
  },
  "housingFundSealDetail": {
    "employeeName": "赵六",
    "idCard": "310101199606061234",
    "fundAccount": "310000000067890",
    "leaveDate": "2026-08-31",
    "sealReason": "员工离职"
  }
}
```

---

## 字段详细规范

### 1. 参保登记扩展 (`insuranceDetail`)
| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `employeeName` | ✅ | string | 员工姓名 |
| `idCard` | ✅ | string | 身份证号（18位） |
| `employmentStartDate` | ✅ | string | 就业起始日期（`yyyy-MM-dd`） |
| `contractSignType` | ✅ | string | 合同签订方式：`未签` / `初签` |
| `contractTerm` | ✅ | string | 合同期限：`固定期限劳动合同` / `无固定期限劳动合同` / `以完成一定工作任务为期限` |
| `contractStartDate` | ✅ | string | 合同开始日期（`yyyy-MM-dd`） |
| `contractEndDate` | ✅ | string | 合同结束日期（`yyyy-MM-dd`） |
| `employmentForm` | ❌ | string | 用工形式，默认 `全日制` |
| `isDispatch` | ❌ | string | 是否劳务派遣：`是` / `否`，默认 `否` |

### 2. 参保转出扩展 (`insuranceOutDetail`)
| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `employeeName` | ✅ | string | 员工姓名 |
| `idCard` | ✅ | string | 身份证号（18位） |

### 3. 公积金转入扩展 (`housingFundInDetail`)
| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `employeeName` | ✅ | string | 员工姓名 |
| `idCard` | ✅ | string | 身份证号（18位） |
| `fundAccount` | ✅ | string | 公积金账号 |
| `fundBase` | ✅ | number | 公积金基数（数字，可保留2位小数） |

### 4. 公积金封存扩展 (`housingFundSealDetail`)
| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `employeeName` | ✅ | string | 员工姓名 |
| `idCard` | ✅ | string | 身份证号（18位） |
| `fundAccount` | ✅ | string | 公积金账号 |
| `leaveDate` | ❌ | string | 退工日期（`yyyy-MM-dd`） |
| `sealReason` | ❌ | string | 封存原因（如 "员工离职"） |

---

## 工单创建后的回复规范

当脚本返回 `success=true` 且包含 `ticket_id` 字段时，**必须**按如下格式回复用户：

> ✅ 人事业务工单已创建，工单号：`{ticket_id}`。请等待经办人确认后进行后续操作。
