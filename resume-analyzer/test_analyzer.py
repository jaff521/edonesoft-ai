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

def run_test():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.dirname(current_dir)
    env = load_env(os.path.join(skills_dir, '.env'))

    api_key = env.get('DASHSCOPE_API_KEY')
    api_base = env.get('DASHSCOPE_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    model = 'qwen-plus'

    if not api_key:
        print("Error: DASHSCOPE_API_KEY not found in .env")
        return

    # 读取 Prompts
    with open(os.path.join(current_dir, 'AGENTS.md'), 'r', encoding='utf-8') as f:
        agents_content = f.read()
    with open(os.path.join(current_dir, 'SOUL.md'), 'r', encoding='utf-8') as f:
        soul_content = f.read()

    system_prompt = f"{agents_content}\n\n# 行为准则与心智要求\n{soul_content}"

    # 测试用例 1：高匹配度，包含附加条件得分
    test_case_1 = """
岗位信息：
- 岗位名称：高级前端开发工程师
- 职责：开发企业级管理系统的前端核心模块，优化渲染效率。
- 任职要求：本科及以上学历，计算机相关专业；5年以上前端开发经验；熟练掌握 React/Vue，有 Webpack/Vite 性能优化经验；
- 薪资范围：20-30K
- 工作地点：上海

候选人简历：
- 基本信息：陈大前端 | 男 | 30岁 | 本科 | 上海交通大学计算机系 | 7年前端工作经验
- 期望职位：高级前端开发工程师
- 期望薪资：25k
- 期望城市：上海
- 专业技能：熟练使用 React 及其生态，掌握 Vite 打包调优；熟悉 Webpack 插件编写，解决过大型页面重绘重排导致的性能瓶颈；
- 过往经历：在某头部电商公司任前端架构师，单份工作在职均超过3年。
- 自我评价：沟通顺畅，擅长跨团队协作。

聊天记录：
HR：“你好，我们这个岗位偶尔需要配合版本上线进行一些合理的加班，请问您这边可以接受吗？”
陈大前端：“可以的，我理解发版上线的需要，偶尔加班没问题。”
HR：“另外我们需要在1个月内到岗，您目前是离职状态吗？”
陈大前端：“是的，我已经离职了，随时能到岗，1个月内绝对没问题。”
"""

    # 测试用例 2：硬性条件不满足（缺证书）且总得分低（< 60）
    test_case_2 = """
岗位信息：
- 岗位名称：特种高空作业电工
- 职责：负责工厂高空高压电力设备的日常维护与紧急抢修。
- 任职要求：持有【高压电工特种作业操作证】（硬性条件，有一项不满足即不符合安全操作要求）；大专及以上学历；2年以上相关经验。
- 薪资范围：8-10K
- 工作地点：上海

候选人简历：
- 基本信息：王低电 | 男 | 22岁 | 中专 | 某职业中学汽修专业 | 1年电工助手经历
- 期望职位：低压电工/学徒
- 期望薪资：5k
- 期望城市：上海
- 专业技能：会接线、排查家用电器故障，熟悉汽修电路。
- 过往经历：在物业公司做过1年低压电工助手，工作跳槽频繁（3次，每次3个月左右）。
- 自我评价：人老实肯干。

聊天记录：
HR：“你好，由于我们的岗位是特种高空高压电工作业，国家法规要求必须持有【高压电工特种作业操作证】。请问你持有这个证件吗？”
王低电：“我没有高压电工证，我只有一个低压电工本，但是高空接线我也干过，不需要那个证也可以干活吧？”
HR：“这个是安全硬性指标，高压操作必须有证的。另外请问如果工作需要，能接受三班倒吗？”
王低电：“三班倒我接受不了，我只能上白班。”
"""

    # 测试用例 3：无意向用例
    test_case_3 = """
岗位信息：
- 岗位名称：销售经理
- 职责：开发新客户，维护老客户。
- 任职要求：大专及以上学历；1年以上销售经验。
- 薪资范围：10-15K
- 工作地点：上海

候选人简历：
- 基本信息：张经理 | 男 | 28岁 | 本科 | 3年大客户销售经验
- 期望职位：销售总监/经理
- 期望薪资：12k
- 期望城市：上海

聊天记录：
HR：“你好，看了你的简历，觉得你和我们的销售经理岗位很契合，不知道你最近看新机会吗？”
张经理：“你好，谢谢联系，不过我已经拿到另一家大厂的 Offer 并且签了三方了，暂时不考虑新的机会了，非常抱歉。”
"""

    cases = [
        ("高匹配度测试用例", test_case_1, "优秀"),
        ("低匹配与硬性缺失测试用例", test_case_2, "不匹配"),
        ("无意向测试用例", test_case_3, "无意向")
    ]

    for title, case, expected_grade in cases:
        print("\n" + "="*60)
        print(f"开始模拟测试：{title}")
        print("="*60)

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
            print("-" * 60)

            # 提取 JSON 块
            match = re.search(r'```json\s*(.*?)\s*```', reply, re.DOTALL)
            json_str = match.group(1) if match else reply
            
            try:
                result = json.loads(json_str)
                print("✅ JSON 解析成功！开始校验分数逻辑与标签：")
                
                total = result.get("scoring_rule", {}).get("total_score", 0)
                grade = result.get("scoring_rule", {}).get("grade", "")
                
                basic_score = result.get("basic_conditions", {}).get("actual_score", 0)
                basic_items = result.get("basic_conditions", {}).get("items", [])
                basic_sum = sum([item.get("score", 0) for item in basic_items])
                
                soft_score = result.get("soft_skills", {}).get("actual_score", 0)
                soft_items = result.get("soft_skills", {}).get("items", [])
                soft_sum = sum([item.get("score", 0) for item in soft_items])
                
                add_score = result.get("additional_conditions", {}).get("actual_score", 0)
                add_items = result.get("additional_conditions", {}).get("items", [])
                add_sum = sum([item.get("score", 0) for item in add_items])
                
                print(f"- 匹配等级(grade): {grade} (预期: {expected_grade})")
                print(f"- 声明的基础得分: {basic_score}, items之和: {basic_sum}")
                print(f"- 声明的软性得分: {soft_score}, items之和: {soft_sum}")
                print(f"- 声明的附加得分: {add_score}, items之和: {add_sum}")
                print(f"- 声明的总得分: {total}, 理论总得分(min(100, basic + soft + add)): {min(100.0, basic_score + soft_score + add_score)}")

                is_valid = True
                if abs(basic_score - basic_sum) > 0.01:
                    print("❌ 错误：基础条件声明得分与 items 之和不匹配！")
                    is_valid = False
                if abs(soft_score - soft_sum) > 0.01:
                    print("❌ 错误：软性条件声明得分与 items 之和不匹配！")
                    is_valid = False
                if abs(add_score - add_sum) > 0.01:
                    print("❌ 错误：附加条件声明得分与 items 之和不匹配！")
                    is_valid = False
                if abs(total - min(100.0, basic_score + soft_score + add_score)) > 0.01:
                    print("❌ 错误：total_score 与三部分累加上限值不匹配！")
                    is_valid = False
                if grade != expected_grade:
                    # 如果预期是"不匹配"，实际可以是"不匹配"；如果是"优秀"，实际也可以是"优秀"等
                    if expected_grade == "不匹配" and grade != "不匹配":
                        print(f"❌ 错误：预期匹配评级为 '不匹配'，实际输出为 '{grade}'！")
                        is_valid = False
                    elif expected_grade == "无意向" and grade != "无意向":
                        print(f"❌ 错误：预期匹配评级为 '无意向'，实际输出为 '{grade}'！")
                        is_valid = False
                    elif expected_grade == "优秀" and grade not in ["优秀", "良好"]:
                        print(f"❌ 错误：预期匹配评级为优秀，实际输出为 '{grade}'！")
                        is_valid = False

                # 检查 highlights, improvements, suggestions 长度
                h_len = len(result.get("highlights", []))
                i_len = len(result.get("improvements", []))
                s_len = len(result.get("suggestions", []))
                if h_len < 3 or i_len < 3 or s_len < 3:
                    print(f"❌ 错误：亮点(个:{h_len})、改进(个:{i_len})、建议(个:{s_len})均必须至少3条！")
                    is_valid = False

                if is_valid:
                    print("✅ 该用例校验完全通过！")
                else:
                    print("❌ 该用例存在逻辑/数学校验错误。")

            except Exception as ex:
                print(f"❌ JSON 转换/读取字段出错: {ex}")

        except Exception as e:
            print(f"API 请求失败: {e}")

if __name__ == '__main__':
    run_test()
