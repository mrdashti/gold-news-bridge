"""پل خبرچین بورس — خواندن پیش‌نمایش عمومی کانال‌های تلگرام و استخراج «متادیتا».

نکته مهم: هیچ متن خامی منتشر نمی‌شود؛ فقط: کانال، زمان پست، نمادهای منشن‌شده،
کلمات کلیدی، لحن (مثبت/منفی)، طول متن — خروجی JSON برای مصرف هاست.
اجرا روی GitHub Actions (خارج از ایران) — نه روی لپ‌تاپ/هاست.
"""
from __future__ import annotations

import html as htmllib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

SITE = "https://mrdashti.ir"
SITE_TOKEN = "f0178a413c9a1c3fba09285c07702df0"

# فهرست پشتیبان (اگر سایت در دسترس نبود)
FALLBACK_CHANNELS = [
    "farshidu2",
    "hossein_adibiniya",
    "kahnamoue",
    "Identify_Movements",
    "BehnamSamadi_ir",
    "MarketSummary",
    "validhelalat",
    "sinarahbarshahlan",
    "bourse_hosein_zamani",
]

KEYWORDS = ["کدال", "مجمع", "افزایش سرمایه", "تعدیل", "شفاف‌سازی", "شفاف سازی", "گزارش", "نرخ",
            "دلار", "طلا", "سکه", "مس", "فولاد", "سنگ آهن", "عرضه اولیه", "پذیره", "سود نقدی",
            "DPS", "EPS", "صندوق", "ETF", "بازگشایی", "توقف نماد", "گزارش ماهانه", "گزارش عملکرد"]

POS = ["رشد", "افزایش", "سود", "مثبت", "صعود", "صف خرید", "تعدیل مثبت", "رکورد", "جهش",
       "بهبود", "قوی", "بازگشت", "اقبال", "خرید", "حمایت", "سقف", "بازدهی", "درخشش"]
NEG = ["افت", "کاهش", "زیان", "منفی", "نزول", "صف فروش", "تعدیل منفی", "ریزش", "فروش",
       "ضعیف", "توقف", "هشدار", "سقوط", "ترس", "اصلاح", "خروج", "ابهام", "ریسک"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def load_channels() -> list[str]:
    """فهرست منابع فعال را از سایت می‌خواند (قابل مدیریت از پنل ادمین)."""
    try:
        url = f"{SITE}/api.php?action=news_sources_list&token={SITE_TOKEN}"
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        chans = [c for c in (d.get("channels") or []) if isinstance(c, str) and c]
        if chans:
            print(f"sources from site: {len(chans)}")
            return chans
    except Exception as e:  # noqa: BLE001
        print("sources fetch failed:", str(e)[:80])
    print("using fallback channel list")
    return FALLBACK_CHANNELS


def load_symbols() -> list[str]:
    p = Path(__file__).parent / "symbols.txt"
    if not p.exists():
        return []
    syms = [s.strip() for s in p.read_text(encoding="utf-8").splitlines() if s.strip()]
    return sorted(syms, key=len, reverse=True)


def strip_tags(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = htmllib.unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


def fetch_channel(ch: str) -> list[dict]:
    url = f"https://t.me/s/{ch}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    out = []
    for block in re.findall(r'<div class="tgme_widget_message[^"]*"[^>]*>(.*?)(?=<div class="tgme_widget_message[^"]*"|$)', page, re.S):
        m = re.search(r'<time datetime="([^"]+)"', block)
        if not m:
            continue
        ts = m.group(1)
        tm = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        text = strip_tags(tm.group(1)) if tm else ""
        if not text:
            continue
        out.append({"channel": ch, "post_ts": ts[:19].replace("T", " "), "text": text})
    return out


def analyze(post: dict, symbols: list[str]) -> dict:
    text = post["text"]
    found = []
    for s in symbols:
        if s in text:
            found.append(s)
            if len(found) >= 8:
                break
    kws = [k for k in KEYWORDS if k in text][:6]
    p = sum(1 for w in POS if w in text)
    n = sum(1 for w in NEG if w in text)
    sent = (p - n) / (p + n + 1)
    return {"channel": post["channel"], "post_ts": post["post_ts"],
            "symbols": found, "keywords": kws, "sentiment": round(sent, 3),
            "text_len": len(text)}


def main() -> int:
    out_path = sys.argv[1] if len(sys.argv) > 1 else "news_latest.json"
    symbols = load_symbols()
    channels = load_channels()
    posts, ok, fail = [], [], []
    for ch in channels:
        try:
            raw = fetch_channel(ch)
            posts.extend(analyze(pp, symbols) for pp in raw)
            ok.append(ch)
        except Exception as e:  # noqa: BLE001
            fail.append(f"{ch}: {str(e)[:60]}")
        time.sleep(1.2)
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "channels_ok": len(ok), "channels_fail": fail,
        "posts": posts,
    }
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"channels ok={len(ok)} fail={len(fail)} | posts={len(posts)}")
    for f in fail:
        print("  FAIL:", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
