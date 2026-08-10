# 章程备案时间 (BYLAW_ARTICLE) 参考文档

## 办理逻辑

### 1. 信息收集
必须收集以下信息：

| 项目 | 是否必填 |
|------|----------|
| 章程备案日期 | ✅ 必填 |

### 2. 注意事项
- 该事项无 `beforeChange`，设为 `null`。
- 仅需收集一个日期字段 `amendmentDate`，格式为 `YYYY-MM-DD`。
- 无需证件核验。

## 字段结构规范
```json
{
  "itemName": "BYLAW_ARTICLE",
  "beforeChange": null,
  "afterChange": {
    "amendmentDate": "{章程备案日期，格式 YYYY-MM-DD}"
  }
}
```
