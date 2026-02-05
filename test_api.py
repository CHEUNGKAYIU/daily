import json
from dashscope import Application

# 加载配置
with open('config.json', 'r') as f:
    config = json.load(f)

api_key = config['API_KEY']
app_id = config['APP_ID']

# 测试问题
test_prompt = """题目: 以下哪首歌没得到过十大劲歌金曲的金曲金奖？
选项:
a1: Shall We Talk-陈奕迅
a2: 明年今日-陈奕迅
a3: K歌之王-陈奕迅
a4: 少女的祈祷-杨千嬅
请选择正确答案，只返回选项ID（如a1、a2、a3、a4）："""

print("开始测试阿里云API...")
print(f"API_KEY: {api_key[:20]}...")
print(f"APP_ID: {app_id}")
print("-" * 50)

try:
    response = Application.call(
        api_key=api_key,
        app_id=app_id,
        prompt=test_prompt,
        timeout=60
    )
    
    print("API调用成功！")
    print(f"响应: {response}")
    if response:
        print(f"答案: {response.output.text}")
    
except Exception as e:
    print(f"API调用失败: {e}")
    print(f"错误类型: {type(e).__name__}")
