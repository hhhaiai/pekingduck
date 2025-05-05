import requests
from playwright.sync_api import sync_playwright
import json
import base_get_channel as channel
from typing import Optional, Dict
import time
from datetime import datetime, timedelta
# 禁用 SSL 警告
import urllib3
import traceback
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

debug = True
last_request_time = 0  # 上次请求的时间戳
cache_duration = 14400  # 缓存有效期，单位：秒 (4小时)
'''用于存储缓存的模型数据'''
cached_models = {
    "object": "list",
    "data": [],
    "version": "1.0.1",
    "provider": "DuckAI",
    "name": "DuckAI",
    "default_locale": "zh-CN",
    "status": True,
    "time": 0
}

'''基础模型'''
base_model = "gpt-4o-mini"
# 全局变量：存储所有模型的统计信息
# 格式：{model_name: {"calls": 调用次数, "fails": 失败次数, "last_fail": 最后失败时间}}
MODEL_STATS: Dict[str, Dict] = {}


def reload_check():
    """
    清除 cached_models 中的 data，重新加载模型数据，并获取最优模型
    """
    global cached_models
    # 清除 cached_models 中的 data
    cached_models = {
        "object": "list",
        "data": [],
        "version": "1.0.1",
        "provider": "DuckAI",
        "name": "DuckAI",
        "default_locale": "zh-CN",
        "status": True,
        "time": 0
    }

    # 重新加载模型数据
    get_models()

    # 获取最优模型
    best_model = get_auto_model()
    if debug:
        print(f"最优模型: {best_model}")
    return best_model


def record_call(model_name: str, success: bool = True) -> None:
    """
    记录模型调用情况
    Args:
        model_name: 模型名称
        success: 调用是否成功
    """
    global MODEL_STATS
    if model_name not in MODEL_STATS:
        MODEL_STATS[model_name] = {"calls": 0, "fails": 0, "last_fail": None}

    stats = MODEL_STATS[model_name]
    stats["calls"] += 1
    if not success:
        stats["fails"] += 1
        stats["last_fail"] = datetime.now()


def get_auto_model(cooldown_seconds: int = 300) -> str:
    """异步获取最优模型"""
    try:
        if not MODEL_STATS:
            get_models()

        best_model = None
        best_rate = -1.0
        now = datetime.now()

        for name, stats in MODEL_STATS.items():
            if stats.get("last_fail") and (now - stats["last_fail"]) < timedelta(seconds=cooldown_seconds):
                continue

            total_calls = stats["calls"]
            if total_calls > 0:
                success_rate = (total_calls - stats["fails"]) / total_calls
                if success_rate > best_rate:
                    best_rate = success_rate
                    best_model = name

        default_model = best_model or base_model
        if debug:
            print(f"选择模型: {default_model}")
        return default_model
    except Exception as e:
        if debug:
            print(f"模型选择错误: {e}")
        return base_model


def get_models():
    """model data retrieval with thread safety"""
    global cached_models, last_request_time
    current_time = time.time()
    if (current_time - last_request_time) > cache_duration:
        try:
            if debug:
                print(f"will get model ")
            # Update timestamp before awaiting to prevent concurrent updates
            get_model_impl_by_playwright()
            last_request_time = current_time
            if debug:
                print(f"success get model ")
        except Exception as e:
            print(f"000000---{e}")

    return json.dumps(cached_models)


def parser_models_info_form_page(page):
    global cached_models
    models = page.query_selector_all('ul[role="radiogroup"] > li')

    # 创建现有模型的 ID 集合用于快速查找
    existing_ids = {item["id"] for item in cached_models['data']}
    if debug:
        print(existing_ids)
    result = []
    # 确保有内容时更新
    is_update = False
    for model in models:
        # 使用更精确的选择器
        name_element = model.query_selector('.J58ouJfofMIxA2Ukt6lA')
        description_element = model.query_selector('.tDjqHxDUIeGL37tpvoSI')
        # 模型真实名字
        value = model.query_selector('input').get_attribute('value')
        # 确保有效
        if not name_element or not value:
            continue

        # 模型名字
        name = name_element.inner_text()
        description = description_element.inner_text() if description_element else ""
        # 确定描述供应商
        owned_by = channel.get_channel_company(value, description)
        # 生成新模型数据
        new_model = {
            "id": value,
            "object": "model",
            "model": value,
            "created": int(time.time() * 1000),  # 使用当前时间戳
            "name": name,
            "support": "text",
            "owned_by": owned_by,
            "description": name
        }
        if debug:
            print(f"new_model: {new_model}")
        # 记录成功
        record_call(value)
        if debug:
            print(f"after record_call")
        # 检查是否已存在相同 ID 的模型
        if new_model['id'] in existing_ids:
            # 更新已存在的模型数据
            for idx, item in enumerate(cached_models['data']):
                if item['id'] == new_model['id']:
                    cached_models['data'][idx] = new_model  # 完全替换旧数据
                    break
        else:
            # 添加新模型到缓存
            cached_models['data'].append(new_model)
        if debug:
            print(f"解析cached_models模型信息: {cached_models}")

        is_updated = True

    # 仅在检测到更新时刷新时间戳
    if is_updated:
        cached_models['time'] = int(time.time() * 1000)
    return json.dumps(cached_models, ensure_ascii=False)


def get_model_impl_by_playwright():
    """
        从网页获取获取模型
    """
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)  # headless=False 表示显示浏览器窗口
        context = browser.new_context()
        page = browser.new_page()

        try:
            # 导航到网页
            page.goto("https://duckduckgo.com/?q=DuckDuckGo+AI+Chat&ia=chat&duckai=1")

            # print(page.content())
            # 点击试试看
            # page.locator("//div[@class='G7rDHS2k8fykjYYMbnTg']/button").click()
            tool_selector = "//div[@class='G7rDHS2k8fykjYYMbnTg']/button"
            page.wait_for_selector(tool_selector, state="visible")
            page.locator(tool_selector).click()

            # 点击我同意
            # page.locator("//div[@class='G7rDHS2k8fykjYYMbnTg NHrnRvFtkZSdVRA6P3kD']/button").click()
            tool_selector = "//div[@class='G7rDHS2k8fykjYYMbnTg NHrnRvFtkZSdVRA6P3kD']/button"
            page.wait_for_selector(tool_selector, state="visible")
            page.locator(tool_selector).click()

            # 点击下拉框，出现5个AI工具
            # page.locator('//div[@class="eHTKOmyhnmDrrdAFuwDc"]/button').click()
            tool_selector = 'div.eHTKOmyhnmDrrdAFuwDc > button'
            page.wait_for_selector(tool_selector, state="visible", timeout=15000)
            page.locator(tool_selector).click(delay=500)

            # 等待所有模型加载完成
            page.wait_for_function(
                "document.querySelectorAll('ul[role=\"radiogroup\"] > li').length > 0",
                timeout=20000
            )

            # 解析模型信息
            if debug:
                print("\n开始解析模型信息...")
            parser_models_info_form_page(page)

        except Exception as e:
            print(f"发生错误: {e}")
        finally:
            browser.close()


def is_model_available(model_id: str, cooldown_seconds: int = 300) -> bool:
    """
    判断模型是否在模型列表中且非最近失败的模型

    Args:
        model_id: 模型ID，需要检查的模型标识符
        cooldown_seconds: 失败冷却时间（秒），默认300秒

    Returns:
        bool: 如果模型可用返回True，否则返回False

    Note:
        - 当MODEL_STATS为空时会自动调用get_models()更新数据
        - 检查模型是否在冷却期内，如果在冷却期则返回False
    """
    global MODEL_STATS

    # 如果MODEL_STATS为空，加载模型数据
    if not MODEL_STATS:
        get_models()

    # 检查模型是否在统计信息中
    if model_id not in MODEL_STATS:
        return False

    # 检查是否在冷却期内
    stats = MODEL_STATS[model_id]
    if stats["last_fail"]:
        time_since_failure = datetime.now() - stats["last_fail"]
        if time_since_failure < timedelta(seconds=cooldown_seconds):
            return False

    return True


def get_model_by_autoupdate(model_id: Optional[str] = None, cooldown_seconds: int = 300) -> Optional[str]:
    """
    检查提供的model_id是否可用，如果不可用则返回成功率最高的模型

    Args:
        model_id: 指定的模型ID，可选参数
        cooldown_seconds: 失败冷却时间（秒），默认300秒

    Returns:
        str | None: 返回可用的模型ID，如果没有可用模型则返回None

    Note:
        - 当MODEL_STATS为空时会自动调用get_models()更新数据
        - 如果指定的model_id可用，则直接返回
        - 如果指定的model_id不可用，则返回成功率最高的模型
    """
    global MODEL_STATS

    # 如果MODEL_STATS为空，加载模型数据
    if not MODEL_STATS:
        get_models()

    # 如果提供了model_id且可用，直接返回
    if model_id and is_model_available(model_id, cooldown_seconds):
        return model_id

    # 否则返回成功率最高的可用模型
    return get_auto_model(cooldown_seconds=cooldown_seconds)


################################################################################################


# 元素存放变量及时间
vqd4_time = ("", 0)
vqd4_hash_time = ("", 0)

def extract_x_vqd_4(default_host='duckduckgo.com', max_retries=3, retry_delay=1):
    """
    获取 x-vqd-4 token
    Args:
        default_host: 请求的主机地址
        max_retries: 最大重试次数
        retry_delay: 重试延迟时间(秒)
    Returns:
        str: 成功返回token，失败返回空字符串
    """
    url = f"https://{default_host}/duckchat/v1/status"
    global vqd4_time
    global vqd4_hash_time
    headers = {
        'Accept': '*/*',  # 修正 Accept 头
        'Sec-Fetch-Site': 'same-origin',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Sec-Fetch-Mode': 'cors',
        'Cache-Control': 'no-store',  # 修正缓存控制
        'Host': default_host,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15 Ddg/18.4',
        'Referer': f"https://{default_host}/",
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Cookie': 'dcm=3',
        'X-DuckDuckGo-Client': 'macOS',
        'x-vqd-accept': '1'
    }

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=10,  # 添加超时设置
                verify=False  # 忽略 SSL 验证
            )
            response.encoding = 'utf-8'

            if response.status_code == 200:
                # print(response.text)
                # print(response.headers)
                vqd4 = response.headers.get('x-vqd-4', '')
                vqd4_hash = response.headers.get('x-vqd-hash-1', '')  # 假设存在 x-vqd-4-hash 头
                if vqd4 and vqd4_hash:
                    vqd4_time = (vqd4, int(time.time() * 1000))
                    vqd4_hash_time = (vqd4_hash, int(time.time() * 1000))
                    if debug:
                        print(f"extract_x_vqd_4() 成功获取vqd4: {vqd4} , vqd4_hash: {vqd4_hash}")
                    return
                else:
                    if debug:
                        print(f"extract_x_vqd_4() Token或Hash为空，尝试次数: {attempt + 1}/{max_retries}")

            # 如果不是最后一次尝试，则等待后重试
            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        except requests.RequestException as e:
            if debug:
                print(f"请求异常: {e}，尝试次数: {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            continue

    if debug:
        print("获取token失败，已达到最大重试次数")


def parse_response(response_text):
    """
    逐行解析
    """
    lines = response_text.split('\n')
    result = ""
    for line in lines:
        if line.startswith("data:"):
            data = json.loads(line[len("data:"):])
            if "message" in data:
                result += data["message"]
    print(result)


def chat_completion_message(user_prompt,  model=base_model,
                            system_message='You are a helpful assistant.',
                            user_id: str = None, session_id: str = None, default_host="duckduckgo.com"
                            , stream=False, temperature=0.3, max_tokens=1024, top_p=0.5, frequency_penalty=0,
                            presence_penalty=0):
    """
    单条消息请求: https://duckduckgo.com/duckchat/v1/chat
    """

    messages = [
        # 需要 system-> user
        {"role": "user", "content": system_message},
        {"role": "user", "content": user_prompt}
    ]
    return chat_completion_messages(messages=messages, model=model, default_host=default_host
                                    , user_id=user_id
                                    , session_id=session_id
                                    , stream=stream
                                    , temperature=temperature
                                    , max_tokens=max_tokens
                                    , top_p=top_p
                                    , frequency_penalty=frequency_penalty
                                    , presence_penalty=presence_penalty
                                    )


def chat_completion_messages(
        messages,
        model=base_model,
        default_host="duckduckgo.com",
        user_id: str = None,
        session_id: str = None,
        stream=False, temperature=0.3,
        max_tokens=1024, top_p=0.5,
        frequency_penalty=0, presence_penalty=0):
    try:
        global vqd4_time
        global vqd4_hash_time
        # 确保model有效
        if not model or model == "auto":
            model = get_auto_model()
        else:
            model = get_model_by_autoupdate(model)
        if debug:
            print(f"chat_completion_messages 校准后的model: {model}")

        # 处理 token
        if vqd4_time[0] == '' or vqd4_hash_time[0] == '':
            extract_x_vqd_4()
        x_vqd_4 = vqd4_time[0]
        vqd4_hash = vqd4_hash_time[0]


        if debug:
            print(f"chat_completion_messages 获取的token: {x_vqd_4}, hash: {vqd4_hash}")

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Sec-Fetch-Site': 'same-origin',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Mode': 'cors',
            'Host': default_host,
            'Origin': f"https://{default_host}",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.4 Safari/605.1.15 Ddg/18.4',
            'Referer': f"https://{default_host}/",
            'Connection': 'keep-alive',
            'Cookie': 'dcm=3; dcs=1',
            'Sec-Fetch-Dest': 'empty',
            'x-fe-version': 'serp_20250411_055722_ET-227034fa144d75d4af83',
            'X-Vqd-4': x_vqd_4,
            'X-DuckDuckGo-Client': 'macOS',
            'X-Vqd-Hash-1': vqd4_hash
        }

        # 检查模型，如果messages 包含 system那么修改为user
        for message in messages:
            if message.get("role") == "system":
                message["role"] = "user"

        data = {
            "model": model,
            "messages": messages
        }
        return chat_completion(default_host=default_host, model=model, headers=headers, payload=data)

    except Exception as e:
        print(f"x1  使用模型[{model}]发生了异常：", e)
        traceback.print_exc()
    return ""


def chat_completion(default_host, model, headers, payload):
    global vqd4_time
    global vqd4_hash_time
    try:
        response = requests.post(f'https://{default_host}/duckchat/v1/chat', headers=headers, json=payload)
        response.encoding = 'utf-8'  # 明确设置字符编码
        # response.raise_for_status()

        print("chat Status Code :", response.status_code)
        print("chat Content-Type: ", response.headers.get('Content-Type'))
        print("chat response.text: ",response.text)
        print("response.headers: ",response.headers)

        final_content = ""
        if response.status_code == 200:
            # # 将 headers 转换为普通字典
            # headers_dict = dict(response.headers)
            # # 将字典转换为 JSON 字符串
            # headers_json = json.dumps(headers_dict, ensure_ascii=False, indent=4)
            # print(headers_json)
            # 解析请求头
            vqd4 = response.headers.get('x-vqd-4', '')
            vqd4_hash = response.headers.get('x-vqd-hash-1', '')  # 假设存在 x-vqd-4-hash 头
            if vqd4 and vqd4_hash:
                vqd4_time = (vqd4, int(time.time() * 1000))
                vqd4_hash_time = (vqd4_hash, int(time.time() * 1000))


            # 解析响应内容
            for line in response.iter_lines(decode_unicode=True):
                print(line)
                # print(line)
                # 检查 if 'data: [DONE]'在行中进行下一步动作
                if 'data: [DONE]' in line:
                    # 如果找到结束信号，退出循环
                    break
                elif line.startswith('data: '):  # 确保行以'data: '开头
                    data_json = line[6:]  # 删除行前缀'data: '
                    datax = json.loads(data_json)  # 解析JSON字符串为字典
                    if 'message' in datax:
                        final_content += datax['message']
                        # print( final_content)
            # 保存最终的content结果
            final_result = final_content
        return final_result
    except Exception as e:
        print(f"⬇️2 使用模型[{model}]发生了异常：", e)
        traceback.print_exc()


    # user_prompt, x_vqd_4='', model=base_model,
def mods(model, prompt):
    t1 = time.time()
    res = chat_completion_message(user_prompt=prompt, model=model)
    t2 = time.time()
    print(
        f"========={model}--->测试耗时【{t2 - t1}】=========本轮开始\r\n{res}\r\n======本文结束======")


# 测试代码
if __name__ == "__main__":
    time1 = time.time() * 1000
    result_json = get_models()
    time2 = time.time() * 1000
    print(f"耗时: {time2 - time1}")
    print(result_json)
    result_json2 = get_models()
    time3 = time.time() * 1000
    print(f"耗时2: {time3 - time2}")
    print(result_json2)

    print(f"获取自动模型1 get_model_by_autoupdate :{get_model_by_autoupdate('hello')}")
    print(f"获取自动模型2 get_auto_model :{get_auto_model()}")
    print(f"获取自动模型3 cached_models :{cached_models}")

    p = "你是谁?你使用的是什么模型?你的知识库截止到什么时间? "
    model_ids = [model['id'] for model in cached_models['data']]
    for id in model_ids:
        mods(id, p)
    # extract_x_vqd_4()
    # # vqd4_time = ("", 0)
    # # vqd4_hash_time = ("", 0)
    # print(f"vqd4_time: {vqd4_time}")
    # print(f"vqd4: {vqd4_time[0]}")
    # print(f"vqd4_hash_time: {vqd4_hash_time}")
    # print(f"vqd4_hash: {vqd4_hash_time[0]}")