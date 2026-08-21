# 监事备案 (SUPERVISOR) 参考文档

## 办理逻辑

### 1. 信息收集
需先确认客户是否设置监事：

| 项目 | 是否必填 |
|------|----------|
| 是否设置监事 | ✅ 必填 |
| 监事姓名 | ✅ 设置监事时必填 |
| 监事手机号 | ✅ 设置监事时必填 |
| 监事身份证正面照片 | ✅ 设置监事时必填 |
| 监事身份证反面照片 | ✅ 设置监事时必填 |

### 2. 证件核验
收到身份证照片后，按主控 SKILL.md Step 3.1 的通用流程处理：
1. 将图片 URL 传入 `image_processor.py`，使用 `idcard` 类型，并传入监事姓名作为对比参数。
2. 校验姓名一致性和证件有效期。
3. OCR 成功后，调用 `oss-uploader` Skill 上传正反面图片至 OSS。
4. 回填字段：`idCardFrontUrl`、`idCardBackUrl`。

### 3. 注意事项
- 该事项无 `beforeChange`，设为 `null`。
- 需先询问客户"是否需要设置监事"，根据回答决定 `hasSupervisor` 取值。
- 若 `hasSupervisor` 为 `false`，`afterChange` 中仅包含该字段，无需收集其他信息。
- 若 `hasSupervisor` 为 `true`，需额外收集监事的姓名、手机号和身份证正反面照片。

## 字段结构规范

不设置监事时：
```json
{
  "itemName": "SUPERVISOR",
  "beforeChange": null,
  "afterChange": {
    "hasSupervisor": false
  }
}
```

设置监事时：
```json
{
  "itemName": "SUPERVISOR",
  "beforeChange": null,
  "afterChange": {
    "hasSupervisor": true,
    "name": "{监事姓名}",
    "phone": "{监事手机号}",
    "idCardFrontUrl": "{监事身份证正面 OSS URL}",
    "idCardBackUrl": "{监事身份证反面 OSS URL}"
  }
}
```
