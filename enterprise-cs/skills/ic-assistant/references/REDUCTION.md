# 减资变更 (REDUCTION / CAPITAL) 参考文档

## 办理逻辑
1. **纯数值收集**：仅收集“变更后的公司目标注册资本额”。不需要向客户索要任何证件照片或手动填报新股东的出资与占比。
2. **自动比例配平**：新股东出资额在内部根据原持股比例自动计算得出（新出资额 = 新注册资本总额 * 原股东占比）。持股比例保持不变。无需人工干预和修正。
3. **数据格式**：所有涉及 `CAPITAL` 项的数据结构都必须按元单位、0~1小数比例。

## 字段结构规范
```json
{
  "itemName": "CAPITAL",
  "beforeChange": {
    "amount": {原资本额_元单位},
    "currency": "CNY",
    "shareholders": [
      { "name": "{股东1}", "amount": {原出资额_元}, "ratio": {原持股比例} }
    ]
  },
  "afterChange": {
    "amount": {目标资本额_元单位},
    "currency": "CNY",
    "shareholders": [
      { "name": "{股东1}", "amount": {自动折算的新出资额_元}, "ratio": {原持股比例} }
    ]
  }
}
```
