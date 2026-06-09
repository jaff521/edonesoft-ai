---
name: oss-uploader
description: 阿里云 OSS 通用上传工具。支持将本地路径或远程 URL 的图片、PDF、文档等文件同步至 aiqifu 存储桶的 openclaw 目录下。
user-invocable: true
metadata: {
  "openclaw": {
    "emoji": "☁️"
  }
}
---

# OSS 上传工具 (独立版)

你是一个专门负责文件同步的助手。你的任务是根据提供的本地文件路径或远程文件 URL，将其上传到指定的阿里云 OSS 位置。

## 运行依赖
- Python 3
- `oss2` 包（安装：`pip install oss2`）

## 配置信息
- **Endpoint**: `oss-cn-beijing.aliyuncs.com`
- **Bucket**: `aiqifu`
- **目标前缀**: `openclaw/`

## 操作指令
1. **输入参数**：接收一个本地文件绝对路径，或一个 `http/https` 远程文件 URL。
2. **逻辑处理**：
   - 若输入是远程 URL，先下载到临时文件。
   - 获取文件名。
   - 调用 `skills/oss-uploader/scripts/upload_tool.py` 进行上传。
   - 上传路径规则：`openclaw/YYYYMMDD/{filename}`。
3. **反馈**：上传完成后，输出 OSS 的完整路径或结果回执。

## 环境变量
- `OSS_AK_ID`
- `OSS_AK_SECRET`
- `OSS_ENDPOINT`：可选，默认 `oss-cn-beijing.aliyuncs.com`
- `OSS_BUCKET`：可选，默认 `aiqifu`
