"""
おむつ単価くらべ: 楽天市場・Yahoo!ショッピング・Amazonから紙おむつの価格を集めて data.json を作る

環境変数（GitHubのSecretsに登録。コードに直接書かないこと）
  楽天
    RAKUTEN_APP_ID        アプリケーションID
    RAKUTEN_ACCESS_KEY    アクセスキー
    RAKUTEN_AFFILIATE_ID  アフィリエイトID
    RAKUTEN_REFERER       楽天のアプリ登録で許可したサイトのURL
  Yahoo!ショッピング（未設定ならYahoo!はスキップ）
    YAHOO_CLIENT_ID       Yahoo!デベロッパーネットワークのClient ID
    VC_SID / VC_PID       バリューコマースのYahoo!ショッピング用 sid と pid
  Amazon（未設定ならAmazonはスキップ）
    AMAZON_CREDENTIAL_ID / AMAZON_CREDENTIAL_SECRET  Creators APIの認証情報
    AMAZON_API_VERSION    認証情報のバージョン（例 3.3）
    AMAZON_PARTNER_TAG    アソシエイトのトラッキングID（例 xxxx-22）

ローカルで商品名の読み取りだけ試す:  python fetch_prices.py --test "商品名"
"""
import json
import os
import re
import statistics
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone

RAKUTEN_VERSIONS = ["20260701", "20220601"]
RAKUTEN_BASE = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/"
YAHOO_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"

JST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
TOP_N = 10           # 商品ごとに残すショップ数（全モールの合計）
RAKUTEN_PAGES = 3    # 楽天: 1ページ30件
YAHOO_PAGES = 2      # Yahoo!: 1ページ50件
AMAZON_PAGES = 3     # Amazon: 1ページ10件
WAIT_SEC = 1.2       # APIへのアクセス間隔（どれも1秒1回まで）
MIN_PRICE = 700      # これより安い出品（お試しパックなど）は取らない
# 送料の金額はAPIでわからないため、送料無料でない出品にはこの目安額を足す
SHIPPING_ESTIMATE = 800
# 1枚の値段として現実的な範囲（外れたら枚数の読み違いとみなす）
PER_SHEET_RANGE = (8, 120)

SIZE_KEYWORD = {"新生児": "新生児", "S": "Sサイズ", "M": "Mサイズ", "L": "Lサイズ",
                "ビッグ": "ビッグ", "ビッグより大きい": "ビッグより大きい"}
SIZE_SLUG = {"新生児": "nb", "S": "s", "M": "m", "L": "l", "ビッグ": "big", "ビッグより大きい": "xbig"}
TYPE_SLUG = {"テープ": "tape", "パンツ": "pants"}



RAKUTEN_RTLINK = "_RTLink150941"   # 楽天アフィリエイトの計測ID（omutsu-tanka）


def add_rtlink(obj):
    """楽天のアフィリエイトリンクに計測IDを付ける（成果をサイトごとに分けて見るため）"""
    if isinstance(obj, dict):
        return {k: add_rtlink(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [add_rtlink(v) for v in obj]
    if isinstance(obj, str) and "hb.afl.rakuten.co.jp/" in obj and "_RTLink" not in obj:
        return re.sub(r"(hb\.afl\.rakuten\.co\.jp/(?:hgc|ichiba)/[^/?]+/)\?", r"\g<1>" + RAKUTEN_RTLINK + "?", obj, count=1)
    return obj

def env(name, required=False):
    v = os.environ.get(name, "").strip()
    if required and not v:
        sys.exit(f"環境変数 {name} が設定されていません")
    return v


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "omutsu-tanka/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def nfkc(s):
    return unicodedata.normalize("NFKC", s)


def low(s):
    return kana_bar(nfkc(s)).lower()


def kana_bar(t):
    """「ム-ニ-マン」のようにカタカナの間のハイフンを長音「ー」にそろえる"""
    return re.sub(r"(?<=[ァ-ヴ])[-‐‑–—―−ｰ](?=[ァ-ヴ]|$|\s)", "ー", t)


# ================= 楽天 =================
def rakuten_call(params, referer):
    headers = {"Referer": referer, "Origin": referer.rstrip("/")}
    last_err = None
    for ver in RAKUTEN_VERSIONS:
        url = RAKUTEN_BASE + ver + "?" + urllib.parse.urlencode(params)
        try:
            return get_json(url, headers)
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code} ({ver}): {e.read().decode('utf-8', 'replace')[:300]}"
            if e.code == 404:
                continue
            break
    raise RuntimeError(last_err)


def rakuten_items(keyword, cfg):
    out = []
    for page in range(1, RAKUTEN_PAGES + 1):
        params = {
            "applicationId": cfg["app_id"], "accessKey": cfg["access_key"],
            "keyword": keyword, "NGKeyword": "中古 お試し 水遊び",
            "sort": "standard", "minPrice": MIN_PRICE,
            "availability": 1, "hits": 30, "page": page, "imageFlag": 1,
            "format": "json", "formatVersion": 2,
        }
        if cfg["aff_id"]:
            params["affiliateId"] = cfg["aff_id"]
        if page > 1:
            time.sleep(WAIT_SEC)
        data = rakuten_call(params, cfg["referer"])
        for it in data.get("Items") or data.get("items") or []:
            it = it.get("Item", it)
            imgs = it.get("mediumImageUrls") or []
            img = imgs[0] if imgs else ""
            if isinstance(img, dict):
                img = img.get("imageUrl", "")
            out.append({
                "mall": "楽天",
                "name": it.get("itemName", ""),
                "price": int(it.get("itemPrice", 0) or 0),
                "free_shipping": it.get("postageFlag") == 0,
                "shop": it.get("shopName", ""),
                "url": it.get("affiliateUrl") or it.get("itemUrl", ""),
                "image": img,
                "point_rate": int(it.get("pointRate", 1) or 1),
            })
        if page >= int(data.get("pageCount", 1) or 1):
            break
    return out


# ================= Yahoo!ショッピング =================
def vc_link(url, sid, pid):
    if not (sid and pid):
        return url
    return ("https://ck.jp.ap.valuecommerce.com/servlet/referral?"
            f"sid={sid}&pid={pid}&vc_url=" + urllib.parse.quote(url, safe=""))


def yahoo_items(keyword, cfg):
    out = []
    for page in range(YAHOO_PAGES):
        params = {
            "appid": cfg["client_id"], "query": keyword,
            "results": 50, "start": 1 + page * 50, "sort": "-score",
            "price_from": MIN_PRICE, "in_stock": "true", "image_size": 146,
        }
        if page:
            time.sleep(WAIT_SEC)
        try:
            data = get_json(YAHOO_URL + "?" + urllib.parse.urlencode(params))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}")
        hits = data.get("hits") or []
        for h in hits:
            ship = (h.get("shipping") or {}).get("code")
            img = h.get("image") or {}
            out.append({
                "mall": "Yahoo!",
                "name": h.get("name", ""),
                "price": int(h.get("price", 0) or 0),
                "free_shipping": ship == 2,          # 2 = 送料無料
                "shop": (h.get("seller") or {}).get("name", ""),
                "url": vc_link(h.get("url", ""), cfg["vc_sid"], cfg["vc_pid"]),
                "image": img.get("medium") or img.get("small") or "",
                "point_rate": int((h.get("point") or {}).get("times", 1) or 1),
            })
        if len(hits) < 50:
            break
    return out


# ================= Amazon（Creators API） =================
def _get(obj, *path):
    for p in path:
        if obj is None:
            return None
        obj = obj[p] if isinstance(p, int) else getattr(obj, p, None)
    return obj


def amazon_items(keyword, cfg):
    from amazon_creatorsapi import AmazonCreatorsApi, Country

    if "client" not in cfg:
        cfg["client"] = AmazonCreatorsApi(
            credential_id=cfg["credential_id"], credential_secret=cfg["credential_secret"],
            version=cfg["version"], tag=cfg["tag"], country=Country.JP)
    api = cfg["client"]
    out = []
    for page in range(1, AMAZON_PAGES + 1):
        if page > 1:
            time.sleep(WAIT_SEC)
        try:
            res = api.search_items(keywords=keyword, item_count=10, item_page=page)
        except Exception as e:
            if type(e).__name__ == "ItemsNotFoundError":
                break
            raise
        items = _get(res, "items") or []
        for it in items:
            listings = _get(it, "offers_v2", "listings") or []
            if not listings:
                continue
            lst = listings[0]
            amount = _get(lst, "price", "money", "amount")
            if not amount:
                continue
            merchant = _get(lst, "merchant_info", "name") or "Amazon"
            out.append({
                "mall": "Amazon",
                "name": _get(it, "item_info", "title", "display_value") or "",
                "price": int(round(float(amount))),
                # Amazon販売分は送料無料として扱い、他の出品者は目安送料を足す
                "free_shipping": "amazon" in merchant.lower(),
                "shop": merchant,
                "url": _get(it, "detail_page_url") or "",
                "image": _get(it, "images", "primary", "medium", "url")
                         or _get(it, "images", "primary", "large", "url") or "",
                "point_rate": 1,
            })
        if len(items) < 10:
            break
    return out


# ================= 商品名の読み取り =================
NOT_LETTER_BEFORE = r"(?<![A-Za-z])"
NOT_LETTER_AFTER = r"(?![A-Za-z])"
SIZE_PATTERNS = {
    "ビッグより大きい": r"ビッグより大き|BIGより大き|ビッグよりおおき|ビッグ大|BIG大|XXL",
    "ビッグ": r"ビッグ(?!より)|BIG(?!より)|" + NOT_LETTER_BEFORE + "XL" + NOT_LETTER_AFTER,
    "L": NOT_LETTER_BEFORE + "L" + NOT_LETTER_AFTER,
    "M": NOT_LETTER_BEFORE + "M" + NOT_LETTER_AFTER,
    "S": NOT_LETTER_BEFORE + "S" + NOT_LETTER_AFTER,
    "新生児": r"新生児|お誕生|" + NOT_LETTER_BEFORE + "NB" + NOT_LETTER_AFTER,
}


def detect_sizes(name):
    """商品名に出てくるサイズをすべて返す（例 {'M'}）。'S〜M'などは両方入る"""
    t = nfkc(name)
    # 「ビッグより大きい」が「ビッグ」として二重に数えられないように先に消す
    found = set()
    for size, pat in SIZE_PATTERNS.items():
        if re.search(pat, t):
            found.add(size)
            t = re.sub(pat, " ", t)
    return found


def parse_sheets(name):
    """商品名から合計枚数を読む。「232枚(58枚×4)」「58枚×4パック」「64枚 3個セット」など"""
    t = nfkc(name)
    t = re.sub(r"(\d{1,4})\s*(?:マイ|P)(?![A-Za-z])", r"\1枚", t)   # 「38マイ」「26P」
    vals = [int(x) for x in re.findall(r"(\d{1,4})\s*枚", t)]
    vals = [v for v in vals if 2 <= v <= 1500]
    if not vals:
        return None
    mx = max(vals)
    # 合計と内訳が両方書いてある → 合計をそのまま使う
    if any(v < mx and mx % v == 0 and 2 <= mx // v <= 16 for v in vals):
        return mx
    # 「58枚×4」「58枚入り)×4」
    m = re.search(rf"{mx}\s*枚(?:入り?)?\s*[)）\]】]?\s*[×xX✕*]\s*(\d{{1,2}})(?!\d)", t)
    if m and 2 <= int(m.group(1)) <= 16:
        return mx * int(m.group(1))
    # 「4パック」「3個セット」「×2」
    t2 = re.sub(r"\d{1,4}\s*枚", " ", t)
    t2 = re.sub(r"\d+(?:\.\d+)?[~〜\-]\d+(?:\.\d+)?", " ", t2)          # 「6-11kg」などの範囲
    t2 = re.sub(r"\d+(?:\.\d+)?\s*(?:kg|g|cm|時間|ヶ月|か月|カ月|歳|才|倍|%|円|日|位)", " ", t2, flags=re.I)
    ks = [int(m.group(1)) for m in re.finditer(r"(\d{1,2})\s*(?:パック|個|袋|セット|コ|ケース)(?!入)", t2)]
    ks += [int(m.group(1)) for m in re.finditer(r"[×xX✕*]\s*(\d{1,2})(?!\d)", t2)]
    ks = [k for k in ks if 2 <= k <= 16]
    return mx * max(ks) if ks else mx


def expand(catalog):
    """products.json の「ライン×タイプ×サイズ」を1つずつの比較対象に展開する"""
    common_ng = catalog.get("common_ng", [])
    for line in catalog["lines"]:
        for typ, tcfg in line["types"].items():
            for size in tcfg["sizes"]:
                yield {
                    "id": f"{line['id']}_{TYPE_SLUG[typ]}_{SIZE_SLUG[size]}",
                    "maker": line["maker"], "brand": line["brand"], "name": line["name"],
                    "type": typ, "size": size,
                    "keyword": f"{tcfg['keyword']} {SIZE_KEYWORD[size]}",
                    "must": line.get("must", []) + tcfg.get("must", []),
                    "must_any": tcfg.get("must_any") or line.get("must_any") or [],
                    "ng": common_ng + line.get("ng", []) + tcfg.get("ng", []),
                    "type_words": tcfg.get("type_words") or [typ],
                    "other_type_words": ["パンツ"] if typ == "テープ" else ["テープ"],
                }


SAMPLES = {}          # 除外した商品名の例（debug.json 用）


def reject(stats, reason, name):
    stats[reason] += 1
    box = SAMPLES.setdefault(stats["_id"], {}).setdefault(reason, [])
    if len(box) < 5 and name not in box:
        box.append(name)
    return None


def to_offer(product, it, stats):
    name, norm = it["name"], low(it["name"])
    if not all(low(w) in norm for w in product["must"]):
        return reject(stats, "条件の言葉なし", name)
    if product["must_any"] and not any(low(w) in norm for w in product["must_any"]):
        return reject(stats, "条件の言葉なし", name)
    if any(low(w) in norm for w in product["ng"]):
        return reject(stats, "除外ワード", name)
    if not any(low(w) in norm for w in product["type_words"]) or \
            any(low(w) in norm for w in product["other_type_words"]):
        return reject(stats, "タイプ違い", name)
    sizes = detect_sizes(name)
    if sizes != {product["size"]}:
        return reject(stats, "サイズ違い・複数", name)
    sheets = parse_sheets(name)
    if not sheets or not it["price"]:
        return reject(stats, "枚数が読めない", name)

    # 楽天24（ベビー館など）は39ショップ：3,980円以上は送料無料（API上は「送料別」と返ることがある）
    if it["mall"] == "楽天" and it["shop"].startswith("楽天24") and it["price"] >= 3980:
        it = {**it, "free_shipping": True}
    shipping = 0 if it["free_shipping"] else SHIPPING_ESTIMATE
    total = it["price"] + shipping
    per = total / sheets
    if not (PER_SHEET_RANGE[0] <= per <= PER_SHEET_RANGE[1]):
        return reject(stats, "単価が不自然", name)
    pr = it["point_rate"]
    return {
        "mall": it["mall"], "shop": it["shop"], "item_name": name,
        "price": it["price"], "postage_separate": not it["free_shipping"],
        "shipping_estimate": shipping, "total": total, "sheets": sheets,
        "per_sheet": round(per, 2),
        "point_rate": pr,
        "per_sheet_after_points": round((total - it["price"] * pr / 100) / sheets, 2),
        "url": it["url"], "image": it["image"],
    }


def build(product, raw_items):
    stats = Counter(fetched=len(raw_items))
    stats["_id"] = product["id"]
    offers = [o for o in (to_offer(product, it, stats) for it in raw_items) if o]
    if len(offers) >= 3:
        med = statistics.median(o["per_sheet"] for o in offers)
        before = len(offers)
        offers = [o for o in offers if o["per_sheet"] >= med * 0.6]
        stats["安すぎて除外"] += before - len(offers)
    best = {}
    for o in sorted(offers, key=lambda o: o["per_sheet"]):
        best.setdefault((o["mall"], o["shop"]), o)
    offers = sorted(best.values(), key=lambda o: o["per_sheet"])
    stats["使えた件数"] = len(offers)
    del stats["_id"]
    return offers[:TOP_N], dict(stats)


# ================= 手動のお得情報（deals.json） =================
def rakuten_aff_link(url, aff_id):
    if "hb.afl.rakuten.co.jp" in url:                # すでにアフィリエイトリンク
        return url
    url = re.sub(r"[?&]scid=[^&#]*", "", url)        # アプリの共有用パラメータを外す
    if not aff_id or "rakuten.co.jp" not in url:
        return url
    q = urllib.parse.quote(url, safe="")
    return f"https://hb.afl.rakuten.co.jp/hgc/{aff_id}/?pc={q}&m={q}"


def build_deals(aff_id):
    """deals.json を読み、期限切れを除いて、サイズごとのクーポン後1枚単価を計算する"""
    path = os.path.join(HERE, "deals.json")
    if not os.path.exists(path):
        return [], []
    with open(path, encoding="utf-8") as f:
        src = json.load(f)
    now = datetime.now(JST)
    alive = lambda iso: not iso or datetime.fromisoformat(iso) > now
    out = []
    for d in src.get("deals", []):
        if not alive(d.get("until")):
            continue
        link = rakuten_aff_link(d["url"], aff_id) if d.get("mall", "楽天") == "楽天" else d["url"]
        for v in d["variants"]:
            pay = v["price"] - d.get("coupon", 0) + (0 if d.get("free_shipping", True) else SHIPPING_ESTIMATE)
            pb_on = alive(d.get("point_until"))          # ポイントバックだけ先に終わることがある
            back = pay * (1 + (d.get("point_back", 0) if pb_on else 0)) / 100
            bulk_note = ""
            bc = d.get("bulk_coupon")                   # 例: 10,000円以上で1,500円OFF
            if bc and alive(bc.get("until")):
                qty = -(-bc["min_price"] // v["price"])
                bpay = v["price"] * qty - bc["amount"]
                bper = bpay / (v["sheets"] * qty)
                if bper < pay / v["sheets"] - 0.05:
                    bulk_note = (f"{qty}セットまとめ買い（{bc['min_price']:,}円以上）なら{bc['amount']:,}円OFFクーポンで"
                                 f"¥{bpay:,}・{v['sheets'] * qty}枚＝1枚{bper:.1f}円")
            out.append({
                "id": f"{d['id']}-{SIZE_SLUG.get(v['size'], v['size'])}" + (f"-{v['asin']}" if v.get("asin") else ""),
                "bulk_note": bulk_note,
                "ref": (f"{d['line']}_{TYPE_SLUG.get(d['type'], '')}_{SIZE_SLUG.get(v['size'], '')}"
                        if d.get("line") else ""),
                **{k: d[k] for k in ("maker", "brand", "name", "type", "mall", "shop")},
                "size": v["size"], "label": v.get("label", ""), "sheets": v["sheets"],
                "price": v["price"], "coupon": d.get("coupon", 0), "pay": pay,
                "per_sheet": round(pay / v["sheets"], 2),
                "per_sheet_after_points": round((pay - back) / v["sheets"], 2),
                "coupon_note": d.get("coupon_note", ""), "point_note": d.get("point_note", "") if pb_on else "",
                "until": d.get("until", ""), "checked": d.get("checked", ""),
                "url": v.get("url") or (f"https://www.amazon.co.jp/dp/{v['asin']}?tag={d['tag']}" if v.get("asin") else link),
            })
    events = [{**e, "url": rakuten_aff_link(e["url"], aff_id)} if e.get("url") else e
              for e in src.get("events", []) if alive(e.get("end"))]
    events += [{"shop_coupon": sc} for sc in src.get("shop_coupons", []) if alive(sc.get("until"))]
    return sorted(out, key=lambda o: o["per_sheet"]), events


def deals_only():
    """価格は取り直さず、data.json のお得情報だけを差し替える"""
    path = os.path.join(HERE, "data.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data["deals"], data["events"] = build_deals(env("RAKUTEN_AFFILIATE_ID"))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(add_rtlink(data), f, ensure_ascii=False, indent=2)
    print(f"お得情報 {len(data['deals'])}件・お知らせ {len(data['events'])}件を反映しました")


def test_names(names):
    for n in names:
        print(f"{n}\n  サイズ: {sorted(detect_sizes(n))}  枚数: {parse_sheets(n)}")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--test":
        return test_names(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "--deals-only":
        return deals_only()

    rk = {"app_id": env("RAKUTEN_APP_ID"), "access_key": env("RAKUTEN_ACCESS_KEY"),
          "aff_id": env("RAKUTEN_AFFILIATE_ID"), "referer": env("RAKUTEN_REFERER")}
    yh = {"client_id": env("YAHOO_CLIENT_ID"), "vc_sid": env("VC_SID"), "vc_pid": env("VC_PID")}
    az = {"credential_id": env("AMAZON_CREDENTIAL_ID"), "credential_secret": env("AMAZON_CREDENTIAL_SECRET"),
          "version": env("AMAZON_API_VERSION") or "3.3", "tag": env("AMAZON_PARTNER_TAG")}
    use_rakuten = all(rk[k] for k in ("app_id", "access_key", "referer"))
    use_yahoo = bool(yh["client_id"])
    use_amazon = all(az[k] for k in ("credential_id", "credential_secret", "tag"))
    if not (use_rakuten or use_yahoo or use_amazon):
        sys.exit("楽天・Yahoo!・Amazonのどのキーも設定されていません")
    print(f"楽天: {'ON' if use_rakuten else 'OFF'} / Yahoo!: {'ON' if use_yahoo else 'OFF'}"
          f" / Amazon: {'ON' if use_amazon else 'OFF'}")

    with open(os.path.join(HERE, "products.json"), encoding="utf-8") as f:
        catalog = json.load(f)

    result = []
    for p in expand(catalog):
        raw, errors = [], {}
        for mall, on, fn, cfg in (("楽天", use_rakuten, rakuten_items, rk),
                                  ("Yahoo!", use_yahoo, yahoo_items, yh),
                                  ("Amazon", use_amazon, amazon_items, az)):
            if not on:
                continue
            time.sleep(WAIT_SEC)
            try:
                raw += fn(p["keyword"], cfg)
            except Exception as e:
                errors[mall] = str(e)[:300]
                print(f"NG  {mall} {p['brand']} {p['name']} {p['type']} {p['size']}: {e}")
        offers, stats = build(p, raw)
        stats["malls"] = Counter(o["mall"] for o in offers)
        if errors:
            stats["errors"] = errors
        print(f"OK  {p['brand']} {p['name']} {p['type']} {p['size']}: {stats}")
        meta = {k: p[k] for k in ("id", "maker", "brand", "name", "type", "size")}
        result.append({**meta, "offers": offers, "stats": stats})

    out = {"updated": datetime.now(JST).isoformat(timespec="minutes"),
           "sources": [m for m, on in (("楽天市場", use_rakuten), ("Yahoo!ショッピング", use_yahoo),
                                       ("Amazon", use_amazon)) if on],
           "shipping_estimate": SHIPPING_ESTIMATE, "products": result}
    out["deals"], out["events"] = build_deals(rk["aff_id"])
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(add_rtlink(out), f, ensure_ascii=False, indent=2)
    with open(os.path.join(HERE, "debug.json"), "w", encoding="utf-8") as f:
        json.dump(SAMPLES, f, ensure_ascii=False, indent=1)
    print("data.json と debug.json を書き出しました")


if __name__ == "__main__":
    main()
