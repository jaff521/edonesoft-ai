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
import tempfile
from urllib.parse import urlparse
import requests
import os

DASHSCOPE_API = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
VISION_MODEL = os.getenv("DASHSCOPE_VISION_MODEL", "qwen-vl-max")


def is_remote_url(path_or_url):
    parsed = urlparse(str(path_or_url))
    return parsed.scheme in {"http", "https"}


def guess_file_suffix(path_or_url, content_type=""):
    parsed = urlparse(str(path_or_url))
    filename = os.path.basename(parsed.path)
    _, ext = os.path.splitext(filename)
    if ext:
        return ext

    if "png" in content_type:
        return ".png"
    if "webp" in content_type:
        return ".webp"
    if "pdf" in content_type:
        return ".pdf"
    return ".jpg"


def materialize_image_input(path_or_url):
    if not is_remote_url(path_or_url):
        return path_or_url, None

    response = requests.get(path_or_url, stream=True, timeout=30)
    response.raise_for_status()

    suffix = guess_file_suffix(path_or_url, response.headers.get("Content-Type", "").lower())
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                temp_file.write(chunk)
    finally:
        temp_file.close()

    return temp_file.name, temp_file.name

def call_qwen_vision(image_path, prompt, model=None):
    """调用阿里云通义千问视觉模型"""
    if not API_KEY:
        return {"success": False, "error": "未配置 DashScope API Key，请检查 DASHSCOPE_API_KEY 环境变量"}

    local_image_path = image_path
    temp_path = None
    try:
        local_image_path, temp_path = materialize_image_input(image_path)
        with open(local_image_path, 'rb') as f:
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
        "model": model or VISION_MODEL,
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
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

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
    issuing_auth = re.search(r'["`]?issuing_authority["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    side = re.search(r'["`]?side["`]?[:：]\s*["`]?(front|back)["`]?', text, re.I)
    address = re.search(r'["`]?address["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)

    result = {}
    if name: result["name"] = name.group(1).strip()
    if id_number: result["id_number"] = id_number.group(1).strip()
    if expiry: result["expiry_date"] = expiry.group(1).strip()
    if issuing_auth: result["issuing_authority"] = issuing_auth.group(1).strip()
    if side: result["side"] = side.group(1).strip()
    if address: result["address"] = address.group(1).strip()

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
  "name": "身份证上的姓名（人像面可见，国徽面无此字段则留空）",
  "id_number": "身份证号码（人像面可见，国徽面无此字段则留空）",
  "gender": "性别",
  "birth_date": "出生日期",
  "address": "住址（人像面可见，国徽面无此字段则留空）",
  "expiry_date": "证件有效期（格式如2025-01-01或长期）",
  "is_expired": true或false（判断是否已过期），
  "nationality": "国籍",
  "issuing_authority": "签发机关/发证机关（国徽面可见，人像面无此字段则留空）",
  "side": "front或back（判断是人像面front还是国徽面back）"
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

    # 验证姓名是否识别成功
    if not extracted.get("name"):
        issues.append("无法识别证件姓名，请确保图片清晰完整")
    elif compare_name and extracted.get("name"):
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
            "error": "用法: python3 validate_document.py <证件类型:idcard|business_license> <图片路径或URL> [对比名称]"
        }, ensure_ascii=False, indent=2))
        return

    doctype = sys.argv[1]
    image_path = sys.argv[2]
    compare_name = sys.argv[3] if len(sys.argv) > 3 else None

    result = validate_document(doctype, image_path, compare_name)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
