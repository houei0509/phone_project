"""
Phan IV (1/2): Thu thap gia ban le tu CellphoneS (cellphones.com.vn) -> data/prices_cellphones.csv
Chay tu thu muc goc du an:
    python backend/price_scraper.py --debug          # lan dau: xem co doc duoc gia khong
    python backend/price_scraper.py                  # cao tat ca trang trong danh sach
    python backend/price_scraper.py --urls-file my_urls.txt   # dung danh sach trang rieng (moi dong 1 URL)

Chi cao ~15 trang danh sach (khong cao tung trang san pham), cach nhau 6-12 giay, co cache.
TRUOC KHI CHAY: mo https://cellphones.com.vn/robots.txt tren trinh duyet va doc dieu khoan,
chi cao cac trang khong bi Disallow. Day la bai tap hoc tap, quy mo nho.
"""
import argparse, hashlib, random, re, time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache_price"
OUT = ROOT / "data" / "prices_cellphones.csv"
CACHE.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
}

# Cac trang da thay trong menu cua CellphoneS. vivo/realme CHUA kiem chung: neu 404 thi sua lai bang URL that tren trinh duyet.
DEFAULT_URLS = [
    "https://cellphones.com.vn/mobile/samsung.html",
    "https://cellphones.com.vn/mobile/samsung/galaxy-s.html",
    "https://cellphones.com.vn/mobile/samsung/galaxy-a.html",
    "https://cellphones.com.vn/mobile/samsung/galaxy-m.html",
    "https://cellphones.com.vn/mobile/samsung/galaxy-z.html",
    "https://cellphones.com.vn/mobile/apple.html",
    "https://cellphones.com.vn/mobile/apple/iphone-17.html",
    "https://cellphones.com.vn/mobile/apple/iphone-16.html",
    "https://cellphones.com.vn/mobile/xiaomi.html",
    "https://cellphones.com.vn/mobile/xiaomi/redmi/note-17-series.html",
    "https://cellphones.com.vn/mobile/oppo.html",
    "https://cellphones.com.vn/mobile/vivo.html",       # chua kiem chung
    "https://cellphones.com.vn/mobile/realme.html",     # chua kiem chung
]

PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3})+)\s*đ")
session = requests.Session()
session.headers.update(HEADERS)


def get_html(url):
    path = CACHE / (hashlib.md5(url.encode()).hexdigest() + ".html")
    if path.exists():
        return path.read_text(encoding="utf-8")
    time.sleep(random.uniform(6, 12))
    r = session.get(url, timeout=30)
    if r.status_code in (403, 429):
        raise SystemExit(f"Bi chan ({r.status_code}) o {url}. Dung lai, doi vai gio roi chay lai (cache van con).")
    if r.status_code == 404:
        print("  404 - bo qua (kiem tra lai URL):", url)
        return ""
    r.raise_for_status()
    path.write_text(r.text, encoding="utf-8")
    return r.text


def clean_name(text):
    """Lay ten may tu chu trong the <a>: cat truoc 'Tra gop', bo 'Hang moi ve', gop ten bi lap 2 lan."""
    text = text.split("Trả góp")[0]
    m = PRICE_RE.search(text)
    if m:
        text = text[:m.start()]
    text = re.sub(r"Hàng mới về|Giảm\s*\d+%", " ", text)
    words = text.replace(":", " ").split()
    n = len(words)
    for k in range(1, n // 2 + 1):                  # ten bi lap lai: A A -> A
        if n == 2 * k and words[:k] == words[k:]:
            words = words[:k]
            break
    return " ".join(words).strip()


def parse_listing(html, source):
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for a in soup.select("a[href]"):
        href = a["href"]
        if not href.endswith(".html"):
            continue
        text = a.get_text(" ", strip=True)
        prices = [int(p.replace(".", "")) for p in PRICE_RE.findall(text)]
        if not prices:
            continue
        name = clean_name(text)
        if not name or (name, href) in seen:
            continue
        seen.add((name, href))
        sale = prices[0]
        listed = prices[1] if len(prices) > 1 and prices[1] > sale else None
        rows.append({
            "Name_raw": name,
            "Price_VND": sale,                # gia ban hien tai
            "ListPrice_VND": listed,          # gia niem yet (neu dang giam gia)
            "URL": href if href.startswith("http") else "https://cellphones.com.vn" + href,
            "Source_page": source,
            "Scraped_on": date.today().isoformat(),
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls-file", help="file txt, moi dong 1 URL trang danh sach")
    ap.add_argument("--debug", action="store_true", help="in mau du lieu tho de kiem tra")
    args = ap.parse_args()
    urls = [u.strip() for u in open(args.urls_file, encoding="utf-8") if u.strip()] if args.urls_file else DEFAULT_URLS

    all_rows = []
    try:
        for u in urls:
            print("Tai:", u)
            html = get_html(u)
            if not html:
                continue
            rows = parse_listing(html, u)
            print(f"  -> {len(rows)} san pham co gia")
            if args.debug:
                soup = BeautifulSoup(html, "html.parser")
                print(f"  [debug] tong so the <a>: {len(soup.select('a[href]'))}")
                for r in rows[:3]:
                    print("  [debug]", r["Name_raw"], r["Price_VND"], r["ListPrice_VND"])
            all_rows += rows
    except SystemExit as e:
        print(e)                                  # bi chan: van luu phan da cao duoc

    if not all_rows:
        print("Khong cao duoc gi. Chay lai voi --debug va gui ket qua cho nguoi huong dan.")
        return
    df = pd.DataFrame(all_rows).drop_duplicates(subset=["Name_raw", "URL"])
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\nDa luu {OUT}: {len(df)} dong")


if __name__ == "__main__":
    main()
