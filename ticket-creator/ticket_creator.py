import os
import sys
import json
import time
import requests
from typing import Dict, Any


def execute(params: Dict[str, Any]) -> str:
    """
    OpenClaw Skill 的标准 Python 执行体
    :param params: 大模型根据 markdown 规范提取出来的结构化 JSON 字典
    """
    # 提取三大根块
    work_order = params.get("workOrder", {})
    item_list = params.get("itemList", [])
    agent_list = params.get("agentList", [])

    # 基础空值防御
    if not work_order or not item_list or not agent_list:
        return json.dumps({
            "success": False,
            "message": "Skill 参数校验失败：创建工单必须同时包含工单信息、变更事项及至少一名经办人。"
        }, ensure_ascii=False)

    # 清洗经办人列表：只保留后端需要的业务字段，剔除审计字段
    clean_agents = []
    for agent in agent_list:
        clean_agent = {}
        for key in [
            "agentName", "agentPhone", "agentIdentityType",
            "agentType", "agentIdCard", "idCardFrontUrl", "idCardBackUrl"
        ]:
            if key in agent and agent[key]:
                clean_agent[key] = agent[key]
        # 默认身份类型
        if "agentIdentityType" not in clean_agent:
            clean_agent["agentIdentityType"] = "1"
        clean_agents.append(clean_agent)

    # 清洗事项列表：只保留业务字段
    clean_items = []
    for item in item_list:
        clean_item = {}
        for key in ["itemName", "beforeChange", "afterChange"]:
            if key in item:
                clean_item[key] = item[key]
        clean_items.append(clean_item)

    # 关键点：对齐 Knife4j 页面中展示的"多层包裹（套娃）"兼容逻辑
    # 深度克隆 workOrder 并把子表数组镜像塞入其内部，实现内外层双向对齐
    extended_work_order = {**work_order}
    extended_work_order["itemList"] = clean_items
    extended_work_order["agentList"] = clean_agents

    # 组装发往 JeecgBoot 开放接口的真实 Payload
    final_payload = {
        "workOrder": extended_work_order,
        "itemList": clean_items,
        "agentList": clean_agents
    }

    base_url = "http://139.196.78.56:8081/jeecg-boot"
    api_token = "7f3a8c2b1d6e4f598a0b7c5d3e2f1a09b6c4d2e0f8a7b5c3d1e9f0a2b4c6d8e0f"

    url = f"{base_url}/bizorder/openapi/workOrder/add"
    headers = {
        "Content-Type": "application/json",
        "X-Open-Token": api_token
    }

    try:
        response = requests.post(url, json=final_payload, headers=headers, timeout=12)

        if response.status_code == 200:
            return json.dumps(response.json(), ensure_ascii=False)
        elif response.status_code == 401:
            return json.dumps({"success": False, "message": "身份凭证(X-Open-Token)无效或已过期"}, ensure_ascii=False)
        else:
            return json.dumps({"success": False, "message": f"远端服务器返回异常状态码: {response.status_code}"}, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({"success": False, "message": f"连接物理接口产生网络异常: {str(e)}"}, ensure_ascii=False)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            input_params = json.loads(sys.argv[1])
            print(execute(input_params))
        except Exception as err:
            print(json.dumps({"success": False, "message": f"CLI 传参解析失败: {str(err)}"}))
