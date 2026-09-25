#!/usr/bin/env python3
"""
Sync Google Merchant Center feed to match ONLY products currently active on leafanoo.com.
Removes all 221 phantom products that do not exist on the store.
Also removes any prohibited motor vehicles (e.g. Golf Cart) that violate GMC policy.
"""

import urllib.request, json, xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

WORKSPACE = Path("/Users/khalidaitelmaati/Desktop/GMC")
FEED_FILE = WORKSPACE / "catalog" / "google_merchant_center_feed.xml"

# 1. Fetch live active products from leafanoo.com
print("Fetching live active products from leafanoo.com...")
url = "https://leafanoo.com/products.json?limit=250"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=10) as resp:
    shop_products = json.loads(resp.read().decode())["products"]

shop_handles = {p["handle"]: p for p in shop_products}
print(f"Total live products on Shopify: {len(shop_handles)}")

# 2. Parse current feed
tree = ET.parse(FEED_FILE)
root = tree.getroot()
channel = root.find("channel")
ns = {"g": "http://base.google.com/ns/1.0"}

items = channel.findall("item")
print(f"Total items currently in feed: {len(items)}")

# 3. Filter items: Keep only those that exist on Shopify and don't violate vehicle policies
kept_items = []
removed_404 = 0
removed_policy = 0

# Prohibited by Google Merchant Center Vehicles Policy
PROHIBITED_KEYWORDS = ["golf cart"]

for item in items:
    link = item.find("g:link", ns).text
    handle = link.split("/")[-1]
    title = (item.find("g:title", ns).text or "").lower()
    
    if handle not in shop_handles:
        channel.remove(item)
        removed_404 += 1
        continue
    
    if any(k in title for k in PROHIBITED_KEYWORDS):
        print(f"  Removing policy-prohibited item: {title}")
        channel.remove(item)
        removed_policy += 1
        continue
        
    kept_items.append(item)

remaining_count = len(channel.findall("item"))
print(f"\nRemoved {removed_404} phantom products (not on Shopify).")
print(f"Removed {removed_policy} prohibited products.")
print(f"Remaining clean products in feed: {remaining_count}")

# 4. Save updated feed
tree.write(FEED_FILE, encoding="utf-8", xml_declaration=True)
print(f"Saved clean feed to {FEED_FILE}")
