---
name: ticket-creator
description: 当客户反馈业务需求(feature)或需要人工介入(consult)时，调用此工具创建支持工单。
user-invocable: true
metadata: {
  "openclaw": {
    "emoji": "🎫"
    
  }
}
---

# 支持工单创建助手

你负责将客户的反馈转化为系统工单。

## 调用指南
1. **触发时机**：客户咨询业务后，确认了需求，提交工单。
2. **前置交互**：
   - 必须确保已经获取了客户的**需求详情**（用于总结 `note`）。
   - 尽量确认客户的 **公司名称**，如果上下文中没有，可以礼貌询问。
3. **字段处理**：
   - `title`: 提取关键词生成简短标题。
   - `type`: 根据内容判断分类（feature/consult/complain）。
   - `note`: 整理客户的原始诉求，去掉寒暄，保留核心诉求。

## API 定义 (Internal)
- **Method**: POST
- **URL**: http://127.0.0.1:8080/api/tickets?apiToken=qwert12345
- **Payload**:
```json
{
  "type": "object",
  "properties": {
    "title": { "type": "string", "description": "简短的工单标题，例如：客户张三变更上海今明有限公司的股权" },
    "type": { "enum": ["feature", "consult", "complain"], "description": "工单类型" },
    "customer_name": { "type": "string", "description": "客户的姓名或昵称" },
    "company_name": { "type": "string", "description": "客户所在的公司名称" },
    "note": { "type": "string", "description": "详细的问题描述或AI总结" },
    "materials": { "type": "array", "items": { "type": "string" }, "description": "JSON 格式的任务材料，包含公司全称、法人信息、变更事项、材料清单等。" }
  },
  "required": ["title", "type", "note"]
}