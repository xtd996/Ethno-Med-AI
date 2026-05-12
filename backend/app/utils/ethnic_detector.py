import jieba


# 民族关键词映射
_ETHNIC_KEYWORDS: dict[str, list[str]] = {
    "藏族": ["藏族", "藏医", "藏药"],
    "羌族": ["羌族", "羌医", "羌药"],
    "彝族": ["彝族", "彝医", "彝药"],
}

# 民族医药关键词（用于判断是否触发检索）
_ETHNIC_MEDICINE_KEYWORDS: list[str] = [
    "藏族医学", "藏医", "藏药",
    "彝族医学", "彝医", "彝药",
    "羌族医学", "羌医", "羌药",
]

# 症状相关关键词
_SYMPTOM_KEYWORDS: list[str] = [
    "症状", "痛", "干", "咳嗽", "不适", "热", "肿", "痒", "晕",
    "发烧", "头痛", "腹痛", "恶心", "呕吐", "乏力", "失眠",
]


def infer_ethnic(query: str) -> str:
    """从用户查询中推断目标民族。

    使用 jieba 分词对查询进行切分，然后匹配民族关键词。
    默认返回 "藏族"。
    """
    tokens = set(jieba.cut(query))
    for ethnic, keywords in _ETHNIC_KEYWORDS.items():
        if any(kw in tokens or kw in query for kw in keywords):
            return ethnic
    return "藏族"


def needs_retrieval(query: str, model_name: str) -> bool:
    """判断当前查询是否需要进行 RAG 检索。

    仅当使用专业模型且查询中包含民族医药关键词时触发检索。
    """
    if model_name != "专业模型":
        return False
    return any(kw in query for kw in _ETHNIC_MEDICINE_KEYWORDS)


def is_symptom_related(query: str) -> bool:
    """判断查询是否与症状描述相关。"""
    tokens = set(jieba.cut(query))
    return any(kw in tokens or kw in query for kw in _SYMPTOM_KEYWORDS)
