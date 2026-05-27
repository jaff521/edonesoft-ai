#!/usr/bin/env python3
"""
工商信息整合查询脚本
输入：企业全称
输出：完整的工商信息JSON（含股权信息）
"""
import sys
import json
import time
import requests
import hashlib
import os

APP_ID = os.getenv("QYXQK_APP_ID", "")
SECRET = os.getenv("QYXQK_SECRET", "")
FUZZY_QUERY_API = os.getenv("QYXQK_FUZZY_QUERY_API", "https://gateway.qyxqk.com/wdyl/openapi/fuzzy_query/")
SHAREHOLDER_API = os.getenv("QYXQK_SHAREHOLDER_API", "https://gateway.qyxqk.com/wdyl/openapi/company_stockholder_query/")

def generate_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def calculate_sign(app_id, timestamp, secret, payload_dict):
    sorted_keys = sorted(payload_dict.keys())
    concat_str = ''.join(str(payload_dict[key]) for key in sorted_keys)
    sign_string = app_id + timestamp + secret + concat_str
    md5_hash = hashlib.md5()
    md5_hash.update(sign_string.encode('utf-8'))
    return md5_hash.hexdigest()

def query_company(company_name):
    """模糊查询企业基本信息"""
    request_data = {"key": company_name}
    request_body = json.dumps(request_data, ensure_ascii=False)
    timestamp = generate_timestamp()
    sign = calculate_sign(APP_ID, timestamp, SECRET, request_data)

    headers = {
        "APPID": APP_ID,
        "TIMESTAMP": timestamp,
        "SIGN": sign,
        "Content-Type": "application/json"
    }

    response = requests.post(FUZZY_QUERY_API, headers=headers, data=request_body, timeout=10)
    if response.status_code == 200:
        return response.json()
    return None

def query_shareholders(unified_credit_code):
    """查询股东信息"""
    request_data = {
        "key": unified_credit_code,
        "page_index": 1,
        "page_size": 20
    }
    request_body = json.dumps(request_data, ensure_ascii=False)
    timestamp = generate_timestamp()
    sign = calculate_sign(APP_ID, timestamp, SECRET, request_data)

    headers = {
        "APPID": APP_ID,
        "TIMESTAMP": timestamp,
        "SIGN": sign,
        "Content-Type": "application/json"
    }

    response = requests.post(SHAREHOLDER_API, headers=headers, data=request_body, timeout=10)
    if response.status_code == 200:
        return response.json()
    return None

def detect_shareholder_type(name):
    """自动识别股东类型：企业 or 自然人"""
    enterprise_keywords = ['公司', '有限', '股份', '合伙', '厂', '中心', '集团', '社', '部', '所', '店', '行']
    for keyword in enterprise_keywords:
        if name.endswith(keyword):
            return "企业"
    return "自然人"

def format_capital(amount):
    """格式化注册资本"""
    if not amount:
        return "未知"
    try:
        val = float(amount)
        if val >= 10000:
            return f"{val/10000:.0f}万"
        else:
            return f"{val:.0f}万"
    except:
        return str(amount)


def amount_to_yuan_from_wan(amount):
    """将工商接口常见的'万'单位金额转成元整数。"""
    if amount in (None, ""):
        return None
    try:
        return int(float(amount) * 10000)
    except:
        return None

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "请输入企业全称"}, ensure_ascii=False, indent=2))
        return

    if not APP_ID or not SECRET:
        print(json.dumps({"success": False, "error": "未配置企信查询凭证，请检查 QYXQK_APP_ID / QYXQK_SECRET 环境变量"}, ensure_ascii=False, indent=2))
        return

    company_name = sys.argv[1]

    result = {
        "success": False,
        "company_name": company_name,
        "error": ""
    }

    # Step 1: 查询企业基本信息
    company_data = query_company(company_name)
    if not company_data or company_data.get("code") != 200:
        result["error"] = "企业信息查询失败"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # 解析企业信息
    company_info = company_data.get("data", {}).get("data", [{}])[0] if company_data.get("data", {}).get("data") else {}
    unified_credit_code = company_info.get("UNISCID") or company_info.get("unified_credit_code")
    if not unified_credit_code:
        result["error"] = "未找到统一社会信用代码"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    official_company_name = company_info.get("ENTNAME") or company_info.get("NAME") or company_name
    legal_representative = company_info.get("FRNAME", "未知")
    raw_registered_capital = company_info.get("regcap")
    registered_capital = format_capital(raw_registered_capital)
    registered_capital_yuan = amount_to_yuan_from_wan(raw_registered_capital)
    registration_status = company_info.get("ENTSTATUS", "正常")
    established_date = company_info.get("ESDATE", "")

    result["company_name"] = official_company_name
    result["companyName"] = official_company_name
    result["unified_credit_code"] = unified_credit_code
    result["creditCode"] = unified_credit_code
    result["legal_representative"] = legal_representative
    result["legalRepresentative"] = legal_representative
    result["registered_capital"] = registered_capital
    result["registeredCapital"] = registered_capital
    result["registeredCapitalYuan"] = registered_capital_yuan
    result["registration_status"] = registration_status
    result["registrationStatus"] = registration_status
    result["established_date"] = established_date
    result["establishedDate"] = established_date

    # Step 2: 查询股东信息
    shareholder_data = query_shareholders(unified_credit_code)
    shareholders = []

    if shareholder_data and shareholder_data.get("code") == 200:
        holder_data = shareholder_data.get("data", {}).get("SHAREHOLDER", {})
        data_list = holder_data.get("datalist", [])
        regcap = company_info.get("regcap", 0)

        for item in data_list:
            name = item.get("SHANAME", "")
            amount = float(item.get("SUBCONAM", 0) or 0)

            # 计算占比
            percentage = "0%"
            if regcap and amount > 0:
                try:
                    pct = (amount / float(regcap)) * 100
                    percentage = f"{pct:.1f}%"
                except:
                    pass

            shareholders.append({
                "name": name,
                "amount": f"{amount:.0f}万" if amount > 0 else "0",
                "amountYuan": amount_to_yuan_from_wan(amount) if amount > 0 else 0,
                "percentage": percentage,
                "ratio": round((amount / float(regcap)), 4) if regcap and amount > 0 else 0,
                "type": detect_shareholder_type(name)
            })

    result["shareholders"] = shareholders
    result["standardChangeHints"] = {
        "registeredCapitalYuan": registered_capital_yuan,
        "equityBeforeChange": {
            "shareholders": [
                {
                    "name": shareholder["name"],
                    "amount": shareholder.get("amountYuan", 0),
                    "ratio": shareholder.get("ratio", 0),
                }
                for shareholder in shareholders
            ]
        }
    }
    result["success"] = True

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
