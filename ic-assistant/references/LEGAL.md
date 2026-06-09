# 法定代表人变更 (LEGAL) 参考文档

## 办理逻辑
1. **信息收集**：必须收集以下四项：新法定代表人姓名、新法定代表人手机号、身份证正面照片、身份证反面照片。
2. **核验**：收到身份证照片后，调用 `validate_document.py` 进行 OCR 识别，校验姓名是否一致、证件是否过期。
3. **上传**：图片需调用 `oss-uploader` 存储至 OSS，获取永久 URL。
4. **强制校验**：未收集齐全以上四项信息前，不得进入汇总确认或建单。

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
    "idCardBackUrl": "{新法人身份证反面 OSS URL（必填）}"
  }
}
```
