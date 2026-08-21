#!/usr/bin/env python3
"""
统一企业客服视觉图片处理器 (Universal Vision Image Processor)
自动分类与识别：身份证(idcard)、营业执照(business_license)、发票开票截图(invoice)

用法:
  # 自动检测图片类型并识别 (推荐)
  python3 image_processor.py "/path/to/image.jpg"
  python3 image_processor.py "https://example.com/img1.png" "https://example.com/img2.png"

  # 显式指定类型（跳过自动分类，支持对比名称）
  python3 image_processor.py --type idcard "/path/to/idcard.jpg" "张三"
  python3 image_processor.py --type business_license "/path/to/license.jpg" "上海星辰科技有限公司"
  python3 image_processor.py --type invoice "/path/to/invoice1.jpg" "/path/to/invoice2.png"
"""

import sys
import os
import re
import json
import base64
import argparse
import tempfile
from urllib.parse import urlparse
import requests
from typing import Dict, Any, List, Optional, Tuple

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

DASHSCOPE_API = os.getenv("DASHSCOPE_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
VISION_MODEL = os.getenv("DASHSCOPE_VISION_MODEL", "qwen-vl-max")


def is_remote_url(path_or_url: str) -> bool:
    parsed = urlparse(str(path_or_url))
    return parsed.scheme in {"http", "https"}


def guess_file_suffix(path_or_url: str, content_type: str = "") -> str:
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


def materialize_image_input(path_or_url: str) -> Tuple[str, Optional[str]]:
    """如果输入是远程 URL，将其安全下载到本地临时文件；否则返回原路径。"""
    if not is_remote_url(path_or_url):
        if not os.path.exists(path_or_url):
            raise FileNotFoundError(f"本地图片文件不存在: {path_or_url}")
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


def call_dashscope_vision(image_path: str, prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
    """底层通用 DashScope Vision 接口调用"""
    if not API_KEY:
        return {"success": False, "error": "未配置 DASHSCOPE_API_KEY 环境变量"}

    local_path, temp_path = None, None
    try:
        local_path, temp_path = materialize_image_input(image_path)
        with open(local_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        return {"success": False, "error": f"无法读取图片 ({str(e)})"}
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ],
        "max_tokens": max_tokens
    }

    try:
        resp = requests.post(f"{DASHSCOPE_API}/chat/completions", headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return {"success": False, "error": f"Vision API 返回 HTTP 状态码 {resp.status_code}"}

        resp_data = resp.json()
        if "choices" not in resp_data or not resp_data["choices"]:
            return {"success": False, "error": f"Vision API 未返回有效内容: {resp_data}"}

        text = resp_data["choices"][0]["message"]["content"]
        return {"success": True, "text": text}
    except Exception as e:
        return {"success": False, "error": f"Vision API 调用失败: {str(e)}"}


def classify_image(image_path: str) -> str:
    """使用视觉大模型自动分类图片类型：idcard | business_license | invoice | unknown"""
    prompt = """请分析这张图片的类型，仅输出以下四个字符串之一，绝对不要输出任何其他多余字符：
- idcard (如果图片是中华人民共和国居民身份证的正或反面照片)
- business_license (如果图片是企业营业执照或个体工商户营业执照照片)
- invoice (如果图片是发票联、开票申请单、费用结算明细表、销售清单、收据或包含商品开票明细列表的表格截图)
- unknown (如果不属于上述任何一种)
"""
    res = call_dashscope_vision(image_path, prompt, max_tokens=10)
    if not res.get("success"):
        return "unknown"

    raw = res.get("text", "").strip().lower()
    if "idcard" in raw:
        return "idcard"
    elif "business_license" in raw or "license" in raw:
        return "business_license"
    elif "invoice" in raw or "bill" in raw:
        return "invoice"
    return "unknown"


# ==================== 1. 身份证 (ID Card) 识别逻辑 ====================

def parse_idcard_json(text: str) -> Dict[str, Any]:
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass

    # 正则降级提炼
    result = {}
    name = re.search(r'["`]?name["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    id_number = re.search(r'["`]?id_number["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    expiry = re.search(r'["`]?expiry_date["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    side = re.search(r'["`]?side["`]?[:：]\s*["`]?(front|back)["`]?', text, re.I)
    issuing_auth = re.search(r'["`]?issuing_authority["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    address = re.search(r'["`]?address["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)

    if name: result["name"] = name.group(1).strip()
    if id_number: result["id_number"] = id_number.group(1).strip()
    if expiry: result["expiry_date"] = expiry.group(1).strip()
    if side: result["side"] = side.group(1).strip()
    if issuing_auth: result["issuing_authority"] = issuing_auth.group(1).strip()
    if address: result["address"] = address.group(1).strip()
    return result


def process_idcard(image_path: str, compare_name: Optional[str] = None) -> Dict[str, Any]:
    prompt = '''请仔细识别这张身份证照片中的所有信息，直接返回 JSON 格式：
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

    res = call_dashscope_vision(image_path, prompt)
    if not res.get("success"):
        return res

    extracted = parse_idcard_json(res["text"])
    issues = []

    if extracted.get("is_expired") is True:
        issues.append("证件已过期，请提供有效证件")

    if not extracted.get("name") and extracted.get("side") == "front":
        issues.append("无法识别证件姓名，请确保图片清晰完整")

    if compare_name and extracted.get("name"):
        if compare_name.strip() != extracted["name"].strip():
            issues.append(f"提交的证件姓名【{extracted['name']}】与登记信息【{compare_name}】不符")

    return {
        "success": True,
        "imageType": "idcard",
        "doctype": "idcard",
        "extracted": extracted,
        "matched": len(issues) == 0,
        "issues": issues
    }


# ==================== 2. 营业执照 (Business License) 识别逻辑 ====================

def parse_license_json(text: str) -> Dict[str, Any]:
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass

    result = {}
    company_name = re.search(r'["`]?company_name["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    credit_code = re.search(r'["`]?unified_credit_code["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)
    legal_rep = re.search(r'["`]?legal_representative["`]?[:：]\s*["`]?([^["`\n,}]+)["`]?', text, re.I)

    if company_name: result["company_name"] = company_name.group(1).strip()
    if credit_code: result["unified_credit_code"] = credit_code.group(1).strip()
    if legal_rep: result["legal_representative"] = legal_rep.group(1).strip()
    return result


def process_business_license(image_path: str, compare_name: Optional[str] = None) -> Dict[str, Any]:
    prompt = '''请仔细识别这张营业执照照片中的所有信息，直接返回 JSON 格式：
{
  "company_name": "企业名称",
  "unified_credit_code": "统一社会信用代码",
  "registered_capital": "注册资本",
  "legal_representative": "法定代表人",
  "establish_date": "成立日期",
  "expiry_date": "营业期限（格式如2025-01-01或长期）",
  "is_expired": true或false（判断是否已过期）
}'''

    res = call_dashscope_vision(image_path, prompt)
    if not res.get("success"):
        return res

    extracted = parse_license_json(res["text"])
    issues = []

    if extracted.get("is_expired") is True:
        issues.append("营业执照已过期，请提供有效证件")

    if compare_name and extracted.get("company_name"):
        comp_name = extracted["company_name"]
        if compare_name not in comp_name and comp_name not in compare_name:
            issues.append(f"提交的企业名称【{comp_name}】与登记信息【{compare_name}】不符")

    return {
        "success": True,
        "imageType": "business_license",
        "doctype": "business_license",
        "extracted": extracted,
        "matched": len(issues) == 0,
        "issues": issues
    }


# ==================== 3. 发票 / 开票申请单 (Invoice) 识别逻辑 ====================

def process_invoice_images(image_paths: List[str]) -> Dict[str, Any]:
    prompt = """你是一个专业的高精度发票与开票申请单 OCR 识别工具。
请仔细分析图片结构并提取开票要素数据：

结构识别指引：
1. 区分“购货单位”（买方/采购方）与“销货单位”（卖方/销售方）。
   - 注意：如果图片顶侧/左侧区域标注为“购货单位”或“买方”，其右侧对应的名称、纳税人识别号/税号为【买方/采购方】数据！
   - 如果对应区域内容为空，则填空字符串 ""。
2. 货物或应税劳务明细：
   - 提取商品/服务名称（若包含 *分类*货物名 格式请完整保留）、规格型号、单位、数量、单价、金额/含税金额、税率。
   - 排除全空行和合计/汇总行。
3. 清理数值格式：所有数值中的人民币符号（￥、$）、千分位逗号（,）必须去掉，转换为纯数字。

请严格输出格式良好的 JSON，示例如下：
{
  "buyerName": "购货单位名称",
  "buyerTaxNo": "购货单位纳税人识别号/统一社会信用代码",
  "sellerName": "销货单位名称",
  "sellerTaxNo": "销货单位纳税人识别号/统一社会信用代码",
  "detailList": [
    {
      "itemName": "货物或应税劳务名称",
      "spec": "规格型号",
      "unit": "计量单位",
      "quantity": 1,
      "unitPrice": 88980.00,
      "taxInclusiveAmount": 88980.00,
      "taxRate": "13%"
    }
  ]
}
"""

    all_details = []
    buyer_name, buyer_tax_no = "", ""
    seller_name, seller_tax_no = "", ""
    failed_count = 0
    err_msgs = []

    for img_input in image_paths:
        res = call_dashscope_vision(img_input, prompt)
        if not res.get("success"):
            failed_count += 1
            err_msgs.append(f"{os.path.basename(img_input)}: {res.get('error')}")
            continue

        raw_content = res.get("text", "")
        json_match = re.search(r'\{[\s\S]*\}', raw_content)
        if not json_match:
            failed_count += 1
            err_msgs.append(f"{os.path.basename(img_input)}: 解析 JSON 失败")
            continue

        try:
            parsed = json.loads(json_match.group())
            if not buyer_name and parsed.get("buyerName"):
                buyer_name = parsed.get("buyerName")
            if not buyer_tax_no and parsed.get("buyerTaxNo"):
                buyer_tax_no = parsed.get("buyerTaxNo")
            if not seller_name and parsed.get("sellerName"):
                seller_name = parsed.get("sellerName")
            if not seller_tax_no and parsed.get("sellerTaxNo"):
                seller_tax_no = parsed.get("sellerTaxNo")

            details = parsed.get("detailList", [])
            if isinstance(details, list):
                all_details.extend(details)
        except Exception as e:
            failed_count += 1
            err_msgs.append(f"{os.path.basename(img_input)}: JSON 异常 ({str(e)})")

    if failed_count == len(image_paths):
        return {
            "success": False,
            "imageType": "invoice",
            "error": f"所传发票图片识别全部失败: {'; '.join(err_msgs)}"
        }

    msg = f"成功识别 {len(image_paths) - failed_count}/{len(image_paths)} 张发票截图，提取 {len(all_details)} 条明细"
    if failed_count > 0:
        msg += f"（部分图片识别失败: {'; '.join(err_msgs)}）"

    return {
        "success": True,
        "imageType": "invoice",
        "buyerName": buyer_name,
        "buyerCreditCode": buyer_tax_no,
        "buyerTaxNo": buyer_tax_no,
        "sellerName": seller_name,
        "sellerTaxNo": seller_tax_no,
        "detailList": all_details,
        "message": msg
    }


# ==================== 主入口与路由逻辑 ====================

def process_images_auto(image_paths: List[str], compare_name: Optional[str] = None) -> Dict[str, Any]:
    """多图或单图自动分类处理"""
    if not image_paths:
        return {"success": False, "error": "未提供图片路径"}

    # 如果只有一张图片，先检测分类
    if len(image_paths) == 1:
        img = image_paths[0]
        img_type = classify_image(img)
        if img_type == "idcard":
            return process_idcard(img, compare_name)
        elif img_type == "business_license":
            return process_business_license(img, compare_name)
        elif img_type == "invoice":
            return process_invoice_images([img])
        else:
            return {
                "success": False,
                "imageType": "unknown",
                "error": "无法自动识别该图片的证件/单据类型，请确认图片是否清晰完整"
            }

    # 多张图片：优先检测第一张
    first_type = classify_image(image_paths[0])
    if first_type == "invoice":
        return process_invoice_images(image_paths)
    elif first_type in {"idcard", "business_license"}:
        # 多张身份证或营业执照：处理第一张并给出结果
        if first_type == "idcard":
            return process_idcard(image_paths[0], compare_name)
        else:
            return process_business_license(image_paths[0], compare_name)
    else:
        return {
            "success": False,
            "imageType": "unknown",
            "error": "无法识别所传图片的类型，请提供清晰的身份证、营业执照或发票截图"
        }


def main():
    parser = argparse.ArgumentParser(description="企业客服统一视觉图片处理器")
    parser.add_argument("images", nargs="*", help="图片路径或远程 URL 列表")
    parser.add_argument("--type", choices=["idcard", "business_license", "invoice"], help="显式指定图片类型（跳过自动分类）")
    parser.add_argument("--compare", help="对比名称（用于身份证姓名或企业名称校验）")

    # 兼容旧版的 positional 参数: validate_document.py <doctype> <image_path> [compare_name]
    args, unknown = parser.parse_known_args()

    # 处理旧版传参兼容性
    if len(sys.argv) >= 3 and sys.argv[1] in ["idcard", "business_license"]:
        doctype = sys.argv[1]
        img_path = sys.argv[2]
        comp_name = sys.argv[3] if len(sys.argv) > 3 else None
        if doctype == "idcard":
            res = process_idcard(img_path, comp_name)
        else:
            res = process_business_license(img_path, comp_name)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    image_inputs = args.images + unknown
    if not image_inputs:
        res = {
            "success": False,
            "error": "用法: python3 image_processor.py <图片路径或URL> [图片2 ...]\n可选参数: --type [idcard|business_license|invoice] --compare [对比名称]"
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    # 显式指定类型
    if args.type:
        if args.type == "idcard":
            res = process_idcard(image_inputs[0], args.compare)
        elif args.type == "business_license":
            res = process_business_license(image_inputs[0], args.compare)
        elif args.type == "invoice":
            res = process_invoice_images(image_inputs)
    else:
        # 自动识别分类
        res = process_images_auto(image_inputs, args.compare)

    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
