#!/usr/bin/env python3
import sys
import os
import json
import time
import urllib.parse
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

TICKET_CREATOR_BASE_URL = os.getenv("TICKET_CREATOR_BASE_URL", "").strip()
TICKET_CREATOR_OPEN_TOKEN = os.getenv("TICKET_CREATOR_OPEN_TOKEN", "").strip()
RPA_BASE_URL = os.getenv("RPA_BASE_URL", "").strip()
RPA_API_KEY = os.getenv("RPA_API_KEY", "").strip()
GATEWAY_URL = os.getenv("GATEWAY_URL", "").strip()
GATEWAY_API_TOKEN = os.getenv("GATEWAY_API_TOKEN", "").strip()

def check_env():
    missing = []
    if not TICKET_CREATOR_BASE_URL: missing.append("TICKET_CREATOR_BASE_URL")
    if not TICKET_CREATOR_OPEN_TOKEN: missing.append("TICKET_CREATOR_OPEN_TOKEN")
    if not RPA_BASE_URL: missing.append("RPA_BASE_URL")
    if not RPA_API_KEY: missing.append("RPA_API_KEY")
    if not GATEWAY_URL: missing.append("GATEWAY_URL")
    if not GATEWAY_API_TOKEN: missing.append("GATEWAY_API_TOKEN")
    
    if missing:
        print(json.dumps({
            "success": False,
            "message": f"缺少必要的环境变量配置: {', '.join(missing)}"
        }, ensure_ascii=False))
        sys.exit(1)

def get_work_order(order_id):
    url = f"{TICKET_CREATOR_BASE_URL}/bizorder/openapi/workOrder/queryById?id={order_id}"
    headers = {
        "X-Open-Token": TICKET_CREATOR_OPEN_TOKEN,
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    res_data = response.json()
    if not res_data.get("success"):
        raise Exception(f"查询工单失败: {res_data.get('message')}")
    return res_data.get("result")

def validate_and_parse_agent(work_order_page):
    agent = work_order_page.get("agent")
    work_order = work_order_page.get("workOrder") or {}
    order_no = work_order.get("orderNo", "未知工单")
    
    if not agent:
        return False, f"工单[{order_no}] 未关联经办人信息"
        
    required_fields = {
        "agentName": "姓名",
        "agentPhone": "手机号",
        "idCardFrontUrl": "身份证正面照片URL",
        "idCardBackUrl": "身份证反面照片URL"
    }
    
    missing = []
    for field, name in required_fields.items():
        val = agent.get(field)
        if not val or not str(val).strip():
            missing.append(name)
            
    if missing:
        missing_str = "、".join(missing)
        return False, f"工单[{order_no}] 经办人关键信息缺失 ({missing_str})"
        
    parsed_agent = {
        "id_card_front_path": agent.get("idCardFrontUrl"),
        "id_card_back_path": agent.get("idCardBackUrl"),
        "name": agent.get("agentName"),
        "mobile_phone": agent.get("agentPhone"),
        "cert_number": agent.get("agentIdCard") or "",
        "cert_type": "中华人民共和国居民身份证",
        "agent_type": "经营主体登记注册代理人",
        "is_agent": "否"
    }
    
    return True, parsed_agent

def resolve_mapping_key(key):
    if not key:
        return None
    if key.startswith("agent:"):
        url = f"{GATEWAY_URL}/api/session"
        headers = {
            "Authorization": f"Bearer {GATEWAY_API_TOKEN}"
        }
        params = {
            "session_key": key
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                resolved = data.get("mapping_key")
                if resolved:
                    print(f"成功将 sessionKey [{key}] 解析为 mappingKey [{resolved}]")
                    return resolved
            print(f"解析 sessionKey 失败 ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"解析 sessionKey 网络异常: {str(e)}")
    return key

def send_gateway_message(mapping_key, text, image_url=None):
    if not mapping_key:
        print(f"[微信群消息模拟] 因 mapping_key 为空，无法实际发送到群聊。消息内容: {text}")
        return
    url = f"{GATEWAY_URL}/api/send"
    headers = {
        "Authorization": f"Bearer {GATEWAY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "mapping_key": mapping_key,
        "text": text
    }
    if image_url:
        payload["image_url"] = image_url
        payload["image_headers"] = {
            "X-API-Key": RPA_API_KEY
        }
        
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            print(f"微信群消息发送成功: {text}")
        else:
            print(f"微信群消息发送失败 ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"微信群消息发送网络异常: {str(e)}")

def check_login_status(company_name):
    url = f"{RPA_BASE_URL}/api/v1/task/verify"
    headers = {
        "X-API-Key": RPA_API_KEY
    }
    params = {
        "company_name": company_name,
        "check_only": "true"
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 200:
                return True
        return False
    except Exception as e:
        print(f"检查登录状态请求失败: {str(e)}")
        return False


def trigger_capital_reduction(company_name, item, agent_delegate):
    after_change = item.get("afterChange") or {}
    amount = after_change.get("amount")
    if amount is None:
        raise Exception("工单变更事项中缺失变更后的注册资本额(amount)")
        
    payload = {
        "new_capital": str(amount),
        "agent_delegate": agent_delegate
    }
    
    callback_url = os.getenv("RPA_CALLBACK_URL", "http://127.0.0.1/dummy_webhook")
    
    url = f"{RPA_BASE_URL}/api/v1/task/capital-reduction/start"
    params = {
        "company_name": company_name,
        "callback_url": callback_url
    }
    headers = {
        "X-API-Key": RPA_API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"调用 RPA 减资接口... 参数: {payload}")
    response = requests.post(url, json=payload, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    res_data = response.json()
    if res_data.get("code") != 200:
        raise Exception(f"RPA 接口返回错误: {res_data.get('message')}")
    return res_data.get("data", {})

def transit_work_order_status(order_id, target_status):
    url = f"{TICKET_CREATOR_BASE_URL}/bizorder/openapi/workOrder/transit"
    headers = {
        "X-Open-Token": TICKET_CREATOR_OPEN_TOKEN,
        "Content-Type": "application/json"
    }
    params = {
        "id": order_id,
        "targetStatus": target_status
    }
    try:
        response = requests.post(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        res_data = response.json()
        if not res_data.get("success"):
            print(f"流转工单状态失败: {res_data.get('message')}")
            return False
        print(f"成功将工单状态流转至 {target_status}")
        return True
    except Exception as e:
        print(f"流转工单状态网络异常: {str(e)}")
        return False

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "message": "请输入工单 ID"}, ensure_ascii=False))
        sys.exit(1)
        
    order_id = sys.argv[1]
    
    # 0. Check Environment
    check_env()
    
    # 1. Fetch Work Order Details
    try:
        print(f"正在拉取工单[{order_id}]详情...")
        work_order_page = get_work_order(order_id)
    except Exception as e:
        print(json.dumps({"success": False, "message": f"获取工单详情失败: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)
        
    work_order = work_order_page.get("workOrder") or {}
    order_no = work_order.get("orderNo", "未知工单")
    wechat_mapping_key = resolve_mapping_key(work_order.get("wechatMappingKey"))
    company_name = work_order.get("enterpriseName")
    order_status = work_order.get("orderStatus")
    
    print(f"工单编号: {order_no}, 企业名称: {company_name}, 当前状态: {order_status}")
    
    # Check if status is PENDING
    if order_status != "PENDING":
        print(json.dumps({
            "success": False,
            "message": f"工单[{order_no}]当前状态为[{order_status}]，并非'待提交(PENDING)'，中止执行。"
        }, ensure_ascii=False))
        sys.exit(0)
        
    # 2. Validate and Parse Agent Delegate
    success, agent_res = validate_and_parse_agent(work_order_page)
    if not success:
        # Send error alert message to WeChat group
        alert_msg = f"❌ 工单[{order_no}] 未关联完整的经办人信息（{agent_res.split('缺失')[1] if '缺失' in agent_res else agent_res}），无法执行 RPA 自动化，请管理员补充后重试。"
        send_gateway_message(wechat_mapping_key, alert_msg)
        print(json.dumps({"success": False, "message": agent_res}, ensure_ascii=False))
        sys.exit(0)
        
    agent_delegate = agent_res
    print(f"经办人校验成功: {agent_delegate.get('name')} ({agent_delegate.get('mobile_phone')})")
    
    # 3. Login Verification Loop
    print("开始检测登录状态...")
    logged_in = False
    any_captcha_sent = False
    company_name_encoded = urllib.parse.quote(company_name)
    
    for attempt in range(1, 6):
        if check_login_status(company_name):
            print("检测到已登录政府平台！")
            logged_in = True
            break
            
        print(f"未检测到登录。尝试获取二维码 (第 {attempt} 次/共 5 次)...")
        # Build qr code endpoint URL
        captcha_url = f"{RPA_BASE_URL}/api/v1/task/captcha?company_name={company_name_encoded}"
        
        # Pre-flight request to verify captcha screenshot is successfully generated
        captcha_ok = False
        try:
            headers = {"X-API-Key": RPA_API_KEY}
            captcha_resp = requests.get(captcha_url, headers=headers, timeout=120)
            if captcha_resp.status_code == 200:
                captcha_ok = True
            else:
                print(f"RPA 获取二维码接口返回异常 (HTTP {captcha_resp.status_code}): {captcha_resp.text}")
        except Exception as e:
            print(f"RPA 获取二维码接口网络异常: {str(e)}")
            
        if captcha_ok:
            prompt_text = f"📋 工单[{order_no}]（企业：{company_name}）需要扫码登录一网通办平台（第{attempt}次，二维码60秒有效，请使用电子营业执照 APP 扫码）："
            send_gateway_message(wechat_mapping_key, prompt_text, image_url=captcha_url)
            any_captcha_sent = True
            
            # Sub-loop: check login status every 5 seconds for a total of 60 seconds (12 times)
            print("二维码消息发送成功，进入扫码轮询检测（每 5 秒检测一次，最长 60 秒）...")
            for check_round in range(1, 13):
                time.sleep(5)
                if check_login_status(company_name):
                    print("在轮询中检测到已成功登录！")
                    logged_in = True
                    break
            
            if logged_in:
                break
        else:
            print("由于获取二维码图片失败，本次不发送微信消息，将在 10 秒后重试...")
            time.sleep(10)
        
    if not logged_in:
        if any_captcha_sent:
            timeout_msg = f"❌ 工单[{order_no}]（企业：{company_name}）扫码登录超时（已尝试5次），本次执行终止，请联系客服处理。"
            send_gateway_message(wechat_mapping_key, timeout_msg)
            print(json.dumps({"success": False, "message": "扫码登录超时，退出任务。"}, ensure_ascii=False))
        else:
            print(json.dumps({"success": False, "message": "获取登录二维码失败，退出任务。"}, ensure_ascii=False))
        sys.exit(0)
        
    # 4. Trigger RPA Tasks
    item_list = work_order_page.get("itemList") or []
    if not item_list:
        print(json.dumps({"success": False, "message": "工单中没有变更登记事项明细(itemList)。"}, ensure_ascii=False))
        sys.exit(0)
        
    print(f"开始处理工单变更事项，共 {len(item_list)} 个事项...")
    rpa_triggered = False
    unsupported_items = []
    
    for item in item_list:
        item_name = item.get("itemName")
        if item_name == "CAPITAL":
            try:
                trigger_capital_reduction(company_name, item, agent_delegate)
                rpa_triggered = True
                print("注册资本减少(CAPITAL) RPA 启动成功。")
            except Exception as e:
                err_msg = f"❌ 工单[{order_no}] 触发 RPA 注册资本减少任务失败: {str(e)}"
                send_gateway_message(wechat_mapping_key, err_msg)
                print(json.dumps({"success": False, "message": f"触发减资 RPA 失败: {str(e)}"}, ensure_ascii=False))
                sys.exit(1)
        elif item_name == "EQUITY":
            unsupported_items.append("股权变更(EQUITY，RPA开发中)")
        elif item_name == "PERIOD":
            unsupported_items.append("经营期限变更(PERIOD，暂无RPA接口)")
        else:
            unsupported_items.append(f"未识别或不支持的事项({item_name})")
            
    # Send warnings for unsupported items
    if unsupported_items:
        items_str = "、".join(unsupported_items)
        warn_msg = f"⚠️ 注意：工单部分事项 [{items_str}] 暂不支持自动执行，已跳过，请人工手动跟进办理。"
        send_gateway_message(wechat_mapping_key, warn_msg)
        print(f"部分事项不支持自动执行: {items_str}")
        
    if not rpa_triggered:
        print(json.dumps({
            "success": False,
            "message": "没有可以自动执行的变更事项被触发。"
        }, ensure_ascii=False))
        sys.exit(0)
        
    # 5. Transition Work Order Status
    print("所有支持的 RPA 任务均已启动成功，流转工单状态为 '办理中(PROCESSING)'...")
    success = transit_work_order_status(order_id, "PROCESSING")
    
    if success:
        finish_msg = f"✅ 工单[{order_no}] 已成功触发一网通办 RPA 自动申报，工单状态已流转为“办理中(PROCESSING)”。"
        send_gateway_message(wechat_mapping_key, finish_msg)
        print(json.dumps({"success": True, "message": "工单自动化执行流程全部成功完成。"}, ensure_ascii=False))
    else:
        print(json.dumps({"success": True, "message": "RPA任务启动成功，但工单状态流转失败。"}, ensure_ascii=False))

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
