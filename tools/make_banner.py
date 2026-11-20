"""ساخت بنر پنل (assets/banner.jpg): تم ریل قطار + نارنجی/مشکی. اجرا: python3 tools/make_banner.py

متن‌ها لاتین‌اند تا بدون کتابخونه‌ی شکل‌دهی فارسی درست بیان. اسم/تگ‌لاین رو بالای فایل عوض کن.
"""
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

TITLE = "RAILWAY"
SUB = "SELF"
TAGLINE = "TELEGRAM  SELF  ·  AUTOMATION  PANEL"
W, H = 1200, 800
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "..", "fonts", "DejaVuSans-Bold.ttf")
OUT = os.path.join(HERE, "..", "assets", "banner.jpg")
rnd = random.Random(7)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vgrad(w, h, top, bottom):
    img = Image.new("RGB", (w, h))
    px = ImageDraw.Draw(img)
    for y in range(h):
        px.line([(0, y), (w, y)], fill=lerp(top, bottom, y / (h - 1)))
    return img


def glow(layer, radius, strength=1.0):
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        g = Image.eval(g, lambda v: min(255, int(v * strength)))
    return g


def add(base, layer):
    return ImageChops.add(base, layer)


def main():
    img = vgrad(W, H, (5, 5, 8), (22, 8, 6))
    vp = (W // 2, 318)  # نقطه‌ی گریز ریل‌ها

    # هاله‌ی افق
    halo = Image.new("RGB", (W, H), (0, 0, 0))
    hd = ImageDraw.Draw(halo)
    for r in range(380, 0, -6):
        c = lerp((0, 0, 0), (255, 110, 20), (1 - r / 380) ** 2.2)
        hd.ellipse([vp[0] - r * 1.5, vp[1] - r * 0.55, vp[0] + r * 1.5, vp[1] + r * 0.55], fill=c)
    img = add(img, glow(halo, 30, 0.95))

    # شبکه‌ی محو زمین
    grid = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for i in range(-14, 15):
        gd.line([vp, (vp[0] + i * 170, H + 10)], fill=(70, 32, 8), width=1)
    for k in range(1, 15):
        y = vp[1] + (H - vp[1]) * (k / 14) ** 2.1
        gd.line([(0, y), (W, y)], fill=(60, 28, 8), width=1)
    img = add(img, grid)

    # ریل‌ها و تراورس‌ها
    tracks = Image.new("RGB", (W, H), (0, 0, 0))
    td = ImageDraw.Draw(tracks)
    base_l, base_r = 130, W - 130

    def edge(x_base, y):
        return vp[0] + (x_base - vp[0]) * (y - vp[1]) / (H - vp[1])

    for i in range(26):
        t = (i / 25) ** 2.05
        y = vp[1] + (H - vp[1]) * t + 4
        xl, xr = edge(base_l, y), edge(base_r, y)
        pad = 55 * (y - vp[1]) / (H - vp[1]) + 6
        th = max(2, int(2 + 20 * t))
        td.rectangle([xl - pad, y, xr + pad, y + th], fill=lerp((60, 28, 10), (255, 120, 30), t ** 0.8))
    for xb, wid in ((base_l, 12), (base_r, 12)):
        td.polygon([(vp[0] - 1.5, vp[1]), (vp[0] + 1.5, vp[1]), (xb + wid, H), (xb - wid, H)], fill=(255, 150, 50))
        td.polygon([(vp[0] - 0.6, vp[1]), (vp[0] + 0.6, vp[1]), (xb + wid * 0.45, H), (xb - wid * 0.45, H)], fill=(255, 225, 160))
    img = add(img, glow(tracks, 14, 1.1))
    img = add(img, tracks)

    # جرقه‌ها
    sp = Image.new("RGB", (W, H), (0, 0, 0))
    sd = ImageDraw.Draw(sp)
    for _ in range(140):
        x, y = rnd.randint(0, W), rnd.randint(40, H - 40)
        r = rnd.choice((1, 1, 2, 2, 3))
        c = lerp((255, 120, 20), (255, 220, 140), rnd.random())
        sd.ellipse([x - r, y - r, x + r, y + r], fill=c)
    img = add(img, glow(sp, 2.5, 1.2))
    img = add(img, Image.eval(sp, lambda v: int(v * 0.55)))

    # آرم شش‌ضلعی + رعد (بالای تصویر)
    em = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ed = ImageDraw.Draw(em)
    cx, cy, R = W // 2, 118, 62
    hexa = [(cx + R * math.cos(math.radians(60 * k - 90)), cy + R * math.sin(math.radians(60 * k - 90))) for k in range(6)]
    ed.polygon(hexa, fill=(14, 8, 4, 255))
    ed.line(hexa + [hexa[0]], fill=(255, 140, 40, 255), width=5, joint="curve")
    ed.polygon([(cx + 8, cy - 46), (cx - 26, cy + 8), (cx - 3, cy + 8), (cx - 12, cy + 46), (cx + 26, cy - 10), (cx + 3, cy - 10)], fill=(255, 190, 70, 255))
    emg = glow(Image.merge("RGB", em.split()[:3]), 16, 1.0)
    emg = ImageChops.multiply(emg, Image.merge("RGB", [em.split()[3]] * 3).filter(ImageFilter.GaussianBlur(18)))
    img = add(img, Image.eval(glow(em.convert("RGB"), 18, 1.4), lambda v: int(v * 0.8)))
    img = img.convert("RGBA")
    img.alpha_composite(em)
    img = img.convert("RGB")

    # عنوان
    def title_layer(text, size, y, skew=0.18, spacing=6):
        font = ImageFont.truetype(FONT, size)
        wtxt = sum(font.getlength(c) + spacing for c in text) - spacing
        pad = 80
        lay = Image.new("L", (int(wtxt) + pad * 2, size + 80), 0)
        d = ImageDraw.Draw(lay)
        x = pad
        for c in text:
            d.text((x, 30), c, font=font, fill=255)
            x += font.getlength(c) + spacing
        # اریب (ایتالیک)
        lay = lay.transform(lay.size, Image.AFFINE, (1, skew, -skew * lay.size[1] * 0.5, 0, 1, 0), resample=Image.BICUBIC)
        return lay, y

    def paint(lay, y, top, bottom, outline=(20, 6, 2)):
        wl, hl = lay.size
        grad = vgrad(wl, hl, top, bottom).convert("RGBA")
        solid = Image.new("RGBA", (wl, hl), (0, 0, 0, 0))
        solid.paste(grad, (0, 0), lay)
        edge_ = lay.filter(ImageFilter.MaxFilter(9))
        stroke = Image.new("RGBA", (wl, hl), outline + (255,))
        out = Image.new("RGBA", (wl, hl), (0, 0, 0, 0))
        out.paste(stroke, (0, 0), edge_)
        out.alpha_composite(solid)
        return out

    x0 = lambda im: (W - im.size[0]) // 2
    t1, y1 = title_layer(TITLE, 150, 280)
    t2, y2 = title_layer(SUB, 190, 450, spacing=22)
    for lay, y, top, bot in ((t1, y1, (255, 238, 190), (255, 120, 20)), (t2, y2, (255, 150, 90), (225, 25, 10))):
        gl = Image.merge("RGB", [lay] * 3)
        tint = ImageChops.multiply(gl, Image.new("RGB", gl.size, (255, 100, 20)))
        base = Image.new("RGB", (W, H), (0, 0, 0))
        base.paste(tint, (x0(lay), y))
        img = add(img, glow(base, 26, 1.5))
        pl = paint(lay, y, top, bot)
        img = img.convert("RGBA")
        img.alpha_composite(pl, (x0(lay), y))
        img = img.convert("RGB")

    # تگ‌لاین: روی یه نوار تیره تا زیر تراورس‌های روشن گم نشه
    f = ImageFont.truetype(FONT, 25)
    tw = sum(f.getlength(c) + 3 for c in TAGLINE)
    bar = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    bx0, bx1 = (W - tw) / 2 - 46, (W + tw) / 2 + 46
    bd.rounded_rectangle([bx0, 676, bx1, 742], radius=30, fill=(6, 3, 2, 225), outline=(255, 120, 30, 255), width=2)
    img = img.convert("RGBA")
    img.alpha_composite(bar.filter(ImageFilter.GaussianBlur(0.6)))
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)
    x = (W - tw) / 2
    for c in TAGLINE:
        d.text((x, 695), c, font=f, fill=(255, 205, 130))
        x += f.getlength(c) + 3

    # وینیت
    vg = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vg)
    vd.ellipse([-W * 0.25, -H * 0.3, W * 1.25, H * 1.3], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(120))
    img = Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), vg.point(lambda v: 90 + int(v * 0.65)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, "JPEG", quality=90, optimize=True, progressive=True)
    print("saved", OUT, os.path.getsize(OUT) // 1024, "KB", img.size)


if __name__ == "__main__":
    main()
