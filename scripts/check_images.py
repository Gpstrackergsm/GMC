#!/usr/bin/env python3
"""
Image URL Reachability & GMC Compliance Checker for Leafanoo Catalog
Validates that image URLs are accessible (HTTP 200) and return image MIME types.
"""

import sys
import os
import csv
import urllib.request
import urllib.error

def check_images(file_path, limit=50):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"\n=======================================================")
    print(f"Checking Image URLs in: {file_path}")
    print(f"=======================================================\n")

    valid_urls = 0
    empty_urls = 0
    failed_urls = 0

    with open(file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            if idx > limit:
                print(f"\nReached check limit of {limit} products.")
                break

            title = row.get('Title', row.get('title', 'Unknown Product'))
            img_url = row.get('Image Src', row.get('image_source_url', '')).strip()

            if not img_url:
                empty_urls += 1
                continue

            try:
                req = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    content_type = response.headers.get('Content-Type', '')
                    if response.status == 200 and 'image' in content_type:
                        valid_urls += 1
                        print(f"  [OK] Product {idx}: {title[:40]}...")
                    else:
                        failed_urls += 1
                        print(f"  [FAIL] Product {idx}: {title[:40]}... (Content-Type: {content_type})")
            except Exception as e:
                failed_urls += 1
                print(f"  [FAIL] Product {idx}: {title[:40]}... (Error: {e})")

    print(f"\nSummary:")
    print(f"  Reachable Valid Images: {valid_urls}")
    print(f"  Empty/Placeholder Image URLs: {empty_urls}")
    print(f"  Failed/Unreachable URLs: {failed_urls}")

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'catalog/shopify_import.csv'
    check_images(target)
