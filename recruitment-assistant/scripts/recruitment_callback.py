import sys
import os
import json
import re
import requests

def execute(params: dict) -> str:
    # 1. 提取并校验 sessionId
    session_id = params.get("sessionId") or params.get("session_id")
    if not session_id:
        return json.dumps({
            "success": False,
            "msg": "缺少必填参数 sessionId。请直接从用户聊天消息的开头提取并作为参数传入。"
        }, ensure_ascii=False)
    
    # 清洗逻辑：使用正则从传入文本中提取符合规范的 UUID (36位 hex 字符组成的段落)
    if isinstance(session_id, str):
        uuid_match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", session_id)
        if uuid_match:
            session_id = uuid_match.group(0)
        else:
            # 兜底切分逻辑：兼容冒号（中英文）隔开的情况
            if ":" in session_id:
                session_id = session_id.split(":")[-1].strip()
            elif "：" in session_id:
                session_id = session_id.split("：")[-1].strip()
            session_id = session_id.strip(" ;；,，")
    
    # 2. 提取并校验 action
    action = params.get("action")
    if not action:
        return json.dumps({
            "success": False,
            "msg": "缺少必填参数 action。"
        }, ensure_ascii=False)
        
    if action not in ("request_resume", "schedule_interview"):
        return json.dumps({
            "success": False,
            "msg": f"无效的 action: {action}。当前支持的 action 为 request_resume 或 schedule_interview。"
        }, ensure_ascii=False)

    # 3. 提取其他可选参数
    content = params.get("content")
    interview_time = params.get("interviewTime") or params.get("interview_time")
    interview_end_time = params.get("interviewEndTime") or params.get("interview_end_time")

    # 4. 构造请求 Payload
    payload = {
        "sessionId": session_id,
        "action": action
    }
    
    if content is not None:
        payload["content"] = content
        
    if action == "schedule_interview":
        if not interview_time or not interview_end_time:
            return json.dumps({
                "success": False,
                "msg": "当 action 为 schedule_interview 时，interviewTime 和 interviewEndTime 为必填项。"
            }, ensure_ascii=False)
        payload["interviewTime"] = interview_time
        payload["interviewEndTime"] = interview_end_time

    # 5. 获取环境配置或使用默认值
    api_url = os.getenv("RECRUITMENT_API_URL", "http://61.169.217.122:10680/api/callback/recruitment")
    api_token = os.getenv("RECRUITMENT_API_TOKEN", "7f3a8c2b1d6e4f598a0b7c5d3e2f1a09b6c4d2e0f8a7b5c3d1e9f0a2b4c6d8e6f")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_token}"
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            return json.dumps({
                "success": False,
                "msg": f"接口请求失败，HTTP 状态码: {response.status_code}，响应内容: {response.text[:200]}"
            }, ensure_ascii=False)
        
        try:
            res_json = response.json()
            return json.dumps(res_json, ensure_ascii=False)
        except ValueError:
            return json.dumps({
                "success": False,
                "msg": f"接口返回了非 JSON 内容: {response.text[:300]}"
            }, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        return json.dumps({
            "success": False,
            "msg": f"接口调用网络异常: {str(e)}"
        }, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            args = json.loads(sys.argv[1])
            print(execute(args))
        except Exception as err:
            print(json.dumps({"success": False, "msg": f"参数解析错误: {str(err)}"}, ensure_ascii=False))
    else:
        print(json.dumps({"success": False, "msg": "未传入命令行 JSON 参数。"}, ensure_ascii=False))
