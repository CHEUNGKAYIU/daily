import requests
from bs4 import BeautifulSoup
import re
import os
import argparse
import json
import time
from PIL import Image
from io import BytesIO
import ddddocr
import base64
import shutil
from datetime import datetime, timedelta, timezone
from dashscope import Application

username = None
password = None
pushplus_token = None
api_key = None
app_id = None
address = None

# 全局日志收集器
log_messages = []

def add_log(message):
    """添加日志到推送消息中"""
    global log_messages
    log_messages.append(message)
    print(message)

def save_response_on_failure(response, step_name):
    """在失败时保存response内容到本地"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"failure_{step_name}_{timestamp}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"失败时的{step_name}响应已保存到: {filename}")
    except Exception as e:
        print(f"保存{step_name}响应失败: {e}")

def random_wait():
    """随机等待30-60秒，模拟真人操作"""
    import random
    wait_time = random.randint(10, 13)
    print(f"[调试] 随机等待 {wait_time} 秒...")
    time.sleep(wait_time)

class RequestsSession:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Ch-Ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1'
        })
        self.cookie_file = 'session_cookies.json'
        self.load_cookies()
    
    def load_cookies(self):
        """不加载cookies，每次都重新获取"""
        print("[调试] 跳过cookies加载，每次重新获取")
        # 删除旧的cookies文件
        if os.path.exists(self.cookie_file):
            try:
                os.remove(self.cookie_file)
                print("[调试] 已删除旧的cookies文件")
            except Exception as e:
                print(f"[调试] 删除cookies文件失败: {e}")
    
    def save_cookies(self):
        """保存cookies到文件"""
        try:
            cookies_dict = {}
            for cookie in self.session.cookies:
                cookies_dict[cookie.name] = cookie.value
            with open(self.cookie_file, 'w') as f:
                json.dump(cookies_dict, f)
            print(f"[调试] 已保存 {len(cookies_dict)} 个cookies")
        except Exception as e:
            print(f"[调试] 保存cookies失败: {e}")
    
    def print_cookies(self):
        """打印当前cookies信息"""
        cookies = list(self.session.cookies)
        print(f"[调试] 当前cookies数量: {len(cookies)}")
        for cookie in cookies:
            print(f"[调试] Cookie: {cookie.name} = {cookie.value[:20]}...")
    
    def check_forum_cookies(self):
        """检查论坛相关的cookies"""
        forum_cookies = {}
        for cookie in self.session.cookies:
            if cookie.name.startswith('sNgB_2132_'):
                forum_cookies[cookie.name] = cookie.value
        print(f"[调试] 论坛cookies数量: {len(forum_cookies)}")
        for name, value in forum_cookies.items():
            print(f"[调试] 论坛Cookie: {name} = {value[:20]}...")
        return forum_cookies

def string_to_hex(text):
    """将字符串转换为十六进制，模拟JavaScript的stringToHex函数"""
    hex_val = ""
    for char in text:
        hex_val += format(ord(char), 'x')
    return hex_val

def verify(session):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[调试] 登录尝试 {attempt + 1}/{max_retries}")
            login_url = f"{address}/FORUM/member.php?mod=logging&action=login"
            
            # 获取登录页面
            response = session.get(login_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取所有隐藏字段
            hidden_fields = {}
            for input_tag in soup.find_all('input', type='hidden'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    hidden_fields[name] = value

            # 处理验证码
            verify_img = soup.find('img', class_='verifyimg')
            if verify_img:
                img_url = verify_img.get('src')
                if img_url.startswith('data:'):
                    base64_data = img_url.split(',')[1]
                    image_data = base64.b64decode(base64_data)
                    image = Image.open(BytesIO(image_data))

                    image.save("debug_verify_code.png")
                    print("[调试] 验证码图片已保存为 debug_verify_code.png")

                    print("[调试] 开始验证码识别...")
                    start_time = time.time()
                    
                    try:
                        # 使用ddddocr识别验证码
                        ocr = ddddocr.DdddOcr(show_ad=False)
                        code = ocr.classification(image_data)
                        
                        end_time = time.time()
                        print(f"[调试] 验证码识别完成，耗时: {end_time - start_time:.2f}秒")
                        # add_log(f"识别的验证码: '{code}'")
                        
                        # 验证是否为5位数字
                        if not (code.isdigit() and len(code) == 5):
                            print(f"[警告] 识别结果不是5位数字，使用默认值")
                            code = "12345"
                            
                    except Exception as e:
                        print(f"[错误] 验证码识别失败: {e}")
                        code = "12345"

                    # 三步验证流程处理
                    print(f"[调试] 原始验证码: {code}")
                    hex_code = string_to_hex(code.strip())
                    print(f"[调试] 十六进制验证码: {hex_code}")
                    
                    # 获得验证码后等待，模拟真人思考时间
                    random_wait()
                    
                    # 第一步：检查并获取security_session_verify cookie
                    security_session_verify = None
                    for cookie in session.cookies:
                        if cookie.name == 'security_session_verify':
                            security_session_verify = cookie.value
                            print(f"[调试] 找到security_session_verify: {security_session_verify}")
                            break
                    
                    if not security_session_verify:
                        print("[错误] 未找到security_session_verify cookie")
                        return False
                    
                    # 第二步：设置srcurl cookie
                    current_url = login_url
                    hex_url = string_to_hex(current_url)
                    session.cookies.set('srcurl', hex_url, path='/')
                    print(f"[调试] 设置srcurl cookie: {hex_url}")
                    
                    # 第三步：发送验证码到验证页面（带上security_session_verify和srcurl）
                    verify_url = f"{address}/forum/index.php?security_verify_img={hex_code}"
                    print(f"[调试] 跳转验证页面: {verify_url}")
                    
                    # 设置完整的请求头
                    verify_headers = {
                        'Referer': f'{address}/forum/index.php',
                        'Host': address.replace('https://', '').replace('http://', '')
                    }
                    
                    time.sleep(1)
                    response = session.get(verify_url, headers=verify_headers)
                    print(f"[调试] 验证页面响应状态: {response.status_code}")
                    
                    # 第四步：检查是否获得security_session_high_verify
                    security_session_high_verify = None
                    for cookie in session.cookies:
                        if cookie.name == 'security_session_high_verify':
                            security_session_high_verify = cookie.value
                            print(f"[调试] 获得security_session_high_verify: {security_session_high_verify}")
                            break
                    
                    if not security_session_high_verify:
                        print("[错误] 未获得security_session_high_verify，验证码可能错误")
                        continue  # 重试
                    
                    # 第五步：现在拥有3个必需的cookies，重新请求登录页面
                    print("[调试] 拥有完整的验证cookies，重新获取登录页面")
                    
                    # 确认当前拥有的所有cookies
                    required_cookies = ['security_session_verify', 'srcurl', 'security_session_high_verify']
                    print("[调试] 检查必需的cookies:")
                    for cookie_name in required_cookies:
                        cookie_found = False
                        for cookie in session.cookies:
                            if cookie.name == cookie_name:
                                print(f"[调试] ✓ {cookie_name}: {cookie.value[:20]}...")
                                cookie_found = True
                                break
                        if not cookie_found:
                            print(f"[调试] ✗ {cookie_name}: 未找到")
                    
                    time.sleep(2)
                    response = session.get(login_url)
                    print(f"[调试] 重新请求验证页面状态: {response.status_code}")
                    
                    # 保存响应体用于调试
                    # with open('debug_login_page_after_verify.html', 'w', encoding='utf-8') as f:
                    #     f.write(response.text)
                    # print("[调试] 验证后验证页面响应已保存到 debug_login_page_after_verify.html")
                    
                    # 输出响应体的前500字符用于快速查看
                    print(f"[调试] 响应体前500字符: {response.text[:500]}...")
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 验证是否成功进入登录页面（检查是否还有验证码）
                    verify_img_check = soup.find('img', class_='verifyimg')
                    if verify_img_check:
                        print("[调试] 页面仍有验证码，验证可能失败")
                        continue  # 重试
                    else:
                        print("[调试] 验证码验证成功，可以进行登录")
                        return True  # 验证成功，返回True
                    
                    # 重新提取隐藏字段
                    hidden_fields = {}
                    for input_tag in soup.find_all('input', type='hidden'):
                        name = input_tag.get('name')
                        value = input_tag.get('value', '')
                        if name:
                            hidden_fields[name] = value

        except Exception as e:
            print(f"[错误] 验证过程中出现异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return False
    return False

def login(session):
    """登录函数，在验证码验证成功后调用"""
    login_url = f"{address}/FORUM/member.php?mod=logging&action=login"
    
    # 获取登录页面
    response = session.get(login_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取formhash
    formhash_input = soup.find('input', {'name': 'formhash'})
    formhash = formhash_input.get('value') if formhash_input else ''
    
    # 提取loginhash
    loginhash_input = soup.find('input', {'name': 'loginhash'})
    loginhash = loginhash_input.get('value') if loginhash_input else ''
    
    print(f"[调试] 提取到formhash: {formhash}")
    print(f"[调试] 提取到loginhash: {loginhash}")
    
    # 构建正确的登录URL
    login_submit_url = f"{address}/FORUM/member.php?mod=logging&action=login&loginsubmit=yes&handlekey=login&loginhash={loginhash}&inajax=1"
    print(f"[调试] 登录提交URL: {login_submit_url}")
    
    # 构建登录表单数据
    login_data = {
        'formhash': formhash,
        'referer': 'https%3A%2F%2Fwww.easonfans.com%2FFORUM%2F',
        'loginfield': 'username',
        'username': username,
        'password': password,
        'questionid': '0',
        'answer': ''
    }
    
    print(f"[调试] 登录表单数据: {login_data}")
    
    # 设置登录请求头
    login_headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': login_url
    }
    
    # 提交登录
    response = session.post(login_submit_url, data=login_data, headers=login_headers)
    print(f"[调试] 登录提交响应状态: {response.status_code}")
    
    # 保存登录响应用于调试
    # with open('debug_login_submit_response.html', 'w', encoding='utf-8') as f:
    #     f.write(response.text)
    # print("[调试] 登录提交响应已保存到 debug_login_submit_response.html")
    
    # 检查是否登录成功
    if '欢迎您回来' in response.text:
        add_log("登录成功！")
        return True
    else:
        print("[调试] 登录失败")
        print(f"[调试] 登录响应内容: {response.text[:300]}...")
        save_response_on_failure(response, "login")
        return False

def signin(session):
    # 导航到签到页面
    url = f"{address}/forum/plugin.php?id=dsu_paulsign:sign"
    response = session.get(url)
    
    # 检查是否有徽章弹窗
    try:
        if 'fwin_badgewin_7ree' in response.text:
            print("徽章弹窗出现，准备领取徽章。")
            # 打开徽章领取页面
            badge_url = f"{address}/forum/plugin.php?id=badge_7ree:badge_7ree&code=1"
            badge_response = session.get(badge_url)
            
            # 模拟点击领取按钮
            soup = BeautifulSoup(badge_response.text, 'html.parser')
            badge_link = soup.find('a', href=re.compile(r'plugin\.php\?id=badge_7ree'))
            if badge_link:
                badge_href = badge_link.get('href')
                if not badge_href.startswith('http'):
                    badge_href = f"{address}/forum/" + badge_href
                session.get(badge_href)
                print("徽章领取成功！")
    except Exception:
        print("没有徽章弹窗。")
    
    # 重新导航到签到页面
    response = session.get(url)
    
    # 开始签到流程
    if '您今天已经签到过了或者签到时间还未开始' in response.text:
        add_log("今天已签到或签到未开始。")
        return
    
    try:
        # 获取页面表单数据
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取formhash
        formhash_input = soup.find('input', {'name': 'formhash'})
        formhash = formhash_input.get('value') if formhash_input else ''
        
        # 构建签到数据
        signin_data = {
            'formhash': formhash,
            'qdxq': 'kx',
            'qdmode': '3',
            'todaysay': '',
            'fastreply': '0'
        }
        
        # 签到请求URL
        signin_url = f"{address}/forum/plugin.php?id=dsu_paulsign:sign&operation=qiandao&infloat=1&inajax=1"
        
        # 提交签到
        response = session.post(signin_url, data=signin_data)
        
        # 检查签到结果
        if '签到成功' in response.text or '恭喜' in response.text:
            add_log("签到成功！")
        elif '您今天已经签到过了' in response.text:
            add_log("今天已签到。")
        else:
            add_log("签到失败。")
            save_response_on_failure(response, "signin")
            
    except Exception as e:
        print(f"签到过程中出现错误: {e}")
        add_log("签到失败。")

def question(session):
    base_url = f"{address}/forum/plugin.php?id=ahome_dayquestion:pop&infloat=yes&handlekey=pop&inajax=1&ajaxtarget=fwin_content_pop"

    try:
        response = session.get(base_url)

        time.sleep(1)

        # 检查是否已完成答题
        if '今日答题已完成' in response.text or '您今天已经答过题了' in response.text:
            add_log("今日答题已完成。")
            return

        # 开始答题流程
        question_count = 0
        max_questions = 3  # 设置最大答题数量防止无限循环
        
        while question_count < max_questions:
            response = session.get(base_url)
            time.sleep(1)
            
            # 检查是否还有题目
            if '今日答题已完成' in response.text or '您今天已经答过题了' in response.text:
                add_log("今日答题已完成。")
                break
                
            try:
                answer_question(session, question_count)
                question_count += 1
            except Exception as e:
                print(f"答题第{question_count + 1}题过程中出现错误: {e}")
                save_response_on_failure(response, f"question_{question_count}")
                time.sleep(5)
                continue
                
    except Exception as e:
        print(f"答题过程中出现错误: {e}")
        add_log("答题失败。")

def answer_question(session, question_number):
    base_url = f"{address}/forum/plugin.php?id=ahome_dayquestion:pop"
    response = session.get(base_url)
    print(response)
    # print("abcabcacbaca"+response.text)

    prompt = build_prompt(response.text)
    print("===============")
    print(prompt)
    label = get_answer_from_api(prompt)
    if not label or label.strip() == '':
        print("API 未返回结果，默认选择 a2")
        label = 'a2'

    # 标准化去除空格，并检查是否合法选项
    if label not in ['a1', 'a2', 'a3', 'a4']:
        print("API 返回结果不在合法选项中，默认选择 a2")
        label = 'a2'

    # 构建答题数据
    soup = BeautifulSoup(response.text, 'html.parser')
    answer_data = {}

    # 提取formhash
    formhash_input = soup.find('input', {'name': 'formhash'})
    if formhash_input:
        answer_data['formhash'] = formhash_input.get('value', '')

    # 找到对应的radio button并获取其value
    radio_input = soup.find('input', {'id': label, 'type': 'radio'})
    if radio_input:
        answer_data['answer'] = radio_input.get('value', '2')
    else:
        answer_data['answer'] = '2'

    answer_data['submit'] = 'true'

    # 提交答案
    submit_response = session.post(base_url, data=answer_data)
    
    # 解析答题结果
    if '恭喜你，回答正确！奖励' in submit_response.text:
        money_match = re.search(r'奖励(\d+)金钱', submit_response.text)
        money = money_match.group(1) if money_match else '0'
        add_log(f"第{question_number + 1}题回答正确，获得{money}金钱")
    elif '回答错误！扣除' in submit_response.text:
        money_match = re.search(r'扣除(\d+)金钱', submit_response.text)
        money = money_match.group(1) if money_match else '0'
        add_log(f"第{question_number + 1}题回答错误，扣除{money}金钱")
    else:
        add_log(f"第{question_number + 1}题答题完成，结果未知")

def build_prompt(html):
    import re
    
    # 提取题目
    question_match = re.search(r'【题目】</b>&nbsp;([^<]+)', html)
    question_text = question_match.group(1) if question_match else ""
    
    # 检查题目是否为空
    if not question_text.strip():
        return ""

    # 提取选项 - 简化正则，匹配id和后面的文本
    options = []
    radio_pattern = r'id="(a\d)"[^>]*>&nbsp;&nbsp;([^<]+)'
    matches = re.findall(radio_pattern, html, re.DOTALL)
    
    for option_id, option_text in matches:
        options.append(f"{option_id}: {option_text.strip()}")
    
    # 检查选项数量
    if len(options) < 4:
        # 备用方案：直接查找a1-a4
        for i in range(1, 5):
            aid = f"a{i}"
            pattern = rf'id="{aid}"[^>]*>.*?([^<]+)</div>'
            match = re.search(pattern, html, re.DOTALL)
            if match and aid not in [opt.split(':')[0] for opt in options]:
                text = match.group(1).replace('&nbsp;', ' ').strip()
                options.append(f"{aid}: {text}")
    
    prompt = f"题目: {question_text}\n选项:\n" + "\n".join(options) + "\n请选择正确答案，只返回选项ID（如a1、a2、a3、a4）："
    
    return prompt

def get_answer_from_api(prompt):
    import time
    
    try:
        start_time = time.time()
        response = Application.call(
            api_key=api_key,
            app_id=app_id,
            prompt=prompt)
        
        elapsed = time.time() - start_time
        if elapsed > 120:
            print("API调用超时(2分钟)，默认选择 a2")
            return 'a2'
            
        if response:
            label = response.output.text
            match = re.search(r'\ba[1-4]\b', label)
            label = match.group(0) if match else None
            print(f"API 返回的答案标签: {label}")
            return label if label else 'a2'
            
    except Exception as e:
        print(f"API调用异常: {e}，默认选择 a2")
        return 'a2'
    
    return 'a2'

def check_free_lottery(session):
    # 获取抽奖页面
    url = f"{address}/forum/plugin.php?id=gplayconstellation:front"
    response = session.get(url)
    
    # 从页面中查找game_info，检查今日剩余免费次数
    return '今日剩余免费次数：0次' not in response.text

def lottery(session):
    if not check_free_lottery(session):
        add_log("今天已免费抽奖。")
        return

    try:
        # 获取抽奖页面的formhash
        url = f"{address}/forum/plugin.php?id=gplayconstellation:front"
        response = session.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        formhash_input = soup.find('input', {'name': 'formhash'})
        formhash = formhash_input.get('value') if formhash_input else ''
        
        # 第一步：获取抽奖结果
        game_result_url = f"{address}/forum/plugin.php?id=gplayconstellation:front&mod=index&formhash={formhash}&act=game_result&inajax=1&ajaxtarget=myaward"
        response = session.get(game_result_url)
        
        # 第二步：显示奖励
        lottery_url = f"{address}/forum/plugin.php?id=gplayconstellation:front&mod=index&act=show_award&msg1=1&msg2=6&msg3=6&infloat=yes&handlekey=gplayconstellation&inajax=1&ajaxtarget=fwin_content_gplayconstellation"
        response = session.get(lottery_url)
        
        # 提取抽奖获得的金钱信息
        money_match = re.search(r'获得【[^】]*】(\d+)金钱', response.text)
        if money_match:
            lottery_money = money_match.group(1)
            add_log(f"抽奖成功！获得金钱")
        else:
            add_log("抽奖完成，但未找到金钱信息。")
            
    except Exception as e:
        print(f"抽奖过程中出现错误: {e}")
        add_log("抽奖失败。")
    
def getMoney(session):
    try:
        url = f"{address}/forum/home.php?mod=spacecp&ac=credit&showcredit=1"
        response = session.get(url)
        
        # 首先找到creditl类的内容
        creditl_match = re.search(r'<ul class="creditl[^"]*"[^>]*>(.*?)</ul>', response.text, re.DOTALL)
        if creditl_match:
            creditl_content = creditl_match.group(1)
            # 在creditl内容中查找金钱数字
            money_match = re.search(r'金钱:\s*</em>(\d+)', creditl_content)
            if money_match:
                return int(money_match.group(1))
        
        return 0
    except Exception as e:
        print(f"获取金钱信息失败: {e}")
        return 0
    
def sendPushplus(msg):
    try:
        global log_messages
        
        # 构建完整的推送内容
        content = f"<h3>执行结果: {msg}</h3>\n"
        if log_messages:
            content += "<h4>详细日志:</h4>\n<ul>\n"
            for log_msg in log_messages:
                content += f"<li>{log_msg}</li>\n"
            content += "</ul>"
        else:
            content += "<p>无详细日志</p>"
        
        url = "http://www.pushplus.plus/send"
        data = {
            "token": pushplus_token,
            "title": "神经研究所每日签到"+msg,
            "content": content,
            "template": "html"
        }
        response = requests.post(url, json=data)
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 200:
                print("推送消息发送成功。")
            else:
                print(f"推送消息发送失败: {result.get('msg')}")
        else:
            print(f"推送消息发送失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"推送消息发送失败: {e}")
     
def merge(local: bool):
    global username, password, pushplus_token

    # 创建会话
    req_session = RequestsSession()
    
    # 打印初始cookies信息
    req_session.print_cookies()
    req_session.check_forum_cookies()

    beijing_tz = timezone(timedelta(hours=8))
    now_str = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
    if local:
        print(f"=== Script for {username} started at {now_str} locally===")
    else:
        print(f"=== Script for {username} started at {now_str} remotely===")

    # 先进行验证码验证
    verify_success = False
    while not verify_success:
        verify_success = verify(req_session.session)
        if verify_success:
            print("[调试] 验证码验证成功，开始登录")
            break
        else:
            print("重新尝试验证...")
            time.sleep(5)
    
    # 验证成功后进行登录
    login_success = False
    max_login_retries = 3
    for attempt in range(max_login_retries):
        login_success = login(req_session.session)
        if login_success:
            # 登录成功后保存cookies
            req_session.save_cookies()
            req_session.print_cookies()
            req_session.check_forum_cookies()
            break
        else:
            print(f"登录失败，尝试 {attempt + 1}/{max_login_retries}")
            if attempt < max_login_retries - 1:
                time.sleep(2)
    
    if not login_success:
        print("登录失败，程序退出")
        add_log("登录失败，任务终止")
        raise Exception("登录失败")
    
    # 登录成功后随机等待
    random_wait()
    initial_money = getMoney(req_session.session)
    
    # 签到前随机等待
    random_wait()
    signin(req_session.session)
    
    # 答题前随机等待
    random_wait()
    question(req_session.session)
    
    # 抽奖前随机等待
    random_wait()
    lottery(req_session.session)
    
    # 最后获取金钱前随机等待
    random_wait()
    final_money = getMoney(req_session.session)
    add_log(f"金钱变化：{initial_money} -> {final_money}。")
    
    # 任务完成后再次保存cookies
    req_session.save_cookies()

def main():
    global username, password, pushplus_token, api_key, app_id, address

    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='Use local config')
    args = parser.parse_args()
    
    # 配置加载
    try:
        if args.local:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.json")
            with open(config_path, 'r') as f:
                config = json.load(f)
            username = config['USERNAME']
            password = config['PASSWORD']
            pushplus_token = config['PUSHPLUS_TOKEN']
            api_key = config['API_KEY']
            app_id = config['APP_ID']
            address = config['ADDRESS']
        else:
            username = os.environ['USERNAME']
            password = os.environ['PASSWORD']
            pushplus_token = os.environ['PUSHPLUS_TOKEN']
            api_key = os.environ['API_KEY']
            app_id = os.environ['APP_ID']
            address = os.environ['ADDRESS']
    except KeyError as e:
        raise Exception(f"Missing required configuration: {e}")

    try:
        merge(local=args.local)
        sendPushplus('成功')
    except Exception as e:
        print(f"任务执行失败: {e}")
        # 保存失败时的响应到本地
        save_failure_response(str(e))
        sendPushplus('失败')

def save_failure_response(error_msg):
    """任务失败时保存相关信息到本地"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        failure_info = {
            "timestamp": timestamp,
            "error": error_msg,
            "log_messages": log_messages
        }
        
        filename = f"failure_log_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(failure_info, f, ensure_ascii=False, indent=2)
        print(f"失败信息已保存到: {filename}")
    except Exception as e:
        print(f"保存失败信息时出错: {e}")

if __name__ == '__main__':
    main()