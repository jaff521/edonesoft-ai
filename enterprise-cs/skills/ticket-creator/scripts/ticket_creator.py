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
    "待客户确认": "CONFIRM_BY_C",
    "待经办人确认": "CONFIRM_BY_A",
    "待提交": "PENDING",
    "待填报": "PENDING",
    "暂存": "DRAFT",
    "取消": "CANCEL",
    "终止办理": "CANCEL",
    "取消/终止办理": "CANCEL",
    "已下发RPA": "DISPATCHED",
    "RPA执行中": "RUNNING",
    "RPA执行完成待确认": "WAIT_CONFIRM",
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
    "职务": "POSITION",
    "职务变更": "POSITION",
    "高级管理人员备案": "SENIOR_MANAGER",
    "登记联络员备案": "LIAISON",
    "联络员": "LIAISON",
    "章程备案时间": "BYLAW_ARTICLE",
    "章程备案": "BYLAW_ARTICLE",
    "监事备案": "SUPERVISOR",
    "监事": "SUPERVISOR",
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


def normalize_legal_change(change: Dict[str, Any], is_after: bool = False) -> Dict[str, Any]:
    """法定代表人 LEGAL 事项归一化。
    beforeChange：仅保留 name。
    afterChange：name 必填，额外透传 phone / idCardFrontUrl / idCardBackUrl / needLiaison / liaison（均可选）。
    注：监事已拆分为独立事项 SUPERVISOR，不再内嵌在 LEGAL 中。
    """
    name = change.get("name")
    if not name:
        raw_value = first_non_empty_value(change)
        name = raw_value if raw_value not in (None, "") else None

    result: Dict[str, Any] = {}
    if name:
        result["name"] = name

    if is_after:
        for field in ("phone", "idCardFrontUrl", "idCardBackUrl"):
            val = change.get(field)
            if val not in (None, ""):
                result[field] = val
        # v2.9: 登记联络员
        need_liaison = change.get("needLiaison")
        if need_liaison is not None:
            result["needLiaison"] = need_liaison
        liaison = change.get("liaison")
        if isinstance(liaison, dict) and liaison.get("name"):
            result["liaison"] = liaison

    return result


def normalize_position_change(change: Dict[str, Any], is_after: bool = False) -> Dict[str, Any]:
    """职务 POSITION 事项归一化（v2.5 新增）。
    beforeChange：name + position。
    afterChange：name + position + 可选 phone / idCardFrontUrl / idCardBackUrl。
    """
    result: Dict[str, Any] = {}
    for field in ("name", "position"):
        val = change.get(field)
        if val not in (None, ""):
            result[field] = val

    if is_after:
        for field in ("phone", "idCardFrontUrl", "idCardBackUrl"):
            val = change.get(field)
            if val not in (None, ""):
                result[field] = val

    return result


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


def parse_ratio_to_float(value: Any) -> Any:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            val = float(value)
        else:
            text = str(value).strip()
            if text.endswith("%"):
                val = float(text[:-1]) / 100
            else:
                val = float(text)
        
        return round(val / 100, 4) if val > 1 else val
    except (TypeError, ValueError):
        return None



def normalize_equity_change(change: Dict[str, Any], is_after: bool = False) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
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
            ratio_value = parse_ratio_to_float(ratio)
            if ratio_value is not None:
                entry["ratio"] = ratio_value

            # v1.1: 透传股东证件字段（可选）
            for cert_key in ("certType", "certNumber", "certFrontUrl", "certBackUrl"):
                cert_value = shareholder.get(cert_key)
                if cert_value not in (None, ""):
                    entry[cert_key] = cert_value

            # v2.4: 透传股东手机号
            phone = shareholder.get("phone")
            if phone not in (None, ""):
                entry["phone"] = phone

            # v2.5: 透传认缴时间（仅 afterChange）
            if is_after:
                for date_key in ("subscriptionStartDate", "subscriptionContributionDate"):
                    date_value = shareholder.get(date_key)
                    if date_value not in (None, ""):
                        entry[date_key] = date_value

            if entry:
                normalized.append(entry)

        result["shareholders"] = normalized
    else:
        raw_value = first_non_empty_value(change)
        if raw_value in (None, ""):
            return {}
        if isinstance(raw_value, str):
            parsed = parse_shareholders_from_text(raw_value)
            if parsed:
                return parsed
            return change
        return change

    # v2.4+v2.6: 透传 afterChange 顶层字段
    if is_after:
        # 股权转让明细
        equity_transfers = change.get("equityTransfers")
        if isinstance(equity_transfers, list) and equity_transfers:
            result["equityTransfers"] = equity_transfers
        # 变更后企业类型
        enterprise_type = change.get("enterpriseType")
        if enterprise_type not in (None, ""):
            result["enterpriseType"] = enterprise_type
        # 监事信息
        need_sup = change.get("needSupervisor")
        if need_sup is not None:
            result["needSupervisor"] = need_sup
        supervisor = change.get("supervisor")
        if isinstance(supervisor, dict) and supervisor.get("name"):
            result["supervisor"] = supervisor

    return result


def normalize_capital_change(change: Dict[str, Any], is_after: bool = False) -> Dict[str, Any]:
    amount = parse_amount_to_yuan(change.get("amount"))
    if amount is None:
        raw_value = first_non_empty_value(change)
        amount = parse_amount_to_yuan(raw_value)

    if amount is None:
        return change

    currency = change.get("currency") or "CNY"
    result = {"amount": amount, "currency": currency}

    # v2.1: 处理 CAPITAL 中的 shareholders
    shareholders = change.get("shareholders")
    if isinstance(shareholders, list):
        normalized_shs = []
        for sh in shareholders:
            if not isinstance(sh, dict):
                continue
            entry = {}
            if sh.get("name"):
                entry["name"] = sh["name"]
            
            sh_amount = parse_amount_to_yuan(sh.get("amount"))
            if sh_amount is not None:
                entry["amount"] = sh_amount
                
            sh_ratio = sh.get("ratio")
            ratio_value = parse_ratio_to_float(sh_ratio)
            if ratio_value is not None:
                entry["ratio"] = ratio_value

            # v2.8: 认缴时间（仅 afterChange）
            if is_after:
                for date_key in ("subscriptionStartDate", "subscriptionContributionDate"):
                    date_value = sh.get(date_key)
                    if date_value not in (None, ""):
                        entry[date_key] = date_value

            if entry:
                normalized_shs.append(entry)
        result["shareholders"] = normalized_shs

    return result


def normalize_senior_manager_change(change: Dict[str, Any], is_after: bool = False) -> Dict[str, Any]:
    """高级管理人员备案 SENIOR_MANAGER 事项归一化。
    beforeChange：name + position。
    afterChange：name + position + 可选 phone / idCardFrontUrl / idCardBackUrl。
    """
    result: Dict[str, Any] = {}
    for field in ("name", "position"):
        val = change.get(field)
        if val not in (None, ""):
            result[field] = val

    if is_after:
        for field in ("phone", "idCardFrontUrl", "idCardBackUrl"):
            val = change.get(field)
            if val not in (None, ""):
                result[field] = val

    return result


def normalize_liaison_change(change: Dict[str, Any]) -> Dict[str, Any]:
    """登记联络员备案 LIAISON 事项归一化（仅 afterChange）。"""
    result: Dict[str, Any] = {}
    for field in ("name", "phone", "email", "address", "idCardFrontUrl", "idCardBackUrl"):
        val = change.get(field)
        if val not in (None, ""):
            result[field] = val
    return result


def normalize_bylaw_article_change(change: Dict[str, Any]) -> Dict[str, Any]:
    """章程备案时间 BYLAW_ARTICLE 事项归一化（仅 afterChange）。"""
    amendment_date = change.get("amendmentDate")
    if amendment_date not in (None, ""):
        return {"amendmentDate": amendment_date}
    raw_value = first_non_empty_value(change)
    return {"amendmentDate": raw_value} if raw_value not in (None, "") else {}


def normalize_supervisor_change(change: Dict[str, Any]) -> Dict[str, Any]:
    """监事备案 SUPERVISOR 事项归一化（仅 afterChange）。"""
    has_supervisor = change.get("hasSupervisor")
    if has_supervisor is False:
        return {"hasSupervisor": False}
    result: Dict[str, Any] = {"hasSupervisor": True}
    for field in ("name", "phone", "idCardFrontUrl", "idCardBackUrl"):
        val = change.get(field)
        if val not in (None, ""):
            result[field] = val
    return result


def normalize_change_payload(item_name: str, change: Any, is_after: bool = False) -> Any:
    if not isinstance(change, dict):
        return change

    # v2.8: 通用可选字段 bylawFilingDate（除 LEGAL 外所有事项 afterChange 可含）
    bylaw_filing_date = change.get("bylawFilingDate") if is_after and item_name != "LEGAL" else None

    if item_name == "NAME":
        result = normalize_name_change(change)
    elif item_name == "LEGAL":
        result = normalize_legal_change(change, is_after=is_after)
    elif item_name == "SCOPE":
        result = normalize_text_change(change, "scope")
    elif item_name == "ADDR":
        result = normalize_text_change(change, "address")
    elif item_name == "PERIOD":
        result = normalize_period_change(change)
    elif item_name == "CAPITAL":
        result = normalize_capital_change(change, is_after=is_after)
    elif item_name == "EQUITY":
        result = normalize_equity_change(change, is_after=is_after)
    elif item_name == "POSITION":
        result = normalize_position_change(change, is_after=is_after)
    elif item_name == "SENIOR_MANAGER":
        result = normalize_senior_manager_change(change, is_after=is_after)
    elif item_name == "LIAISON":
        result = normalize_liaison_change(change)
    elif item_name == "BYLAW_ARTICLE":
        result = normalize_bylaw_article_change(change)
    elif item_name == "SUPERVISOR":
        result = normalize_supervisor_change(change)
    else:
        result = change

    # 追加 bylawFilingDate
    if bylaw_filing_date not in (None, "") and isinstance(result, dict):
        result["bylawFilingDate"] = bylaw_filing_date

    return result


def normalize_work_order(work_order: Dict[str, Any]) -> Dict[str, Any]:
    clean_work_order = {}
    for key in [
        "enterpriseName", "creditCode", "objectType",
        "matterType", "orderType", "orderStatus",
        "wechatMappingKey", "customerId", "agentId",
        "relatedAttachments"
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
        "CONFIRM_BY_C",
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
            "beforeChange": normalize_change_payload(item_name, item.get("beforeChange"), is_after=False),
            "afterChange": normalize_change_payload(item_name, item.get("afterChange"), is_after=True),
        }
        clean_items.append(clean_item)

    return clean_items


def execute(params: Dict[str, Any]) -> str:
    """
    OpenClaw Skill 的标准 Python 执行体
    :param params: 大模型根据 markdown 规范提取出来的结构化 JSON 字典
    """
    # 自动提取会话路由键并注入 (支持从顶层参数、workOrder 内部、以及环境变量中获取)
    work_order = params.get("workOrder", {})
    session_key = (
        params.get("sessionKey") or
        params.get("session_key") or
        work_order.get("sessionKey") or
        work_order.get("session_key") or
        work_order.get("wechatMappingKey") or
        os.getenv("OPENCLAW_SESSION_KEY")
    )

    if session_key:
        work_order = {**work_order, "wechatMappingKey": session_key}

    # 提取根块
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

        # 从 result 字段解析工单 ID，例如 "添加成功！id=2050000000000005001"
        ticket_id = None
        result_str = response_json.get("result", "") if isinstance(response_json, dict) else ""
        if isinstance(result_str, str) and "id=" in result_str:
            try:
                ticket_id = result_str.split("id=")[-1].strip()
            except Exception:
                ticket_id = None

        # 组装 H5 确认页 URL，方便用户在聊天界面中点击直达工单
        confirm_url = None
        if ticket_id:
            h5_base = os.getenv("TICKET_CREATOR_H5_BASE_URL", base_url)
            confirm_url = f"{h5_base}/bizorder/h5?id={ticket_id}"

        # 将工单 ID 和确认 URL 附加到返回结果中供 LLM 使用
        enriched = dict(response_json) if isinstance(response_json, dict) else {"raw": response_json}
        if ticket_id:
            enriched["ticket_id"] = ticket_id
        if confirm_url:
            enriched["confirm_url"] = confirm_url

        return json.dumps(enriched, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({"success": False, "message": f"连接物理接口产生网络异常: {str(e)}"}, ensure_ascii=False)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        try:
            input_params = json.loads(sys.argv[1])
            print(execute(input_params))
        except Exception as err:
            print(json.dumps({"success": False, "message": f"CLI 传参解析失败: {str(err)}"}, ensure_ascii=False))
