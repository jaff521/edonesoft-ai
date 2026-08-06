#!/usr/bin/env python3
"""
税收分类编码查询工具
输入：商品/服务关键字，可选 limit 数量
输出：匹配的叶子税收分类编码列表 JSON
"""
import sys
import json
import os
import requests

def search_tax_categories(keyword: str, limit: int = 10):
    base_url = os.getenv("TICKET_CREATOR_BASE_URL", "http://139.196.78.56:8081/jeecg-boot")
    token = os.getenv("TICKET_CREATOR_OPEN_TOKEN") or os.getenv("RPA_API_KEY", "")

    result = {
        "success": False,
        "keyword": keyword,
        "total": 0,
        "candidates": [],
        "message": ""
    }

    if not keyword:
        result["message"] = "关键字不能为空"
        return result

    if not base_url or not token:
        result["message"] = "未配置 TICKET_CREATOR_BASE_URL 或 TICKET_CREATOR_OPEN_TOKEN 环境变量"
        return result

    url = f"{base_url}/bizorder/openapi/taxCategory/search"
    params = {"keyword": keyword, "limit": limit}
    headers = {"X-Open-Token": token}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            result["message"] = f"接口返回异常 HTTP {resp.status_code}"
            return result

        data = resp.json()
        if not data.get("success"):
            result["message"] = data.get("message", "接口返回失败")
            return result

        records = data.get("result", {})
        if isinstance(records, dict):
            records = records.get("records", [])
        if not isinstance(records, list):
            records = []

        candidates = []
        for item in records:
            code = item.get("code")
            name = item.get("name")
            short_name = item.get("shortName") or ""
            is_leaf = item.get("isLeaf")

            if code and name:
                candidates.append({
                    "code": str(code),
                    "name": str(name),
                    "shortName": str(short_name),
                    "isLeaf": is_leaf in (1, True)
                })

        result["success"] = True
        result["total"] = len(candidates)
        result["candidates"] = candidates
        return result

    except Exception as e:
        result["message"] = f"请求税收分类编码接口失败: {str(e)}"
        return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "message": "用法: python3 tax_query.py <关键字> [limit]"
        }, ensure_ascii=False, indent=2))
        return

    keyword = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10

    res = search_tax_categories(keyword, limit)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
