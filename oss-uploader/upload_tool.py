import os
import sys
import datetime
try:
    import oss2
except ImportError:
    print("Error: Missing dependency 'oss2'. Please wait for auto-install or run 'pip install oss2'.")
    sys.exit(1)

def main():
    # 1. 参数检查
    if len(sys.argv) < 2:
        print("Usage: python3 upload_tool.py <local_file_path>")
        return

    local_path = sys.argv[1]
    if not os.path.exists(local_path):
        print(f"Error: File {local_path} not found.")
        return

    # 2. 鉴权信息获取 (从环境变量读取)
    ak_id = os.getenv('OSS_AK_ID')
    ak_secret = os.getenv('OSS_AK_SECRET')
    endpoint = 'oss-cn-beijing.aliyuncs.com'
    bucket_name = 'aiqifu'

    if not ak_id or not ak_secret:
        print("Error: AccessKey environment variables not set.")
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
        print(f"Successfully uploaded to: {remote_path}")
    except Exception as e:
        print(f"Failed to upload: {str(e)}")

if __name__ == "__main__":
    main()