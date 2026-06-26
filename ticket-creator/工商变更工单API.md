# 工商变更工单模块 — 外部系统对接参考文档

> **文档版本**：v3.1  
> **更新日期**：2026-06-25  
> **适用模块**：工单管理（前端路由 `/bizorder/workOrder`）  
> **数据来源**：数据库字典（`sys_dict` / `sys_dict_item`）、后端实体与开放接口、前端事项 JSON 表单组件

---

## 目录

- [1. 概述](#1-概述)
- [2. 鉴权方式](#2-鉴权方式)
  - [2.1 错误响应](#21-错误响应)
- [3. 接口基础信息](#3-接口基础信息)
- [4. 开放接口清单（工单）](#4-开放接口清单)
  - [4.1 列表查询参数](#41-列表查询参数)
  - [4.2 统一成功响应格式](#42-统一成功响应格式)
- [5. 数据模型](#5-数据模型)
  - [5.1 聚合对象 WorkOrderPage](#51-聚合对象-workorderpage)
  - [5.2 工单主表](#52-工单主表-workorderbiz_work_order)
  - [5.4 工单编号规则](#54-工单编号规则)
  - [5.5 事项明细](#55-事项明细-itemlistbiz_order_item)
  - [5.6 相关附件](#56-相关附件-relatedattachments)
- [6. 字典与枚举](#6-字典与枚举)
  - [6.1 工单状态](#61-工单状态-biz_order_status)
  - [6.2 状态流转规则](#62-工单状态流转规则)
  - [6.3 对象类型](#63-对象类型-biz_object_type)
  - [6.4 事项类型](#64-事项类型-biz_matter_type)
  - [6.5 工单类型](#65-工单类型-biz_order_type)
  - [6.6 事项名称](#66-事项名称-biz_item_name)
- [7. 事项明细 JSON 字段规范](#7-事项明细-json-字段规范重点)
  - [7.1 企业名称 NAME](#71-企业名称-name)
  - [7.2 法定代表人 LEGAL](#72-法定代表人-legal)
  - [7.3 高级管理人员备案 SENIOR_MANAGER](#73-高级管理人员备案-senior_manager)
  - [7.4 登记联络员备案 LIAISON](#74-登记联络员备案-liaison)
  - [7.5 章程备案时间 BYLAW_ARTICLE](#75-章程备案时间-bylaw_article)
  - [7.6 监事备案 SUPERVISOR](#76-监事备案-supervisor)
  - [7.7 注册资本 CAPITAL](#77-注册资本-capital)
  - [7.8 经营范围 SCOPE](#78-经营范围-scope)
  - [7.9 经营地址 ADDR](#79-经营地址-addr)
  - [7.10 经营期限 PERIOD](#710-经营期限-period)
  - [7.11 股权 EQUITY](#711-股权-equity)
  - [7.12 未识别事项类型（兜底）](#712-未识别事项类型兜底)
- [8. 完整对接示例](#8-完整对接示例)
  - [8.1 新增工单](#81-新增工单)
  - [8.2 查询详情](#82-查询详情)
  - [8.3 状态流转](#83-状态流转)
- [9. 编辑行为说明](#9-编辑行为说明)
- [10. 校验与注意事项](#10-校验与注意事项)
- [11. 附录](#11-附录数据库表与字典-sql-来源)
- [12. 变更记录](#12-变更记录)
- [13. 客户信息 OpenAPI](#13-客户信息-openapi)
  - [13.1 接口清单](#131-接口清单)
  - [13.2 客户信息字段](#132-客户信息字段-bizcustomerinfo)
  - [13.3 典型对接流程](#133-典型对接流程推荐)
  - [13.4 findOrCreate](#134-findorcreate--查找或创建客户核心接口)
  - [13.5 edit](#135-edit--按-id-更新客户信息)
- [14. 发票记录 OpenAPI](#14-发票记录-openapi)
  - [14.1 接口清单](#141-接口清单)
  - [14.2 发票信息字段](#142-发票信息字段-bizinvoiceinfo)
  - [14.3 发票明细字段](#143-发票明细字段-bizinvoicedetail)
- [15. 经营范围 OpenAPI](#15-经营范围-openapi)
  - [15.1 接口清单](#151-接口清单)
  - [15.2 返回字段](#152-返回字段-bizbusinessscope)

---

## 1. 概述

本系统提供 **工商变更工单** 管理能力，包含：

- **工单主表**（`biz_work_order`）：企业基本信息、类型、状态、客户确认标记等
- **事项明细表**（`biz_order_item`）：变更登记事项及变更前/后 JSON 数据

> 经办人（`biz_agent` 表）由后台管理端创建和管理；工单通过 `agentId` 字段关联经办人，开放接口可传入 `agentId` 完成关联。

外部系统通过 **开放接口**（静态 Token 鉴权）进行读写，接口路径前缀为 `/bizorder/openapi/workOrder/**`，与内部管理端接口（需登录 + 权限）相互独立。

---

## 2. 鉴权方式

| 项目 | 说明 |
|------|------|
| 鉴权类型 | 静态 Token（请求头校验） |
| 请求头名称 | `X-Open-Token` |
| 配置项 | 服务端 `bizorder.openapi.enabled`、`bizorder.openapi.token` |
| 生效范围 | 仅 `/bizorder/openapi/*` |
| Token 获取 | 由本系统运维/对接方线下分配，**请勿写入客户端代码仓库** |

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

| code | 含义 |
|------|------|
| 401 | Token 缺失或不匹配 |
| 500 | 服务端未配置 token |
| 503 | 开放接口未启用 |

---

## 3. 接口基础信息

| 项目 | 值 |
|------|-----|
| 默认 Context Path | `/jeecg-boot` |
| 开放接口 Base URL | `{host}/jeecg-boot/bizorder/openapi/workOrder` |
| Content-Type | `application/json`（POST/PUT 请求体） |
| 字符编码 | UTF-8 |

> 生产环境 host、context-path 以实际部署为准。

---

## 4. 开放接口清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 分页列表（含事项明细） |
| GET | `/queryById?id={id}` | 聚合详情（主单 + 事项） |
| POST | `/add` | 新增工单（聚合写入） |
| PUT | `/edit` | 编辑工单（主单更新 + 子表全量替换） |
| POST | `/transit?id={id}&targetStatus={status}` | 状态流转（受状态机约束） |

> **注意**：股权变更确认接口 `/bizorder/workOrder/confirmEquityChange` 为**后台管理端内部接口**（需登录权限），不在开放接口范围内。外部系统如需写入股权转让明细和变更后企业类型，请通过 `/edit` 接口更新 EQUITY 事项的 `afterChange` 字段。

### 4.1 列表查询参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| pageNo | int | 否 | 页码，默认 1 |
| pageSize | int | 否 | 每页条数，默认 10 |
| orderNo | string | 否 | 工单编号（精确/模糊，按 QueryGenerator 规则） |
| enterpriseName | string | 否 | 企业名称 |
| orderStatus | string | 否 | 工单状态字典值，如 `PENDING` |
| objectType | string | 否 | 对象类型字典值，如 `ENTERPRISE` |

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
  "itemList": [ ],
  "agent": { },
  "workOrderLogs": [ ]
}
```

> `agent` 为经办人信息，`workOrderLogs` 为操作日志列表，均为查询响应中的可选字段。新增/编辑时只需传 `workOrder` + `itemList`。

### 5.2 工单主表 workOrder（biz_work_order）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 编辑必填 | 主键，新增可不传（系统自动生成） |
| orderNo | string | 否 | 工单编号；留空自动生成，规则见 5.4 |
| objectType | string | 否 | 对象类型，字典 `biz_object_type`，默认 `ENTERPRISE` |
| matterType | string | 否 | 事项类型，字典 `biz_matter_type`，默认 `CHANGE` |
| orderType | string | 否 | 工单类型，字典 `biz_order_type`，默认 `BIZ_CHANGE` |
| orderStatus | string | 否 | 工单状态，字典 `biz_order_status`，新增默认 `CONFIRM_BY_C`（待客户确认） |
| enterpriseName | string | **是** | 企业名称 / 对象名称 |
| creditCode | string | 否 | 18 位统一社会信用代码 |
| agentId | string | 否 | 经办人 ID，关联 `biz_agent` 表 |
| currentSessionId | string | 否 | 当前办理会话 ID（RPA 标记） |
| wechatMappingKey | string | 否 | 微信路由唯一凭证 Key，格式 `{robot_wxid}:{chat_type}:{target_wxid}`；仅微信群聊渠道发起的工单有此值，后台手动创建的工单为 `null` |
| customerId | string | 否 | 关联客户 ID，关联 `biz_customer_info` 表（v3.0 新增）。传入后服务端可自动加载客户绑定的经办人 |
| agent | object | — | 经办人信息（仅查询响应，查询时按 `agentId` 自动填充） |
| rpaAgentId | string | 否 | 执行该工单的 RPA ID（Phase2 RPA 任务调度） |
| rpaTaskStatus | string | 否 | RPA 执行状态，取值：`running` / `qrcode_waiting` / `done` / `failed` |
| rpaErrorMsg | string | 否 | RPA 执行错误信息 |
| relatedAttachments | string | 否 | 相关附件 JSON，结构见 5.6 节（股东会决议 / 章程修正案 / 减资公告 / 股东名册） |
| createTime | datetime | — | 创建时间，格式 `yyyy-MM-dd HH:mm:ss` |
| updateTime | datetime | — | 更新时间 |

**字典翻译字段**（仅查询响应可能出现）：`objectType_dictText`、`matterType_dictText`、`orderType_dictText`、`orderStatus_dictText`


### 5.4 工单编号规则

- 格式：`GS` + `yyyyMMdd` + 6 位序号
- 示例：`GS20260520000001`
- 新增时 `orderNo` 为空则服务端自动生成

### 5.5 事项明细 itemList（biz_order_item）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | 否 | 主键；编辑时子表会先删后插 |
| orderId | string | — | 工单 ID，服务端自动填充 |
| itemName | string | **是** | 事项名称，字典 `biz_item_name` 的 **item_value** |
| beforeChange | object / null | 否 | 变更前 JSON 对象 |
| afterChange | object / null | 否 | 变更后 JSON 对象 |
| rpaExecStatus | string | 否 | RPA 执行状态（仅查询响应），取值：`PENDING` / `RUNNING` / `DONE` / `FAILED` |
| rpaExecMessage | string | 否 | RPA 执行信息（失败原因等，仅查询响应） |

> **重要**：`beforeChange`、`afterChange` 在 API 中为 **JSON 对象**，不是字符串。空数据请传 `null`，不要传 `{}` 或全空占位对象。

### 5.6 相关附件 relatedAttachments

`relatedAttachments` 为 JSON 字符串（存储时序列化），结构如下：

```json
{
  "shareholderResolution": [
    { "name": "股东会决议.pdf", "url": "https://example.com/files/xxx.pdf" }
  ],
  "articlesAmendment": [
    { "name": "章程修正案.pdf", "url": "https://example.com/files/yyy.pdf" }
  ],
  "capitalReductionNotice": [
    { "name": "减资公告.pdf", "url": "https://example.com/files/zzz.pdf" }
  ],
  "shareholderRoster": [
    { "name": "股东名册.xlsx", "url": "https://example.com/files/www.xlsx" }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| shareholderResolution | array | 股东会决议文件列表（可选） |
| articlesAmendment | array | 章程修正案文件列表（可选） |
| capitalReductionNotice | array | 减资公告文件列表（可选） |
| shareholderRoster | array | 股东名册文件列表（可选） |

每个文件对象包含 `name`（文件名）和 `url`（文件下载地址）。

---

## 6. 字典与枚举

所有字典存储于数据库表 `sys_dict`（字典定义）和 `sys_dict_item`（字典项）。  
对接时 **传值使用 `item_value`（英文代码）**，展示时使用 `item_text`（中文名称）。

### 6.1 工单状态 biz_order_status

后端枚举类：`OrderStatusEnum`（与字典值一致）

| item_text（中文） | item_value（代码） | 说明 |
|-------------------|-------------------|------|
| 待客户确认 | CONFIRM_BY_C | 开放接口新增默认状态，等待客户在 H5 确认 |
| 待经办人确认 | CONFIRM_BY_A | 客户确认后进入，等待后台经办人确认 |
| 待提交 | PENDING | 经办人确认后进入，等待填报或下发 RPA |
| 暂存 | DRAFT | 草稿 |
| 取消/终止办理 | CANCEL | 终止该工单，不可再流转 |
| 已下发RPA | DISPATCHED | 工单已派发给 RPA，等待机器处理（v3.1） |
| RPA执行中 | RUNNING | RPA 正在办理中（v3.1） |
| RPA执行完成待确认 | WAIT_CONFIRM | RPA 执行完成，待经办人确认结果（v3.1） |
| 办理中 | PROCESSING | 人工正在办理 |
| 已办结 | DONE | 终态 |

### 6.2 工单状态流转规则

仅允许以下流转（调用 `/transit` 接口）：

```
CONFIRM_BY_C → CONFIRM_BY_A          （客户 H5 确认）
CONFIRM_BY_A → PENDING               （后台经办人确认）
PENDING      → DISPATCHED, DRAFT, CANCEL
DRAFT        → PROCESSING, CANCEL, DRAFT
DISPATCHED   → RUNNING, PENDING      （RPA 拾取执行 / 退回）
RUNNING      → WAIT_CONFIRM, DONE, PENDING  （RPA 完成 / 退回）
WAIT_CONFIRM → DONE                  （经办人确认 RPA 结果）
CANCEL       → （不可再流转）
PROCESSING   → DONE
DONE         → （不可再流转）
```

> `CONFIRM_BY_C → CONFIRM_BY_A` 由 H5 的「确认资料无误」按钮触发（接口 `/bizorder/workOrder/confirmByCustomer`，免鉴权），非 `/transit` 接口。
> `CONFIRM_BY_A → PENDING` 由后台管理端「经办人确认」按钮触发（接口 `/bizorder/workOrder/confirmByAgent`，需权限 `bizorder:workOrder:edit`）。**确认前会校验工单是否已关联经办人，若未关联则需先选择经办人。**
> `PENDING → DISPATCHED` / `DISPATCHED → RUNNING` 等 RPA 相关流转由 RPA 系统调度触发，接入方通常无需手动调用。
> 若工单包含 **股权变更（EQUITY）** 事项，经办人确认时会弹出股权变更确认弹窗，需填写**股权转让明细**和**变更后企业类型**，提交后调用内部接口 `/bizorder/workOrder/confirmEquityChange`（需后台管理端权限，非开放接口）。

非法流转将返回业务异常，如：`工单状态不允许从 PENDING 流转到 DONE`。

### 6.3 对象类型 biz_object_type

| item_text | item_value |
|-----------|------------|
| 企业 | ENTERPRISE |
| 个体工商户 | INDIVIDUAL |
| 农民专业合作社 | COOP |
| 外国（地区）企业常驻代表机构 | FOREIGN_OFFICE |
| 外国（地区）企业在中国境内经营 | FOREIGN_BIZ |

### 6.4 事项类型 biz_matter_type

| item_text | item_value |
|-----------|------------|
| 设立 | SETUP |
| 变更 | CHANGE |
| 迁移 | MIGRATE |
| 注销 | CANCEL |
| 个转企 | IND2ENT |
| 跨省迁移 | CROSS_PROVINCE |
| 名称自主申报 | NAME_DECLARE |

### 6.5 工单类型 biz_order_type

| item_text | item_value |
|-----------|------------|
| 工商变更 | BIZ_CHANGE |
| 工商设立 | BIZ_SETUP |
| 工商注销 | BIZ_CANCEL |

### 6.6 事项名称 biz_item_name

事项名称决定 `beforeChange` / `afterChange` 的 JSON 结构（见第 7 节）。

| item_text | item_value | JSON 结构类型 |
|-----------|------------|---------------|
| 企业名称 | NAME | 单字段 `name` |
| 注册资本 | CAPITAL | 金额 + 币种 |
| 股权 | EQUITY | 股东列表 |
| 经营范围 | SCOPE | 多行文本 `scope` |
| 经营期限 | PERIOD | 期限类型 + 到期日 |
| 经营地址 | ADDR | 多行文本 `address` |
| 法定代表人 | LEGAL | 单字段 `name`（变更后额外含手机号、身份证） |
| 高级管理人员备案 | SENIOR_MANAGER | 姓名 + 职务（变更后额外含手机号、身份证） |
| 登记联络员备案 | LIAISON | 仅变更后，姓名/手机号/邮箱/住址/身份证 |
| 章程备案时间 | BYLAW_ARTICLE | 仅变更后，单个日期 |
| 监事备案 | SUPERVISOR | 仅变更后，开关 + 监事信息 |

---

## 7. 事项明细 JSON 字段规范（重点）

`itemName` 取值来自字典 `biz_item_name` 的 **item_value**。  
`beforeChange` 与 `afterChange` 使用 **相同结构**，分别表示变更前、变更后的快照。

### 7.1 企业名称 NAME

> beforeChange 与 afterChange 结构相同，分别表示变更前后的企业名称。

```json
{
  "name": "北京示例科技有限公司"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 企业名称 |

### 7.2 法定代表人 LEGAL

**变更前（beforeChange）** — 仅姓名：

```json
{
  "name": "张三"
}
```

**变更后（afterChange）** — 姓名 + 手机号 + 身份证正反面：

```json
{
  "name": "李四",
  "phone": "13800138000",
  "idCardFrontUrl": "https://example.com/files/legal_idcard_front.jpg",
  "idCardBackUrl": "https://example.com/files/legal_idcard_back.jpg"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | **是** | 法定代表人姓名 |
| phone | string | 否（仅 afterChange） | 新法定代表人手机号 |
| idCardFrontUrl | string | 否（仅 afterChange） | 新法定代表人身份证正面图片 URL |
| idCardBackUrl | string | 否（仅 afterChange） | 新法定代表人身份证反面图片 URL |

> **约定**：`beforeChange` 仅保留变更前的姓名。`phone`、`idCardFrontUrl`、`idCardBackUrl` 仅用于 `afterChange`。监事备案、登记联络员备案已拆分为独立事项类型（SUPERVISOR、LIAISON），不再内嵌在 LEGAL 中。如需设置监事，请在 `itemList` 中单独添加 `itemName: "SUPERVISOR"` 的事项。

### 7.3 高级管理人员备案 SENIOR_MANAGER

**变更前（beforeChange）** — 姓名 + 职务：

```json
{ "name": "张三", "position": "财务负责人" }
```

**变更后（afterChange）** — 姓名 + 职务 + 手机号 + 身份证：

```json
{ "name": "李四", "position": "经理", "phone": "13800138000", "idCardFrontUrl": "...", "idCardBackUrl": "..." }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | **是** | 人员姓名 |
| position | string | **是** | 职务类型：`财务负责人` / `经理` |
| phone | string | 否（仅 afterChange） | 手机号 |
| idCardFrontUrl | string | 否（仅 afterChange） | 身份证正面 URL |
| idCardBackUrl | string | 否（仅 afterChange） | 身份证反面 URL |

> RPA 下发时归入 `legal_rep.senior_managers`，字段 `position_type`。

### 7.4 登记联络员备案 LIAISON

> 仅变更后，新增时自动填法人信息。

```json
{ "name": "联络员", "phone": "138...", "email": "...", "address": "...", "idCardFrontUrl": "...", "idCardBackUrl": "..." }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name/phone/email/address/idCardFrontUrl/idCardBackUrl | — | — | 同上 |

> RPA 下发时归入 `legal_rep.liaison` 对象。

### 7.5 章程备案时间 BYLAW_ARTICLE

> 仅变更后，单个日期。

```json
{ "amendmentDate": "2026-06-18" }
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| amendmentDate | string | **是** | 章程备案日期 `YYYY-MM-DD` |

> RPA 下发时转为独立 `change_type: "articles_amendment"`，字段 `amendment_date`。

### 7.6 监事备案 SUPERVISOR

> 仅变更后。

不设监事：`{ "hasSupervisor": false }`

设置监事：`{ "hasSupervisor": true, "name": "...", "phone": "...", "idCardFrontUrl": "...", "idCardBackUrl": "..." }`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hasSupervisor | boolean | **是** | 是否设置监事 |
| name/phone/idCardFrontUrl/idCardBackUrl | — | hasSupervisor=true 时必填 | 监事信息 |

> RPA 下发时为独立 `change_type: "supervisor"`，字段 `has_supervisor`。

### 7.7 注册资本 CAPITAL

> beforeChange 与 afterChange 结构基本一致，但 `afterChange` 的 shareholders 额外包含认缴日期字段。

**变更后（afterChange）完整示例：**

```json
{
  "amount": 5000000,
  "currency": "CNY",
  "shareholders": [
    {
      "name": "张三",
      "amount": 2500000,
      "ratio": 0.50,
      "subscriptionStartDate": "2024-01-15",
      "subscriptionContributionDate": "2034-01-14"
    },
    {
      "name": "李四",
      "amount": 2500000,
      "ratio": 0.50,
      "subscriptionStartDate": "2024-01-15",
      "subscriptionContributionDate": "2034-01-14"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| amount | number | 是 | 注册资本金额，单位：**元** |
| currency | string | 否 | 币种代码，默认 `CNY` |
| shareholders | array | 否 | 股东出资明细列表 |
| shareholders[].name | string | 是(若有该对象) | 股东姓名 / 企业名称 |
| shareholders[].amount | number | 是(若有该对象) | 出资额，单位：**元** |
| shareholders[].ratio | number | 是(若有该对象) | 出资比例，**0~1 小数**（如 0.50 表示 50%） |
| shareholders[].subscriptionStartDate | string | 否（仅 afterChange） | 认缴开始时间，格式 `YYYY-MM-DD`，v2.8 新增 |
| shareholders[].subscriptionContributionDate | string | 否（仅 afterChange） | 认缴出资时间，格式 `YYYY-MM-DD`，v2.8 新增 |

**约定说明**：

- `shareholders` 数组在 `beforeChange` 和 `afterChange` 中的语义不同：
  - **beforeChange**：用户手动填写，变更前各位股东的出资额和出资比例
  - **afterChange**：金额由前端自动根据 `beforeChange.shareholders` 的姓名和比例计算（`afterChange.shareholders[i].amount = afterChange.amount × beforeChange.shareholders[i].ratio`）。**对接方若直接调用 API 写入，需自行计算**
  - `subscriptionStartDate`、`subscriptionContributionDate` 仅用于 `afterChange`，为可选字段
- 所有股东 `ratio` 之和建议等于 `1`（100%）
- 前端编辑表单按 **0~1 小数** 存储 `ratio`；展示时乘以 100 显示为百分数
- 过滤掉 name、amount、ratio 均为空的股东行

**币种代码（前端约定）**：

| 代码 | 含义 |
|------|------|
| CNY | 人民币 |
| USD | 美元 |
| EUR | 欧元 |
| HKD | 港币 |
| JPY | 日元 |

### 7.8 经营范围 SCOPE

> beforeChange 与 afterChange 结构相同，分别表示变更前后的经营范围。

```json
{
  "scope": "计算机软件开发；技术咨询；信息系统集成服务。"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| scope | string | 经营范围全文，多条可用顿号或分号分隔 |

### 7.9 经营地址 ADDR

> beforeChange 与 afterChange 结构相同，分别表示变更前后的经营地址。

```json
{
  "address": "上海市浦东新区XX路XX号XX室"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| address | string | 完整经营地址 |

### 7.10 经营期限 PERIOD

> beforeChange 与 afterChange 结构相同，分别表示变更前后的经营期限。

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

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | `fixed` = 固定期限；`forever` = 长期 |
| date | string | 到期日，格式 `YYYY-MM-DD`；`type=forever` 时可省略 |

> 详情展示层还兼容别名：`periodType`、`endDate`、字符串直传日期等，**对接写入建议统一使用 `type` + `date`**。

### 7.11 股权 EQUITY

**变更前（beforeChange）** — 仅股东基本信息：

```json
{
  "shareholders": [
    {
      "name": "王五",
      "amount": 3000000,
      "ratio": 0.60,
      "phone": "13800138000",
      "certType": "ID_CARD",
      "certNumber": "310101199001011234",
      "certFrontUrl": "https://example.com/files/xxx_front.jpg",
      "certBackUrl": "https://example.com/files/xxx_back.jpg"
    },
    {
      "name": "赵六",
      "amount": 2000000,
      "ratio": 0.40,
      "phone": "13900139000",
      "certType": "ID_CARD",
      "certNumber": "310101198501012345",
      "certFrontUrl": "https://example.com/files/yyy_front.jpg",
      "certBackUrl": "https://example.com/files/yyy_back.jpg"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| shareholders | array | 变更前股东列表 |
| shareholders[].name | string | 股东姓名 / 企业名称 |
| shareholders[].amount | number | 出资额，单位：**元** |
| shareholders[].ratio | number | 持股比例，**0~1 小数**（如 0.60 表示 60%） |
| shareholders[].phone | string | 股东手机号（可选） |
| shareholders[].certType | string | 证件类型（可选），取值：ID_CARD / BUSINESS_LICENSE / PASSPORT |
| shareholders[].certNumber | string | 证件号码（可选） |
| shareholders[].certFrontUrl | string | 证件正面图片 URL（可选） |
| shareholders[].certBackUrl | string | 证件反面图片 URL（可选） |

> **约定**：`beforeChange` 仅包含变更前股东列表及其证件信息。`equityTransfers`、`enterpriseType`、`needSupervisor`、`supervisor`、`subscriptionStartDate`、`subscriptionContributionDate` 等字段仅用于 `afterChange`。

**变更后（afterChange）** — 股东 + 转让明细 + 企业类型 + 监事：

```json
{
  "shareholders": [
    {
      "name": "王五",
      "amount": 2550000,
      "ratio": 0.51,
      "phone": "13800138000",
      "certType": "ID_CARD",
      "certNumber": "310101199001011234",
      "certFrontUrl": "https://example.com/files/xxx_front.jpg",
      "certBackUrl": "https://example.com/files/xxx_back.jpg",
      "subscriptionStartDate": "2026-01-01",
      "subscriptionContributionDate": "2030-12-31"
    },
    {
      "name": "某投资有限公司",
      "amount": 1500000,
      "ratio": 0.30,
      "phone": "021-12345678",
      "certType": "BUSINESS_LICENSE",
      "certNumber": "91310000MA002B002X",
      "certFrontUrl": "https://example.com/files/yyy_license.jpg",
      "subscriptionStartDate": "2026-01-01",
      "subscriptionContributionDate": "2028-06-30"
    }
  ],
  "equityTransfers": [
    {
      "transferor": "王五",
      "transferee": "孙七",
      "transferDate": "2026-06-12",
      "transferAmount": 45.00,
      "transferPrice": 50.00,
      "transferType": "PURCHASE"
    }
  ],
  "enterpriseType": "有限责任公司(自然人投资或控股)",
  "needSupervisor": true,
  "supervisor": {
    "name": "赵八",
    "phone": "13700137000",
    "idCardFrontUrl": "https://example.com/files/sup_eq_front.jpg",
    "idCardBackUrl": "https://example.com/files/sup_eq_back.jpg"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| shareholders | array | 股东列表 |
| shareholders[].name | string | 股东姓名 / 企业名称 |
| shareholders[].amount | number | 出资额，单位：**元** |
| shareholders[].ratio | number | 持股比例，**0~1 小数**（如 0.51 表示 51%） |
| shareholders[].phone | string | 股东手机号（可选，v2.4 新增） |
| shareholders[].subscriptionStartDate | string | 认缴开始时间（可选，仅 afterChange，v2.5 新增），格式 `YYYY-MM-DD` |
| shareholders[].subscriptionContributionDate | string | 认缴出资时间（可选，仅 afterChange，v2.5 新增），格式 `YYYY-MM-DD` |
| shareholders[].certType | string | 证件类型（可选），取值见下方证件类型表 |
| shareholders[].certNumber | string | 证件号码（可选） |
| shareholders[].certFrontUrl | string | 证件正面图片 URL（可选） |
| shareholders[].certBackUrl | string | 证件反面图片 URL（可选，身份证需正反面） |
| equityTransfers | array | 股权转让列表（仅 afterChange，v2.4 新增） |
| equityTransfers[].transferor | string | 转让方姓名 |
| equityTransfers[].transferee | string | 受让方姓名 |
| equityTransfers[].transferDate | string | 转让日期，格式 `yyyy-MM-dd` |
| equityTransfers[].transferAmount | number | 转让股权数额，单位：**万元** |
| equityTransfers[].transferPrice | number | 转让价格，单位：**万元** |
| equityTransfers[].transferType | string | 转让类型，取值见下方转让类型表 |
| enterpriseType | string | 变更后企业类型（仅 afterChange，v2.4 新增） |
| needSupervisor | boolean | 是否需要设置一名监事（仅 afterChange，v2.6 新增） |
| supervisor | object | 监事信息对象（仅 afterChange，needSupervisor=true 时必填，v2.6 新增） |
| supervisor.name | string | 监事姓名 |
| supervisor.phone | string | 监事手机号 |
| supervisor.idCardFrontUrl | string | 监事身份证正面图片 URL |
| supervisor.idCardBackUrl | string | 监事身份证反面图片 URL |

**约定说明**：

- 前端编辑表单按 **0~1 小数** 存储 `ratio`；展示时乘以 100 显示为百分数
- 所有股东 `ratio` 之和建议等于 `1`（100%）
- 过滤掉 name、amount、ratio 均为空的股东行
- 证件字段均为可选，仅在已上传 / 填写时出现
- 股权变更时，`beforeChange` 存储原股东及其证件信息，`afterChange` 存储新股东及其证件信息
- `equityTransfers` 和 `enterpriseType` 由经办人在确认环节填写，通过 `confirmEquityChange` 接口写入

**证件类型 certType 取值**：

| 值 | 含义 | 适用对象 |
|----|------|----------|
| ID_CARD | 身份证 | 自然人股东 |
| BUSINESS_LICENSE | 营业执照 | 企业法人股东 |
| PASSPORT | 护照 | 外籍自然人股东 |

**转让类型 transferType 取值**：

| 值 | 含义 |
|----|------|
| PURCHASE | 购买 |
| INHERITANCE | 继承 |
| GIFT | 赠予 |
| JUDICIAL | 司法判决 |
| OTHER | 其他 |

**企业类型 enterpriseType 常用取值**：

| 值 |
|----|
| 有限责任公司(自然人投资或控股) |
| 有限责任公司(自然人独资) |
| 有限责任公司(法人独资) |
| 有限责任公司(非自然人投资或控股的法人独资) |
| 有限责任公司(外商投资企业投资) |
| 有限责任公司(外国自然人独资) |
| 有限责任公司(台港澳自然人独资) |
| 有限责任公司(台港澳与境内合资) |
| 有限责任公司(中外合资) |
| 有限责任公司(国有独资) |
| 股份有限公司(上市) |
| 股份有限公司(非上市) |
| 一人有限责任公司 |
| 其他有限责任公司 |

### 7.12 未识别事项类型（兜底）

若 `itemName` 不在上述 8 种标准类型内，可传任意合法 JSON 对象，例如：

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
    "customerId": "2050000000000009001",
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
POST /jeecg-boot/bizorder/openapi/workOrder/transit?id=2050000000000005002&targetStatus=DRAFT
X-Open-Token: <your-token>
```

---

## 9. 编辑行为说明

调用 `/edit` 时：

1. `workOrder.id` **必填**
2. 事项明细采用 **先逻辑删除再全量重插** 策略
3. 子表记录的 `id` 可不传，服务端会重新生成
4. 未传的 `itemList` 视为空列表（会清空原有事项数据）
5. `agentId`、`currentSessionId` 等辅助字段可按需传入，不会被覆盖为 null

---

## 10. 校验与注意事项

| 项目 | 规则 |
|------|------|
| 统一社会信用代码 | 18 位，字符集 `[0-9A-HJ-NPQRTUWXY]` |
| 企业名称 | 不能为空 |
| JSON 字段 | 必须为合法 JSON 对象；空值用 `null` |
| 金额单位 | `amount`、股东 `amount` 均为 **元**（非万元） |
| 持股比例 | 推荐 **0~1 小数**；详情展示兼容大于 1 的历史数据 |
| 字典值 | 必须使用 `item_value` 英文代码，不要使用中文 `item_text` |
| 时区 | 日期时间字段为 `GMT+8` |
| 开放接口 | 无删除接口；如需删除请联系本系统管理员走内部接口 |
| currentSessionId | RPA 标记字段，由 RPA 系统写入，人工操作通常不传 |

---

## 11. 附录：数据库表与字典 SQL 来源

| 类型 | 位置 |
|------|------|
| 建表 + 字典初始化 | `jeecg-boot/db/biz_order_init.sql` |
| 后端实体 | `jeecg-boot-module-bizorder` 模块 |
| 开放接口 Controller | `WorkOrderOpenApiController.java` |
| 状态机枚举 | `OrderStatusEnum.java` |
| 前端 JSON 表单组件 | `jeecgboot-vue3/src/views/bizorder/workorder/BizItemChangeFields.vue` |
| 前端聚合提交逻辑 | `WorkOrderEditDrawer.vue` |

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

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-05-24 | 首版：整合字典、状态机、事项 JSON 规范及开放接口说明 |
| v1.1 | 2026-05-25 | EQUITY 事项增加股东证件字段（certType / certNumber / certFrontUrl / certBackUrl） |
| v2.0 | 2026-05-26 | 去除经办人相关内容（由后台管理端创建关联）；新增 CONFIRM_BY_C / CONFIRM_BY_A 状态；新增 customerConfirmed 字段；开放接口新增默认状态改为 CONFIRM_BY_C |
| v2.1 | 2026-05-26 | CAPITAL（注册资本）事项新增 `shareholders` 股东出资明细字段（beforeChange 手动填写，afterChange 按比例自动计算）；移除 `contributionType` 字段 |
| v2.2 | 2026-05-29 | PENDING 状态中文名由「待填报」改为「待提交」；删除 SAVED、CONFIRMED 状态，新增 CANCEL（取消/终止办理）；workOrder 新增 `agentId`（经办人ID）、`currentSessionId`（RPA 会话标记）字段；补充 confirmByCustomer 免鉴权说明；补充经办人确认前校验说明 |
| v2.3 | 2026-06-08 | 法定代表人 LEGAL 事项 `afterChange` 新增可选字段 `phone`、`idCardFrontUrl`、`idCardBackUrl`（新法人手机号及身份证正反面图片）；`beforeChange` 保持不变仅含 `name` |
| v2.4 | 2026-06-12 | EQUITY 事项新增 `shareholders[].phone` 字段；新增 `equityTransfers`（股权转让列表）、`enterpriseType`（变更后企业类型）字段（仅 afterChange）；新增 `/confirmEquityChange` 接口用于股权变更确认 |
| v2.5 | 2026-06-17 | 新增事项类型 POSITION（职务变更），包含 `name`、`position`、`phone` 字段（phone 仅 afterChange）；EQUITY `shareholders` 新增 `subscriptionStartDate`（认缴开始时间）、`subscriptionContributionDate`（认缴出资时间）字段（仅 afterChange） |
| v2.6 | 2026-06-17 | LEGAL 事项 `afterChange` 新增 `needSupervisor`（是否需要监事）、`supervisor`（监事姓名/手机号/身份证正反面）字段；EQUITY 事项 `afterChange` 新增 `needSupervisor`、`supervisor` 字段；POSITION 事项 `afterChange` 新增 `idCardFrontUrl`、`idCardBackUrl`（身份证正反面）字段 |
| v2.7 | 2026-06-17 | 文档完善：所有事项类型（NAME、LEGAL、POSITION、CAPITAL、SCOPE、ADDR、PERIOD、EQUITY）均补充了 `beforeChange` 结构说明或标注 "beforeChange 与 afterChange 结构相同"；EQUITY 新增变更前股东列表示例及独立字段表 |
| v2.8 | 2026-06-18 | CAPITAL 事项 `afterChange.shareholders` 新增可选字段 `subscriptionStartDate`（认缴开始时间）、`subscriptionContributionDate`（认缴出资时间）；除 LEGAL 外所有事项 `afterChange` 新增通用可选字段 `bylawFilingDate`（章程备案时间），格式 `YYYY-MM-DD`，下发 RPA 时转换为独立的 `articles_amendment` 变更项；股权变更确认时企业类型改为非必填；股权转让 `transfer_type` 取值改为中文（购买/继承/赠予/司法判决/其他） |
| v2.9 | 2026-06-18 | LEGAL 事项 `afterChange` 新增 `needLiaison`（是否需要登记联络员）、`liaison`（联络员姓名/手机号/邮箱/住址/身份证正反面）字段，开启后默认填充法人信息，下发 RPA 时包含在 `legal_rep` 的 `liaison` 字段中 |

| v3.0 | 2026-06-25 | 新增客户信息 OpenAPI（/bizorder/openapi/customer/**）、发票记录 OpenAPI（/bizorder/openapi/invoice/**）、经营范围 OpenAPI（/bizorder/openapi/businessScope/**）；工单新增 `customerId` 字段关联客户，`agentId` 支持自动从客户绑定加载 |
| v3.1 | 2026-06-25 | 文档完善：工单主表字段表补充 `customerId`、`rpaAgentId`、`rpaTaskStatus`、`rpaErrorMsg`、`relatedAttachments` 字段；事项明细补充 `rpaExecStatus`、`rpaExecMessage` 字段；工单状态字典补充 DISPATCHED / RUNNING / WAIT_CONFIRM 三个 RPA 状态；状态流转规则更新完整路径（含 RPA 阶段）；聚合对象 WorkOrderPage 补充 `agent`、`workOrderLogs` 字段；客户信息补充 6 个遗漏字段；移除开放接口清单中不存在于 OpenAPI Controller 的 `/confirmEquityChange` 端点（该接口为后台管理端内部接口）；新增 5.6 节 relatedAttachments JSON 结构说明；章节编号修正；客户 OpenAPI 新增 `/findOrCreate`（第三方对接核心接口，查不到自动创建）和 `/edit`（按ID更新）接口；新增 13.3 节第三方对接推荐流程 |

---

## 13. 客户信息 OpenAPI

**Base URL**: `{host}/jeecg-boot/bizorder/openapi/customer`

### 13.1 接口清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/search?keyword=&limit=20` | 模糊搜索（名称+信用代码） |
| GET | `/list?pageNo=&pageSize=&enterpriseName=` | 分页列表 |
| GET | `/queryById?id=` | 按ID查单条 |
| GET | `/getByCreditCode?creditCode=` | 按信用代码精确查 |
| POST | `/save` | 新增/更新（按creditCode去重） |
| POST | `/findOrCreate` | **推荐** 按名称+信用代码查找，不存在则自动创建（第三方对接核心接口） |
| PUT | `/edit` | 按ID更新客户信息 |

### 13.2 客户信息字段（BizCustomerInfo）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
| enterpriseName | string | 企业名称 |
| enterpriseType | string | 企业类型，字典 `biz_enterprise_type`（ENTERPRISE/INDIVIDUAL_BUSINESS） |
| creditCode | string | 统一社会信用代码 |
| taxpayerType | string | 纳税人类型，字典 `biz_taxpayer_type`（GENERAL_TAXPAYER/SMALL_TAXPAYER） |
| bizAgentId | string | 工单经办人ID |
| invoiceAgentId | string | 开票经办人ID |
| taxAgentId | string | 报税经办人ID |
| legalRepresentative | string | 法定代表人 |
| legalPhone | string | 法人电话 |
| financialOfficer | string | 财务负责人 |
| financialOfficerPhone | string | 财务负责人电话 |
| registeredAddress | string | 注册地址 |
| businessAddress | string | 经营地址 |
| businessScope | string | 经营范围 |
| openingDate | date | 开业日期（yyyy-MM-dd） |
| registeredCapital | string | 注册资本 |
| employeeCount | int | 从业人数 |
| taxpayerStatus | string | 纳税人状态 |
| taxAuthority | string | 主管税务机关 |
| enterprisePhone | string | 企业联系电话 |
| enterpriseEmail | string | 企业邮箱 |
| invoiceHandlerUserId | string | 开票经办人用户 ID（关联系统用户） |
| bizHandlerUserId | string | 工商经办人用户 ID（关联系统用户） |
| invoiceFetchStartTime | datetime | 发票抓取历史开始时间，格式 `yyyy-MM-dd HH:mm:ss` |
| invoiceFetchEndTime | datetime | 发票抓取历史结束时间，格式 `yyyy-MM-dd HH:mm:ss` |

### 13.3 典型对接流程（推荐）

第三方系统创建工单的推荐流程：

```
1. 调用 /findOrCreate 查找或创建客户 → 获得 customerId
2. 调用 /bizorder/openapi/workOrder/add 创建工单（传入 customerId）
   → 服务端自动加载客户绑定的经办人
3. 平台经办人在后台确认工单 → 分发 RPA 办理
```

---

### 13.4 findOrCreate — 查找或创建客户（核心接口）

**请求**

```http
POST /jeecg-boot/bizorder/openapi/customer/findOrCreate
X-Open-Token: <your-token>
Content-Type: application/json
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| enterpriseName | string | **是** | 企业名称 |
| creditCode | string | 否 | 统一社会信用代码（18 位） |

**查找逻辑**：
1. 若传了 `creditCode`，优先按信用代码精确匹配
2. 若未匹配，再按 `enterpriseName` 精确匹配
3. 均未命中则自动创建新客户（`enterpriseType` 默认 `ENTERPRISE`）

**请求示例**：

```json
{
  "enterpriseName": "上海星辰贸易有限公司",
  "creditCode": "91310000MA002B002X"
}
```

**响应** — 返回完整 `BizCustomerInfo` 对象（已有客户直接返回，新建客户创建后返回）：

```json
{
  "success": true,
  "code": 200,
  "message": "",
  "result": {
    "id": "2050000000000009001",
    "enterpriseName": "上海星辰贸易有限公司",
    "creditCode": "91310000MA002B002X",
    "enterpriseType": "ENTERPRISE",
    "taxpayerType": null,
    "bizAgentId": null,
    "invoiceAgentId": null,
    "taxAgentId": null,
    "legalRepresentative": null,
    "legalPhone": null,
    "financialOfficer": null,
    "financialOfficerPhone": null,
    "registeredAddress": null,
    "businessAddress": null,
    "businessScope": null,
    "openingDate": null,
    "registeredCapital": null,
    "employeeCount": null,
    "taxpayerStatus": null,
    "taxAuthority": null,
    "enterprisePhone": null,
    "enterpriseEmail": null,
    "invoiceHandlerUserId": null,
    "bizHandlerUserId": null,
    "invoiceFetchStartTime": null,
    "invoiceFetchEndTime": null,
    "createTime": "2026-06-25 15:30:00",
    "updateTime": "2026-06-25 15:30:00"
  }
}
```

拿到 `result.id` 后即可作为 `customerId` 传入工单新增接口。

---

### 13.5 edit — 按 ID 更新客户信息

**请求**

```http
PUT /jeecg-boot/bizorder/openapi/customer/edit
X-Open-Token: <your-token>
Content-Type: application/json
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | string | **是** | 客户主键 ID |
| enterpriseName | string | 否 | 企业名称 |
| creditCode | string | 否 | 统一社会信用代码 |
| taxpayerType | string | 否 | 纳税人类型，`GENERAL_TAXPAYER` / `SMALL_TAXPAYER` |
| ... | — | 否 | 其他字段见 13.2 节字段表，按需传入即可 |

**请求示例**（只更新需要变更的字段）：

```json
{
  "id": "2050000000000009001",
  "legalRepresentative": "张三",
  "legalPhone": "13800138000",
  "taxpayerType": "GENERAL_TAXPAYER",
  "taxAuthority": "上海市浦东新区税务局"
}
```

**响应**：

```json
{
  "success": true,
  "code": 200,
  "message": "编辑成功",
  "result": "编辑成功"
}
```

> **注意**：`/save` 接口也支持更新（按 `creditCode` 匹配后更新），适用于按信用代码 upsert 的场景。`/edit` 按 ID 更新，适用于已知客户 ID 的场景。两者功能互补。

---

## 14. 发票记录 OpenAPI

**Base URL**: `{host}/jeecg-boot/bizorder/openapi/invoice`

### 14.1 接口清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list?pageNo=&pageSize=&invoiceNo=&sellerName=&buyerName=` | 分页列表 |
| GET | `/queryById?id=` | 查单条（含明细行） |
| GET | `/getByCustomerCreditCode?creditCode=` | 按客户信用代码查历史开票 |
| GET | `/getByCustomerId?customerId=` | 按客户ID查历史开票 |

### 14.2 发票信息字段（BizInvoiceInfo）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 主键 |
| invoiceNo | string | 发票编号 |
| invoiceType | string | 发票种类（ELECTRONIC=数电发票） |
| invoiceStatus | string | 发票状态（正常/已红冲-全额） |
| buyerName | string | 购买方名称 |
| buyerTaxNo | string | 购买方税号 |
| sellerName | string | 销售方名称 |
| sellerTaxNo | string | 销售方税号 |
| totalAmount | decimal | 金额合计 |
| totalTax | decimal | 税额合计 |
| totalPriceTax | decimal | 价税合计 |
| invoiceDate | date | 开票日期 |
| drawer | string | 开票人 |

### 14.3 发票明细字段（BizInvoiceDetail）

| 字段 | 类型 | 说明 |
|------|------|------|
| invoiceId | string | 关联发票ID |
| itemName | string | 项目名称 |
| spec | string | 规格型号 |
| unit | string | 单位 |
| quantity | decimal | 数量 |
| unitPrice | decimal | 单价 |
| amount | decimal | 金额 |
| taxRate | string | 税率 |
| taxAmount | decimal | 税额 |

---

## 15. 经营范围 OpenAPI

**Base URL**: `{host}/jeecg-boot/bizorder/openapi/businessScope`

### 15.1 接口清单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/search?keyword=&limit=20` | 模糊搜索（匹配规范表述/描述/国标名/编码） |
| GET | `/page?keyword=&pageNo=&pageSize=` | 分页查询 |
| GET | `/getByCode?code=` | 按经营范围编码精确查 |

### 15.2 返回字段（BizBusinessScope）

| 字段 | 类型 | 说明 |
|------|------|------|
| scopeCode | string | 经营范围编码 |
| standardItem | string | 规范表述名称 |
| description | string | 描述说明 |
| gbName | string | 国标名称 |
| gbObjList | string | 国标分类路径（JSON数组） |
| permitType | int | 许可类型 0一般/1前置许可/2后置许可 |
| specialTips | string | 特别提示 |
| negativeListRule | string | 负面清单规则 |
