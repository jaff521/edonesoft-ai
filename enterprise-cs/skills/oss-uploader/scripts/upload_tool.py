import os
import sys
import datetime
import tempfile
from urllib.parse import urlparse
import requests
try:
    import oss2
except ImportError:
    print("Error: Missing dependency 'oss2'. Please wait for auto-install or run 'pip install oss2'.")
    sys.exit(1)


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
    return ".bin"


def materialize_input_file(path_or_url):
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

def main():
    # 1. 参数检查
    if len(sys.argv) < 2:
        print("Usage: python3 upload_tool.py <local_file_path_or_url>")
        return

    source_input = sys.argv[1]
    temp_path = None
    try:
        local_path, temp_path = materialize_input_file(source_input)
    except Exception as e:
        print(f"Error: Failed to download remote file: {str(e)}")
        return

    if not os.path.exists(local_path):
        print(f"Error: File {local_path} not found.")
        return

    # 2. 鉴权信息获取 (从环境变量读取)
    ak_id = os.getenv('OSS_AK_ID')
    ak_secret = os.getenv('OSS_AK_SECRET')
    endpoint = os.getenv('OSS_ENDPOINT', 'oss-cn-beijing.aliyuncs.com')
    bucket_name = os.getenv('OSS_BUCKET', 'aiqifu')
    public_base = f"https://{bucket_name}.{endpoint}"

    if not ak_id or not ak_secret:
        print("Error: OSS credentials not configured. Set OSS_AK_ID and OSS_AK_SECRET.")
        return

    # 3. 执行上传
    auth = oss2.Auth(ak_id, ak_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    filename = os.path.basename(local_path)
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    # 构造 OSS 路径: openclaw/日期/文件名
    remote_path = f"openclaw/{date_str}/{filename}"

    try:
        bucket.put_object_from_file(remote_path, local_path)
        print(f"Successfully uploaded to: {public_base}/{remote_path}")
    except Exception as e:
        print(f"Failed to upload: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
