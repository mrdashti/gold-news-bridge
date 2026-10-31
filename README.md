# gold-news-bridge

پل «خبرچین بورس» — خواندن **متادیتای** کانال‌های عمومی تلگرام از GitHub Actions
(خارج از ایران) و انتشار خروجی JSON در برنچ `news` برای مصرف سایت.

- هیچ متن خامی بازنشر نمی‌شود؛ فقط: کانال، زمان، نمادهای منشن‌شده، کلمات کلیدی، لحن.
- اجرا: هر ۱۰ دقیقه (`Actions → news-bridge`).
- خروجی: برنچ `news` → فایل `news_latest.json`
  (مصرف: `raw.githubusercontent.com/mrdashti/gold-news-bridge/news/news_latest.json`)
