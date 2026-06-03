"""轻量知识层:文件/ wiki 抽文本 + 可插拔检索(RAG seam,当前用关键词)。

设计:不上向量库,但把"检索"抽成 KnowledgeRetriever 协议;当前实现 KeywordRetriever
(分块 + 关键词重叠打分)。日后要上 embedding,只需补一个 VectorRetriever,调用方不变。
专家发言时按当前议题取最相关片段拼进 system prompt → "知识升级"让专家更懂业务。
"""
from __future__ import annotations

import io
import re
from typing import Protocol

from . import store


# ---------- 抽取 ----------
def extract_text_from_file(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((pg.extract_text() or "") for pg in reader.pages).strip()
    # txt / md / 其它按文本解码
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore").strip()


async def extract_text_from_url(url: str) -> tuple[str, str]:
    """抓网页/wiki 正文 → (title, text)。去脚本/样式/导航,保留正文文本。"""
    import httpx
    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(follow_redirects=True, timeout=20,
                                 headers={"User-Agent": "Mozilla/5.0 RoundtableBot"}) as cli:
        r = await cli.get(url)
        r.raise_for_status()
        html = r.text
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string if soup.title else "") or url
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript"]):
        tag.decompose()
    # 维基类站点正文常在 #mw-content-text / #content / article / main
    main = (soup.select_one("#mw-content-text") or soup.select_one("article")
            or soup.select_one("main") or soup.select_one("#content") or soup.body or soup)
    text = re.sub(r"\n{3,}", "\n\n", main.get_text("\n", strip=True))
    return title.strip(), text.strip()


# ---------- 检索(RAG seam)----------
def _chunks(text: str, size: int = 400) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    for p in paras:
        if len(p) <= size:
            out.append(p)
        else:
            for i in range(0, len(p), size):
                out.append(p[i : i + size])
    return out


def _tokens(s: str) -> list[str]:
    # 中文按字 + 英文按词,简单够用
    return re.findall(r"[A-Za-z0-9]+|[一-鿿]", s.lower())


class KnowledgeRetriever(Protocol):
    def retrieve(self, query: str, expert_id: str, k: int = 4) -> list[str]: ...


class KeywordRetriever:
    """关键词重叠打分的轻量检索。"""

    def retrieve(self, query: str, expert_id: str, k: int = 4) -> list[str]:
        expert = store.get_expert(expert_id)
        if not expert:
            return []
        docs = store.docs_by_ids(expert.get("knowledge_ids", []))
        docs += store.list_docs(expert_id=expert_id, with_text=True)
        seen, chunks = set(), []
        for d in docs:
            if d["id"] in seen:
                continue
            seen.add(d["id"])
            for ch in _chunks(d.get("text_content", "")):
                chunks.append((d.get("title", ""), ch))
        if not chunks:
            return []
        qt = set(_tokens(query))
        scored = []
        for title, ch in chunks:
            ct = _tokens(ch)
            if not ct:
                continue
            overlap = sum(1 for t in ct if t in qt)
            if overlap:
                scored.append((overlap / (len(ct) ** 0.5), title, ch))
        scored.sort(reverse=True)
        return [f"[{t}] {c}" if t else c for _, t, c in scored[:k]]


# 当前默认检索器(换成 VectorRetriever 不影响调用方)
RETRIEVER: KnowledgeRetriever = KeywordRetriever()


def knowledge_context(expert_id: str, topic: str, k: int = 4) -> str:
    """给专家发言用:取与议题最相关的知识片段,拼成可注入 system prompt 的块。"""
    snips = RETRIEVER.retrieve(topic, expert_id, k=k)
    if not snips:
        return ""
    body = "\n".join(f"- {s}" for s in snips)
    return "你掌握以下专业资料(优先据此作答,不要编造资料外的数字):\n" + body
