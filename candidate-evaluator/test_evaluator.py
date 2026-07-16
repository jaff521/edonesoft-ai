import os
import json
import re
import requests

def load_env(env_path):
    env = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key_value = line.split('=', 1)
                    if len(key_value) == 2:
                        env[key_value[0].strip()] = key_value[1].strip()
    return env

def run_simulation():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.dirname(current_dir)
    env = load_env(os.path.join(skills_dir, '.env'))

    api_key = env.get('DASHSCOPE_API_KEY')
    api_base = env.get('DASHSCOPE_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    model = 'qwen-plus'  # 使用大语言模型进行文本打分匹配评估

    if not api_key:
        print("Error: DASHSCOPE_API_KEY not found in .env file")
        return

    # 读取 AGENTS.md 和 SOUL.md 作为系统 Prompt
    with open(os.path.join(current_dir, 'AGENTS.md'), 'r', encoding='utf-8') as f:
        agents_content = f.read()
    with open(os.path.join(current_dir, 'SOUL.md'), 'r', encoding='utf-8') as f:
        soul_content = f.read()

    system_prompt = f"{agents_content}\n\n# 行为准则与心智要求\n{soul_content}"

    # 测试用例 1：高匹配度用例
    test_case_1 = """
岗位信息：
- 岗位名称：高级 Python 开发工程师
- 职责：负责高并发爬虫系统开发与 AI 智能体后台业务逻辑搭建。
- 任职要求：本科及以上学历，计算机相关专业；3年以上 Python 开发经验；熟练掌握 Django/FastAPI，有 MongoDB/Redis 优化经验；
- 薪资范围：15-25K
- 工作地点：上海

候选人简历：
- 基本信息：张小帅 | 男 | 29岁 | 本科 | 同济大学软件工程专业 | 5年工作经验
- 期望职位：Python 后端工程师
- 期望薪资：18k
- 期望城市：上海
- 专业技能：精通 Python 核心开发，熟悉 FastAPI/Django 框架；有高并发分布式爬虫项目实战经验；精通 Redis 缓存设计和 MongoDB 性能调优；
- 过往经历：2021-至今在某中型互联网公司任资深后端，独立重构核心数据流模块，单份工作在职均超过2年。
- 自我评价：工作细致负责，抗压能力强，沟通清晰。
"""

    # 测试用例 2：低匹配度用例
    test_case_2 = """
岗位信息：
- 岗位名称：高级 Python 开发工程师
- 职责：负责高并发爬虫系统开发与 AI 智能体后台业务逻辑搭建。
- 任职要求：本科及以上学历，计算机相关专业；3年以上 Python 开发经验；熟练掌握 Django/FastAPI，有 MongoDB/Redis 优化经验；
- 薪资范围：15-25K
- 工作地点：上海

候选人简历：
- 基本信息：李小华 | 女 | 24岁 | 大专 | 某艺术学院视觉传达专业 | 1年工作经验
- 期望职位：新媒体运营/助理
- 期望薪资：6k
- 期望城市：杭州
- 专业技能：熟练使用剪映、PS，熟悉公众号推文排版，了解基础 Python 语法（写过简单的网页爬虫）；
- 过往经历：2025年毕业后在某网店做新媒体文案策划3个月，毕业前实习过半年。
- 自我评价：学习能力强，性格开朗。
"""

    cases = [
        ("高匹配度测试用例", test_case_1),
        ("低匹配度测试用例", test_case_2)
    ]

    for title, case in cases:
        print("\n" + "="*50)
        print(f"开始模拟测试：{title}")
        print("="*50)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": case}
            ],
            "temperature": 0.1
        }

        try:
            url = f"{api_base}/chat/completions"
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            reply = res_json['choices'][0]['message']['content'].strip()

            print("模型原始回复：")
            print(reply)
            print("-" * 50)

            # 解析并验证 JSON 格式
            match = re.search(r'```json\s*(.*?)\s*```', reply, re.DOTALL)
            json_str = match.group(1) if match else reply
            
            try:
                result = json.loads(json_str)
                print("JSON 解析成功！开始校验分数逻辑：")
                
                total = result.get("totalScore", None)
                print(f"- 输出的总得分: {total}")
                
                is_valid = True
                if total is None:
                    print("❌ 错误：输出结果中未包含 totalScore 字段！")
                    is_valid = False
                elif not isinstance(total, (int, float)):
                    print(f"❌ 错误：totalScore 字段不是数值类型！实际类型为: {type(total)}")
                    is_valid = False
                elif total < 0 or total > 100:
                    print(f"❌ 错误：totalScore 数值超出合理区间 [0, 100]！实际数值: {total}")
                    is_valid = False
                
                if is_valid:
                    print("✅ 校验通过：输出的 JSON 符合单一 totalScore 的精简格式规范！")
                else:
                    print("❌ 校验失败。")
                    
            except Exception as ex:
                print(f"❌ JSON 解析失败: {ex}")

        except Exception as e:
            print(f"请求失败: {e}")

if __name__ == '__main__':
    run_simulation()
