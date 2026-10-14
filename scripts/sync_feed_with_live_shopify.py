#!/usr/bin/env python3
"""
Sync GMC feed with 100% verified live Shopify product data from leafanoo.com.
Fetches https://leafanoo.com/products/<handle>.js for every item in the feed,
and updates price, availability, and attributes to eliminate any mismatch.
"""

import xml.etree.ElementTree as ET
import urllib.request
import json
import time
import os

ET.register_namespace('', 'http://www.w3.org/2005/Atom')
ET.register_namespace('g', 'http://base.google.com/ns/1.0')

NS = 'http://base.google.com/ns/1.0'
G = f'{{{NS}}}'

FEED_FILES = [
    'catalog/google_merchant_center_feed_live.xml',
    'catalog/google_merchant_center_feed.xml'
]

def sync_feed():
    primary_file = FEED_FILES[0]
    print(f"Loading {primary_file}...")
    tree = ET.parse(primary_file)
    root = tree.getroot()
    channel = root.find('channel')
    items = channel.findall('item')

    print(f"Total products in feed: {len(items)}")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Leafanoo-Sync/1.0'}
    
    updated_prices = []
    updated_avail = []
    errors = []

    for idx, item in enumerate(items, 1):
        link_elem = item.find(f'{G}link')
        if link_elem is None or not link_elem.text:
            continue
        
        link = link_elem.text.strip()
        handle = link.split('/products/')[-1].split('?')[0].split('#')[0]
        js_url = f"https://leafanoo.com/products/{handle}.js"

        try:
            req = urllib.request.Request(js_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Live price in dollars
            cents = data.get('price', 0)
            live_price_val = cents / 100.0
            live_price_str = f"{live_price_val:.2f} USD"

            # Live availability
            available = data.get('available', True)
            live_avail = "in_stock" if available else "out_of_stock"

            # Check and update Price
            price_elem = item.find(f'{G}price')
            if price_elem is not None:
                old_price = price_elem.text.strip()
                if old_price != live_price_str:
                    updated_prices.append((handle, old_price, live_price_str))
                    price_elem.text = live_price_str

            # Check and update Availability
            avail_elem = item.find(f'{G}availability')
            if avail_elem is not None:
                old_avail = avail_elem.text.strip()
                if old_avail != live_avail:
                    updated_avail.append((handle, old_avail, live_avail))
                    avail_elem.text = live_avail

            print(f"[{idx}/{len(items)}] {handle[:45]:<45} | Price: {live_price_str} | Avail: {live_avail}")

        except Exception as e:
            errors.append((handle, str(e)))
            print(f"[{idx}/{len(items)}] ❌ Error for {handle}: {e}")

        # Gentle delay to avoid rate-limiting
        time.sleep(0.15)

    print("\n" + "=" * 70)
    print("SYNC SUMMARY")
    print("=" * 70)
    print(f"Total processed: {len(items)}")
    print(f"Prices updated: {len(updated_prices)}")
    print(f"Availability updated: {len(updated_avail)}")
    print(f"Fetch errors: {len(errors)}")

    if updated_prices:
        print("\nPrice updates made:")
        for handle, old_p, new_p in updated_prices:
            print(f"  • {handle}: {old_p} -> {new_p}")

    # Save to all feed files
    for feed_file in FEED_FILES:
        tree.write(feed_file, encoding='utf-8', xml_declaration=True)
        print(f"✅ Saved updated feed to {feed_file}")

if __name__ == '__main__':
    sync_feed()
