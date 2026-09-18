#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import re
import os
import csv
import time

headers = {'User-Agent': 'LeafanooCatalogBot/1.0 (contact@leafanoo.com)'}

def search_wikimedia_image(query):
    clean_q = query.replace('&', 'and').strip()
    url = f'https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={urllib.parse.quote(clean_q)}&gsrlimit=5&prop=imageinfo&iiprop=url|mime|size&format=json'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pages = data.get('query', {}).get('pages', {})
            for pid, pdata in pages.items():
                info = pdata.get('imageinfo', [{}])[0]
                img_url = info.get('url', '')
                mime = info.get('mime', '')
                if 'image' in mime and ('jpg' in img_url.lower() or 'jpeg' in img_url.lower() or 'png' in img_url.lower()):
                    if not img_url.endswith('.svg') and not img_url.endswith('.tif'):
                        return img_url.split('?')[0]
    except Exception as e:
        pass
    return None

print("Testing internet image fetcher...")
test_items = [
    ("OXO Mixing Bowl", "mixing bowl"),
    ("Lodge Cast Iron", "cast iron skillet"),
    ("Rubbermaid Storage", "food storage container"),
    ("Pyrex Baking Dish", "glass baking dish"),
    ("Salad Spinner", "salad spinner"),
    ("Peeler", "vegetable peeler"),
    ("Digital Thermometer", "digital meat thermometer"),
    ("Measuring Spoons", "measuring spoons"),
    ("Cutting Board", "wooden cutting board"),
    ("Kitchen Scale", "digital kitchen scale"),
    ("KONG Dog Toy", "dog chew toy"),
    ("Dog Harness", "dog harness"),
    ("Cat Water Fountain", "cat water fountain"),
    ("Pruning Shears", "pruning shears secateurs"),
    ("Garden Hose Nozzle", "garden hose nozzle"),
    ("Travel Backpack", "travel backpack"),
    ("Travel Pillow", "neck pillow"),
    ("Electric Toothbrush", "electric toothbrush"),
    ("Hair Dryer", "hair dryer"),
    ("Wireless Mouse", "wireless computer mouse"),
    ("Yoga Mat", "yoga mat"),
    ("Resistance Bands", "resistance bands"),
    ("Wireless Headphones", "wireless bluetooth headphones"),
    ("Bluetooth Speaker", "portable bluetooth speaker"),
    ("Smartwatch", "smartwatch")
]

results = {}
for label, query in test_items:
    img = search_wikimedia_image(query)
    results[label] = img
    print(f"✓ {label} -> {img}")

print(f"\nFetched {sum(1 for v in results.values() if v)} / {len(test_items)} direct internet images successfully.")
