# 高级管理人员备案 (SENIOR_MANAGER) 参考文档

## 办理逻辑

### 1. 信息收集
必须收集以下信息：

| 项目 | 是否必填 |
|------|----------|
| 原人员姓名 | ✅ 必填 |
| 原职务名称 | ✅ 必填 |
| 新人员姓名 | ✅ 必填 |
| 新职务名称 | ✅ 必填 |
| 新人员电话号码 | ❌ 可选 |
| 新人员身份证正面照片 | ❌ 可选 |
| 新人员身份证反面照片 | ❌ 可选 |

### 2. 证件核验（可选）
如客户提供了新人员身份证照片，按主控 SKILL.md Step 3.1 的通用流程处理：
1. 将图片 URL 传入 `validate_document.py`，使用 `idcard` 类型，并传入新人员姓名作为对比参数。
2. 校验姓名一致性和证件有效期。
3. OCR 成功后，调用 `oss-uploader` Skill 上传正反面图片至 OSS。
4. 回填字段：`idCardFrontUrl`、`idCardBackUrl`。

### 3. 注意事项
- `beforeChange` 仅需姓名和职务。
- `phone`、`idCardFrontUrl`、`idCardBackUrl` 仅用于 `afterChange`，均为可选字段。
- `position` 取值范围：`财务负责人` / `经理`。

## 字段结构规范
```json
{
  "itemName": "SENIOR_MANAGER",
  "beforeChange": {
    "name": "{原人员姓名}",
    "position": "{原职务名称}"
  },
  "afterChange": {
    "name": "{新人员姓名}",
    "position": "{新职务名称}",
    "phone": "{新人员电话号码（可选）}",
    "idCardFrontUrl": "{新人员身份证正面 OSS URL（可选）}",
    "idCardBackUrl": "{新人员身份证反面 OSS URL（可选）}"
  }
}
```
