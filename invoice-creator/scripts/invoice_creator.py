import sys
import json
import os
import requests
from typing import Dict, Any, Optional, List


# ─── 枚举归一化字典 ───────────────────────────────────────────────

INVOICE_TYPE_ALIASES = {
    "蓝字": "BLUE_INVOICE",
    "蓝字发票": "BLUE_INVOICE",
    "蓝票": "BLUE_INVOICE",
    "红字": "RED_INVOICE",
    "红字发票": "RED_INVOICE",
    "红票": "RED_INVOICE",
    "红冲": "RED_INVOICE",
}

INVOICE_CATEGORY_ALIASES = {
    "专票": "SPECIAL_VAT_INVOICE",
    "专用发票": "SPECIAL_VAT_INVOICE",
    "增值税专用发票": "SPECIAL_VAT_INVOICE",
    "增值税专票": "SPECIAL_VAT_INVOICE",
    "普票": "NORMAL_INVOICE",
    "普通发票": "NORMAL_INVOICE",
    "增值税普通发票": "NORMAL_INVOICE",
    "增值税普票": "NORMAL_INVOICE",
}

ORDER_STATUS_ALIASES = {
    "材料准备中": "PREPARING",
    "待客户确认": "CONFIRM_BY_C",
    "待经办人确认": "CONFIRM_BY_A",
    "待提交": "PENDING",
    "已下发RPA": "DISPATCHED",
    "RPA执行中": "RUNNING",
    "RPA执行完成待确认": "WAIT_CONFIRM",
    "已办结": "DONE",
}


def normalize_enum(value: Any, aliases: Dict[str, str], default: str = "") -> str:
    """将中文别名归一化为标准枚举值。"""
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return aliases.get(text, text)


# ─── 税收分类编码自动搜索 ────────────────────────────────────────

# ─── 国家标准 19 位商品和服务税收分类编码本地匹配字典 ──────────────

COMMON_TAX_CATEGORY_MAP = {
    # 软件与信息技术服务
    "软件开发": "1090601020000000000",
    "软件": "1090601020000000000",
    "开发": "1090601020000000000",
    "程序": "1090601020000000000",
    "系统集成": "1090601010000000000",
    "数据处理": "1090601030000000000",
    "数据": "1090601030000000000",
    "云计算": "1090601040000000000",
    "信息技术": "1090601000000000000",
    "网络": "1090601000000000000",

    # 咨询与管理服务
    "技术咨询": "1090602000000000000",
    "咨询": "1090602000000000000",
    "顾问": "1090602000000000000",
    "管理咨询": "1090602020000000000",
    "企业管理": "1090602020000000000",

    # 广告与宣传服务
    "广告": "1090603000000000000",
    "宣传": "1090603000000000000",
    "推广": "1090603000000000000",
    "营销": "1090603000000000000",

    # 设计与文化服务
    "设计": "1090604010000000000",
    "图文": "1090604010000000000",
    "文化": "1090604000000000000",

    # 研发与技术服务
    "技术服务": "1090601020000000000",
    "技术": "1090601000000000000",
    "研发": "1090601000000000000",
    "检测": "1090606000000000000",
    "测试": "1090606000000000000",

    # 会展与培训
    "会议": "1090605000000000000",
    "展销": "1090605000000000000",
    "培训": "1090701000000000000",
    "教育": "1090701000000000000",

    # 租赁与商务服务
    "租赁": "1090400000000000000",
    "设备": "1090402000000000000",
    "中介": "1090602000000000000",

    # 建筑与工程
    "建筑": "1080000000000000000",
    "施工": "1080100000000000000",
    "工程": "1080100000000000000",
    "装修": "1080300000000000000",

    # 运输与物流
    "运输": "1090501000000000000",
    "物流": "1090500000000000000",
    "仓储": "1090502000000000000",

    # 生活服务
    "餐饮": "1090702000000000000",
    "住宿": "1090703000000000000",
    "物业": "1090704000000000000",
}

DEFAULT_TAX_CATEGORY_CODE = "1090000000000000000"  # 现代服务业通用编码


def search_tax_category_local(keyword: str) -> str:
    """本地国家标准税收分类编码模糊匹配 fallback 机制。"""
    if not keyword:
        return DEFAULT_TAX_CATEGORY_CODE
    text = str(keyword).strip()
    for key, code in COMMON_TAX_CATEGORY_MAP.items():
        if key in text:
            return code
    return DEFAULT_TAX_CATEGORY_CODE


def search_tax_category(keyword: str, base_url: str, token: str, limit: int = 5) -> str:
    """通过关键词搜索税收分类编码，优先请求远端接口，远端不可用时自动回退本地标准库。"""
    if base_url and token:
        url = f"{base_url}/bizorder/openapi/taxCategory/search"
        params = {"keyword": keyword, "limit": limit}
        headers = {"X-Open-Token": token}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    records = data.get("result", {})
                    if isinstance(records, dict):
                        records = records.get("records", [])
                    if isinstance(records, list) and records:
                        for record in records:
                            if record.get("isLeaf") in (1, True) and record.get("code"):
                                return record["code"]
                        if records[0].get("code"):
                            return records[0]["code"]
        except Exception:
            pass

    # 远端接口未就绪或未找到时，回退使用本地国家标准匹配库
    return search_tax_category_local(keyword)


# ─── 参数归一化与校验 ────────────────────────────────────────────

def normalize_work_order(work_order: Dict[str, Any]) -> Dict[str, Any]:
    """归一化工单主表字段。"""
    clean = {}
    for key in ["enterpriseName", "creditCode", "agentId", "isFinalSubmit",
                 "orderType", "matterType", "orderStatus", "wechatMappingKey", "customerId"]:
        value = work_order.get(key)
        if value not in (None, ""):
            clean[key] = value

    # 开票工单固定 orderType = BIZ_INVOICE, matterType = CHANGE
    clean["orderType"] = clean.get("orderType", "BIZ_INVOICE")
    clean["matterType"] = clean.get("matterType", "CHANGE")
    clean["orderStatus"] = normalize_enum(
        clean.get("orderStatus"), ORDER_STATUS_ALIASES, "PREPARING"
    )

    return clean


def normalize_invoice_order(invoice_order: Dict[str, Any]) -> Dict[str, Any]:
    """归一化发票扩展信息字段。"""
    clean = {}
    for key in ["buyerName", "buyerCreditCode", "invoiceType",
                 "invoiceCategory", "invoiceRemark"]:
        value = invoice_order.get(key)
        if value not in (None, ""):
            clean[key] = value

    clean["invoiceType"] = normalize_enum(
        clean.get("invoiceType"), INVOICE_TYPE_ALIASES, ""
    )
    clean["invoiceCategory"] = normalize_enum(
        clean.get("invoiceCategory"), INVOICE_CATEGORY_ALIASES, ""
    )

    return clean


def normalize_detail_list(
    detail_list: List[Dict[str, Any]],
    base_url: str,
    token: str,
) -> List[Dict[str, Any]]:
    """归一化开票明细行，含税收编码自动搜索。"""
    clean_list = []
    for item in detail_list:
        if not isinstance(item, dict):
            continue

        clean_item: Dict[str, Any] = {}
        for key in ["itemName", "goodsServiceTaxCode", "spec", "unit",
                     "quantity", "unitPrice", "amount", "taxRate"]:
            value = item.get(key)
            if value not in (None, ""):
                clean_item[key] = value

        # 税收编码自动搜索：如果没有 goodsServiceTaxCode
        if not clean_item.get("goodsServiceTaxCode"):
            tax_keyword = item.get("taxKeyword") or item.get("itemName")
            code = search_tax_category(tax_keyword, base_url, token)
            if code:
                clean_item["goodsServiceTaxCode"] = code

        # 移除临时字段
        clean_item.pop("taxKeyword", None)

        if clean_item:
            clean_list.append(clean_item)

    return clean_list


# ─── 校验逻辑 ─────────────────────────────────────────────────

def validate_params(
    work_order: Dict[str, Any],
    invoice_order: Dict[str, Any],
    detail_list: List[Dict[str, Any]],
) -> Optional[str]:
    """校验必填字段，返回错误消息或 None。"""
    if not work_order.get("enterpriseName"):
        return "enterpriseName（销方企业名称）为必填项"

    if not invoice_order.get("buyerName"):
        return "buyerName（购买方名称）为必填项"

    if not invoice_order.get("invoiceType"):
        return "invoiceType（发票类型：蓝字/红字）为必填项"

    if not invoice_order.get("invoiceCategory"):
        return "invoiceCategory（发票类别：专票/普票）为必填项"

    if not detail_list:
        return "invoiceDetailList（开票明细行）不能为空，至少需要一行"

    for i, item in enumerate(detail_list, 1):
        if not item.get("itemName"):
            return f"第 {i} 行明细缺少 itemName（项目名称）"
        if item.get("quantity") in (None, ""):
            return f"第 {i} 行明细缺少 quantity（数量）"
        if item.get("unitPrice") in (None, ""):
            return f"第 {i} 行明细缺少 unitPrice（单价）"
        if not item.get("taxRate"):
            return f"第 {i} 行明细缺少 taxRate（税率）"

    return None


# ─── 主执行函数 ──────────────────────────────────────────────

def execute(params: Dict[str, Any]) -> str:
    """
    OpenClaw Skill 的标准 Python 执行体
    :param params: 大模型根据 markdown 规范提取出来的结构化 JSON 字典
    """
    base_url = os.getenv("TICKET_CREATOR_BASE_URL", "")
    api_token = os.getenv("TICKET_CREATOR_OPEN_TOKEN") or os.getenv("RPA_API_KEY", "")

    if not base_url or not api_token:
        return json.dumps({
            "success": False,
            "message": "未配置 TICKET_CREATOR_BASE_URL 或 TICKET_CREATOR_OPEN_TOKEN / RPA_API_KEY 环境变量"
        }, ensure_ascii=False)

    # 提取根块
    work_order_raw = params.get("workOrder", {})
    invoice_order_raw = params.get("invoiceOrder", {})
    detail_list_raw = params.get("invoiceDetailList", [])

    # 基础空值防御
    if not work_order_raw or not invoice_order_raw:
        return json.dumps({
            "success": False,
            "message": "Skill 参数校验失败：创建开票工单必须同时包含工单信息（workOrder）和发票信息（invoiceOrder）。"
        }, ensure_ascii=False)

    # 自动提取会话路由键并注入
    session_key = (
        params.get("sessionKey") or
        params.get("session_key") or
        work_order_raw.get("sessionKey") or
        work_order_raw.get("session_key") or
        work_order_raw.get("wechatMappingKey") or
        os.getenv("OPENCLAW_SESSION_KEY")
    )

    if session_key:
        work_order_raw = {**work_order_raw, "wechatMappingKey": session_key}

    # 归一化
    clean_work_order = normalize_work_order(work_order_raw)
    clean_invoice_order = normalize_invoice_order(invoice_order_raw)
    clean_detail_list = normalize_detail_list(detail_list_raw, base_url, api_token)

    # 校验
    error = validate_params(clean_work_order, clean_invoice_order, clean_detail_list)
    if error:
        return json.dumps({
            "success": False,
            "message": f"Skill 参数校验失败：{error}"
        }, ensure_ascii=False)

    # 关键点：对齐 JeecgBoot 接口的"多层包裹（套娃）"兼容逻辑
    # 深度克隆 workOrder 并把子表镜像塞入其内部，实现内外层双向对齐
    extended_work_order = {**clean_work_order}
    extended_work_order["invoiceOrder"] = clean_invoice_order
    extended_work_order["invoiceDetailList"] = clean_detail_list

    # 组装发往 JeecgBoot 开放接口的 Payload
    final_payload = {
        "workOrder": extended_work_order,
        "invoiceOrder": clean_invoice_order,
        "invoiceDetailList": clean_detail_list,
    }

    url = f"{base_url}/bizorder/openapi/workOrder/add"
    headers = {
        "Content-Type": "application/json",
        "X-Open-Token": api_token,
    }

    try:
        response = requests.post(url, json=final_payload, headers=headers, timeout=12)

        if response.status_code == 401:
            return json.dumps({
                "success": False,
                "message": "身份凭证(X-Open-Token)无效或已过期"
            }, ensure_ascii=False)
        if response.status_code != 200:
            return json.dumps({
                "success": False,
                "message": f"远端服务器返回异常状态码: {response.status_code}"
            }, ensure_ascii=False)

        try:
            response_json = response.json()
        except ValueError:
            return json.dumps({
                "success": False,
                "message": f"远端接口返回了非 JSON 内容: {response.text[:300]}"
            }, ensure_ascii=False)

        if isinstance(response_json, dict) and response_json.get("success") is False:
            return json.dumps(response_json, ensure_ascii=False)

        # 从 result 字段解析工单 ID，例如 "添加成功！id=2082323735033016330"
        ticket_id = None
        result_str = response_json.get("result", "") if isinstance(response_json, dict) else ""
        if isinstance(result_str, str) and "id=" in result_str:
            try:
                ticket_id = result_str.split("id=")[-1].strip()
            except Exception:
                ticket_id = None

        # 将工单 ID 附加到返回结果中供 LLM 使用
        enriched = dict(response_json) if isinstance(response_json, dict) else {"raw": response_json}
        if ticket_id:
            enriched["ticket_id"] = ticket_id

        return json.dumps(enriched, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({
            "success": False,
            "message": f"连接物理接口产生网络异常: {str(e)}"
        }, ensure_ascii=False)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            input_params = json.loads(sys.argv[1])
            print(execute(input_params))
        except Exception as err:
            print(json.dumps({
                "success": False,
                "message": f"CLI 传参解析失败: {str(err)}"
            }))
