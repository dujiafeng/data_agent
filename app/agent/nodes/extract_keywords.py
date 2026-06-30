import jieba.analyse
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime
from app.agent.llm import keyword_llm
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt

# ── 判断阈值 ──────────────────────────────────────────────
JIEBA_MAX_LEN = 30          # query 长度超过此值视为"复杂"
JIEBA_MIN_KW_COUNT = 3      # jieba 提取的关键词少于这个数，说明覆盖不足


def _is_complex_query(query: str, jieba_keywords: list[str]) -> bool:
    """
    判断是否需要升级到 LLM 提取关键词。
    满足以下任一条件即视为复杂查询：
      1. query 长度超过阈值
      2. jieba 提取的关键词数量不足（说明 jieba 覆盖不了）
      3. query 中包含多个子句（有逗号/句号/问号等分隔）
    """
    if len(query) > JIEBA_MAX_LEN:
        return True
    if len(jieba_keywords) < JIEBA_MIN_KW_COUNT:
        return True
    # 包含多个子句分隔符，说明语义较复杂
    clause_separators = ("，", ",", "。", "？", "！", "；", ";")
    if any(sep in query for sep in clause_separators):
        return True
    return False


async def _extract_by_jieba(query: str) -> list[str]:
    """使用 jieba 提取关键词（轻量方案）"""
    allow_pos = (
        "n", "nr", "ns", "nt", "nz",
        "v", "vn", "a", "an", "eng", "i", "l",
    )
    keywords = jieba.analyse.extract_tags(query, topK=20, allowPOS=allow_pos)
    # 将原始查询加入并去重，保持顺序
    seen = set()
    result = []
    for kw in keywords + [query]:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


async def _extract_by_llm(
    query: str,
    runtime: Runtime[DataAgentContext],
) -> list[str]:
    """使用微调后的小模型提取关键词（重量方案）"""
    prompt = PromptTemplate(
        template=load_prompt("extract_keyword"),
        input_variables=["query"],
    )
    str_parser = StrOutputParser()
    chain = prompt | keyword_llm | str_parser

    # PromptTemplate 需要字典来填充 {query} 占位符
    raw = await chain.ainvoke({"query": query})

    # 按中文逗号分隔解析
    keywords = [kw.strip() for kw in raw.split("，") if kw.strip()]

    # 兜底
    if not keywords:
        keywords = [query]

    # 将原始查询加入并去重，保持顺序
    seen = set()
    result = []
    for kw in keywords + [query]:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "抽取关键词", "status": "running"})

    try:
        query = state["query"]

        # 第一步：始终先用 jieba 做一轮轻量提取
        jieba_keywords = await _extract_by_jieba(query)

        # 第二步：判断是否需要升级到 LLM
        if _is_complex_query(query, jieba_keywords):
            logger.info(f"查询较复杂，切换到 LLM 提取关键词: {query}")
            keywords = await _extract_by_llm(query, runtime)
            method = "llm"
        else:
            keywords = jieba_keywords
            method = "jieba"

        writer({"type": "progress", "step": "抽取关键词", "status": "success"})
        logger.info(f"抽取关键词成功 [{method}]: {keywords}")
        return {"keywords": keywords}

    except Exception as e:
        logger.error(f"抽取关键词失败: {e}")
        writer({"type": "progress", "step": "抽取关键词", "status": "error"})
        raise