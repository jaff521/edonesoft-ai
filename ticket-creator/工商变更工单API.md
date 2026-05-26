# 工商变更工单模块 — 外部系统对接参考文档

> **文档版本**：v2.1  
> **更新日期**：2026-05-26  
> **适用模块**：工单管理（前端路由 `/bizorder/workOrder`）  
> **数据来源**：数据库字典（`sys_dict` / `sys_dict_item`）、后端实体与开放接口、前端事项 JSON 表单组件

---

## 1. 概述

本系统提供 **工商变更工单** 管理能力，包含：

- **工单主表**（`biz_work_order`）：企业基本信息、类型、状态、客户确认标记等
- **事项明细表**（`biz_order_item`）：变更登记事项及变更前/后 JSON 数据

> 经办人由后台管理端创建并关联，开放接口 **不涉及** 经办人数据的读写。

外部系统通过 **开放接口**（静态 Token 鉴权）进行读写，接口路径前缀为 `/bizorder/openapi/workOrder/**`，与内部管理端接口（需登录 + 权限）相互独立。

---

## 2. 鉴权方式

| 项目       | 说明                                                        |
| ---------- | ----------------------------------------------------------- |
| 鉴权类型   | 静态 Token（请求头校验）                                    |
| 请求头名称 | `X-Open-Token`                                              |
| 配置项     | 服务端 `bizorder.openapi.enabled`、`bizorder.openapi.token` |
| 生效范围   | 仅 `/bizorder/openapi/*`                                    |
| Token 获取 | 由本系统运维/对接方线下分配，**请勿写入客户端代码仓库**     |

### 2.1 错误响应

鉴权失败时 HTTP 状态码通常为 **200**，响应体中 `success=false`，`code` 为业务错误码：

```json
{
  "success": false,
  "code": 401,
  "message": "无效的开放接口 Token",
  "result": null,
  "timestamp": 1716537600000
}
```

| code | 含义               |
| ---- | ------------------ |
| 401  | Token 缺失或不匹配 |
| 500  | 服务端未配置 token |
| 503  | 开放接口未启用     |

---

## 3. 接口基础信息

| 项目              | 值                                             |
| ----------------- | ---------------------------------------------- |
| 默认 Context Path | `/jeecg-boot`                                  |
| 开放接口 Base URL | `{host}/jeecg-boot/bizorder/openapi/workOrder` |
| Content-Type      | `application/json`（POST/PUT 请求体）          |
| 字符编码          | UTF-8                                          |

> 生产环境 host、context-path 以实际部署为准。

---

## 4. 开放接口清单

| 方法 | 路径                                     | 说明                                |
| ---- | ---------------------------------------- | ----------------------------------- |
| GET  | `/list`                                  | 分页列表（含事项明细）              |
| GET  | `/queryById?id={id}`                     | 聚合详情（主单 + 事项）             |
| POST | `/add`                                   | 新增工单（聚合写入）                |
| PUT  | `/edit`                                  | 编辑工单（主单更新 + 子表全量替换） |
| POST | `/transit?id={id}&targetStatus={status}` | 状态流转（受状态机约束）            |

### 4.1 列表查询参数

| 参数           | 类型   | 必填 | 说明                                          |
| -------------- | ------ | ---- | --------------------------------------------- |
| pageNo         | int    | 否   | 页码，默认 1                                  |
| pageSize       | int    | 否   | 每页条数，默认 10                             |
| orderNo        | string | 否   | 工单编号（精确/模糊，按 QueryGenerator 规则） |
| enterpriseName | string | 否   | 企业名称                                      |
| orderStatus    | string | 否   | 工单状态字典值，如 `PENDING`                  |
| objectType     | string | 否   | 对象类型字典值，如 `ENTERPRISE`               |

### 4.2 统一成功响应格式

```json
{
  "success": true,
  "code": 200,
  "message": "",
  "result": { },
  "timestamp": 1716537600000
}
```

- 列表接口 `result` 为 MyBatis-Plus 分页对象，含 `records`、`total`、`current`、`size` 等
- 详情接口 `result` 为 `WorkOrderPage` 聚合对象（见第 5 节）
- 新增接口 `result` 为字符串消息，如 `"添加成功！id=2050000000000005001"`

---

## 5. 数据模型

### 5.1 聚合对象 WorkOrderPage

新增/编辑/详情均使用同一聚合结构：

```json
{
  "workOrder": { },
  "itemList": [ ]
}
```

### 5.2 工单主表 workOrder（biz_work_order）

| 字段             | 类型     | 必填     | 说明                                                         |
| ---------------- | -------- | -------- | ------------------------------------------------------------ |
| id               | string   | 编辑必填 | 主键，新增可不传（系统自动生成）                             |
| orderNo          | string   | 否       | 工单编号；留空自动生成，规则见 5.4                           |
| objectType       | string   | 否       | 对象类型，字典 `biz_object_type`，默认 `ENTERPRISE`          |
| matterType       | string   | 否       | 事项类型，字典 `biz_matter_type`，默认 `CHANGE`              |
| orderType        | string   | 否       | 工单类型，字典 `biz_order_type`，默认 `BIZ_CHANGE`           |
| orderStatus      | string   | 否       | 工单状态，字典 `biz_order_status`，新增默认 `CONFIRM_BY_C`（待客户确认） |
| enterpriseName   | string   | **是**   | 企业名称 / 对象名称                                          |
| creditCode       | string   | 否       | 18 位统一社会信用代码                                        |
| wechatMappingKey | string   | 否       | 微信路由唯一凭证 Key，格式 `{robot_wxid}:{chat_type}:{target_wxid}`；仅微信群聊渠道发起的工单有此值，后台手动创建的工单为 `null` |
| createTime       | datetime | —        | 创建时间，格式 `yyyy-MM-dd HH:mm:ss`                         |
| updateTime       | datetime | —        | 更新时间                                                     |

**字典翻译字段**（仅查询响应可能出现）：`objectType_dictText`、`matterType_dictText`、`orderType_dictText`、`orderStatus_dictText`


### 5.4 工单编号规则

- 格式：`GS` + `yyyyMMdd` + 6 位序号
- 示例：`GS20260520000001`
- 新增时 `orderNo` 为空则服务端自动生成

### 5.5 事项明细 itemList（biz_order_item）

| 字段         | 类型          | 必填   | 说明                                             |
| ------------ | ------------- | ------ | ------------------------------------------------ |
| id           | string        | 否     | 主键；编辑时子表会先删后插                       |
| orderId      | string        | —      | 工单 ID，服务端自动填充                          |
| itemName     | string        | **是** | 事项名称，字典 `biz_item_name` 的 **item_value** |
| beforeChange | object / null | 否     | 变更前 JSON 对象                                 |
| afterChange  | object / null | 否     | 变更后 JSON 对象                                 |

> **重要**：`beforeChange`、`afterChange` 在 API 中为 **JSON 对象**，不是字符串。空数据请传 `null`，不要传 `{}` 或全空占位对象。

---

## 6. 字典与枚举

所有字典存储于数据库表 `sys_dict`（字典定义）和 `sys_dict_item`（字典项）。  
对接时 **传值使用 `item_value`（英文代码）**，展示时使用 `item_text`（中文名称）。

### 6.1 工单状态 biz_order_status

后端枚举类：`OrderStatusEnum`（与字典值一致）

| item_text（中文） | item_value（代码） | 说明                                     |
| ----------------- | ------------------ | ---------------------------------------- |
| 待客户确认        | CONFIRM_BY_C       | 开放接口新增默认状态，等待客户在 H5 确认 |
| 待经办人确认      | CONFIRM_BY_A       | 客户确认后进入，等待后台经办人确认       |
| 待填报            | PENDING            | 经办人确认后进入                         |
| 暂存              | DRAFT              | 草稿                                     |
| 材料已保存        | SAVED              | 材料已保存                               |
| 材料已人工确认    | CONFIRMED          | 人工确认完成                             |
| 办理中            | PROCESSING         | 正在办理                                 |
| 已办结            | DONE               | 终态                                     |

### 6.2 工单状态流转规则

仅允许以下流转（调用 `/transit` 接口）：

```
CONFIRM_BY_C → CONFIRM_BY_A   （客户 H5 确认，自动流转）
CONFIRM_BY_A → PENDING        （后台经办人确认）
PENDING      → DRAFT, SAVED
DRAFT        → SAVED, DRAFT
SAVED        → CONFIRMED, DRAFT
CONFIRMED    → PROCESSING
PROCESSING   → DONE
DONE         → （不可再流转）
```

> `CONFIRM_BY_C → CONFIRM_BY_A` 由 H5 的「确认资料无误」按钮触发（接口 `/bizorder/workOrder/confirmByCustomer`），非 `/transit` 接口。
> `CONFIRM_BY_A → PENDING` 由后台管理端「经办人确认」按钮触发（接口 `/bizorder/workOrder/confirmByAgent`），非 `/transit` 接口。

非法流转将返回业务异常，如：`工单状态不允许从 PENDING 流转到 DONE`。

### 6.3 对象类型 biz_object_type

| item_text                      | item_value     |
| ------------------------------ | -------------- |
| 企业                           | ENTERPRISE     |
| 个体工商户                     | INDIVIDUAL     |
| 农民专业合作社                 | COOP           |
| 外国（地区）企业常驻代表机构   | FOREIGN_OFFICE |
| 外国（地区）企业在中国境内经营 | FOREIGN_BIZ    |

### 6.4 事项类型 biz_matter_type

| item_text    | item_value     |
| ------------ | -------------- |
| 设立         | SETUP          |
| 变更         | CHANGE         |
| 迁移         | MIGRATE        |
| 注销         | CANCEL         |
| 个转企       | IND2ENT        |
| 跨省迁移     | CROSS_PROVINCE |
| 名称自主申报 | NAME_DECLARE   |

### 6.5 工单类型 biz_order_type

| item_text | item_value |
| --------- | ---------- |
| 工商变更  | BIZ_CHANGE |
| 工商设立  | BIZ_SETUP  |
| 工商注销  | BIZ_CANCEL |

### 6.6 事项名称 biz_item_name

事项名称决定 `beforeChange` / `afterChange` 的 JSON 结构（见第 7 节）。

| item_text  | item_value | JSON 结构类型      |
| ---------- | ---------- | ------------------ |
| 企业名称   | NAME       | 单字段 `name`      |
| 注册资本   | CAPITAL    | 金额 + 币种        |
| 股权       | EQUITY     | 股东列表           |
| 经营范围   | SCOPE      | 多行文本 `scope`   |
| 经营期限   | PERIOD     | 期限类型 + 到期日  |
| 经营地址   | ADDR       | 多行文本 `address` |
| 法定代表人 | LEGAL      | 单字段 `name`      |

---

## 7. 事项明细 JSON 字段规范（重点）

`itemName` 取值来自字典 `biz_item_name` 的 **item_value**。  
`beforeChange` 与 `afterChange` 使用 **相同结构**，分别表示变更前、变更后的快照。

### 7.1 企业名称 NAME

```json
{
  "name": "北京示例科技有限公司"
}
```

| 字段 | 类型   | 说明     |
| ---- | ------ | -------- |
| name | string | 企业名称 |

### 7.2 法定代表人 LEGAL

```json
{
  "name": "张三"
}
```

| 字段 | 类型   | 说明           |
| ---- | ------ | -------------- |
| name | string | 法定代表人姓名 |

### 7.3 注册资本 CAPITAL

```json
{
  "amount": 5000000,
  "currency": "CNY",
  "shareholders": [
    {
      "name": "张三",
      "amount": 2500000,
      "ratio": 0.50
    },
    {
      "name": "李四",
      "amount": 2500000,
      "ratio": 0.50
    }
  ]
}
```

| 字段                  | 类型   | 必填           | 说明                                       |
| --------------------- | ------ | -------------- | ------------------------------------------ |
| amount                | number | 是             | 注册资本金额，单位：**元**                 |
| currency              | string | 否             | 币种代码，默认 `CNY`                       |
| shareholders          | array  | 否             | 股东出资明细列表                           |
| shareholders[].name   | string | 是(若有该对象) | 股东姓名 / 企业名称                        |
| shareholders[].amount | number | 是(若有该对象) | 出资额，单位：**元**                       |
| shareholders[].ratio  | number | 是(若有该对象) | 出资比例，**0~1 小数**（如 0.50 表示 50%） |

**约定说明**：

- 所有股东 `ratio` 之和建议等于 `1`（100%）
- 前端编辑表单按 **0~1 小数** 存储 `ratio`；展示时乘以 100 显示为百分数
- 过滤掉 name、amount、ratio 均为空的股东行

**币种代码（前端约定）**：

| 代码 | 含义   |
| ---- | ------ |
| CNY  | 人民币 |
| USD  | 美元   |
| EUR  | 欧元   |
| HKD  | 港币   |
| JPY  | 日元   |

### 7.4 经营范围 SCOPE

```json
{
  "scope": "计算机软件开发；技术咨询；信息系统集成服务。"
}
```

| 字段  | 类型   | 说明                                 |
| ----- | ------ | ------------------------------------ |
| scope | string | 经营范围全文，多条可用顿号或分号分隔 |

### 7.5 经营地址 ADDR

```json
{
  "address": "上海市浦东新区XX路XX号XX室"
}
```

| 字段    | 类型   | 说明         |
| ------- | ------ | ------------ |
| address | string | 完整经营地址 |

### 7.6 经营期限 PERIOD

```json
{
  "type": "fixed",
  "date": "2030-12-31"
}
```

或长期：

```json
{
  "type": "forever"
}
```

| 字段 | 类型   | 说明                                               |
| ---- | ------ | -------------------------------------------------- |
| type | string | `fixed` = 固定期限；`forever` = 长期               |
| date | string | 到期日，格式 `YYYY-MM-DD`；`type=forever` 时可省略 |

> 详情展示层还兼容别名：`periodType`、`endDate`、字符串直传日期等，**对接写入建议统一使用 `type` + `date`**。

### 7.7 股权 EQUITY

```json
{
  "shareholders": [
    {
      "name": "王五",
      "amount": 2550000,
      "ratio": 0.51,
      "certType": "ID_CARD",
      "certNumber": "310101199001011234",
      "certFrontUrl": "https://example.com/files/xxx_front.jpg",
      "certBackUrl": "https://example.com/files/xxx_back.jpg"
    },
    {
      "name": "某投资有限公司",
      "amount": 1500000,
      "ratio": 0.30,
      "certType": "BUSINESS_LICENSE",
      "certNumber": "91310000MA002B002X",
      "certFrontUrl": "https://example.com/files/yyy_license.jpg"
    }
  ]
}
```

| 字段                        | 类型   | 说明                                       |
| --------------------------- | ------ | ------------------------------------------ |
| shareholders                | array  | 股东列表                                   |
| shareholders[].name         | string | 股东姓名 / 企业名称                        |
| shareholders[].amount       | number | 出资额，单位：**元**                       |
| shareholders[].ratio        | number | 持股比例，**0~1 小数**（如 0.51 表示 51%） |
| shareholders[].certType     | string | 证件类型（可选），取值见下方证件类型表     |
| shareholders[].certNumber   | string | 证件号码（可选）                           |
| shareholders[].certFrontUrl | string | 证件正面图片 URL（可选）                   |
| shareholders[].certBackUrl  | string | 证件反面图片 URL（可选，身份证需正反面）   |

**约定说明**：

- 前端编辑表单按 **0~1 小数** 存储 `ratio`；展示时乘以 100 显示为百分数
- 所有股东 `ratio` 之和建议等于 `1`（100%）
- 过滤掉 name、amount、ratio 均为空的股东行
- 证件字段均为可选，仅在已上传 / 填写时出现
- 股权变更时，`beforeChange` 存储原股东及其证件信息，`afterChange` 存储新股东及其证件信息

**证件类型 certType 取值**：

| 值               | 含义     | 适用对象       |
| ---------------- | -------- | -------------- |
| ID_CARD          | 身份证   | 自然人股东     |
| BUSINESS_LICENSE | 营业执照 | 企业法人股东   |
| PASSPORT         | 护照     | 外籍自然人股东 |

### 7.8 未识别事项类型（兜底）

若 `itemName` 不在上述 7 种标准类型内，可传任意合法 JSON 对象，例如：

```json
{
  "key": "value"
}
```

---

## 8. 完整对接示例

### 8.1 新增工单

**请求**

```http
POST /jeecg-boot/bizorder/openapi/workOrder/add
X-Open-Token: <your-token>
Content-Type: application/json
```

```json
{
  "workOrder": {
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "objectType": "ENTERPRISE",
    "matterType": "CHANGE",
    "orderType": "BIZ_CHANGE"
  },
  "itemList": [
    {
      "itemName": "CAPITAL",
      "beforeChange": {
        "amount": 1000000,
        "currency": "CNY",
        "shareholders": [
          { "name": "张三", "amount": 600000, "ratio": 0.60 },
          { "name": "李四", "amount": 400000, "ratio": 0.40 }
        ]
      },
      "afterChange": {
        "amount": 5000000,
        "currency": "CNY",
        "shareholders": [
          { "name": "张三", "amount": 3000000, "ratio": 0.60 },
          { "name": "李四", "amount": 2000000, "ratio": 0.40 }
        ]
      }
    },
    {
      "itemName": "SCOPE",
      "beforeChange": {
        "scope": "计算机软件开发；技术咨询。"
      },
      "afterChange": {
        "scope": "计算机软件开发；技术咨询；信息系统集成服务；数据处理服务。"
      }
    },
    {
      "itemName": "EQUITY",
      "beforeChange": {
        "shareholders": [
          { "name": "王五", "amount": 3000000, "ratio": 0.60, "certType": "ID_CARD", "certNumber": "310101199001011234" },
          { "name": "赵六", "amount": 2000000, "ratio": 0.40, "certType": "ID_CARD", "certNumber": "310101198501012345" }
        ]
      },
      "afterChange": {
        "shareholders": [
          { "name": "王五", "amount": 2550000, "ratio": 0.51, "certType": "ID_CARD", "certNumber": "310101199001011234" },
          { "name": "赵六", "amount": 1500000, "ratio": 0.30, "certType": "ID_CARD", "certNumber": "310101198501012345" },
          { "name": "孙七", "amount": 950000, "ratio": 0.19, "certType": "ID_CARD", "certNumber": "440300198001011234" }
        ]
      }
    }
  ]
}
```

**响应**

```json
{
  "success": true,
  "code": 200,
  "message": "",
  "result": "添加成功！id=2050000000000005002"
}
```

### 8.2 查询详情

**请求**

```http
GET /jeecg-boot/bizorder/openapi/workOrder/queryById?id=2050000000000005002
X-Open-Token: <your-token>
```

**响应 result 结构示例**

```json
{
  "workOrder": {
    "id": "2050000000000005002",
    "orderNo": "GS20260520000002",
    "objectType": "ENTERPRISE",
    "objectType_dictText": "企业",
    "matterType": "CHANGE",
    "matterType_dictText": "变更",
    "orderType": "BIZ_CHANGE",
    "orderType_dictText": "工商变更",
    "orderStatus": "DRAFT",
    "orderStatus_dictText": "暂存",
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "createTime": "2026-05-20 10:00:00"
  },
  "itemList": [
    {
      "id": "...",
      "orderId": "2050000000000005002",
      "itemName": "CAPITAL",
      "beforeChange": { "amount": 1000000, "currency": "CNY", "shareholders": [{ "name": "张三", "amount": 600000, "ratio": 0.60 }] },
      "afterChange": { "amount": 5000000, "currency": "CNY", "shareholders": [{ "name": "张三", "amount": 3000000, "ratio": 0.60 }] }
    }
  ]
}
```

### 8.3 状态流转

**请求**

```http
POST /jeecg-boot/bizorder/openapi/workOrder/transit?id=2050000000000005002&targetStatus=SAVED
X-Open-Token: <your-token>
```

---

## 9. 编辑行为说明

调用 `/edit` 时：

1. `workOrder.id` **必填**
2. 事项明细采用 **先逻辑删除再全量重插** 策略
3. 子表记录的 `id` 可不传，服务端会重新生成
4. 未传的 `itemList` 视为空列表（会清空原有事项数据）

---

## 10. 校验与注意事项

| 项目             | 规则                                                     |
| ---------------- | -------------------------------------------------------- |
| 统一社会信用代码 | 18 位，字符集 `[0-9A-HJ-NPQRTUWXY]`                      |
| 企业名称         | 不能为空                                                 |
| JSON 字段        | 必须为合法 JSON 对象；空值用 `null`                      |
| 金额单位         | `amount`、股东 `amount` 均为 **元**（非万元）            |
| 持股比例         | 推荐 **0~1 小数**；详情展示兼容大于 1 的历史数据         |
| 字典值           | 必须使用 `item_value` 英文代码，不要使用中文 `item_text` |
| 时区             | 日期时间字段为 `GMT+8`                                   |
| 开放接口         | 无删除接口；如需删除请联系本系统管理员走内部接口         |

---

## 11. 附录：数据库表与字典 SQL 来源

| 类型                | 位置                                                         |
| ------------------- | ------------------------------------------------------------ |
| 建表 + 字典初始化   | `jeecg-boot/db/biz_order_init.sql`                           |
| 后端实体            | `jeecg-boot-module-bizorder` 模块                            |
| 开放接口 Controller | `WorkOrderOpenApiController.java`                            |
| 状态机枚举          | `OrderStatusEnum.java`                                       |
| 前端 JSON 表单组件  | `jeecgboot-vue3/src/views/bizorder/workorder/BizItemChangeFields.vue` |
| 前端聚合提交逻辑    | `WorkOrderEditDrawer.vue`                                    |

### 11.1 字典在线查询（可选）

若对接方需动态拉取最新字典，可使用系统字典接口（需另行开通权限或使用内部账号）：

```
GET /jeecg-boot/sys/dict/getDictItems/biz_order_status
GET /jeecg-boot/sys/dict/getDictItems/biz_item_name
...（将 dict_code 替换为对应字典编码）
```

开放接口路径 **不包含** 字典查询；建议对接方按本文档缓存字典，或通过线下同步。

---

## 12. 变更记录

| 版本 | 日期       | 说明                                                         |
| ---- | ---------- | ------------------------------------------------------------ |
| v1.0 | 2026-05-24 | 首版：整合字典、状态机、事项 JSON 规范及开放接口说明         |
| v1.1 | 2026-05-25 | EQUITY 事项增加股东证件字段（certType / certNumber / certFrontUrl / certBackUrl） |
| v2.0 | 2026-05-26 | 去除经办人相关内容（由后台管理端创建关联）；新增 CONFIRM_BY_C / CONFIRM_BY_A 状态；新增 customerConfirmed 字段；开放接口新增默认状态改为 CONFIRM_BY_C |
| v2.1 | 2026-05-26 | CAPITAL（注册资本）事项新增 `shareholders` 股东出资明细字段；移除 `contributionType` 字段 |