import re


def get_channel_company(value: str, description: str = "") -> str:
    """
    提取模型所属公司，优先级：value > description > 截取value首段
    """

    # 匹配规则表（可扩展）
    RULES = [
        (r"claude", "Anthropic"),
        (r"gemini|palm", "Google"),
        (r"llama2?|llama3?|meta-llama", "Meta"),
        (r"gpt-|dall·e|o1|o2|o3|o4", "OpenAI"),
        (r"deepseek", "DeepSeek"),
        (r"abab|minimax", "MiniMax"),
        (r"mistral", "Mistral"),
        (r"ernie|文心一言", "Baidu"),
        (r"chatglm|智谱", "Zhipu")
    ]

    def _match(text: str) -> str | None:
        """从文本中匹配公司（兼容空值）"""
        if not text: return None
        return next((owner for pattern, owner in RULES if re.search(pattern, text.lower())), None)

    # 优先级逻辑
    owner = _match(value) or _match(description)
    if owner: return owner

    # 截取首段逻辑优化（过滤空字符）
    if value:
        # 分割并过滤空字符串
        #parts = [p for p in re.split(r'[-\s/]+', value) if p.strip()]
        parts = [p for p in re.split(r'[-\s/._]+', value) if p.strip()]
        if parts:
            return parts[0].capitalize()  # 首字母大写

    return "unknown"  # 全空或无有效内容
