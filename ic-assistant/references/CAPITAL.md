# 注册资本变更 (CAPITAL) 参考文档

## 办理逻辑

### 1. 信息收集
- **原注册资本**：从企业查询结果中自动获取，无需客户手动提供。
- **原股东出资明细**：从企业查询结果中获取各股东姓名、出资额、持股比例。
- **目标注册资本**：询问客户变更后的目标注册资本金额。
- **币种**：默认为 `CNY`（人民币），如需其他币种（`USD`/`EUR`/`HKD`/`JPY`）请客户明确。
- **认缴时间**（可选）：可根据实际情况收集股东的认缴开始时间（`subscriptionStartDate`）和认缴出资时间（`subscriptionContributionDate`），格式需符合 `YYYY-MM-DD`。

### 2. 自动配平计算
- 新股东出资额 = 新注册资本总额 × 原股东占比
- 持股比例保持不变（除非客户明确要求调整比例）
- 校验：所有股东 `ratio` 之和 = 1，所有股东 `amount` 之和 = 总注册资本

### 3. 数据格式
- `amount`：单位为**元**（非万元）
- `ratio`：**0~1 小数**（如 0.50 表示 50%）

> **注意**：纯减资场景请参考 `REDUCTION.md`，其办理逻辑更简化（仅收集目标资本额，自动按原比例折算）。

## 字段结构规范
```json
{
  "itemName": "CAPITAL",
  "beforeChange": {
    "amount": "{原资本额_元单位}",
    "currency": "CNY",
    "shareholders": [
      { "name": "{股东1}", "amount": "{原出资额_元}", "ratio": "{原持股比例_0至1}" }
    ]
  },
  "afterChange": {
    "amount": "{目标资本额_元单位}",
    "currency": "CNY",
    "shareholders": [
      { 
        "name": "{股东1}", 
        "amount": "{自动折算的新出资额_元}", 
        "ratio": "{原持股比例_0至1}",
        "subscriptionStartDate": "{认缴开始时间 YYYY-MM-DD（可选）}",
        "subscriptionContributionDate": "{认缴出资时间 YYYY-MM-DD（可选）}"
      }
    ]
  }
}
```

