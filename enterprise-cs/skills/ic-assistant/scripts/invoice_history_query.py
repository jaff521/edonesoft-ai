#!/usr/bin/env python3
"""
按会话ID查询历史开票企业与明细行工具
用于在开票流程前按企微会话ID（wechatMappingKey/sessionKey）预取该会话下出现过的企业信息（销售方+购买方合并去重）与历史开票明细（去重），辅助智能预填与联想推荐。

用法:
  # 查询当前会话下历史企业与开票明细（全量）
  python3 invoice_history_query.py "wrChat_xxxx"
  
  # 仅查历史企业
  python3 invoice_history_query.py "wrChat_xxxx" --type enterprises

  # 仅查历史开票明细
  python3 invoice_history_query.py "wrChat_xxxx" --type details
"""

import sys
import os
import json
import argparse
import requests
from typing import Dict, Any, List, Optional


# 自动向上搜寻加载 .env 环境变量
def load_dotenv():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        env_file = os.path.join(cur_dir, ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            if k.strip() not in os.environ:
                                os.environ[k.strip()] = v.strip()
            except Exception:
                pass
            break
        parent = os.path.dirname(cur_dir)
        if parent == cur_dir:
            break
        cur_dir = parent


load_dotenv()


def query_enterprise_by_chat_id(wechat_mapping_key: str, base_url: str, token: str) -> Dict[str, Any]:
    """4.4 按会话ID查企业信息（销售方+购买方合并去重）"""
    url = f"{base_url}/bizorder/openapi/invoiceWorkOrder/getEnterpriseByChatId"
    params = {"wechatMappingKey": wechat_mapping_key}
    headers = {"X-Open-Token": token}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"success": False, "message": f"企业查询接口返回异常 HTTP {resp.status_code}", "data": []}
        data = resp.json()
        if not data.get("success"):
            return {"success": False, "message": data.get("message", "企业查询失败"), "data": []}
        records = data.get("result", [])
        if not isinstance(records, list):
            records = []
        return {"success": True, "message": "查询成功", "data": records}
    except Exception as e:
        return {"success": False, "message": f"连接企业查询接口异常: {str(e)}", "data": []}


def query_invoice_details_by_chat_id(wechat_mapping_key: str, base_url: str, token: str) -> Dict[str, Any]:
    """4.5 按会话ID查历史开票明细（itemName+goodsServiceTaxCode 去重）"""
    url = f"{base_url}/bizorder/openapi/invoiceWorkOrder/getInvoiceDetailsByChatId"
    params = {"wechatMappingKey": wechat_mapping_key}
    headers = {"X-Open-Token": token}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"success": False, "message": f"开票明细查询接口返回异常 HTTP {resp.status_code}", "data": []}
        data = resp.json()
        if not data.get("success"):
            return {"success": False, "message": data.get("message", "开票明细查询失败"), "data": []}
        records = data.get("result", [])
        if not isinstance(records, list):
            records = []
        return {"success": True, "message": "查询成功", "data": records}
    except Exception as e:
        return {"success": False, "message": f"连接开票明细接口异常: {str(e)}", "data": []}


def parse_args():
    parser = argparse.ArgumentParser(description="按会话ID查询历史开票企业与明细行工具")
    parser.add_argument("positional_session", nargs="?", default="", help="微信会话ID (wechatMappingKey/sessionKey)")
    parser.add_argument("--session", "-s", dest="flag_session", default="", help="微信会话ID")
    parser.add_argument("--type", "-t", choices=["all", "enterprises", "details"], default="all", help="查询类型: all | enterprises | details")

    args, unknown = parser.parse_known_args()
    session_key = args.flag_session or args.positional_session
    if not session_key and unknown:
        for arg in unknown:
            if not arg.startswith("-"):
                session_key = arg
                break

    return session_key.strip(), args.type


def main():
    session_key, query_type = parse_args()

    if not session_key:
        print(json.dumps({
            "success": False,
            "message": "请输入会话ID (例如: python3 invoice_history_query.py \"wrChat_xxxx\")"
        }, ensure_ascii=False, indent=2))
        return

    base_url = os.getenv("TICKET_CREATOR_BASE_URL", "http://139.196.78.56:8081/jeecg-boot")
    token = os.getenv("TICKET_CREATOR_OPEN_TOKEN") or os.getenv("RPA_API_KEY", "")

    if not base_url or not token:
        print(json.dumps({
            "success": False,
            "message": "未配置 TICKET_CREATOR_BASE_URL 或 TICKET_CREATOR_OPEN_TOKEN / RPA_API_KEY 环境变量"
        }, ensure_ascii=False, indent=2))
        return

    result = {
        "success": True,
        "wechatMappingKey": session_key,
    }

    if query_type in ["all", "enterprises"]:
        ent_res = query_enterprise_by_chat_id(session_key, base_url, token)
        result["enterprises"] = ent_res.get("data", [])
        if not ent_res.get("success"):
            result["enterprisesMessage"] = ent_res.get("message", "")

    if query_type in ["all", "details"]:
        det_res = query_invoice_details_by_chat_id(session_key, base_url, token)
        result["invoiceDetails"] = det_res.get("data", [])
        if not det_res.get("success"):
            result["invoiceDetailsMessage"] = det_res.get("message", "")

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
