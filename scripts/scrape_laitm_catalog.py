#!/usr/bin/env python3
"""
Scrapes all 310 products from laitm.com catalog.
Transforms all brand references to 'Leafanoo'.
Generates:
1. catalog/shopify_import.csv (Full multi-image Shopify import CSV)
2. catalog/shopify_import_single_row.csv (1-row per product Shopify CSV)
3. catalog/google_merchant_center_feed.xml (GMC compliant feed)
4. catalog/products_master.json (Structured catalog cache)
"""

import sys
import os
import re
import json
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET
from xml.dom import minidom
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URLS_FILE = os.path.join(BASE_DIR, "catalog", "laitm_urls.txt")
CSV_OUTPUT = os.path.join(BASE_DIR, "catalog", "shopify_import.csv")
CSV_SINGLE_OUTPUT = os.path.join(BASE_DIR, "catalog", "shopify_import_single_row.csv")
XML_OUTPUT = os.path.join(BASE_DIR, "catalog", "google_merchant_center_feed.xml")
JSON_OUTPUT = os.path.join(BASE_DIR, "catalog", "products_master.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

KNOWN_BRANDS = [
    "BendPak", "MaxJax", "Atlas Automotive Equipment", "Atlas", "QuickJack", "Weaver",
    "AplusLift", "AMGO", "Halo Lifts", "Halo", "Hein-Werner", "Weize", "Ideal Lift",
    "Backyard Discovery", "Purple Leaf", "Yardistry", "Outsunny", "Sunjoy", "Sojag",
    "ShelterLogic", "Creekvine Designs", "Handy Home Products", "Handy Home",
    "Best Barns", "Heartland", "Suncast", "Arrow", "Veikous", "Patiowell", "Lifetime",
    "Husqvarna", "Craftsman", "Cub Cadet", "Troy-Bilt", "Toro", "Ryobi", "Greenworks",
    "DR Power", "EGO Power+", "EGO", "John Deere", "Bad Boy", "STIHL", "Mammotion", "Mova",
    "Bluetti", "Champion Power Equipment", "Champion", "Generac", "DuroMax", "EcoFlow",
    "Westinghouse", "Predator", "Anker", "Yoshino", "Genmax", "Yard Force",
    "Super73", "Aventon", "Ridstar", "Rad Power", "Leonx", "Tuttio", "Rambo", "Revi Bikes",
    "Concept2", "Horizon Fitness", "NordicTrack", "ProForm", "Schwinn", "Sole", "Sunny Health & Fitness",
    "Gorilla Playsets", "KidKraft", "SportsPower", "Creative Cedar Designs", "Congo", "Woodplay",
    "Jack & June", "Klo Kick", "Giantex", "Allstar", "GE Profile", "ZLINE", "Mesa Safe Company"
]

GOOGLE_TAXONOMY_MAP = {
    "car lift": "Vehicles & Parts > Automotive Operating Systems > Automotive Lifts & Cranes",
    "riding lawn mowers": "Home & Garden > Lawn & Garden > Outdoor Power Equipment > Lawn Mowers > Riding Lawn Mowers",
    "walk-behind lawn mowers": "Home & Garden > Lawn & Garden > Outdoor Power Equipment > Lawn Mowers > Push Lawn Mowers",
    "lawn mowers": "Home & Garden > Lawn & Garden > Outdoor Power Equipment > Lawn Mowers",
    "power generators": "Hardware > Generators > Portable Generators",
    "generators": "Hardware > Generators > Portable Generators",
    "electric bicycles": "Sporting Goods > Outdoor Recreation > Cycling > Bicycles > Electric Bicycles",
    "sheds": "Home & Garden > Lawn & Garden > Outdoor Living > Outdoor Structures > Sheds, Garages & Carports",
    "gazebo & pergolas": "Home & Garden > Lawn & Garden > Outdoor Living > Outdoor Structures > Gazebos & Canopies",
    "outdoor spaces": "Home & Garden > Lawn & Garden > Outdoor Living",
    "cardio machines": "Sporting Goods > Exercise & Fitness > Cardio",
    "trampoline": "Sporting Goods > Outdoor Recreation > Trampolines",
    "swing sets": "Toys & Games > Outdoor Play Equipment > Play Sets & Playground Equipment > Swing Sets",
    "home deals": "Home & Garden"
}

def clean_brand_text(text):
    if not text:
        return ""
    text = text.replace("Laitm LLC", "Leafanoo LLC")
    text = text.replace("LAITM LLC", "LEAFANOO LLC")
    text = text.replace("Laitm", "Leafanoo")
    text = text.replace("laitm.com", "leafanoo.com")
    text = text.replace("Contact@laitm.com", "support@leafanoo.com")
    text = text.replace("contact@laitm.com", "support@leafanoo.com")
    text = text.strip()
    return text

def detect_vendor(title):
    title_lower = title.lower()
    for brand in KNOWN_BRANDS:
        if brand.lower() in title_lower:
            return brand
    return "Leafanoo"

def map_google_taxonomy(category):
    cat_lower = category.lower().strip()
    for key, val in GOOGLE_TAXONOMY_MAP.items():
        if key in cat_lower or cat_lower in key:
            return val
    return "Home & Garden > Lawn & Garden > Outdoor Living"

def fetch_product(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
            break
        except Exception as e:
            if attempt == 2:
                print(f"Error fetching {url}: {e}")
                return None
            time.sleep(1)

    slug = url.rstrip('/').split('/')[-1]
    handle = slug.replace("%e2%80%b2", "").replace("%e2%80%b3", "").replace("%20", "-")
    handle = re.sub(r'[^a-zA-Z0-9-]+', '', handle).strip('-').lower()

    m = re.search(r'<script type=\"application/ld\+json\">({.*?})</script>', html, re.DOTALL)
    product_data = {}
    breadcrumb_data = {}
    if m:
        try:
            data = json.loads(m.group(1))
            graph = data.get('@graph', [])
            product_data = next((x for x in graph if x.get('@type') == 'Product'), {})
            breadcrumb_data = next((x for x in graph if x.get('@type') == 'BreadcrumbList'), {})
        except Exception:
            pass

    raw_title = product_data.get('name', '')
    if not raw_title:
        title_m = re.search(r'<h1[^>]*class=\"[^\"]*product_title[^\"]*\"[^>]*>(.*?)</h1>', html, re.DOTALL)
        if title_m:
            raw_title = re.sub(r'<[^>]+>', '', title_m.group(1))
        else:
            raw_title = handle.replace('-', ' ').title()
    title = clean_brand_text(re.sub(r'[\xa0\s]+', ' ', raw_title).strip())

    category = "Outdoor Living"
    crumbs = breadcrumb_data.get('itemListElement', [])
    if len(crumbs) >= 2:
        cat_candidate = crumbs[1].get('item', {}).get('name', '')
        if cat_candidate and cat_candidate.lower() != 'home':
            category = cat_candidate
    if category == "Outdoor Living":
        cat_m = re.search(r'rel=\"tag\">([^<]+)</a>', html)
        if cat_m:
            category = cat_m.group(1).strip()

    price = 699.0
    offers = product_data.get('offers', [])
    if offers and isinstance(offers, list):
        try:
            price = float(offers[0].get('price', 699.0))
        except (ValueError, TypeError):
            pass
    else:
        price_m = re.search(r'<span class=\"woocommerce-Price-amount[^>]*>.*?<bdi>.*?\$([0-9,.]+)', html, re.DOTALL)
        if price_m:
            try:
                price = float(price_m.group(1).replace(',', ''))
            except ValueError:
                pass

    compare_at_price = round(price * 1.18, 2)

    sku = str(product_data.get('sku', '') or '').strip()
    if not sku:
        sku_m = re.search(r'data-id=\"(\d+)\"', html)
        sku = sku_m.group(1) if sku_m else str(abs(hash(handle)) % 100000)
    
    gtin = str(product_data.get('gtin', '') or '').strip()
    vendor = detect_vendor(title)

    raw_desc = product_data.get('description', '')
    if not raw_desc:
        desc_m = re.search(r'<div[^>]*class=\"[^\"]*woocommerce-Tabs-panel--description[^\"]*\"[^>]*>(.*?)</div>\s*<div', html, re.DOTALL)
        if desc_m:
            raw_desc = desc_m.group(1)
        else:
            raw_desc = f"{title}. Premium grade equipment built for lasting durability, performance, and heavy-duty use. Backed by manufacturer warranty."

    clean_desc = clean_brand_text(raw_desc)
    if '<p>' not in clean_desc:
        paragraphs = [p.strip() for p in clean_desc.split('\n\n') if p.strip()]
        body_html = "".join([f"<p>{p}</p>" for p in paragraphs])
    else:
        body_html = clean_desc

    main_img = product_data.get('image', '')
    product_images = []
    if main_img:
        orig_main = re.sub(r'-\d+x\d+(\.(?:jpg|png|webp))$', r'\1', main_img)
        product_images.append(orig_main)
        match_id = re.search(r'ltm-product-(\d+)', main_img)
        if match_id:
            p_id = match_id.group(1)
            pat = rf'https://laitm\.com/wp-content/uploads/\d{{4}}/\d{{2}}/ltm-product-{p_id}-image-[^\"\'\s>]+\.(?:jpg|png|webp)'
            for img in re.findall(pat, html):
                orig = re.sub(r'-\d+x\d+(\.(?:jpg|png|webp))$', r'\1', img)
                if orig not in product_images:
                    product_images.append(orig)

    if not product_images:
        all_imgs = re.findall(r'https://laitm\.com/wp-content/uploads/\d{4}/\d{2}/[^\"\'\s>]+\.(?:jpg|png|webp)', html)
        for img in all_imgs:
            if 'logo' not in img.lower() and 'payment' not in img.lower() and 'fav' not in img.lower():
                orig = re.sub(r'-\d+x\d+(\.(?:jpg|png|webp))$', r'\1', img)
                if orig not in product_images:
                    product_images.append(orig)
            if len(product_images) >= 6:
                break

    return {
        'handle': handle,
        'title': title,
        'body_html': body_html,
        'vendor': vendor,
        'type': category,
        'category': category,
        'tags': f"{category.lower().replace('&', 'and')}, {vendor.lower()}, leafanoo, heavy-equipment",
        'price': f"{price:.2f}",
        'compare_at_price': f"{compare_at_price:.2f}",
        'sku': f"LF-{sku}",
        'gtin': gtin,
        'images': product_images,
        'google_product_category': map_google_taxonomy(category),
        'url': url
    }

def main():
    if os.path.exists(JSON_OUTPUT):
        print(f"Loading existing cache from {JSON_OUTPUT}")
        with open(JSON_OUTPUT, 'r', encoding='utf-8') as f:
            products = json.load(f)
    else:
        if not os.path.exists(URLS_FILE):
            print(f"Error: {URLS_FILE} does not exist.")
            sys.exit(1)
        with open(URLS_FILE, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        products = []
        with ThreadPoolExecutor(max_workers=12) as executor:
            future_to_url = {executor.submit(fetch_product, url): url for url in urls}
            for future in as_completed(future_to_url):
                res = future.result()
                if res:
                    products.append(res)

    # Ensure clean handles and fields
    seen = set()
    deduped = []
    for p in products:
        p['handle'] = re.sub(r'[^a-z0-9-]+', '', p['handle'].lower()).strip('-')
        if p['handle'] not in seen:
            seen.add(p['handle'])
            deduped.append(p)
    products = deduped

    # Generate Shopify CSV with Type column
    headers = [
        "Handle", "Title", "Body (HTML)", "Vendor", "Type", "Standardized Product Type", "Custom Product Type",
        "Tags", "Published", "Option1 Name", "Option1 Value", "Option2 Name", "Option2 Value",
        "Option3 Name", "Option3 Value", "Variant SKU", "Variant Grams", "Variant Inventory Tracker",
        "Variant Inventory Qty", "Variant Inventory Policy", "Variant Fulfillment Service",
        "Variant Price", "Variant Compare At Price", "Variant Requires Shipping", "Variant Taxable",
        "Variant Barcode", "Image Src", "Image Position", "Image Alt Text", "Gift Card",
        "SEO Title", "SEO Description", "Google Shopping / Google Product Category",
        "Google Shopping / Gender", "Google Shopping / Age Group", "Google Shopping / MPN",
        "Google Shopping / Condition", "Google Shopping / Custom Product", "Status"
    ]

    with open(CSV_OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for p in products:
            images = p['images'] or [""]
            for idx, img in enumerate(images, start=1):
                if idx == 1:
                    row = [
                        p['handle'],
                        p['title'],
                        p['body_html'],
                        p['vendor'],
                        p['category'],
                        p['category'],
                        p['category'],
                        p['tags'],
                        "TRUE",
                        "Title",
                        "Default Title",
                        "", "", "", "",
                        p['sku'],
                        "25000",
                        "shopify",
                        "25",
                        "deny",
                        "manual",
                        p['price'],
                        p['compare_at_price'],
                        "TRUE",
                        "TRUE",
                        p['gtin'] if p.get('gtin') else "",
                        img,
                        "1",
                        p['title'],
                        "FALSE",
                        f"{p['title']} | Leafanoo",
                        f"Buy {p['title']} online at Leafanoo. High quality {p['category']} with free shipping and warranty.",
                        p['google_product_category'],
                        "", "",
                        p['sku'],
                        "new",
                        "FALSE",
                        "active"
                    ]
                else:
                    row = [
                        p['handle'],
                        "", "", "", "", "", "", "",
                        "", "", "", "", "", "", "",
                        "", "", "", "", "", "", "",
                        "", "", "",
                        img,
                        str(idx),
                        f"{p['title']} - View {idx}",
                        "", "", "", "", "", "", "", "", "", ""
                    ]
                writer.writerow(row)

    print(f"Generated Multi-Row Shopify Import CSV: {CSV_OUTPUT}")

    # Generate Single-Row Shopify CSV
    with open(CSV_SINGLE_OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for p in products:
            img = p['images'][0] if p['images'] else ""
            row = [
                p['handle'],
                p['title'],
                p['body_html'],
                p['vendor'],
                p['category'],
                p['category'],
                p['category'],
                p['tags'],
                "TRUE",
                "Title",
                "Default Title",
                "", "", "", "",
                p['sku'],
                "25000",
                "shopify",
                "25",
                "deny",
                "manual",
                p['price'],
                p['compare_at_price'],
                "TRUE",
                "TRUE",
                p['gtin'] if p.get('gtin') else "",
                img,
                "1",
                p['title'],
                "FALSE",
                f"{p['title']} | Leafanoo",
                f"Buy {p['title']} online at Leafanoo. High quality {p['category']} with free shipping and warranty.",
                p['google_product_category'],
                "", "",
                p['sku'],
                "new",
                "FALSE",
                "active"
            ]
            writer.writerow(row)

    print(f"Generated Single-Row Shopify Import CSV: {CSV_SINGLE_OUTPUT}")

    # Generate GMC XML Feed
    rss = ET.Element("rss", {
        "xmlns:g": "http://base.google.com/ns/1.0",
        "version": "2.0"
    })
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Leafanoo Products"
    ET.SubElement(channel, "link").text = "https://leafanoo.com"
    ET.SubElement(channel, "description").text = "Leafanoo official store product feed for Google Merchant Center"

    for p in products:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "{http://base.google.com/ns/1.0}id").text = p['sku']
        ET.SubElement(item, "{http://base.google.com/ns/1.0}title").text = p['title']
        clean_text_desc = re.sub(r'<[^>]+>', ' ', p['body_html'])
        clean_text_desc = re.sub(r'\s+', ' ', clean_text_desc).strip()[:4900]
        ET.SubElement(item, "{http://base.google.com/ns/1.0}description").text = clean_text_desc
        ET.SubElement(item, "{http://base.google.com/ns/1.0}link").text = f"https://leafanoo.com/products/{p['handle']}"
        
        if p['images']:
            ET.SubElement(item, "{http://base.google.com/ns/1.0}image_link").text = p['images'][0]
            for extra_img in p['images'][1:10]:
                ET.SubElement(item, "{http://base.google.com/ns/1.0}additional_image_link").text = extra_img
        
        ET.SubElement(item, "{http://base.google.com/ns/1.0}price").text = f"{p['price']} USD"
        ET.SubElement(item, "{http://base.google.com/ns/1.0}availability").text = "in_stock"
        ET.SubElement(item, "{http://base.google.com/ns/1.0}condition").text = "new"
        ET.SubElement(item, "{http://base.google.com/ns/1.0}brand").text = p['vendor']
        ET.SubElement(item, "{http://base.google.com/ns/1.0}mpn").text = p['sku']

        if p.get('gtin'):
            ET.SubElement(item, "{http://base.google.com/ns/1.0}gtin").text = p['gtin']
            ET.SubElement(item, "{http://base.google.com/ns/1.0}identifier_exists").text = "yes"
        else:
            ET.SubElement(item, "{http://base.google.com/ns/1.0}identifier_exists").text = "no"

        ET.SubElement(item, "{http://base.google.com/ns/1.0}google_product_category").text = p['google_product_category']
        ET.SubElement(item, "{http://base.google.com/ns/1.0}product_type").text = p['category']

    xml_str = ET.tostring(rss, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ", encoding="utf-8")

    with open(XML_OUTPUT, "wb") as f:
        f.write(pretty_xml)

    print(f"Generated GMC XML Feed: {XML_OUTPUT}")

if __name__ == "__main__":
    main()
