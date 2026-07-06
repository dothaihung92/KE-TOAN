"""
Sinh nội dung bài đăng / quảng cáo bằng AI.

Nếu có biến môi trường ANTHROPIC_API_KEY hoặc OPENAI_API_KEY, dùng LLM tương
ứng để viết nội dung tiếng Việt tự nhiên. Nếu không có key nào, dùng mẫu
(template) đơn giản để hệ thống vẫn chạy được mà không phụ thuộc dịch vụ
ngoài — tiện cho demo/test.
"""

from __future__ import annotations

import os
from typing import Optional

import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def _prompt(product_name: str, product_desc: str, price: str, tone: str, cta: str) -> str:
    return (
        f"Viết một bài đăng Facebook ngắn (3-5 câu, có emoji phù hợp) bằng tiếng Việt "
        f"để quảng bá sản phẩm sau, giọng văn {tone}:\n"
        f"- Tên sản phẩm: {product_name}\n"
        f"- Mô tả: {product_desc}\n"
        f"- Giá: {price}\n"
        f"Kết thúc bằng lời kêu gọi hành động: {cta}. "
        f"Chỉ trả về nội dung bài đăng, không thêm giải thích."
    )


def _via_anthropic(prompt: str, api_key: str, timeout: int = 30) -> Optional[str]:
    try:
        resp = requests.post(
            ANTHROPIC_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": os.environ.get("FBAI_ANTHROPIC_MODEL", "claude-sonnet-5"),
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        parts = data.get("content", [])
        return "".join(p.get("text", "") for p in parts).strip() or None
    except (requests.RequestException, ValueError, KeyError):
        return None


def _via_openai(prompt: str, api_key: str, timeout: int = 30) -> Optional[str]:
    try:
        resp = requests.post(
            OPENAI_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            json={
                "model": os.environ.get("FBAI_OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip() or None
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def _template_fallback(product_name: str, product_desc: str, price: str, cta: str) -> str:
    return (
        f"🔥 {product_name} đang có mặt tại shop!\n"
        f"{product_desc}\n"
        f"💰 Giá chỉ: {price}\n"
        f"👉 {cta}"
    )


def generate_post_content(
    product_name: str,
    product_desc: str,
    price: str = "Liên hệ",
    tone: str = "thân thiện, gần gũi",
    cta: str = "Inbox ngay để được tư vấn!",
) -> str:
    """Sinh nội dung bài đăng quảng cáo. Ưu tiên LLM nếu có API key cấu hình
    sẵn (ANTHROPIC_API_KEY / OPENAI_API_KEY), nếu không dùng mẫu có sẵn."""
    prompt = _prompt(product_name, product_desc, price, tone, cta)

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if anthropic_key:
        text = _via_anthropic(prompt, anthropic_key)
        if text:
            return text

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        text = _via_openai(prompt, openai_key)
        if text:
            return text

    return _template_fallback(product_name, product_desc, price, cta)
