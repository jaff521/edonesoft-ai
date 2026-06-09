# 经营期限变更 (PERIOD) 参考文档

## 办理逻辑
- 收集客户变更后的日期（或“长期”），校验格式并记录。
- 收集完成后，立即整理为标准结构：
  - 固定期限：`{"itemName":"PERIOD","afterChange":{"type":"fixed","date":"2030-12-31"}}`
  - 长期：`{"itemName":"PERIOD","afterChange":{"type":"forever"}}`
- 若已知原期限，也同步整理 `beforeChange`；若原期限未知，保留为空或待补充，不要臆造。

## 字段结构规范
```json
{
  "itemName": "PERIOD",
  "beforeChange": {
    "type": "fixed",
    "date": "{原期限 YYYY-MM-DD}"
  },
  "afterChange": {
    "type": "fixed 或 forever",
    "date": "{新期限 YYYY-MM-DD，仅 fixed 时有此字段}"
  }
}
```
