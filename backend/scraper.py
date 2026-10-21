"""
Phan I (v2): Thu thap thong so dien thoai tu GSMArena -> CSV (~30 cot so)
Vi du:
  python backend/scraper.py --brands samsung --min-year 2024 --limit 30 --out results_samsung.csv
Co cache HTML (cache_html/) + sleep de tranh bi chan (429).
"""
import random 
import argparse, hashlib, os, re, time
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE = "https://www.gsmarena.com/"
CACHE = "cache_html"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
DELAY_MIN, DELAY_MAX = 10, 20  # giay giua cac request, dung giam qua thap

os.makedirs(CACHE, exist_ok=True)
session = requests.Session()
session.headers.update(HEADERS)


# ---------- Tai trang ----------
def get_html(url):
    path = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest() + ".html")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    r = session.get(url, timeout=30)
    if r.status_code == 429:
        raise SystemExit("Bi GSMArena chan (429). Doi 30-60 phut hoac doi mang roi chay lai, cache van con.")
    r.raise_for_status()
    open(path, "w", encoding="utf-8").write(r.text)
    return r.text


def get_brand_links():
    soup = BeautifulSoup(get_html(BASE + "makers.php3"), "html.parser")
    out = {}
    for a in soup.select("table a"):
        href = a.get("href", "")
        if "-phones-" in href:
            name = re.sub(r"\d+\s*devices?$", "", a.get_text(" ", strip=True)).strip().lower()
            out[name] = BASE + href
    return out


def get_phone_links(brand_url, limit):
    links, url = [], brand_url
    while url and len(links) < limit:
        soup = BeautifulSoup(get_html(url), "html.parser")
        links += [BASE + a["href"] for a in soup.select("div.makers li a")]
        nxt = soup.select_one("a.pages-next")
        url = BASE + nxt["href"] if nxt and nxt.get("href", "").endswith(".php") else None
    return links[:limit]


# ---------- Ham tien ich de doc so ----------
def num(text, pat=r"\d[\d,]*\.?\d*"):
    m = re.search(pat, text or "")
    if not m:
        return None
    s = m.group(1) if m.groups() else m.group()
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def flag(v, no_prefix="no"):
    """Yes/No -> 1/0; khong co thong tin -> None."""
    if not v:
        return None
    return 0 if v.strip().lower().startswith(no_prefix) else 1


def get_specs(soup):
    """Gom bang thong so thanh dict {'Danh muc|Nhan': 'gia tri'} (tranh trung 'Type', 'Size'...)."""
    specs = {}
    for table in soup.select("#specs-list table"):
        th = table.select_one("th")
        cat = th.get_text(strip=True) if th else ""
        last = ""
        for row in table.select("tr"):
            ttl, nfo = row.select_one("td.ttl"), row.select_one("td.nfo")
            if not nfo:
                continue
            label = ttl.get_text(" ", strip=True).strip() if ttl else ""
            label = label or last          # dong khong co nhan -> noi tiep dong truoc
            last = label
            key = f"{cat}|{label}"
            val = nfo.get_text(" ", strip=True)
            specs[key] = f"{specs[key]} ; {val}" if key in specs else val
    return specs


LENS = {"Single": 1, "Dual": 2, "Triple": 3, "Quad": 4, "Penta": 5}
CORES = {"Dual": 2, "Quad": 4, "Hexa": 6, "Octa": 8, "Nona": 9, "Deca": 10}


def camera(specs, cat):
    for label, n in LENS.items():
        v = specs.get(f"{cat}|{label}")
        if v:
            return num(v, r"(\d+(?:\.\d+)?)\s*MP"), n
    return None, None


def price_eur(text):
    m = re.search(r"€\s*([\d,]+(?:\.\d+)?)", text or "") or re.search(r"([\d,]+(?:\.\d+)?)\s*EUR", text or "")
    return float(m.group(1).replace(",", "")) if m else None


# ---------- Doc 1 chiec dien thoai ----------
def parse_phone(url, brand):
    soup = BeautifulSoup(get_html(url), "html.parser")
    title = soup.select_one("h1.specs-phone-name-title")
    if not title:
        return None
    s = get_specs(soup)
    g = lambda k: s.get(k, "")

    dims = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*x\s*([\d.]+)\s*mm", g("Body|Dimensions"))
    res = re.search(r"(\d+)\s*x\s*(\d+)", g("Display|Resolution"))
    nits = [int(x) for x in re.findall(r"(\d+)\s*nits", g("Display|Type"))]
    mem = g("Memory|Internal")
    rams = [float(x) for x in re.findall(r"(\d+)\s*GB\s*RAM", mem)]
    roms = [float(n) * (1024 if u == "TB" else 1) for n, u in re.findall(r"(\d+)\s*(GB|TB)(?!\s*RAM)", mem)]
    cpu = re.search(r"(Dual|Quad|Hexa|Octa|Nona|Deca)-core", g("Platform|CPU"))
    charge = g("Battery|Charging")
    wired = num(charge, r"(\d+)\s*W\s*wired") or num(charge, r"(\d+)\s*W")
    wireless = num(charge, r"(\d+)\s*W\s*wireless")
    main_mp, main_n = camera(s, "Main Camera")
    self_mp, _ = camera(s, "Selfie camera")
    ip = re.search(r"\bIP(\d{2})\b", " ".join(s.values()))
    perf = g("Tests|Performance")

    return {
        "Name": title.get_text(strip=True),
        "Brand": brand.title(),
        "Year": num(g("Launch|Announced"), r"((?:19|20)\d{2})"),
        "Weight_g": num(g("Body|Weight"), r"([\d.]+)\s*g"),
        "Length_mm": float(dims.group(1)) if dims else None,
        "Width_mm": float(dims.group(2)) if dims else None,
        "Thickness_mm": float(dims.group(3)) if dims else None,
        "Display_inch": num(g("Display|Size"), r"([\d.]+)\s*inches"),
        "ScreenToBody_pct": num(g("Display|Size"), r"~?\s*([\d.]+)%"),
        "Res_W": float(res.group(1)) if res else None,
        "Res_H": float(res.group(2)) if res else None,
        "PPI": num(g("Display|Resolution"), r"~?\s*(\d+)\s*ppi"),
        "Refresh_Hz": num(g("Display|Type"), r"(\d+)\s*Hz"),
        "Peak_nits": max(nits) if nits else None,
        "Chipset_nm": num(g("Platform|Chipset"), r"\((\d+)\s*nm\)"),
        "CPU_cores": CORES.get(cpu.group(1)) if cpu else None,
        "RAM_GB": max(rams) if rams else None,
        "Storage_GB": max(roms) if roms else None,
        "SD_slot": flag(g("Memory|Card slot")),
        "Battery_mAh": num(g("Battery|Type"), r"(\d[\d,]*)\s*mAh"),
        "Charge_W": wired,
        "Wireless_W": wireless if wireless is not None else (0 if charge else None),
        "MainCam_MP": main_mp,
        "MainCam_lenses": main_n,
        "SelfieCam_MP": self_mp,
        "NFC": flag(g("Comms|NFC")),
        "Jack_3_5mm": flag(g("Sound|3.5mm jack")),
        "IP_rating": float(ip.group(1)) if ip else 0.0,
        "Bluetooth_ver": num(g("Comms|Bluetooth"), r"(\d\.\d)"),
        "AnTuTu": num(perf, r"AnTuTu:\s*([\d,]+)"),
        "GeekBench": num(perf, r"GeekBench:\s*([\d,]+)"),
        "Price_EUR": price_eur(g("Misc|Price")),
        "Chipset": g("Platform|Chipset") or "N/a",
        "URL": url,
    }


def is_phone(rec):
    """Loai may tinh bang / dong ho."""
    if re.search(r"\b(Tab|Pad|Watch|Band)\b", rec["Name"], re.I):
        return False
    return rec["Display_inch"] is None or rec["Display_inch"] <= 9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brands", nargs="+", required=True)
    ap.add_argument("--min-year", type=int, default=2023)
    ap.add_argument("--limit", type=int, default=40, help="so link toi da moi hang (truoc khi loc)")
    ap.add_argument("--out", default="results.csv", help="ten file CSV dau ra")
    args = ap.parse_args()
    brand_links = get_brand_links()
    rows = []
    try:
        for b in args.brands:
            if b.lower() not in brand_links:
                print("Khong thay hang:", b)
                continue
            for link in get_phone_links(brand_links[b.lower()], args.limit):
                try:
                    rec = parse_phone(link, b)
                except Exception as e:
                    print("Bo qua", link, "->", e)
                    continue
                if rec and rec["Year"] and rec["Year"] >= args.min_year and is_phone(rec):
                    rows.append(rec)
                    print(rec["Brand"], "-", rec["Name"])
    except SystemExit as e:
        print(e)  # bi chan: van luu phan da cao duoc ben duoi

    
    df = pd.DataFrame(rows)
    df = df.sort_values(["Name", "Year"], ascending=[True, False]).fillna("N/a")
    df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Da luu {args.out}: {df.shape[0]} may, {df.shape[1]} cot")


if __name__ == "__main__":
    main()
