# 股权变更 (EQUITY) 参考文档

## 办理逻辑

### 1. 结构调整
展示原股东列表，请客户提供新的股东名录及占股比例明细。优先要求同时给出出资额和持股比例。

### 2. 智能类型识别
对新增股东名称进行正则匹配：
- **企业关键词**：`/(公司|有限|股份|合伙|厂|中心|集团|社|部|所|店|行)$/`
- 若匹配成功，自动标记为"企业法人"；否则标记为"自然人"。
- 话术示例：「已记录新股东【张三】，识别为【自然人】，认缴【300000 元】，持股【0.5】。如有误请更正。」

### 3. 资金平衡校验
- 校验总额是否等于注册资本。如果不符，提示客户调整。
- 校验总比例是否等于 1。如果不符，提示调整，最终使用 `0~1` 小数。

### 4. 证件材料补齐
确认股东结构后，逐一向客户索要所需证件材料，按主控 SKILL.md Step 3.1 的通用流程处理图片：

**自然人股东**：
1. 请求提供身份证正反面照片和身份证号。
2. 调用 `image_processor.py`（类型 `idcard`，传入股东姓名作为对比参数）进行 OCR 识别。
3. OCR 成功后，调用 `oss-uploader` 上传正反面图片至 OSS。
4. 回填字段：
   - `certType` → `"ID_CARD"`
   - `certNumber` → OCR 识别的身份证号
   - `certFrontUrl` → 正面 OSS URL
   - `certBackUrl` → 反面 OSS URL

**企业法人股东**：
1. 请求提供营业执照照片和统一社会信用代码。
2. 调用 `image_processor.py`（类型 `business_license`，传入股东企业名作为对比参数）进行 OCR 识别。
3. OCR 成功后，调用 `oss-uploader` 上传执照图片至 OSS。
4. 回填字段：
   - `certType` → `"BUSINESS_LICENSE"`
   - `certNumber` → OCR 识别的统一社会信用代码
   - `certFrontUrl` → 执照 OSS URL

### 5. 股东手机号收集（可选）
可一并收集各股东的联系电话，回填到 `phone` 字段。

### 6. 认缴时间收集（可选）
变更后股东可选填认缴开始时间 (`subscriptionStartDate`) 和认缴出资时间 (`subscriptionContributionDate`)，格式 `YYYY-MM-DD`。仅用于 afterChange。

### 7. 进度跟踪
检查 `itemListDraft` 中所有变更后股东的证件字段（`certType`/`certNumber`/`certFrontUrl`，自然人还需 `certBackUrl`）是否已填入有效值。
- 示例话术：「进度：已收 2/3 名股东的证件」
- 未收齐的继续逐一索要。

### 8. 监事信息收集（可选）
如客户表示需要设置监事（`needSupervisor=true`），还需收集：
- 监事姓名（必填）
- 监事手机号（可选）
- 监事身份证正反面照片（可选，流程同主控 SKILL.md Step 3.1）

> [!NOTE]
> 此处的监事信息属于股权变更（EQUITY）事项的内嵌附属字段。如果客户只需要单独办理监事备案，并不涉及股权变更，则应当引导客户使用独立的 `SUPERVISOR` 事项，而不是在此处收集。

> **注意**：`equityTransfers`（股权转让明细）和 `enterpriseType`（变更后企业类型）由后台经办人在确认环节填写，材料收集阶段**无需**向客户索要。

## 字段结构规范
```json
{
  "itemName": "EQUITY",
  "beforeChange": {
    "shareholders": [
      {
        "name": "{原股东姓名}",
        "amount": "{原出资额_元}",
        "ratio": "{原持股比例_0至1}",
        "phone": "{股东手机号（可选）}",
        "certType": "{ID_CARD 或 BUSINESS_LICENSE 或 PASSPORT}",
        "certNumber": "{证件号码}",
        "certFrontUrl": "{正面 OSS 地址}",
        "certBackUrl": "{反面 OSS 地址}"
      }
    ]
  },
  "afterChange": {
    "shareholders": [
      {
        "name": "{新股东姓名}",
        "amount": "{新出资额_元}",
        "ratio": "{新持股比例_0至1}",
        "phone": "{股东手机号（可选）}",
        "certType": "{ID_CARD 或 BUSINESS_LICENSE 或 PASSPORT}",
        "certNumber": "{证件号码}",
        "certFrontUrl": "{正面 OSS 地址}",
        "certBackUrl": "{反面 OSS 地址，自然人必填}",
        "subscriptionStartDate": "{认缴开始时间 YYYY-MM-DD（可选）}",
        "subscriptionContributionDate": "{认缴出资时间 YYYY-MM-DD（可选）}"
      }
    ],
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
