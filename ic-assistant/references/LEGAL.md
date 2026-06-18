# 法定代表人变更 (LEGAL) 参考文档

## 办理逻辑

### 1. 信息收集
必须收集以下信息，未收集齐全前**不得**进入汇总确认或建单：

| 项目 | 是否必填 |
|------|----------|
| 新法定代表人姓名 | ✅ 必填 |
| 新法定代表人手机号 | ✅ 必填 |
| 身份证正面照片（人像面） | ✅ 必填 |
| 身份证反面照片（国徽面） | ✅ 必填 |
| 是否需要设置监事 | ❌ 可选（询问客户） |
| 监事姓名 | ⚠️ 条件必填（needSupervisor=true 时） |
| 监事手机号 | ❌ 可选 |
| 监事身份证正面照片 | ❌ 可选 |
| 监事身份证反面照片 | ❌ 可选 |

### 2. 证件核验
收到身份证照片后，按主控 SKILL.md Step 3.1 的通用流程处理：
1. 将客户发送的图片 URL 传入 `validate_document.py`，使用 `idcard` 类型，并传入新法人姓名作为对比参数。
2. 校验内容：
   - 姓名与客户提供的新法人姓名是否一致
   - 证件是否在有效期内
3. **OCR 成功**：展示识别结果（姓名、身份证号、有效期），请客户确认。
4. **OCR 失败**：提示"图片不清晰，请重新拍摄"，等待客户重传。

### 3. 图片上传
OCR 验证通过后，调用 `oss-uploader` Skill 将正反面图片分别上传至 OSS，获取两个永久 URL：
- 正面 → `idCardFrontUrl`
- 反面 → `idCardBackUrl`

### 4. 身份证号提取
从 OCR 结果的 `extracted.id_number` 字段中提取身份证号码，可作为辅助信息向客户展示确认。

### 5. 监事信息收集（可选）
如客户表示需要设置监事（`needSupervisor=true`），还需收集：
- 监事姓名（必填）
- 监事手机号（可选）
- 监事身份证正反面照片（可选，流程同 Step 2-3）

## 字段结构规范
```json
{
  "itemName": "LEGAL",
  "beforeChange": {
    "name": "{原法定代表人姓名}"
  },
  "afterChange": {
    "name": "{新法定代表人姓名}",
    "phone": "{新法人手机号（必填）}",
    "idCardFrontUrl": "{新法人身份证正面 OSS URL（必填）}",
    "idCardBackUrl": "{新法人身份证反面 OSS URL（必填）}",
    "needSupervisor": "{是否需要监事，boolean（可选）}",
    "supervisor": {
      "name": "{监事姓名（needSupervisor=true 时必填）}",
      "phone": "{监事手机号（可选）}",
      "idCardFrontUrl": "{监事身份证正面 OSS URL（可选）}",
      "idCardBackUrl": "{监事身份证反面 OSS URL（可选）}"
    }
  }
}
```
