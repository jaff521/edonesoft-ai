# 登记联络员备案 (LIAISON) 参考文档

## 办理逻辑

### 1. 信息收集
必须收集以下信息：

| 项目 | 是否必填 |
|------|----------|
| 联络员姓名 | ✅ 必填 |
| 手机号 | ✅ 必填 |
| 邮箱 | ✅ 必填 |
| 住址 | ✅ 必填 |
| 身份证正面照片 | ✅ 必填 |
| 身份证反面照片 | ✅ 必填 |

### 2. 证件核验
按主控 SKILL.md Step 3.1 的通用流程处理：
1. 将图片 URL 传入 `validate_document.py`，使用 `idcard` 类型，并传入联络员姓名作为对比参数。
2. 校验姓名一致性和证件有效期。
3. OCR 成功后，调用 `oss-uploader` Skill 上传正反面图片至 OSS。
4. 回填字段：`idCardFrontUrl`、`idCardBackUrl`。

### 3. 注意事项
- 该事项无 `beforeChange`，设为 `null`。
- 新增联络员时，系统默认填充法人信息，客户可在此基础上修改。
- 所有字段均为必填。

## 字段结构规范
```json
{
  "itemName": "LIAISON",
  "beforeChange": null,
  "afterChange": {
    "name": "{联络员姓名}",
    "phone": "{手机号}",
    "email": "{邮箱}",
    "address": "{住址}",
    "idCardFrontUrl": "{身份证正面 OSS URL}",
    "idCardBackUrl": "{身份证反面 OSS URL}"
  }
}
```
