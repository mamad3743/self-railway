"""نرخ ارز / طلا / سکه (بازار آزاد ایران) با چند منبع، کش دیسکی و گزارش دقیق خطا.

ترتیب منابع:
  ۱) JSON سبک tgju (call4 ← call3 ← call2 ← call) — بدون parse کردن HTML، سریع‌ترین و پایدارترین
  ۲) صفحه‌های HTML سایت tgju (روش قدیمی، با regex) — اگه JSON جواب نداد
  ۳) آخرین نرخِ ذخیره‌شده روی دیسک (با سن مشخص) — اگه هر دو منبع جواب ندادن
هیچ منبعی جواب نداد و کشی هم نبود ← FxError با دلیلِ هر منبع (تا بشه عیب‌یابی کرد).

متغیر اختیاری FX_PROXY (مثلاً http://host:port): اگه tgju به IP سرورت جواب نمی‌ده، از این پروکسی رد می‌شه.
"""
import os
import re
import json
import time
import asyncio
from urllib.parse import urlparse

import aiohttp

from core import CFG, log, save_settings

JSON_URLS = [f"https://{h}.tgju.org/ajax.json" for h in ("call4", "call3", "call2", "call")]
HTML_URLS = ["https://www.tgju.org/currency", "https://www.tgju.org/gold-chart", "https://www.tgju.org/coin"]
TIMEOUT = 10  # ثانیه برای هر درخواست
MEM_TTL = 30  # ثانیه: درخواست‌های پشت‌سرهم دوباره به شبکه نمی‌رن
STALE_MAX = 7 * 86400  # کش دیسکی تا یک هفته به‌عنوان جایگزین قابل نمایشه
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "Referer": "https://www.tgju.org/",
}
# slug های tgju (همون‌ها که توی ajax.json و صفحه‌ها هست) ← حداقل مقدار منطقی به «ریال»؛ کمتر از این یعنی عدد به تومانه
MIN_RIAL = {"price_dollar_rl": 100_000, "price_eur": 100_000, "price_gbp": 100_000, "price_aed": 30_000, "price_try": 3_000,
            "geram18": 1_000_000, "mesghal": 4_000_000, "sekee": 10_000_000, "sekeb": 10_000_000, "nim": 5_000_000,
            "rob": 3_000_000, "gerami": 1_000_000}
SLUGS = tuple(MIN_RIAL)

_mem = {"t": 0.0, "data": {}, "source": ""}
_last_save = [0.0]
_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫٬", "01234567890123456789.,")


class FxError(Exception):
    """هیچ منبعی جواب نداد؛ .errors لیست دلیل‌هاست."""

    def __init__(self, errors):
        super().__init__("; ".join(errors) or "no source")
        self.errors = list(errors)


def _proxy():
    return (os.getenv("FX_PROXY") or "").strip() or None


def _num(raw):
    """«62,550» / «۶۲٬۵۵۰» / 62550.5 ← float یا None."""
    if raw is None:
        return None
    t = re.sub(r"[^\d.]", "", str(raw).translate(_DIG))
    try:
        return float(t) if t else None
    except ValueError:
        return None


def _rial(slug, value):
    """عددهایی که به‌اشتباه به تومان‌ان (خیلی کوچیک‌تر از حد منطقی) به ریال برمی‌گردن."""
    if value is None:
        return None
    return value * 10 if value < MIN_RIAL.get(slug, 0) else value


def _why(e) -> str:
    if isinstance(e, asyncio.TimeoutError):
        return "timeout"
    if isinstance(e, aiohttp.ClientResponseError):
        return f"HTTP {e.status}"
    return (str(e) or type(e).__name__)[:70]


def _host(url) -> str:
    p = urlparse(url)
    return p.netloc + (p.path if p.path not in ("", "/") else "")


# ───────────── منبع ۱: JSON ─────────────
def parse_json(obj) -> dict:
    """ساختار tgju: {"current": {slug: {"p": "62,550", "dp": 0.4, "dt": "high"|"low", ...}}} ← {slug: {"p": ریال, "pct": درصد|None}}."""
    cur = obj.get("current") if isinstance(obj, dict) else None
    if not isinstance(cur, dict):
        raise ValueError("ساختار JSON عوض شده (کلید current نیست)")
    out = {}
    for slug in SLUGS:
        item = cur.get(slug)
        if not isinstance(item, dict):
            continue
        p = _rial(slug, _num(item.get("p")))
        if not p:
            continue
        pct = _num(item.get("dp"))
        if pct is not None and str(item.get("dt", "")).lower() in ("low", "down", "-"):
            pct = -abs(pct)
        out[slug] = {"p": p, "pct": pct}
    if not out:
        raise ValueError("هیچ‌کدوم از ارزها/سکه‌ها توی JSON نبود")
    return out


async def _fetch_json(session, url) -> dict:
    async with session.get(url, proxy=_proxy()) as r:
        r.raise_for_status()
        raw = await r.content.read(2_000_000)
    try:
        obj = json.loads(raw.decode("utf-8", "ignore"))
    except ValueError:
        raise ValueError("جواب JSON نبود (احتمالاً صفحه‌ی بلاک/کپچا)")
    return parse_json(obj)


# ───────────── منبع ۲: HTML ─────────────
ROW_TAG_RE = re.compile(r"<tr\b[^>]*data-market-nameslug=[^>]*>", re.I)
SLUG_RE = re.compile(r"""data-market-nameslug=["']([^"']+)["']""", re.I)
PRICE_RE = re.compile(r"""data-price=["']([^"']+)["']""", re.I)


def parse_html(page_html: str) -> dict:
    """از جدول‌های صفحه‌ی tgju: slug → {"p": ریال، "pct": None}."""
    out = {}
    for tag in ROW_TAG_RE.findall(page_html or ""):
        s_, p_ = SLUG_RE.search(tag), PRICE_RE.search(tag)
        if not (s_ and p_):
            continue
        v = _rial(s_.group(1), _num(p_.group(1)))
        if v:
            out[s_.group(1)] = {"p": v, "pct": None}
    return out


async def _fetch_html(session, url) -> dict:
    async with session.get(url, proxy=_proxy()) as r:
        r.raise_for_status()
        raw = await r.content.read(3_000_000)
    data = parse_html(raw.decode("utf-8", "ignore"))
    if not data:
        raise ValueError("جدول قیمت توی صفحه پیدا نشد (ظاهر سایت عوض شده یا صفحه‌ی بلاک)")
    return data


# ───────────── کش دیسکی ─────────────
def _remember(data: dict, source: str):
    now = time.time()
    _mem.update(t=now, data=data, source=source)
    if now - _last_save[0] > 60:  # ذخیره‌ی دیسکی حداکثر دقیقه‌ای یه بار
        _last_save[0] = now
        CFG["fx_cache"] = {"t": now, "data": {k: v["p"] for k, v in data.items()}}
        try:
            save_settings()
        except Exception as e:  # noqa
            log.warning("fx cache save failed: %r", e)


def _disk_cache():
    c = CFG.get("fx_cache") or {}
    t, d = c.get("t", 0), c.get("data") or {}
    if d and time.time() - t < STALE_MAX:
        return t, {k: {"p": float(v), "pct": None} for k, v in d.items() if isinstance(v, (int, float))}
    return 0, {}


# ───────────── API اصلی ─────────────
async def fetch_rates():
    """(rates, meta). rates = {slug: {"p": ریال, "pct": درصد|None}}.
    meta = {"source": "memory|json|html|cache", "t": زمان داده, "stale": bool, "errors": [..]}."""
    now = time.time()
    if _mem["data"] and now - _mem["t"] < MEM_TTL:
        return _mem["data"], {"source": "memory", "t": _mem["t"], "stale": False, "errors": []}
    errors = []
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    async with aiohttp.ClientSession(timeout=timeout, headers=HEADERS) as s:
        for url in JSON_URLS:  # یکی‌یکی تا یکی جواب بده
            try:
                data = await _fetch_json(s, url)
            except Exception as e:  # noqa
                errors.append(f"{_host(url)}: {_why(e)}")
                log.warning("fx json %s: %r", url, e)
                continue
            _remember(data, "json")
            return data, {"source": "json", "t": time.time(), "stale": False, "errors": []}
        merged = {}
        results = await asyncio.gather(*(_fetch_html(s, u) for u in HTML_URLS), return_exceptions=True)
        for url, res in zip(HTML_URLS, results):
            if isinstance(res, Exception):
                errors.append(f"{_host(url)}: {_why(res)}")
                log.warning("fx html %s: %r", url, res)
            else:
                merged.update(res)
    if merged:
        _remember(merged, "html")
        return merged, {"source": "html", "t": time.time(), "stale": False, "errors": errors}
    t, cached = _disk_cache()
    if cached:
        return cached, {"source": "cache", "t": t, "stale": True, "errors": errors}
    raise FxError(errors)
