"""پنل «Railway Self»: پیام عکس‌دار (بنر) + کپشن + دکمه‌های رنگی، با صفحه‌های قابل ناوبری.

چیدمان (مثل سلف‌های حرفه‌ای):
  صفحه‌ی اصلی: [مدیریت سلف | حساب کاربری] + [بستن پنل]
  «مدیریت سلف» ← Self Commands | دستورات سلف: ۸ دکمه‌ی سبز (دو‌تا‌دو‌تا) + شماره‌ی صفحه‌ها (آبی) + بازگشت (قرمز)
  هر دکمه‌ی سبز ← صفحه‌ی همون قابلیت (وضعیت، راهنما، نمونه، روشن/خاموش)

این ماژول فقط متن و کیبورد می‌سازه (بدون شبکه)؛ داده‌های زنده (پینگ، نرخ ارز، اکانت) رو botpanel از قبل می‌گیره و توی ctx می‌ده.
callback_data همه‌جا با «pn:» شروع می‌شه (حداکثر ۶۴ بایت):
  pn:main · pn:close · pn:c:<صفحه> · pn:f:<کلید>:<صفحه‌ی برگشت> · pn:t:<کلید>:<0|1>:<مقصد برگشت>
  pn:info · pn:acct · pn:ctl · pn:ping · pn:game · pn:grp · pn:bak · pn:fx
"""
import math
import html

from core import F, FEATS, FEAT

BRAND = "Railway Self"
PAGE_SIZE = 8
CAPTION_MAX = 1000  # سقف تلگرام برای کپشن عکس ۱۰۲۴ کاراکتره
_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# صفحه‌ی ۱ دستورات: دسته‌های اصلی (id، برچسب)؛ بقیه‌ی صفحه‌ها: همه‌ی قابلیت‌ها به ترتیب
TOP = [("ctl", "🛠 مدیریت سلف"), ("info", "ℹ️ اطلاعات"), ("ping", "🏓 پینگ"), ("game", "🐱 بازی میویی"),
       ("grp", "🛡 مدیریت گروه"), ("bak", "💾 پشتیبان"), ("forcejoin", "🔐 عضویت اجباری"), ("fx", "💱 ارز و طلا")]
GAME_KEYS = ("automeow", "autofish", "autofridge", "autocat", "autobat", "autocatch")
GROUP_KEYS = ("guard", "locks", "filter", "forcejoin", "mute", "antidel", "secretary", "autoreply")


def fa(x) -> str:
    return str(x).translate(_FA)


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def fit(text: str, limit: int = CAPTION_MAX) -> str:
    """کپشن عکس نباید از حد تلگرام بیشتر بشه؛ از آخر خط‌به‌خط کوتاه می‌شه."""
    if len(text) <= limit:
        return text
    lines = text.split("\n")
    while len("\n".join(lines)) > limit - 2 and len(lines) > 2:
        lines.pop()
    out = "\n".join(lines)
    return out[: limit - 2] + "…" if len(out) > limit else out + "\n…"


def _b(text, data, style):
    import botpanel  # تنبل: botpanel خودش panel رو import می‌کنه
    return botpanel.btn(text, data, style)


def quote(title: str) -> str:
    return f"<blockquote>{title}</blockquote>"


# ───────────── کیبوردهای مشترک ─────────────
def nav_back(back_data: str) -> list:
    return [[_b("🔙 برگشت", back_data, "primary"), _b("🏠 منوی اصلی", "pn:main", "danger")]]


def feature_entries() -> list:
    """(کلید، برچسب) همه‌ی قابلیت‌ها به ترتیب تعریف؛ برای صفحه‌های ۲ به بعد."""
    return [(f["key"], f"{f['emoji']} {f['name']}") for f in FEATS]


def all_entries() -> list:
    return [("top:" + k, label) for k, label in TOP] + [("ft:" + k, label) for k, label in feature_entries()]


def page_count() -> int:
    n = len(TOP) + len(FEATS)
    return max(1, math.ceil(n / PAGE_SIZE))


def entry_data(entry_id: str, page: int) -> str:
    kind, _, key = entry_id.partition(":")
    if kind == "top":
        return f"pn:f:{key}:{page}" if key == "forcejoin" else f"pn:{key}"
    return f"pn:f:{key}:{page}"


# ───────────── صفحه‌ی اصلی ─────────────
def page_main():
    cap = quote(f"⚡ <b>{BRAND}</b> · پنل مدیریت")
    kb = [[_b("🛠 مدیریت سلف", "pn:c:1", "primary"), _b("👤 حساب کاربری", "pn:acct", "primary")],
          [_b("🔒 بستن پنل", "pn:close", "danger")]]
    return cap, {"inline_keyboard": kb}


def page_close():
    return quote(f"🔒 پنل <b>{BRAND}</b> بسته شد") + "\nدوباره: <code>.پنل</code>", {"inline_keyboard": []}


# ───────────── Self Commands | دستورات سلف ─────────────
def page_commands(n: int = 1):
    pages = page_count()
    n = min(max(1, int(n)), pages)
    entries = all_entries()[(n - 1) * PAGE_SIZE: n * PAGE_SIZE]
    rows, row = [], []
    for eid, label in entries:
        row.append(_b(label, entry_data(eid, n), "success"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    nums = [_b(f"「{i}」" if i == n else str(i), f"pn:c:{i}", "primary") for i in range(1, pages + 1)]
    for i in range(0, len(nums), 5):
        rows.append(nums[i:i + 5])
    rows.append([_b("بازگشت به منوی اصلی", "pn:main", "danger")])
    cap = quote("Self Commands | دستورات سلف") + f"\nصفحه‌ی {fa(n)} از {fa(pages)}"
    return cap, {"inline_keyboard": rows}


# ───────────── صفحه‌ی یک قابلیت ─────────────
def page_feature(key: str, back_page: int = 1):
    f = FEAT.get(key)
    if not f:
        return None
    on = bool(F.get(key))
    status = ("🟢 روشن" if on else "🔴 خاموش") if f["toggle"] else "🔵 دستوری"
    ex = [f"<code>{esc(e)}</code>" for e in f["examples"]]
    title = f"{f['emoji']} <b>{esc(f['name'])}</b>"
    body = f"{quote(title)}\nوضعیت: {status}\n\n{esc(f['desc'])}"
    cap = fit(body + ("\n\n<b>نمونه:</b>\n" + "\n".join(ex) if ex else ""))
    while len(cap) >= CAPTION_MAX - 2 and ex:  # نمونه‌ها رو کم کن تا جا بشه
        ex.pop()
        cap = fit(body + ("\n\n<b>نمونه:</b>\n" + "\n".join(ex) if ex else ""))
    rows = []
    if f["toggle"]:
        rows.append([_b("🔴 خاموش", f"pn:t:{key}:0:f{back_page}", "danger"), _b("🟢 روشن", f"pn:t:{key}:1:f{back_page}", "success")])
    if key == "clock":
        import core
        target = core.CFG.get("target", "last_name")
        rows.append([_b(("✅ " if target == "bio" else "") + "📝 نمایش داخل بیو", f"pn:ct:bio:{back_page}", "success" if target == "bio" else "primary"),
                     _b(("✅ " if target != "bio" else "") + "👤 نمایش کنار نام‌خانوادگی", f"pn:ct:name:{back_page}", "success" if target != "bio" else "primary")])
        rows.append([_b("🎨 فونت ساعت", f"pn:cf:menu:{back_page}", "primary")])
        rows.append([_b("🧑‍💼 راهنمای تغییر نام و فامیلی", f"pn:cf:help:{back_page}", "primary")])
    rows += nav_back(f"pn:c:{back_page}")
    return cap, {"inline_keyboard": rows}


def page_clock_fonts(back_page: int = 1):
    """صفحه‌ی جداگانه‌ی انتخاب فونت ساعت."""
    import core
    active = str(core.CFG.get("font", "2"))
    cap = quote("🎨 <b>انتخاب فونت ساعت</b>") + "\nفونت دلخواهت رو انتخاب کن:"
    rows, row = [], []
    for n, label in core.CLOCK_FONT_NAMES.items():
        selected = n == active
        row.append(_b(("✅ " if selected else "") + f"{n} · {label}",
                      f"pn:cf:{n}:{back_page}", "success" if selected else "primary"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows += nav_back(f"pn:f:clock:{back_page}")
    return cap, {"inline_keyboard": rows}


# ───────────── صفحه‌های دسته‌ای ─────────────
def _toggle_grid(keys, where: str):
    rows, row = [], []
    for k in keys:
        f = FEAT.get(k)
        if not f or not f["toggle"]:
            continue
        on = bool(F.get(k))
        row.append(_b(f"{'✅' if on else '❌'} {f['name']}", f"pn:t:{k}:{0 if on else 1}:{where}", "success" if on else "danger"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def page_game(ctx):
    cap = fit(quote("🐱 <b>بازی میویی</b>") + "\n" + (ctx.get("games_text") or "—") +
              "\n\nدکمه‌ها کلید کلیِ هر بازی‌ان؛ توی هر چت با <code>.بازی روشن</code> یا <code>.میویی</code> روشن می‌شن.")
    return cap, {"inline_keyboard": _toggle_grid(GAME_KEYS, "g") + nav_back("pn:c:1")}


def page_group():
    on = sum(1 for k in GROUP_KEYS if F.get(k))
    cap = quote("🛡 <b>مدیریت گروه</b>") + f"\n{fa(on)} از {fa(len(GROUP_KEYS))} روشنه.\nروی هر کدوم بزن تا روشن/خاموش بشه؛ تنظیم دقیق‌ترش با دستورهای نقطه‌ای (مثلاً <code>.قفل</code> <code>.فیلتر</code>)."
    return cap, {"inline_keyboard": _toggle_grid(GROUP_KEYS, "r") + nav_back("pn:c:1")}


def page_backup():
    ex = "\n".join(f"<code>{esc(e)}</code>" for e in (FEAT.get("backup") or {}).get("examples", []))
    cap = fit(quote("💾 <b>پشتیبان</b>") + "\nتنظیمات و قابلیت‌هات رو بکاپ بگیر و هر وقت خواستی برگردون.\n\n" + ex +
              "\n\n📱 از مینی‌اپ هم می‌تونی بکاپ بگیری و بازیابی کنی.")
    return cap, {"inline_keyboard": nav_back("pn:c:1")}


def page_info(ctx):
    on = sum(1 for f in FEATS if f["toggle"] and F.get(f["key"]))
    total = sum(1 for f in FEATS if f["toggle"])
    lines = [quote("ℹ️ <b>اطلاعات</b>"),
            f"⏱ مدت اجرا: {esc(ctx.get('uptime', '—'))}",
            f"🎛 قابلیت‌های روشن: <b>{fa(on)}</b> از {fa(total)}",
            f"⚡ مجموع دستورها: {fa(len(FEATS))}"]
    if ctx.get("bot"):
        lines.append(f"🤖 بات: @{esc(ctx['bot'])}")
    lines.append(f"🌐 پنل وب: {esc(ctx['web']) if ctx.get('web') else 'تنظیم نشده'}")
    lines.append(f"📱 مینی‌اپ: {'فعال ✅' if ctx.get('app') else 'تنظیم نشده'}")
    return "\n".join(lines), {"inline_keyboard": nav_back("pn:c:1")}


def page_account(ctx):
    me = ctx.get("me") or {}
    lines = [quote("👤 <b>حساب کاربری</b>")]
    if me:
        lines += [f"نام: <b>{esc(me.get('name') or '—')}</b>",
                  f"یوزرنیم: {('@' + esc(me['username'])) if me.get('username') else '—'}",
                  f"آیدی: <code>{esc(me.get('id'))}</code>", "🔐 وضعیت اکانت: وصل ✅"]
    else:
        lines.append("🔌 اکانت وصل نیست یا اطلاعاتش در دسترس نیست.")
    if ctx.get("sub"):
        lines.append(f"🎫 اشتراک: {esc(ctx['sub'])}")
    return "\n".join(lines), {"inline_keyboard": nav_back("pn:main")}


def page_control(ctx):
    rows = []
    urls = []
    if ctx.get("app_link"):
        urls.append({"text": "📱 مینی‌اپ", "url": ctx["app_link"]})
    if ctx.get("web"):
        urls.append({"text": "🌐 پنل وب", "url": ctx["web"]})
    if urls:
        rows.append(urls)
    rows.append([_b("🔄 تازه‌سازی", "pn:ctl", "primary")])
    rows += nav_back("pn:c:1")
    on = sum(1 for f in FEATS if f["toggle"] and F.get(f["key"]))
    cap = fit(quote("🛠 <b>مدیریت سلف</b>") + f"\n⏱ مدت اجرا: {esc(ctx.get('uptime', '—'))}\n🎛 قابلیت‌های روشن: <b>{fa(on)}</b>\n\n"
              "برای روشن/خاموش کردن تک‌تک قابلیت‌ها از صفحه‌های شماره‌دار «دستورات» استفاده کن، یا مینی‌اپ/پنل وب رو باز کن.")
    return cap, {"inline_keyboard": rows}


def page_ping(ctx):
    p = ctx.get("ping") or {}
    cap = (quote("🏓 <b>پینگ</b>") + f"\n🤖 بات: <b>{fa(p.get('bot', '—'))}</b> میلی‌ثانیه\n"
           f"👤 سلف ↔ تلگرام: <b>{fa(p.get('self', '—'))}</b> میلی‌ثانیه\n⏱ مدت اجرا: {esc(ctx.get('uptime', '—'))}")
    return cap, {"inline_keyboard": [[_b("🔄 دوباره", "pn:ping", "primary")]] + nav_back("pn:c:1")}


def page_fx(ctx):
    cap = fit(quote("💱 <b>ارز و طلا</b>") + "\n" + (ctx.get("rates_text") or "نرخ در دسترس نیست."))
    return cap, {"inline_keyboard": [[_b("🔄 تازه‌سازی", "pn:fx", "primary")]] + nav_back("pn:c:1")}


def rates_text(rates: dict, meta: dict, now_hm: str) -> str:
    """خلاصه‌ی نرخ برای صفحه‌ی ارز (تومان)."""
    pick = [("💵", "دلار", "price_dollar_rl"), ("💶", "یورو", "price_eur"), ("🟡", "طلای ۱۸", "geram18"), ("🪙", "سکه امامی", "sekee")]
    lines = []
    for emoji, name, slug in pick:
        r = (rates.get(slug) or {}).get("p")
        if r:
            lines.append(f"{emoji} {name}: <b>{fa(f'{int(r / 10):,}').replace(',', '٬')}</b> تومان")
    head = "⚠️ آخرین نرخ ثبت‌شده (منابع جواب ندادن)" if meta.get("stale") else f"🕒 {fa(now_hm)}"
    return head + "\n" + ("\n".join(lines) if lines else "نرخ پیدا نشد.")


# ───────────── مسیریاب ─────────────
def render(data: str, ctx: dict = None):
    """data (pn:...) ← (کپشن، کیبورد) یا None."""
    ctx = ctx or {}
    parts = data.split(":")
    if parts[0] != "pn" or len(parts) < 2:
        return None
    k = parts[1]
    try:
        if k == "main":
            return page_main()
        if k == "close":
            return page_close()
        if k == "c":
            return page_commands(int(parts[2]) if len(parts) > 2 else 1)
        if k == "f" and len(parts) >= 3:
            return page_feature(parts[2], int(parts[3]) if len(parts) > 3 else 1)
        if k == "cf" and len(parts) >= 3 and parts[2] == "menu":
            return page_clock_fonts(int(parts[3]) if len(parts) > 3 else 1)
        simple = {"info": lambda: page_info(ctx), "acct": lambda: page_account(ctx), "ctl": lambda: page_control(ctx),
                  "ping": lambda: page_ping(ctx), "game": lambda: page_game(ctx), "grp": page_group, "bak": page_backup,
                  "fx": lambda: page_fx(ctx)}
        if k in simple and len(parts) == 2:
            return simple[k]()
    except (ValueError, IndexError):
        return None
    return None


def parse_toggle(data: str):
    """pn:t:<کلید>:<0|1>:<مقصد> ← (کلید، مقدار، callback برگشت) یا None."""
    p = data.split(":")
    if len(p) != 5 or p[0] != "pn" or p[1] != "t" or p[3] not in ("0", "1"):
        return None
    key, val, where = p[2], p[3] == "1", p[4]
    if key not in FEAT or not FEAT[key]["toggle"]:
        return None
    if where == "g":
        back = "pn:game"
    elif where == "r":
        back = "pn:grp"
    elif where.startswith("f") and where[1:].isdigit():
        back = f"pn:f:{key}:{int(where[1:])}"
    else:
        return None
    return key, val, back
