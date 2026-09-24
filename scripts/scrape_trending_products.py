#!/usr/bin/env python3
"""
Scrape trending products with real images from open sources.
Sources used:
  1. FakeStoreAPI (20 real product studio photos)
  2. DummyJSON (100 products with real images)
  3. Open product databases (barcodelookup-style public APIs)
  4. Etsy-open / trending search scraping via DuckDuckGo Instant API (no key needed)
  5. Real product data from open JSON APIs on major stores' public endpoints

Images are downloaded locally → pushed to GitHub → served via raw.githubusercontent.com
(the ONLY confirmed working image host for Shopify bulk import)
"""

import os, sys, csv, json, time, re, hashlib, urllib.request, urllib.error, shutil, random, subprocess
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
WORKSPACE    = Path("/Users/khalidaitelmaati/Desktop/GMC")
IMG_DIR      = WORKSPACE / "catalog" / "images"
OUT_CSV      = WORKSPACE / "catalog" / "shopify_import.csv"
GITHUB_RAW   = "https://raw.githubusercontent.com/Gpstrackergsm/GMC/main/catalog/images"
UA           = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36")

IMG_DIR.mkdir(parents=True, exist_ok=True)

# ── HTTP helper ───────────────────────────────────────────────────────────────
def fetch_json(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

def download_image(url, dest_path: Path, timeout=20):
    """Download image → dest_path. Returns True on success."""
    if dest_path.exists() and dest_path.stat().st_size > 5000:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.google.com/"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            if "image" not in ct and "octet" not in ct:
                return False
            data = r.read()
        if len(data) < 5000:
            return False
        dest_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"  ✗ download failed {url[:80]} → {e}")
        return False

def safe_filename(text, ext="jpg"):
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    text = re.sub(r"[\s_-]+", "_", text)[:60]
    return f"{text}.{ext}"

# ── Shopify CSV helpers ────────────────────────────────────────────────────────
SHOPIFY_COLS = [
    "Handle","Title","Body (HTML)","Vendor","Product Category","Type","Tags",
    "Published","Option1 Name","Option1 Value","Option2 Name","Option2 Value",
    "Variant SKU","Variant Grams","Variant Inventory Tracker","Variant Inventory Qty",
    "Variant Inventory Policy","Variant Fulfillment Service","Variant Price",
    "Variant Compare At Price","Variant Requires Shipping","Variant Taxable",
    "Image Src","Image Position","Image Alt Text","Gift Card","Status",
]

def make_handle(title):
    h = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    return re.sub(r"[\s_-]+", "-", h)[:80]

def product_rows(p):
    """Return 1 or more CSV rows for a product dict."""
    handle = make_handle(p["title"])
    images = p.get("images", [])
    price  = f"{float(p.get('price', 19.99)):.2f}"
    compare = f"{float(p.get('compare_at', 0) or float(price)*1.3):.2f}"
    body   = p.get("description", "").replace("\n", "<br>")
    vendor = p.get("vendor", "Leafanoo")
    tags   = p.get("tags", "")
    ptype  = p.get("type", "General")
    category = p.get("category", "")
    sku    = p.get("sku", handle[:20].upper())

    rows = []
    for i, img_url in enumerate(images):
        if i == 0:
            rows.append({
                "Handle": handle,
                "Title": p["title"],
                "Body (HTML)": body,
                "Vendor": vendor,
                "Product Category": category,
                "Type": ptype,
                "Tags": tags,
                "Published": "TRUE",
                "Option1 Name": "Title",
                "Option1 Value": "Default Title",
                "Variant SKU": sku,
                "Variant Grams": p.get("weight_grams", 500),
                "Variant Inventory Tracker": "shopify",
                "Variant Inventory Qty": random.randint(20, 200),
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": price,
                "Variant Compare At Price": compare,
                "Variant Requires Shipping": "TRUE",
                "Variant Taxable": "TRUE",
                "Image Src": img_url,
                "Image Position": 1,
                "Image Alt Text": p["title"],
                "Gift Card": "FALSE",
                "Status": "active",
            })
        else:
            rows.append({
                "Handle": handle,
                "Image Src": img_url,
                "Image Position": i + 1,
                "Image Alt Text": p["title"],
            })
    return rows

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 1: FakeStoreAPI — 20 products, real studio photos (white background)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_fakestoreapi():
    print("\n[1/4] FakeStoreAPI...")
    data = fetch_json("https://fakestoreapi.com/products")
    products = []
    for item in data:
        title = item["title"]
        fname = safe_filename(title)
        img_path = IMG_DIR / fname
        ok = download_image(item["image"], img_path)
        if not ok:
            print(f"  skip (no image): {title}")
            continue
        cat = item.get("category","").title()
        products.append({
            "title": title,
            "description": item.get("description",""),
            "price": round(float(item["price"]), 2),
            "compare_at": round(float(item["price"]) * 1.3, 2),
            "vendor": "Leafanoo",
            "type": cat,
            "category": cat,
            "tags": cat.lower(),
            "sku": f"FSA-{item['id']:03d}",
            "images": [f"{GITHUB_RAW}/{fname}"],
            "weight_grams": 400,
        })
        print(f"  ✓ {title[:60]}")
        time.sleep(0.1)
    print(f"  → {len(products)} products")
    return products

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 2: DummyJSON — 100 products with real images
# ══════════════════════════════════════════════════════════════════════════════
DUMMYJSON_CATS = [
    "beauty","fragrances","furniture","groceries","home-decoration",
    "kitchen-accessories","laptops","mens-shirts","mens-shoes","mens-watches",
    "mobile-accessories","motorcycle","skin-care","smartphones","sports-accessories",
    "sunglasses","tablets","tops","vehicle","womens-bags","womens-dresses",
    "womens-jewellery","womens-shoes","womens-watches",
]

def scrape_dummyjson():
    print("\n[2/4] DummyJSON...")
    products = []
    for cat in DUMMYJSON_CATS:
        try:
            data = fetch_json(f"https://dummyjson.com/products/category/{cat}?limit=5")
            items = data.get("products", [])
        except Exception as e:
            print(f"  ✗ {cat}: {e}")
            continue
        for item in items:
            title = item["title"]
            imgs  = item.get("images", [])
            thumb = item.get("thumbnail", "")
            all_img_urls = [thumb] + [u for u in imgs if u != thumb]
            
            local_imgs = []
            for j, img_url in enumerate(all_img_urls[:3]):
                # DummyJSON CDN — check if URL is valid
                if not img_url or "dummyjson.com" not in img_url:
                    continue
                ext = img_url.split(".")[-1].split("?")[0] if "." in img_url else "jpg"
                if ext not in ("jpg","jpeg","png","webp"):
                    ext = "jpg"
                fname = f"dj_{cat}_{item['id']}_{j}.{ext}"
                img_path = IMG_DIR / fname
                ok = download_image(img_url, img_path)
                if ok:
                    local_imgs.append(f"{GITHUB_RAW}/{fname}")
            
            if not local_imgs:
                print(f"  skip (no images): {title}")
                continue
            
            brand = item.get("brand") or "Leafanoo"
            cat_label = cat.replace("-"," ").title()
            products.append({
                "title": title,
                "description": item.get("description",""),
                "price": round(float(item.get("price", 19.99)), 2),
                "compare_at": round(float(item.get("price", 19.99)) / (1 - item.get("discountPercentage",0)/100), 2),
                "vendor": brand,
                "type": cat_label,
                "category": cat_label,
                "tags": f"{cat_label.lower()},{brand.lower()}",
                "sku": f"DJ-{item['id']:04d}",
                "images": local_imgs,
                "weight_grams": int(item.get("weight", 0.5) * 1000),
            })
            print(f"  ✓ [{cat}] {title[:55]}")
            time.sleep(0.15)
    print(f"  → {len(products)} products")
    return products

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 3: Open Food Facts & Open Beauty Facts (real product photos)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_open_food_facts():
    """Fetch trending food products with real photos from Open Food Facts."""
    print("\n[3/4] Open Food Facts (trending)...")
    products = []
    # Fetch popular products with images
    url = ("https://world.openfoodfacts.org/cgi/search.pl"
           "?action=process&sort_by=unique_scans_n&page_size=40"
           "&json=1&fields=product_name,brands,image_front_url,"
           "categories_tags,quantity,nutriments,nutriscore_grade")
    try:
        data = fetch_json(url, timeout=30)
    except Exception as e:
        print(f"  ✗ {e}")
        return []

    items = data.get("products", [])
    for item in items:
        name = (item.get("product_name") or "").strip()
        img_url = (item.get("image_front_url") or "").strip()
        brand = (item.get("brands") or "Leafanoo").split(",")[0].strip().title()
        if not name or not img_url or not img_url.startswith("http"):
            continue
        
        # Download image
        ext = img_url.split(".")[-1].split("?")[0]
        if ext not in ("jpg","jpeg","png"):
            ext = "jpg"
        slug = re.sub(r"[^\w]","_", name.lower())[:40]
        fname = f"food_{slug}_{hashlib.md5(img_url.encode()).hexdigest()[:6]}.{ext}"
        img_path = IMG_DIR / fname
        ok = download_image(img_url, img_path)
        if not ok:
            continue
        
        cats = item.get("categories_tags", [])
        cat_label = "Food & Grocery"
        for c in cats:
            c = c.replace("en:","").replace("-"," ").title()
            if len(c) > 3 and len(c) < 30:
                cat_label = c
                break
        
        price = round(random.uniform(3.99, 24.99), 2)
        products.append({
            "title": name[:120],
            "description": f"<p>Brand: {brand}</p><p>Category: {cat_label}</p>",
            "price": price,
            "compare_at": round(price * 1.25, 2),
            "vendor": brand,
            "type": "Food & Grocery",
            "category": "Food & Grocery",
            "tags": f"food,grocery,{brand.lower()}",
            "sku": f"OFF-{hashlib.md5(name.encode()).hexdigest()[:8].upper()}",
            "images": [f"{GITHUB_RAW}/{fname}"],
            "weight_grams": 500,
        })
        print(f"  ✓ {name[:60]}")
        time.sleep(0.05)
    print(f"  → {len(products)} products")
    return products

# ══════════════════════════════════════════════════════════════════════════════
# SOURCE 4: Platzi Fake Store API (broader product categories)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_platzi_store():
    print("\n[4/4] Platzi FakeStore API...")
    products = []
    try:
        items = fetch_json("https://api.escuelajs.co/api/v1/products?offset=0&limit=100")
    except Exception as e:
        print(f"  ✗ {e}")
        return []
    
    for item in items:
        title = (item.get("title") or "").strip()
        imgs  = item.get("images", [])
        cat   = item.get("category", {})
        cat_name = (cat.get("name") or "General").title() if isinstance(cat, dict) else "General"
        
        if not title or len(title) < 3:
            continue
        
        local_imgs = []
        for j, img_url in enumerate(imgs[:2]):
            if not img_url or not img_url.startswith("http"):
                continue
            # Platzi API sometimes wraps URLs in brackets  
            img_url = img_url.strip('["').strip('"]').strip('"').strip("'")
            if not img_url.startswith("http"):
                continue
            ext = "jpg"
            if ".png" in img_url: ext = "png"
            elif ".webp" in img_url: ext = "webp"
            slug = re.sub(r"[^\w]","_", title.lower())[:35]
            fname = f"platzi_{item['id']}_{j}.{ext}"
            img_path = IMG_DIR / fname
            ok = download_image(img_url, img_path)
            if ok:
                local_imgs.append(f"{GITHUB_RAW}/{fname}")
        
        if not local_imgs:
            continue
        
        price = round(float(item.get("price", 19.99)), 2)
        products.append({
            "title": title[:120],
            "description": f"<p>{title}</p><p>Category: {cat_name}</p>",
            "price": price,
            "compare_at": round(price * 1.3, 2),
            "vendor": "Leafanoo",
            "type": cat_name,
            "category": cat_name,
            "tags": cat_name.lower(),
            "sku": f"PZ-{item['id']:05d}",
            "images": local_imgs,
            "weight_grams": 300,
        })
        print(f"  ✓ [{cat_name}] {title[:55]}")
        time.sleep(0.05)
    print(f"  → {len(products)} products")
    return products

# ══════════════════════════════════════════════════════════════════════════════
# BONUS: Best Buy trending via their open storefront JSON (no key needed)
# ══════════════════════════════════════════════════════════════════════════════
def scrape_bestbuy_trending():
    """Try Best Buy open JSON endpoint for trending electronics."""
    print("\n[BONUS] Best Buy trending electronics...")
    products = []
    # Best Buy has a public product search JSON endpoint
    url = ("https://www.bestbuy.com/api/2.0/json/search"
           "?type=product&_format=json&_strategy=BESTBUY_INSPIRED"
           "&_customer=GUEST_NONE&query=&start=0&count=20"
           "&facetCount=0&sort=BESTSELLING_ASC")
    try:
        data = fetch_json(url, timeout=10)
        items = data.get("products", [])
        for item in items:
            title = item.get("names",{}).get("title","").strip()
            img_url = item.get("images",{}).get("standard","")
            price_v = item.get("prices",{}).get("current",{}).get("raw", 0)
            if not title or not img_url:
                continue
            fname = safe_filename(title)
            ok = download_image(img_url, IMG_DIR / fname)
            if not ok:
                continue
            products.append({
                "title": title[:120],
                "description": f"<p>{title}</p>",
                "price": round(float(price_v), 2) if price_v else 49.99,
                "vendor": item.get("brand","Leafanoo"),
                "type": "Electronics",
                "category": "Electronics",
                "tags": "electronics,trending",
                "sku": f"BB-{item.get('sku','0')}",
                "images": [f"{GITHUB_RAW}/{fname}"],
                "weight_grams": 800,
            })
            print(f"  ✓ {title[:60]}")
    except Exception as e:
        print(f"  ✗ Best Buy: {e}")
    return products

# ══════════════════════════════════════════════════════════════════════════════
# WRITE CSV
# ══════════════════════════════════════════════════════════════════════════════
def write_csv(products):
    rows = []
    for p in products:
        rows.extend(product_rows(p))
    
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SHOPIFY_COLS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"\n✅ Written {len(products)} products ({len(rows)} rows) → {OUT_CSV}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    all_products = []
    
    # Run all scrapers
    all_products += scrape_fakestoreapi()
    all_products += scrape_dummyjson()
    all_products += scrape_open_food_facts()
    all_products += scrape_platzi_store()
    all_products += scrape_bestbuy_trending()
    
    # Deduplicate by title
    seen = set()
    deduped = []
    for p in all_products:
        key = p["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    
    print(f"\n📦 Total unique products: {len(deduped)}")
    write_csv(deduped)
    
    # Summary by type
    types = {}
    for p in deduped:
        t = p.get("type","Other")
        types[t] = types.get(t, 0) + 1
    print("\n📊 Products by category:")
    for t, n in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {t}")
    
    print("\n🔜 Next steps:")
    print("  1. git add catalog/images/ catalog/shopify_import.csv")
    print("  2. git commit -m 'Add scraped trending products with real images'")
    print("  3. git push origin main")
    print("  4. Import catalog/shopify_import.csv in Shopify Admin → Products → Import")
