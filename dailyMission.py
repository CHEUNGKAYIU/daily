from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from time import sleep
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

import requests
import io
import sys
from functools import partial
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from dashscope import Application

username = None
password = None
pushplus_token = None
api_key = None
app_id = None

def login(driver):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"[调试] 登录尝试 {attempt + 1}/{max_retries}")
            driver.get("https://www.easonfans.com/FORUM/member.php?mod=logging&action=login")

            verify_img = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "verifyimg"))
            )

            img_url = verify_img.get_attribute("src")
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
                print(f"识别的验证码: '{code}'")
                
                # 验证是否为5位数字
                if not (code.isdigit() and len(code) == 5):
                    print(f"[警告] 识别结果不是5位数字，使用默认值")
                    code = "12345"
                    
            except Exception as e:
                print(f"[错误] 验证码识别失败: {e}")
                code = "12345"
            
            # time.sleep(3)

            input_box = driver.find_element(By.ID, "intext")
            input_box.clear()
            input_box.send_keys(code.strip())
            time.sleep(1)
            driver.find_element(By.CSS_SELECTOR, 'input[value="点击继续访问网站"]').click()

            # 填写登录表单
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            driver.find_element(By.NAME, "username").send_keys(username)
            driver.find_element(By.NAME, "password").send_keys(password)
            driver.find_element(By.NAME, "loginsubmit").click()

            # 检查是否登录成功
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "umLogin"))
                )
                print("登录成功！")
                return True
            except TimeoutException:
                print(f"[调试] 第{attempt + 1}次登录失败，可能验证码错误")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    return False

        except Exception as e:
            print(f"[错误] 登录过程中出现异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return False
    
    return False

def signin(driver):
    # 导航到签到页面
    driver.get("https://www.easonfans.com/forum/plugin.php?id=dsu_paulsign:sign")
    
    # 检查是否有徽章弹窗
    try:
        badge_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "fwin_badgewin_7ree"))
        )
        if badge_element:
            print("徽章弹窗出现，准备领取徽章。")
            # 打开徽章领取页面
            driver.get("https://www.easonfans.com/forum/plugin.php?id=badge_7ree:badge_7ree&code=1")

            
            button = driver.find_element("css selector", 'a[href*="plugin.php?id=badge_7ree"]')
            before_click_content = driver.page_source  # 记录点击前页面内容
            button.click()  # 点击领取按钮
            WebDriverWait(driver, 5).until(
                EC.staleness_of(badge_element)  # 等待元素失效（通常意味着页面刷新）
            )
            after_click_content = driver.page_source  # 记录点击后页面内容

            if before_click_content != after_click_content:
                print("徽章领取成功！")
            else:
                print("徽章领取失败。")

    except TimeoutException:
        print("没有徽章弹窗。")
    
    # 导航到签到页面
    driver.get("https://www.easonfans.com/forum/plugin.php?id=dsu_paulsign:sign")
    
    # 开始签到流程
    try:
        # 检查是否已经签到或签到未开始
        message_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), '您今天已经签到过了或者签到时间还未开始')]"))
        )
        print("今天已签到或签到未开始。")
    except TimeoutException:
        # 签到按钮可点击，开始签到流程
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@onclick=\"showWindow('qwindow', 'qiandao', 'post', '0');return false\"]"))
            )

            # 点击签到触发元素
            li_element = driver.find_element(By.ID, "kx")
            li_element.click()

            radio_button = driver.find_element(By.CSS_SELECTOR, "input[type='radio'][name='qdmode'][value='3']")
            radio_button.click()

            link = driver.find_element(By.XPATH, "//a[@onclick=\"showWindow('qwindow', 'qiandao', 'post', '0');return false\"]")
            link.click()

            # 重新检查是否签到成功
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), '您今天已经签到过了或者签到时间还未开始')]"))
                )
                print("签到成功！")
            except TimeoutException:
                print("签到失败。")
        except Exception as e:
            print(f"签到过程中出现错误。")


def question(driver):
    base_url = "https://www.easonfans.com/forum/plugin.php?id=ahome_dayquestion:index"

    driver.get(base_url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "inner"))
        )
    except Exception as e:
        print(f"页面加载失败: {e}")

    try:
        page_source = driver.page_source
        total_answered_match = re.search(r"累计答题:\s*(\d+)", page_source)
        total_correct_match = re.search(r"累计答对:\s*(\d+)", page_source)
        initial_answer = int(total_answered_match.group(1)) if total_answered_match else 0
        initial_correct = int(total_correct_match.group(1)) if total_correct_match else 0
        # print(f"初始累计答题：{initial_answer}, 初始累计答对：{initial_correct}")
    except Exception as e:
        print(f"无法提取初始答题信息: {e}")
        initial_answer = 0
        initial_correct = 0

    while True:
        driver.get(base_url)
        try:
            # 等待参与次数元素出现
            participated_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "inner"))
            )
        except Exception as e:
            print(f"页面加载失败: {e}")
            break

        matches = re.search(r"\((\d+)/(\d+)\)", participated_element.text)
        participated, total = map(int, matches.groups())
        if participated >= total:
            try:
                page_source = driver.page_source
                total_answered_match = re.search(r"累计答题:\s*(\d+)", page_source)
                total_correct_match = re.search(r"累计答对:\s*(\d+)", page_source)
                final_answer = int(total_answered_match.group(1)) if total_answered_match else 0
                final_correct = int(total_correct_match.group(1)) if total_correct_match else 0
                # print(f"初始累计答题：{initial_answer}, 初始累计答对：{initial_correct}")
            except Exception as e:
                print(f"无法提取最终答题信息: {e}")
                initial_answer = 0
                initial_correct = 0
            
            if final_answer != initial_answer and initial_answer != 0:
                correct_rate = (final_correct - initial_correct)/(final_answer-initial_answer)
                correct_rate_percent = correct_rate * 100
                print(f"今日答题已完成，答题正确率 {correct_rate_percent:.2f}%。总正确数/答题数：{final_correct}/{final_answer}。")
            else:
                print(f"今日答题已完成。总正确数/答题数：{final_correct}/{final_answer}。")
            break
        
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@name='submit'][@value='true']"))
            )
            answer_question(driver, participated)
        except Exception as e:
            print(f"答题第{participated+1}题过程中出现错误，正在重试。")
            sleep(5)
            continue

def answer_question(driver, question_number):
    prompt = build_prompt(driver)
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

    # 等待选项加载并点击
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, label))).click()
    # 提交答案
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@name='submit'][@value='true']"))
    ).click()
    # print(f"回答第 {question_number + 1} 题成功，提交选项：{label}")
    print(f"回答第 {question_number + 1} 题成功")

def build_prompt(driver):
    # 获取页面 HTML 内容
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')

    # 1. 提取题目内容
    b_tag = soup.find('b', string=lambda s: s and '【题目】' in s)

    # b标签的父节点通常是font或span，拿父节点的所有文本内容
    parent_tag = b_tag.parent

    # 拿父标签内全部文本，去除【题目】及前后空白符
    full_text = parent_tag.get_text(separator='', strip=True)
    full_text = full_text.replace('【题目】', '').replace('\xa0', ' ').strip()

    # 2. 提取选项内容（ID 和 文本）
    options = []
    option_divs = soup.find_all('div', class_='qs_option')
    for div in option_divs:
        input_tag = div.find('input')
        label = input_tag.get('id') if input_tag else 'unknown'
        # 取整段文本，剔除 &nbsp;&nbsp; 或空格
        raw_text = div.get_text(strip=True).replace('\xa0', ' ')
        # 去掉可能的前缀（如 “a1. ”）
        text = raw_text.split(' ', 1)[-1] if ' ' in raw_text else raw_text
        options.append((label, text))

    # 3. 构建 prompt
    prompt = f"题目：{full_text}\n\n选项：\n"
    for label, text in options:
        prompt += f"{label}. {text}\n"
    prompt += "\n请从上述选项中选择一个最合理的答案，并只返回选项标签,如a1,a2,a3,a4"

    return prompt

def get_answer_from_api(prompt):
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError("API调用超时")
    
    # 设置2分钟超时
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(120)  # 120秒 = 2分钟
    
    try:
        response = Application.call(
            api_key=api_key,
            app_id=app_id,
            prompt=prompt)

        label = response.output.text
        match = re.search(r'\ba[1-4]\b', label)
        label = match.group(0) if match else None
        print(f"API 返回的答案标签: {label}")
        return label if label else None
        
    except TimeoutError:
        print("API调用超时(2分钟)，默认选择 a2")
        return 'a2'
    except Exception as e:
        print(f"API调用异常: {e}，默认选择 a2")
        return 'a2'
    finally:
        signal.alarm(0)  # 取消超时设置

def check_free_lottery(driver):
    driver.get("https://www.easonfans.com/forum/plugin.php?id=gplayconstellation:front")
    try:
        # 等待并检查是否还有剩余的免费抽奖次数
        message_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), '今日剩余免费次数：0次')]"))
        )
        return False  # 没有剩余免费抽奖次数
    except:
        return True  # 还有剩余免费抽奖次数

def lottery(driver):
    if not check_free_lottery(driver):
        print("今天已免费抽奖。")
        return

    # 等待抽奖按钮可点击并点击
    
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "pointlevel"))
        ).click()
        print("开始免费抽奖。")
        sleep(5)  # 等待抽奖结果

        # 重新检查是否抽奖成功
        if not check_free_lottery(driver):
            print("免费抽奖成功！")
        else:
            print("免费抽奖失败。")
    except Exception as e:
        print(f"抽奖过程中出现错误。")

def getMoney(driver):
    driver.get("https://www.easonfans.com/forum/home.php?mod=spacecp&ac=credit&showcredit=1")
    try:
        money_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//li[@class='xi1 cl']"))
        )
        money_text = money_element.text
        money_amount = [int(s) for s in money_text.split() if s.isdigit()][0]  # 提取数字并假设第一个数字为金钱数额
        return money_amount
    except Exception as e:
        print(f"获取金钱失败。")
        return 0
    
def sendPushplus(msg):
    try:
        url = "http://www.pushplus.plus/send"
        data = {
            "token": pushplus_token,
            "title": "神经研究所每日签到"+msg,
            "content": msg,
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

def capture_output(func):
    # 重定向标准输出到一个内存缓冲区
    buffer = io.StringIO()
    sys.stdout = buffer
    func()
    sys.stdout = sys.__stdout__  # 恢复标准输出
    return buffer.getvalue()
    
def merge(headless: bool, local: bool, chromedriver_path: str):
    global username, password, pushplus_token

    # 模拟浏览器打开网站
    chrome_options = webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    service = Service(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    beijing_tz = timezone(timedelta(hours=8))
    now_str = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
    if local:
        print(f"=== Script for {username} started at {now_str} locally===")
    else:
        print(f"=== Script for {username} started at {now_str} remotely===")

    login_success = False
    while not login_success:
        login_success = login(driver)
        if login_success:
            break
        else:
            print("重新尝试登录...")
            sleep(5)
    initial_money = getMoney(driver)
    signin(driver)
    question(driver)
    lottery(driver)
    final_money = getMoney(driver)
    print(f"金钱变化：{initial_money} -> {final_money}。")
    driver.quit()

def main():
    global username, password, pushplus_token, api_key, app_id

    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='Use local config and chromedriver path')
    parser.add_argument('--headless', action='store_true', help='Enable headless mode')
    args = parser.parse_args()
    # args.local = True
    # 配置加载
    try:
        if args.local:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            linux_driver_dir = os.path.join(base_dir, "chromedriver-linux64")
            win_driver_dir = os.path.join(base_dir, "chromedriver-win64")

            if os.path.exists(linux_driver_dir):
                chromedriver_path = os.path.join(linux_driver_dir, "chromedriver")
            elif os.path.exists(win_driver_dir):
                chromedriver_path = os.path.join(win_driver_dir, "chromedriver.exe")
            else:
                raise FileNotFoundError("未找到 chromedriver-linux64 或 chromedriver-win64 文件夹")
            
            config_path = os.path.join(base_dir, "config.json")
            with open(config_path, 'r') as f:
                config = json.load(f)
            username = config['USERNAME']
            password = config['PASSWORD']
            pushplus_token = config['PUSHPLUS_TOKEN']
            api_key = config['API_KEY']
            app_id = config['APP_ID']
        else:
            chromedriver_path = shutil.which("chromedriver")
            username = os.environ['USERNAME']
            password = os.environ['PASSWORD']
            pushplus_token = os.environ['PUSHPLUS_TOKEN']
            api_key = os.environ['API_KEY']
            app_id = os.environ['APP_ID']
    except KeyError as e:
        raise Exception(f"Missing required configuration: {e}")

    try:
        merge(headless=args.headless, local=args.local, chromedriver_path=chromedriver_path)
        sendPushplus('成功')
    except Exception as e:
        sendPushplus('失败')

if __name__ == '__main__':
    main()