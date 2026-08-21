#!/usr/bin/env python3
"""
证件验证器适配层 (Validate Document Wrapper)
转调通用视觉图片处理器 image_processor.py
"""

import sys
import os
import json
from image_processor import process_idcard, process_business_license

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

    if doctype == "idcard":
        res = process_idcard(image_path, compare_name)
    elif doctype == "business_license":
        res = process_business_license(image_path, compare_name)
    else:
        res = {"success": False, "error": f"不支持的证件类型: {doctype}"}

    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
