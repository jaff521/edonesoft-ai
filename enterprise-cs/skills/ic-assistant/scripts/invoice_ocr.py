#!/usr/bin/env python3
"""
发票 OCR 识别适配层 (Invoice OCR Wrapper)
转调通用视觉图片处理器 image_processor.py
"""

import sys
import os
import json
from image_processor import process_invoice_images

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "用法: python3 invoice_ocr.py <图片路径或URL> [图片2 ...]"
        }, ensure_ascii=False, indent=2))
        return

    image_paths = sys.argv[1:]
    res = process_invoice_images(image_paths)
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
