"""موتور چندارائه‌دهنده هوش مصنوعی برای Railway Self."""
import os
import aiohttp

# همه ارائه‌دهنده‌ها با API رسمی یا API سازگار با OpenAI
PROVIDERS = {
    "openai": {"label": "OpenAI", "env": "OPENAI_API_KEY", "base": "https://api.openai.com/v1", "model": "gpt-4o-mini", "kind": "openai"},
    "anthropic": {"label": "Claude", "env": "ANTHROPIC_API_KEY", "model": "claude-3-5-haiku-latest", "kind": "anthropic"},
    "gemini": {"label": "Google Gemini", "env": "GEMINI_API_KEY", "model": "gemini-3.8-flash", "kind": "gemini"},
    "deepseek": {"label": "DeepSeek", "env": "DEEPSEEK_API_KEY", "base": "https://api.deepseek.com/v1", "model": "deepseek-chat", "kind": "openai"},
    "groq": {"label": "Groq", "env": "GROQ_API_KEY", "base": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "kind": "openai"},
    "openrouter": {"label": "OpenRouter", "env": "OPENROUTER_API_KEY", "base": "https://openrouter.ai/api/v1", "model": "openai/gpt-4o-mini", "kind": "openai"},
    "mistral": {"label": "Mistral", "env": "MISTRAL_API_KEY", "base": "https://api.mistral.ai/v1", "model": "mistral-small-latest", "kind": "openai"},
    "xai": {"label": "xAI", "env": "XAI_API_KEY", "base": "https://api.x.ai/v1", "model": "grok-2-latest", "kind": "openai"},
    "together": {"label": "Together AI", "env": "TOGETHER_API_KEY", "base": "https://api.together.xyz/v1", "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "kind": "openai"},
    "fireworks": {"label": "Fireworks AI", "env": "FIREWORKS_API_KEY", "base": "https://api.fireworks.ai/inference/v1", "model": "accounts/fireworks/models/llama-v3p3-70b-instruct", "kind": "openai"},
    "cerebras": {"label": "Cerebras", "env": "CEREBRAS_API_KEY", "base": "https://api.cerebras.ai/v1", "model": "llama-3.3-70b", "kind": "openai"},
    "perplexity": {"label": "Perplexity", "env": "PERPLEXITY_API_KEY", "base": "https://api.perplexity.ai", "model": "sonar", "kind": "openai"},
    "sambanova": {"label": "SambaNova", "env": "SAMBANOVA_API_KEY", "base": "https://api.sambanova.ai/v1", "model": "Meta-Llama-3.3-70B-Instruct", "kind": "openai"},
    "nvidia": {"label": "NVIDIA NIM", "env": "NVIDIA_API_KEY", "base": "https://integrate.api.nvidia.com/v1", "model": "meta/llama-3.3-70b-instruct", "kind": "openai"},
}
ALIASES = {"claude": "anthropic", "google": "gemini", "x-ai": "xai", "togetherai": "together"}
SYSTEM_PROMPT = "پاسخ را کوتاه، دقیق و به زبان پیام کاربر بده. اگر جزئیات بیشتری لازم است، شفاف بگو."

def _keys(provider):
    cfg = PROVIDERS[provider]
    raw = os.getenv(cfg["env"], "")
    # امکان تعریف چند کلید با جداکننده کاما؛ کلیدها هرگز در پاسخ چاپ نمی‌شوند.
    return [x.strip() for x in raw.split(",") if x.strip()]

def configured():
    return [p for p in PROVIDERS if _keys(p)]

def normalize_provider(name):
    name = (name or "").strip().lower()
    name = ALIASES.get(name, name)
    if name == "custom":
        return "custom"
    return name if name in PROVIDERS else None

def _custom_config():
    base = os.getenv("AI_BASE_URL", "").strip().rstrip("/")
    key = os.getenv("AI_API_KEY", "").strip()
    if base and key:
        return {"label": "Custom OpenAI-compatible", "base": base, "model": os.getenv("AI_CUSTOM_MODEL", "gpt-4o-mini"), "keys": [x.strip() for x in key.split(",") if x.strip()]}
    return None

async def ask(provider, model, prompt, timeout=75, system=None, history=None):
    provider = normalize_provider(provider) or "auto"
    if provider == "auto":
        available = configured()
        if _custom_config():
            available.insert(0, "custom")
        if not available:
            raise RuntimeError("هیچ API Key تنظیم نشده؛ متغیرهای Railway را بررسی کن.")
        provider = available[0]
    if provider == "custom":
        cfg = _custom_config()
        if not cfg:
            raise RuntimeError("برای Custom باید AI_BASE_URL و AI_API_KEY تنظیم شوند.")
        kind = "openai"
        keys = cfg["keys"]
    else:
        cfg = PROVIDERS[provider]
        kind = cfg["kind"]
        keys = _keys(provider)
    if not keys:
        raise RuntimeError(f"API Key سرویس {cfg['label']} تنظیم نشده است.")
    model = (model or os.getenv(f"{provider.upper()}_MODEL") or os.getenv("AI_MODEL") or cfg["model"]).strip()
    last_error = None
    for key in keys:
        try:
            timeout_cfg = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_cfg) as session:
                if kind == "anthropic":
                    url = "https://api.anthropic.com/v1/messages"
                    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
                    body = {"model": model, "max_tokens": 1200, "system": system or SYSTEM_PROMPT,
                            "messages": (list(history or []) + [{"role": "user", "content": prompt}])}
                    async with session.post(url, headers=headers, json=body) as resp:
                        data = await resp.json(content_type=None)
                        if resp.status >= 400:
                            raise RuntimeError((data.get("error") or {}).get("message", f"HTTP {resp.status}"))
                    answer = "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text")
                elif kind == "gemini":
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    body = {"systemInstruction": {"parts": [{"text": system or SYSTEM_PROMPT}]},
                            "contents": ([{"role": ("model" if x.get("role") == "assistant" else "user"), "parts": [{"text": x.get("content", "")}]} for x in (history or [])] + [{"role": "user", "parts": [{"text": prompt}]}]),
                            "generationConfig": {"maxOutputTokens": 1200}}
                    async with session.post(url, params={"key": key}, json=body) as resp:
                        data = await resp.json(content_type=None)
                        if resp.status >= 400:
                            msg = (data.get("error") or {}).get("message", f"HTTP {resp.status}")
                            raise RuntimeError(msg)
                    answer = "\n".join(p.get("text", "") for c in data.get("candidates", [])
                                       for p in c.get("content", {}).get("parts", []))
                else:
                    base = cfg.get("base") or os.getenv("AI_BASE_URL", "").rstrip("/")
                    url = base + "/chat/completions"
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                    body = {"model": model, "messages": ([{"role": "system", "content": system or SYSTEM_PROMPT}] + list(history or []) +
                        [{"role": "user", "content": prompt}]), "temperature": 0.7, "max_tokens": 1200}
                    async with session.post(url, headers=headers, json=body) as resp:
                        data = await resp.json(content_type=None)
                        if resp.status >= 400:
                            msg = (data.get("error") or {}).get("message", f"HTTP {resp.status}")
                            raise RuntimeError(str(msg)[:300])
                    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if isinstance(answer, list):
                        answer = "\n".join(x.get("text", "") for x in answer if isinstance(x, dict))
            if not answer:
                raise RuntimeError("پاسخ متنی از سرویس دریافت نشد.")
            return answer.strip(), provider, model
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"خطای {cfg['label']}: {str(last_error)[:300]}")
