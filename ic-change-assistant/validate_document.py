#!/usr/bin/env python3
"""
证件验证器 - 使用阿里云通义千问进行OCR识别验证
输入：证件类型，证件图片路径，对比名称
输出：验证结果JSON
"""
import sys
import json
import base64
import os
import re
import requests

# 阿里云DashScope配置
DASHSCOPE_API = "https://dashscope.aliyuncs.com/compatible-mode/v1"
API_KEY = "sk-502c218e860a4c93ad1c4b6550346331"

def call_qwen_vision(image_path, prompt, model="qwen-vl-max"):
    """调用阿里云通义千问视觉模型"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
    except FileNotFoundError:
        return {"success": False, "error": "图片文件不存在"}
    except Exception as e:
        return {"success": False, "error": f"读取图片失败: {str(e)}"}

    # 转换为base64
    img_base64 = base64.b64encode(image_data).decode('utf-8')

    url = f"{DASHSCOPE_API}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # 使用正确的格式
    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}},
            {"type": "text", "text": prompt}
        ]
    }]

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 1024
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return {"success": True, "text": result["choices"][0]["message"]["content"]}
        elif "code" in result:
            return {"success": False, "error": f"API错误: {result.get('message', result)}"}
        else:
            return {"success": False, "error": f"未知响应: {result}"}
    except Exception as e:
        return {"success": False, "error": f"API调用失败: {str(e)}"}

def parse_idcard_response(text):
    """解析身份证识别结果"""
    try:
        # 尝试找到JSON块
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            data = json.loads(json_match.group())
            return {"success": True, "data": data}
    except:
        pass

    # 手动提取
    name = re.search(r'["`]?name["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    id_number = re.search(r'["`]?id_number["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    expiry = re.search(r'["`]?expiry_date["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    is_expired = re.search(r'["`]?is_expired["`]?[:：]\s*(true|false|yes|no)', text, re.I)

    result = {}
    if name: result["name"] = name.group(1).strip()
    if id_number: result["id_number"] = id_number.group(1).strip()
    if expiry: result["expiry_date"] = expiry.group(1).strip()

    # 判断是否过期
    if is_expired:
        result["is_expired"] = is_expired.group(1).lower() in ["true", "yes"]
    else:
        # 检查长期或未来日期
        if expiry and ("长期" in expiry.group(1) or "永久" in expiry.group(1)):
            result["is_expired"] = False

    return {"success": True, "data": result} if result else {"success": False, "error": "解析失败"}

def parse_business_license_response(text):
    """解析营业执照识别结果"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            data = json.loads(json_match.group())
            return {"success": True, "data": data}
    except:
        pass

    # 手动提取
    company_name = re.search(r'["`]?company_name["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    credit_code = re.search(r'["`]?unified_credit_code["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    legal_rep = re.search(r'["`]?legal_representative["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    expiry = re.search(r'["`]?expiry_date["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    is_expired = re.search(r'["`]?is_expired["`]?[:：]\s*(true|false|yes|no)', text, re.I)

    result = {}
    if company_name: result["company_name"] = company_name.group(1).strip()
    if credit_code: result["unified_credit_code"] = credit_code.group(1).strip()
    if legal_rep: result["legal_representative"] = legal_rep.group(1).strip()

    if is_expired:
        result["is_expired"] = is_expired.group(1).lower() in ["true", "yes"]
    else:
        if expiry and ("长期" in expiry.group(1) or "永久" in expiry.group(1)):
            result["is_expired"] = False

    return {"success": True, "data": result} if result else {"success": False, "error": "解析失败"}

def validate_document(doctype, image_path, compare_name=None):
    """验证证件"""
    if doctype == "idcard":
        prompt = '''请仔细识别这张身份证照片中的所有信息，直接返回JSON格式，不要其他内容：
{
  "name": "身份证上的姓名",
  "id_number": "身份证号码",
  "gender": "性别",
  "birth_date": "出生日期",
  "expiry_date": "证件有效期（格式如2025-01-01或长期）",
  "is_expired": true或false（判断是否已过期），
  "nationality": "国籍"
}'''
    elif doctype == "business_license":
        prompt = '''请仔细识别这张营业执照照片中的所有信息，直接返回JSON格式，不要其他内容：
{
  "company_name": "企业名称",
  "unified_credit_code": "统一社会信用代码",
  "registered_capital": "注册资本",
  "legal_representative": "法定代表人",
  "establish_date": "成立日期",
  "expiry_date": "营业期限（格式如2025-01-01或长期）",
  "is_expired": true或false（判断是否已过期）
}'''
    else:
        return {"success": False, "error": "不支持的证件类型"}

    # 调用通义千问VL
    result = call_qwen_vision(image_path, prompt)
    if not result.get("success"):
        return result

    # 解析响应
    if doctype == "idcard":
        parsed = parse_idcard_response(result["text"])
    else:
        parsed = parse_business_license_response(result["text"])

    if not parsed.get("success"):
        return parsed

    extracted = parsed.get("data", {})

    # 检查是否过期
    issues = []
    if extracted.get("is_expired"):
        issues.append("证件已过期，请提供有效证件")

    # 匹配名称
    if compare_name and extracted.get("name"):
        if compare_name != extracted.get("name"):
            issues.append(f"提交的证件姓名【{extracted['name']}】与登记信息【{compare_name}】不符")

    if compare_name and extracted.get("company_name"):
        comp_name = extracted.get("company_name", "")
        # 简单匹配：检查是否包含对方
        if compare_name not in comp_name and comp_name not in compare_name:
            issues.append(f"提交的企业名称【{comp_name}】与登记信息【{compare_name}】不符")

    return {
        "success": True,
        "doctype": doctype,
        "extracted": extracted,
        "matched": len(issues) == 0,
        "issues": issues
    }

def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False,
            "error": "用法: python3 validate_document.py <证件类型:idcard|business_license> <图片路径> [对比名称]"
        }, ensure_ascii=False, indent=2))
        return

    doctype = sys.argv[1]
    image_path = sys.argv[2]
    compare_name = sys.argv[3] if len(sys.argv) > 3 else None

    result = validate_document(doctype, image_path, compare_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()