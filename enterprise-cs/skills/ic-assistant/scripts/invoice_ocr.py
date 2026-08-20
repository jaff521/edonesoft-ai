#!/usr/bin/env python3
"""
发票 / 开票申请单截图 OCR 识别脚本
输入：单张或多张发票/开票申请单图片路径或 URL
输出：从图片中提取的标准开票要素 JSON（销方、购方、开票明细数组）

用法:
  python3 invoice_ocr.py "/path/to/invoice_image.jpg"
  python3 invoice_ocr.py "https://example.com/invoice.png"
  python3 invoice_ocr.py "/path/to/img1.jpg" "/path/to/img2.png"
"""

import sys
import os
import re
import json
import base64
import tempfile
from urllib.parse import urlparse
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
    return ".jpg"


def materialize_image_input(path_or_url: str):
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


def call_vision_ocr(image_path: str) -> Dict[str, Any]:
    """调用 DashScope Vision 视觉模型精准识别单张发票/开票申请单图片。"""
    if not API_KEY:
        return {"success": False, "error": "未配置 DASHSCOPE_API_KEY 环境变量"}

    local_image_path, temp_path = materialize_image_input(image_path)
    try:
        with open(local_image_path, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        return {"success": False, "error": f"无法读取图片文件 ({str(e)})"}
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

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
        "max_tokens": 1024
    }

    try:
        resp = requests.post(f"{DASHSCOPE_API}/chat/completions", headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return {"success": False, "error": f"Vision API 返回 HTTP 状态码 {resp.status_code}"}

        resp_data = resp.json()
        if "choices" not in resp_data or not resp_data["choices"]:
            return {"success": False, "error": f"Vision API 未返回有效内容: {resp_data}"}

        raw_content = resp_data["choices"][0]["message"]["content"]

        # 匹配提取 JSON 字符串
        json_match = re.search(r'\{[\s\S]*\}', raw_content)
        if not json_match:
            return {"success": False, "error": f"识别结果未能提取出合法 JSON: {raw_content}"}

        parsed = json.loads(json_match.group())
        parsed["success"] = True
        return parsed

    except Exception as e:
        return {"success": False, "error": f"调用 DashScope Vision 接口失败: {str(e)}"}


def main():
    if len(sys.argv) < 2:
        res = {
            "success": False,
            "error": "用法: python3 invoice_ocr.py <图片路径或URL> [图片2] ..."
        }
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    image_inputs = sys.argv[1:]
    all_details = []
    buyer_name = ""
    buyer_tax_no = ""
    seller_name = ""
    seller_tax_no = ""
    failed_count = 0
    err_msgs = []

    for img_input in image_inputs:
        res = call_vision_ocr(img_input)
        if not res.get("success"):
            failed_count += 1
            err_msgs.append(f"{os.path.basename(img_input)}: {res.get('error')}")
            continue

        if not buyer_name and res.get("buyerName"):
            buyer_name = res.get("buyerName")
        if not buyer_tax_no and res.get("buyerTaxNo"):
            buyer_tax_no = res.get("buyerTaxNo")
        if not seller_name and res.get("sellerName"):
            seller_name = res.get("sellerName")
        if not seller_tax_no and res.get("sellerTaxNo"):
            seller_tax_no = res.get("sellerTaxNo")

        details = res.get("detailList", [])
        if isinstance(details, list):
            all_details.extend(details)

    if failed_count == len(image_inputs):
        result = {
            "success": False,
            "message": f"所传图片识别全部失败: {'; '.join(err_msgs)}"
        }
    else:
        msg = f"成功识别 {len(image_inputs) - failed_count}/{len(image_inputs)} 张发票截图，共提取 {len(all_details)} 条明细"
        if failed_count > 0:
            msg += f"（部分图片识别失败: {'; '.join(err_msgs)}）"

        result = {
            "success": True,
            "buyerName": buyer_name,
            "buyerCreditCode": buyer_tax_no,
            "buyerTaxNo": buyer_tax_no,
            "sellerName": seller_name,
            "sellerTaxNo": seller_tax_no,
            "detailList": all_details,
            "message": msg
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
