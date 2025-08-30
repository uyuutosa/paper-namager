from __future__ import annotations

from typing import List, Tuple


def generate_with_langchain(prompt: str, context: str, *, model: str = "gpt-4o-mini", temperature: float = 0.2) -> str:
    """Generate output using LangChain + OpenAI chat model with the given context.

    Falls back by raising an explanatory error if dependencies or API key are missing.
    """
    try:
        from langchain_core.prompts import PromptTemplate
        from langchain_openai import ChatOpenAI
        from langchain_core.output_parsers import StrOutputParser
        import os
    except Exception as e:
        raise RuntimeError(f"LangChain/OpenAI not available: {e}")

    if not (os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")):
        raise RuntimeError("OPENAI_API_KEY (or AZURE_OPENAI_API_KEY) is not set")

    sys_pt = (
        "You are a helpful research assistant. Use the provided Context to answer. "
        "Cite paper_ids inline if possible. Be concise but accurate."
    )
    template = (
        "SYSTEM:\n" + sys_pt + "\n\n"
        "USER:\n"
        "Prompt:\n{prompt}\n\n"
        "Context:\n{context}\n\n"
        "Instructions:\n"
        "- Synthesize across documents; avoid repetition.\n"
        "- Include a short bullet list of key points.\n"
        "- If context is insufficient, say so explicitly.\n"
    )
    pt = PromptTemplate.from_template(template)
    llm = ChatOpenAI(model=model, temperature=temperature)
    chain = pt | llm | StrOutputParser()
    return chain.invoke({"prompt": prompt, "context": context})


def build_context_from_docs(docs: List[Tuple[str, str, float]], *, top_k: int = 5, per_doc_chars: int = 2000) -> str:
    """Create a plain-text context from (paper_id, text, weight)."""
    docs = sorted(docs, key=lambda x: x[2], reverse=True)
    parts: List[str] = []
    for pid, text, w in docs[: min(top_k, len(docs))]:
        snippet = text[:per_doc_chars]
        parts.append(f"# [{pid}] (w={w})\n{snippet}")
    return "\n\n---\n\n".join(parts)

