import sys
import json
import os
import re
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

def search_tax_category(keyword: str, base_url: str, token: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """通过关键词搜索税收分类编码，返回最佳匹配的叶子节点。"""
    url = f"{base_url}/bizorder/openapi/taxCategory/search"
    params = {"keyword": keyword, "limit": limit}
    headers = {"X-Open-Token": token}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data.get("success"):
            return None

        records = data.get("result", {})
        # result 可能是 list 或 dict with "records" key
        if isinstance(records, dict):
            records = records.get("records", [])
        if not isinstance(records, list) or not records:
            return None

        # 返回第一个叶子节点
        for record in records:
            if record.get("isLeaf") == 1 or record.get("isLeaf") is True:
                return record
        # 如果没有叶子节点，返回第一条
        return records[0]
    except Exception:
        return None


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

def _parse_tax_rate(raw_rate) -> float:
    """将税率转换为小数形式。支持 '6%' -> 0.06, '0.06' -> 0.06, 6 -> 0.06 等。"""
    if raw_rate is None or raw_rate == "":
        return 0.0
    s = str(raw_rate).strip()
    if s.endswith("%"):
        return float(s[:-1]) / 100.0
    val = float(s)
    # 如果传入的是 6、13 这种整数百分比值，自动转为小数
    if val >= 1:
        return val / 100.0
    return val


def normalize_detail_list(
    detail_list: List[Dict[str, Any]],
    base_url: str,
    token: str,
) -> List[Dict[str, Any]]:
    """归一化开票明细行。

    接口规范（最新）：
    - unitPrice: 不含税单价
    - amount: 不含税金额
    - taxRate: 小数形式（如 0.06）
    - taxAmount: 税额（必填）
    - taxInclusiveAmount: 含税金额（可选，不传时服务端自动计算）

    客户默认提供的是含税金额（taxInclusiveAmount），脚本自动换算为不含税金额、
    不含税单价、税额。数量未提供时默认为 1。
    """
    clean_list = []
    for item in detail_list:
        if not isinstance(item, dict):
            continue

        clean_item: Dict[str, Any] = {}
        for key in ["itemName", "goodsServiceTaxCode", "spec", "unit",
                     "quantity", "unitPrice", "amount", "taxRate",
                     "taxAmount", "taxInclusiveAmount"]:
            value = item.get(key)
            if value not in (None, ""):
                clean_item[key] = value

        # 移除已废弃的临时字段
        clean_item.pop("taxKeyword", None)

        # 数量默认为 1
        if "quantity" not in clean_item or clean_item["quantity"] in (None, ""):
            clean_item["quantity"] = 1

        # 归一化税率为小数形式（如 "6%" -> 0.06）
        if "taxRate" in clean_item:
            try:
                clean_item["taxRate"] = _parse_tax_rate(clean_item["taxRate"])
            except (ValueError, TypeError):
                pass

        # ─── 含税金额 → 不含税金额/单价/税额 自动换算 ───
        # 客户提供的金额默认为含税金额（taxInclusiveAmount）
        # 需要换算为不含税金额(amount)、不含税单价(unitPrice)、税额(taxAmount)
        tax_rate = float(clean_item.get("taxRate", 0))
        qty = float(clean_item.get("quantity", 1))

        # 判断客户传入的 amount 是含税还是不含税：
        # 如果已有 taxInclusiveAmount 则视为已明确区分；
        # 否则将 amount 视为含税金额（默认含税），移到 taxInclusiveAmount
        if "taxInclusiveAmount" not in clean_item and "amount" in clean_item:
            try:
                clean_item["taxInclusiveAmount"] = round(float(clean_item["amount"]), 2)
                del clean_item["amount"]
            except (ValueError, TypeError):
                pass

        # 根据 taxInclusiveAmount 计算 amount(不含税金额)、taxAmount(税额)
        if "taxInclusiveAmount" in clean_item:
            try:
                tax_inclusive = float(clean_item["taxInclusiveAmount"])
                # 不含税金额 = 含税金额 / (1 + 税率)，保留2位小数
                amount_ex_tax = round(tax_inclusive / (1 + tax_rate), 2) if tax_rate > 0 else round(tax_inclusive, 2)
                # 税额 = 含税金额 - 不含税金额
                tax_amount = round(tax_inclusive - amount_ex_tax, 2)

                clean_item["amount"] = amount_ex_tax
                clean_item["taxAmount"] = tax_amount
                clean_item["taxInclusiveAmount"] = round(tax_inclusive, 2)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # 自动计算不含税单价 unitPrice = amount(不含税) / quantity
        if "amount" in clean_item and ("unitPrice" not in clean_item or clean_item["unitPrice"] in (None, "")):
            try:
                amt = float(clean_item["amount"])
                if qty > 0:
                    calc_up = amt / qty
                    clean_item["unitPrice"] = round(calc_up, 13) if not calc_up.is_integer() else int(calc_up)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # 归一化 amount 保留2位小数
        if "amount" in clean_item:
            try:
                clean_item["amount"] = round(float(clean_item["amount"]), 2)
            except (ValueError, TypeError):
                pass

        # 归一化 unitPrice（除不尽保留13位小数）
        if "unitPrice" in clean_item:
            try:
                up_val = float(clean_item["unitPrice"])
                clean_item["unitPrice"] = round(up_val, 13) if not up_val.is_integer() else int(up_val)
            except (ValueError, TypeError):
                pass

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
        
        tax_code = str(item.get("goodsServiceTaxCode") or "").strip()
        if not tax_code:
            return f"第 {i} 行明细缺少 goodsServiceTaxCode（19位商品和服务税收分类编码）"
        if not re.match(r"^\d{19}$", tax_code):
            return f"第 {i} 行明细 goodsServiceTaxCode（{tax_code}）格式不符合 19 位纯数字编码要求"

        if item.get("quantity") in (None, ""):
            return f"第 {i} 行明细缺少 quantity（数量）"
        try:
            qty = float(item.get("quantity"))
            if qty <= 0:
                return f"第 {i} 行明细 quantity（数量）必须大于 0"
        except (ValueError, TypeError):
            return f"第 {i} 行明细 quantity（数量）数值格式不正确"

        if item.get("amount") in (None, ""):
            return f"第 {i} 行明细缺少 amount（不含税金额）"
        try:
            amt = float(item.get("amount"))
            if amt <= 0:
                return f"第 {i} 行明细 amount（不含税金额）必须大于 0"
        except (ValueError, TypeError):
            return f"第 {i} 行明细 amount（不含税金额）数值格式不正确"

        if item.get("unitPrice") in (None, ""):
            return f"第 {i} 行明细缺少 unitPrice（不含税单价）"

        if item.get("taxRate") in (None, ""):
            return f"第 {i} 行明细缺少 taxRate（税率）"

        if item.get("taxAmount") in (None, ""):
            return f"第 {i} 行明细缺少 taxAmount（税额）"

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

    url = f"{base_url}/bizorder/openapi/invoiceWorkOrder/add"
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        try:
            input_params = json.loads(sys.argv[1])
            print(execute(input_params))
        except Exception as err:
            print(json.dumps({
                "success": False,
                "message": f"CLI 传参解析失败: {str(err)}"
            }, ensure_ascii=False))
