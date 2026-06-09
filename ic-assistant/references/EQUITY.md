# 股权变更 (EQUITY) 参考文档

## 办理逻辑
1. **结构调整**：展示原股东列表，请客户提供新的股东名录及占股比例明细。优先要求同时给出出资额和持股比例。
2. **智能类型识别**：对新增股东名称进行正则匹配（企业关键词如：公司/有限/股份/合伙/厂/中心/集团等），自动标记为“企业法人”或“自然人”。
3. **资金平衡校验**：
   - 校验总额是否等于注册资本。如果不符，提示客户调整。
   - 校验总比例是否等于 1。如果不符，提示调整，最终使用 `0~1` 小数。
4. **证件材料补齐**：
   - 自然人股东：身份证正反面和身份证号。通过 `validate_document.py` 验证并获取，通过 `oss-uploader` 上传至 OSS 获取 `certFrontUrl` 和 `certBackUrl`，`certType` 为 `ID_CARD`。
   - 企业法人股东：营业执照和统一社会信用代码。验证并上传至 OSS 获取 `certFrontUrl`，`certType` 为 `BUSINESS_LICENSE`。

## 字段结构规范
```json
{
  "itemName": "EQUITY",
  "beforeChange": {
    "shareholders": [
      { "name": "{原股东姓名}", "amount": {原出资额_元}, "ratio": {原持股比例_0至1} }
    ]
  },
  "afterChange": {
    "shareholders": [
      {
        "name": "{新股东姓名}",
        "amount": {新出资额_元},
        "ratio": {新持股比例_0至1},
        "certType": "{ID_CARD 或 BUSINESS_LICENSE}",
        "certNumber": "{证件号码}",
        "certFrontUrl": "{正面 OSS 地址}",
        "certBackUrl": "{反面 OSS 地址，自然人必填}"
      }
    ]
  }
}
```
