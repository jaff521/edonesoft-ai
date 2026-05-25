import sys
import json
import re
import os
import requests
from typing import Dict, Any


OBJECT_TYPE_ALIASES = {
    "企业": "ENTERPRISE",
    "个体工商户": "INDIVIDUAL",
    "农民专业合作社": "COOP",
    "外国（地区）企业常驻代表机构": "FOREIGN_OFFICE",
    "外国（地区）企业在中国境内经营": "FOREIGN_BIZ",
}

MATTER_TYPE_ALIASES = {
    "设立": "SETUP",
    "变更": "CHANGE",
    "工商变更": "CHANGE",
    "法定代表人变更": "CHANGE",
    "注册资本变更": "CHANGE",
    "经营范围变更": "CHANGE",
    "住所变更": "CHANGE",
    "经营地址变更": "CHANGE",
    "经营期限变更": "CHANGE",
    "企业名称变更": "CHANGE",
    "名称变更": "CHANGE",
    "股东股权变更": "CHANGE",
    "股权变更": "CHANGE",
    "迁移": "MIGRATE",
    "注销": "CANCEL",
    "个转企": "IND2ENT",
    "跨省迁移": "CROSS_PROVINCE",
    "名称自主申报": "NAME_DECLARE",
}

ORDER_TYPE_ALIASES = {
    "工商变更": "BIZ_CHANGE",
    "工商设立": "BIZ_SETUP",
    "工商注销": "BIZ_CANCEL",
}

ORDER_STATUS_ALIASES = {
    "待填报": "PENDING",
    "暂存": "DRAFT",
    "材料已保存": "SAVED",
    "材料已人工确认": "CONFIRMED",
    "办理中": "PROCESSING",
    "已办结": "DONE",
}

ITEM_NAME_ALIASES = {
    "企业名称": "NAME",
    "名称": "NAME",
    "法定代表人": "LEGAL",
    "注册资本": "CAPITAL",
    "经营范围": "SCOPE",
    "经营期限": "PERIOD",
    "期限": "PERIOD",
    "住所": "ADDR",
    "经营地址": "ADDR",
    "地址": "ADDR",
    "股东": "EQUITY",
    "股权": "EQUITY",
}


DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


def normalize_enum(value: Any, aliases: Dict[str, str], default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return aliases.get(text, text)


def first_non_empty_value(data: Dict[str, Any]) -> Any:
    for value in data.values():
        if value not in (None, "", [], {}):
            return value
    return None


def parse_amount_to_yuan(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return int(value)

    text = str(value).strip().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return None

    amount = float(match.group(1))
    if "亿" in text:
        amount *= 100000000
    elif "万" in text:
        amount *= 10000
    return int(amount)


def normalize_period_change(change: Dict[str, Any]) -> Dict[str, Any]:
    period_type = str(change.get("type") or change.get("periodType") or "").strip().lower()
    date = change.get("date") or change.get("endDate")

    if period_type in {"forever", "长期"}:
        return {"type": "forever"}
    if period_type in {"fixed", "固定期限"} and date:
        return {"type": "fixed", "date": str(date)}

    raw_value = first_non_empty_value(change)
    if raw_value is None:
        return {}

    raw_text = str(raw_value).strip()
    if "长期" in raw_text:
        return {"type": "forever"}

    date_match = DATE_PATTERN.search(raw_text)
    if date_match:
        return {"type": "fixed", "date": date_match.group(0)}

    return {"type": "fixed", "date": raw_text}


def normalize_name_change(change: Dict[str, Any]) -> Dict[str, Any]:
    if "name" in change and change["name"]:
        return {"name": change["name"]}

    raw_value = first_non_empty_value(change)
    return {"name": raw_value} if raw_value not in (None, "") else {}


def normalize_text_change(change: Dict[str, Any], field_name: str) -> Dict[str, Any]:
    if field_name in change and change[field_name]:
        return {field_name: change[field_name]}

    raw_value = first_non_empty_value(change)
    return {field_name: raw_value} if raw_value not in (None, "") else {}


def parse_shareholders_from_text(text: str) -> Any:
    shareholders = []
    for segment in re.split(r"[，,；;\n]+", text):
        part = segment.strip()
        if not part:
            continue

        name_match = re.match(r"^([^-\s:：]+)", part)
        ratio_match = re.search(r"(\d+(?:\.\d+)?)\s*%", part)
        amount_match = re.search(r"(\d+(?:\.\d+)?)\s*(亿|万|元)", part)

        if not name_match:
            continue

        shareholder: Dict[str, Any] = {"name": name_match.group(1).strip()}
        if ratio_match:
            shareholder["ratio"] = round(float(ratio_match.group(1)) / 100, 4)
        if amount_match:
            shareholder["amount"] = parse_amount_to_yuan("".join(amount_match.groups()))
        shareholders.append(shareholder)

    return {"shareholders": shareholders} if shareholders else None


def normalize_equity_change(change: Dict[str, Any]) -> Dict[str, Any]:
    shareholders = change.get("shareholders")
    if isinstance(shareholders, list):
        normalized = []
        for shareholder in shareholders:
            if not isinstance(shareholder, dict):
                continue

            entry = {}
            if shareholder.get("name"):
                entry["name"] = shareholder["name"]

            amount = parse_amount_to_yuan(shareholder.get("amount"))
            if amount is not None:
                entry["amount"] = amount

            ratio = shareholder.get("ratio")
            if ratio not in (None, ""):
                try:
                    ratio_value = float(ratio)
                    entry["ratio"] = round(ratio_value / 100, 4) if ratio_value > 1 else ratio_value
                except (TypeError, ValueError):
                    pass

            # v1.1: 透传股东证件字段（可选）
            for cert_key in ("certType", "certNumber", "certFrontUrl", "certBackUrl"):
                cert_value = shareholder.get(cert_key)
                if cert_value not in (None, ""):
                    entry[cert_key] = cert_value

            if entry:
                normalized.append(entry)

        return {"shareholders": normalized}

    raw_value = first_non_empty_value(change)
    if raw_value in (None, ""):
        return {}
    if isinstance(raw_value, str):
        parsed = parse_shareholders_from_text(raw_value)
        if parsed:
            return parsed
    return change


def normalize_capital_change(change: Dict[str, Any]) -> Dict[str, Any]:
    amount = parse_amount_to_yuan(change.get("amount"))
    if amount is None:
        raw_value = first_non_empty_value(change)
        amount = parse_amount_to_yuan(raw_value)

    if amount is None:
        return change

    currency = change.get("currency") or "CNY"
    result = {"amount": amount, "currency": currency}
    if change.get("contributionType"):
        result["contributionType"] = change["contributionType"]
    return result


def normalize_change_payload(item_name: str, change: Any) -> Any:
    if not isinstance(change, dict):
        return change

    if item_name == "NAME":
        return normalize_name_change(change)
    if item_name == "LEGAL":
        return normalize_name_change(change)
    if item_name == "SCOPE":
        return normalize_text_change(change, "scope")
    if item_name == "ADDR":
        return normalize_text_change(change, "address")
    if item_name == "PERIOD":
        return normalize_period_change(change)
    if item_name == "CAPITAL":
        return normalize_capital_change(change)
    if item_name == "EQUITY":
        return normalize_equity_change(change)
    return change


def normalize_work_order(work_order: Dict[str, Any]) -> Dict[str, Any]:
    clean_work_order = {}
    for key in [
        "enterpriseName", "creditCode", "objectType",
        "matterType", "orderType", "orderStatus"
    ]:
        value = work_order.get(key)
        if value not in (None, ""):
            clean_work_order[key] = value

    clean_work_order["objectType"] = normalize_enum(
        clean_work_order.get("objectType"),
        OBJECT_TYPE_ALIASES,
        "ENTERPRISE",
    )
    clean_work_order["matterType"] = normalize_enum(
        clean_work_order.get("matterType"),
        MATTER_TYPE_ALIASES,
        "CHANGE",
    )
    clean_work_order["orderType"] = normalize_enum(
        clean_work_order.get("orderType"),
        ORDER_TYPE_ALIASES,
        "BIZ_CHANGE",
    )
    clean_work_order["orderStatus"] = normalize_enum(
        clean_work_order.get("orderStatus"),
        ORDER_STATUS_ALIASES,
        "PENDING",
    )

    return clean_work_order



def normalize_items(item_list: Any) -> Any:
    clean_items = []
    for item in item_list:
        if not isinstance(item, dict):
            continue

        item_name = normalize_enum(item.get("itemName"), ITEM_NAME_ALIASES, "")
        clean_item = {
            "itemName": item_name,
            "beforeChange": normalize_change_payload(item_name, item.get("beforeChange")),
            "afterChange": normalize_change_payload(item_name, item.get("afterChange")),
        }
        clean_items.append(clean_item)

    return clean_items


def execute(params: Dict[str, Any]) -> str:
    """
    OpenClaw Skill 的标准 Python 执行体
    :param params: 大模型根据 markdown 规范提取出来的结构化 JSON 字典
    """
    # 提取根块
    work_order = params.get("workOrder", {})
    item_list = params.get("itemList", [])

    # 基础空值防御
    if not work_order or not item_list:
        return json.dumps({
            "success": False,
            "message": "Skill 参数校验失败：创建工单必须同时包含工单信息（workOrder）和变更事项（itemList）。"
        }, ensure_ascii=False)

    clean_work_order = normalize_work_order(work_order)
    clean_items = normalize_items(item_list)

    if not clean_work_order.get("enterpriseName") or not clean_work_order.get("creditCode"):
        return json.dumps({
            "success": False,
            "message": "Skill 参数校验失败：enterpriseName 和 creditCode 为必填项。"
        }, ensure_ascii=False)

    if not clean_items or not all(item.get("itemName") for item in clean_items):
        return json.dumps({
            "success": False,
            "message": "Skill 参数校验失败：itemList 不能为空，且每个事项必须包含合法的 itemName。"
        }, ensure_ascii=False)


    # 关键点：对齐 Knife4j 页面中展示的"多层包裹（套娃）"兼容逻辑
    # 深度克隆 workOrder 并把子表数组镜像塞入其内部，实现内外层双向对齐
    extended_work_order = {**clean_work_order}
    extended_work_order["itemList"] = clean_items

    # 组装发往 JeecgBoot 开放接口的真实 Payload
    final_payload = {
        "workOrder": extended_work_order,
        "itemList": clean_items,
    }

    base_url = os.getenv("TICKET_CREATOR_BASE_URL", "")
    api_token = os.getenv("TICKET_CREATOR_OPEN_TOKEN", "")

    if not base_url or not api_token:
        return json.dumps({
            "success": False,
            "message": "ticket_creator 未配置 TICKET_CREATOR_BASE_URL 或 TICKET_CREATOR_OPEN_TOKEN 环境变量"
        }, ensure_ascii=False)

    url = f"{base_url}/bizorder/openapi/workOrder/add"
    headers = {
        "Content-Type": "application/json",
        "X-Open-Token": api_token
    }

    try:
        response = requests.post(url, json=final_payload, headers=headers, timeout=12)

        if response.status_code == 401:
            return json.dumps({"success": False, "message": "身份凭证(X-Open-Token)无效或已过期"}, ensure_ascii=False)
        if response.status_code != 200:
            return json.dumps({"success": False, "message": f"远端服务器返回异常状态码: {response.status_code}"}, ensure_ascii=False)

        try:
            response_json = response.json()
        except ValueError:
            return json.dumps({
                "success": False,
                "message": f"远端接口返回了非 JSON 内容: {response.text[:300]}"
            }, ensure_ascii=False)


        if isinstance(response_json, dict) and response_json.get("success") is False:
            return json.dumps(response_json, ensure_ascii=False)

        return json.dumps(response_json, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({"success": False, "message": f"连接物理接口产生网络异常: {str(e)}"}, ensure_ascii=False)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            input_params = json.loads(sys.argv[1])
            print(execute(input_params))
        except Exception as err:
            print(json.dumps({"success": False, "message": f"CLI 传参解析失败: {str(err)}"}))
