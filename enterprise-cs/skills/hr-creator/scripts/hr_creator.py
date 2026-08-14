import sys
import json
import os
import re
import requests
from typing import Dict, Any, Optional, List

# ─── 枚举归一化字典 ───────────────────────────────────────────────

ORDER_TYPE_ALIASES = {
    "参保登记": "BIZ_INSURANCE",
    "参保登记工单": "BIZ_INSURANCE",
    "参保": "BIZ_INSURANCE",
    "社保参保": "BIZ_INSURANCE",
    "参保转出": "BIZ_INSURANCE_OUT",
    "参保转出工单": "BIZ_INSURANCE_OUT",
    "社保转出": "BIZ_INSURANCE_OUT",
    "公积金转入": "BIZ_HOUSING_FUND_IN",
    "公积金转入工单": "BIZ_HOUSING_FUND_IN",
    "公积金封存": "BIZ_HOUSING_FUND_SEAL",
    "公积金封存工单": "BIZ_HOUSING_FUND_SEAL",
}

ORDER_STATUS_ALIASES = {
    "材料准备中": "PREPARING",
    "待客户确认": "CONFIRM_BY_C",
    "待经办人确认": "CONFIRM_BY_A",
    "待提交": "PENDING",
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


def normalize_date(value: Any) -> str:
    """归一化日期字符串为 yyyy-MM-dd 格式。"""
    if not value:
        return ""
    text = str(value).strip()
    # 支持 2026/08/01, 2026.08.01, 2026年08月01日 -> 2026-08-01
    text = re.sub(r"[年月/.]", "-", text)
    text = re.sub(r"日", "", text).rstrip("-")
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if m:
        year, month, day = m.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return text


def normalize_work_order(work_order: Dict[str, Any]) -> Dict[str, Any]:
    """归一化 workOrder 对象。"""
    clean: Dict[str, Any] = {}
    for key, val in work_order.items():
        if val not in (None, ""):
            clean[key] = val

    raw_type = clean.get("orderType", "")
    clean["orderType"] = normalize_enum(raw_type, ORDER_TYPE_ALIASES, raw_type)

    if "orderStatus" in clean:
        clean["orderStatus"] = normalize_enum(clean["orderStatus"], ORDER_STATUS_ALIASES, clean["orderStatus"])
    else:
        clean["orderStatus"] = "PREPARING"

    if "isFinalSubmit" not in clean:
        clean["isFinalSubmit"] = 0

    return clean


def normalize_insurance_detail(detail: Dict[str, Any]) -> Dict[str, Any]:
    """归一化参保登记明细。"""
    clean: Dict[str, Any] = {}
    for key, val in detail.items():
        if val not in (None, ""):
            clean[key] = val

    for date_key in ["employmentStartDate", "contractStartDate", "contractEndDate"]:
        if date_key in clean:
            clean[date_key] = normalize_date(clean[date_key])

    if "employmentForm" not in clean:
        clean["employmentForm"] = "全日制"

    if "isDispatch" not in clean:
        clean["isDispatch"] = "否"

    return clean


def normalize_insurance_out_detail(detail: Dict[str, Any]) -> Dict[str, Any]:
    """归一化参保转出明细。"""
    clean: Dict[str, Any] = {}
    for key, val in detail.items():
        if val not in (None, ""):
            clean[key] = val
    return clean


def normalize_housing_fund_in_detail(detail: Dict[str, Any]) -> Dict[str, Any]:
    """归一化公积金转入明细。"""
    clean: Dict[str, Any] = {}
    for key, val in detail.items():
        if val not in (None, ""):
            clean[key] = val

    if "fundBase" in clean:
        try:
            clean["fundBase"] = round(float(clean["fundBase"]), 2)
        except (ValueError, TypeError):
            pass
    return clean


def normalize_housing_fund_seal_detail(detail: Dict[str, Any]) -> Dict[str, Any]:
    """归一化公积金封存明细。"""
    clean: Dict[str, Any] = {}
    for key, val in detail.items():
        if val not in (None, ""):
            clean[key] = val

    if "leaveDate" in clean:
        clean["leaveDate"] = normalize_date(clean["leaveDate"])

    return clean


# ─── 校验逻辑 ─────────────────────────────────────────────────

def validate_params(
    work_order: Dict[str, Any],
    insurance_detail: Optional[Dict[str, Any]] = None,
    insurance_out_detail: Optional[Dict[str, Any]] = None,
    housing_fund_in_detail: Optional[Dict[str, Any]] = None,
    housing_fund_seal_detail: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """校验必填字段，返回错误消息或 None。"""
    order_type = work_order.get("orderType")
    valid_types = ["BIZ_INSURANCE", "BIZ_INSURANCE_OUT", "BIZ_HOUSING_FUND_IN", "BIZ_HOUSING_FUND_SEAL"]
    if not order_type or order_type not in valid_types:
        return f"orderType 为必填项，且必须为以下之一：{', '.join(valid_types)}"

    if not work_order.get("enterpriseName"):
        return "enterpriseName（企业名称）为必填项"

    # 1. 参保登记
    if order_type == "BIZ_INSURANCE":
        if not insurance_detail:
            return "参保登记工单缺少 insuranceDetail 扩展明细对象"
        if not insurance_detail.get("employeeName"):
            return "insuranceDetail 缺少 employeeName（员工姓名）"
        if not insurance_detail.get("idCard"):
            return "insuranceDetail 缺少 idCard（身份证号）"
        if not insurance_detail.get("employmentStartDate"):
            return "insuranceDetail 缺少 employmentStartDate（就业起始日期）"
        if not insurance_detail.get("contractSignType"):
            return "insuranceDetail 缺少 contractSignType（合同签订方式：纸质合同/电子合同）"
        if not insurance_detail.get("contractTerm"):
            return "insuranceDetail 缺少 contractTerm（合同期限：6个月/一年/三年/五年/长期）"
        if not insurance_detail.get("contractStartDate"):
            return "insuranceDetail 缺少 contractStartDate（合同开始日期）"
        if not insurance_detail.get("contractEndDate"):
            return "insuranceDetail 缺少 contractEndDate（合同结束日期）"

    # 2. 参保转出
    elif order_type == "BIZ_INSURANCE_OUT":
        if not insurance_out_detail:
            return "参保转出工单缺少 insuranceOutDetail 扩展明细对象"
        if not insurance_out_detail.get("employeeName"):
            return "insuranceOutDetail 缺少 employeeName（员工姓名）"
        if not insurance_out_detail.get("idCard"):
            return "insuranceOutDetail 缺少 idCard（身份证号）"

    # 3. 公积金转入
    elif order_type == "BIZ_HOUSING_FUND_IN":
        if not housing_fund_in_detail:
            return "公积金转入工单缺少 housingFundInDetail 扩展明细对象"
        if not housing_fund_in_detail.get("employeeName"):
            return "housingFundInDetail 缺少 employeeName（员工姓名）"
        if not housing_fund_in_detail.get("idCard"):
            return "housingFundInDetail 缺少 idCard（身份证号）"
        if not housing_fund_in_detail.get("fundAccount"):
            return "housingFundInDetail 缺少 fundAccount（公积金账号）"
        if housing_fund_in_detail.get("fundBase") in (None, ""):
            return "housingFundInDetail 缺少 fundBase（公积金基数）"

    # 4. 公积金封存
    elif order_type == "BIZ_HOUSING_FUND_SEAL":
        if not housing_fund_seal_detail:
            return "公积金封存工单缺少 housingFundSealDetail 扩展明细对象"
        if not housing_fund_seal_detail.get("employeeName"):
            return "housingFundSealDetail 缺少 employeeName（员工姓名）"
        if not housing_fund_seal_detail.get("idCard"):
            return "housingFundSealDetail 缺少 idCard（身份证号）"
        if not housing_fund_seal_detail.get("fundAccount"):
            return "housingFundSealDetail 缺少 fundAccount（公积金账号）"

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

    work_order = params.get("workOrder")
    if not work_order or not isinstance(work_order, dict):
        return json.dumps({
            "success": False,
            "message": "缺少有效的 workOrder 根节点参数"
        }, ensure_ascii=False)

    work_order = normalize_work_order(work_order)
    order_type = work_order.get("orderType", "")

    insurance_detail = None
    insurance_out_detail = None
    housing_fund_in_detail = None
    housing_fund_seal_detail = None

    if order_type == "BIZ_INSURANCE":
        raw = params.get("insuranceDetail") or {}
        if isinstance(raw, dict):
            insurance_detail = normalize_insurance_detail(raw)

    elif order_type == "BIZ_INSURANCE_OUT":
        raw = params.get("insuranceOutDetail") or {}
        if isinstance(raw, dict):
            insurance_out_detail = normalize_insurance_out_detail(raw)

    elif order_type == "BIZ_HOUSING_FUND_IN":
        raw = params.get("housingFundInDetail") or {}
        if isinstance(raw, dict):
            housing_fund_in_detail = normalize_housing_fund_in_detail(raw)

    elif order_type == "BIZ_HOUSING_FUND_SEAL":
        raw = params.get("housingFundSealDetail") or {}
        if isinstance(raw, dict):
            housing_fund_seal_detail = normalize_housing_fund_seal_detail(raw)

    err = validate_params(
        work_order,
        insurance_detail=insurance_detail,
        insurance_out_detail=insurance_out_detail,
        housing_fund_in_detail=housing_fund_in_detail,
        housing_fund_seal_detail=housing_fund_seal_detail,
    )
    if err:
        return json.dumps({"success": False, "message": f"参数校验失败：{err}"}, ensure_ascii=False)

    payload: Dict[str, Any] = {
        "workOrder": work_order
    }

    if insurance_detail:
        payload["insuranceDetail"] = insurance_detail
    if insurance_out_detail:
        payload["insuranceOutDetail"] = insurance_out_detail
    if housing_fund_in_detail:
        payload["housingFundInDetail"] = housing_fund_in_detail
    if housing_fund_seal_detail:
        payload["housingFundSealDetail"] = housing_fund_seal_detail

    # 微信会话路由透传
    session_key = params.get("sessionKey")
    if session_key:
        payload["workOrder"]["wechatMappingKey"] = session_key

    headers = {
        "Content-Type": "application/json",
        "X-Open-Token": api_token
    }

    url = f"{base_url.rstrip('/')}/bizorder/openapi/workOrder/add"

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code != 200:
            return json.dumps({
                "success": False,
                "message": f"工单服务 HTTP 异常：{resp.status_code} - {resp.text}"
            }, ensure_ascii=False)

        res_json = resp.json()
        if not res_json.get("success"):
            return json.dumps({
                "success": False,
                "message": res_json.get("message", "工单创建失败，接口未返回成功标记")
            }, ensure_ascii=False)

        result_str = str(res_json.get("result", ""))
        ticket_id = ""
        m = re.search(r"id=([0-9a-zA-Z]+)", result_str)
        if m:
            ticket_id = m.group(1)

        return json.dumps({
            "success": True,
            "ticket_id": ticket_id,
            "message": "人事业务工单创建成功"
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"调用工单接口发生网络或未知异常：{str(e)}"
        }, ensure_ascii=False)


# CLI 直接运行支持
if __name__ == "__main__":
    if len(sys.argv) > 1:
        raw_arg = sys.argv[1].strip()
        try:
            input_json = json.loads(raw_arg)
            print(execute(input_json))
        except json.JSONDecodeError as err:
            print(json.dumps({"success": False, "message": f"解析命令行输入的 JSON 失败: {str(err)}"}, ensure_ascii=False))
    else:
        print(json.dumps({"success": False, "message": "请通过命令行参数传入 JSON 字符串"}, ensure_ascii=False))
