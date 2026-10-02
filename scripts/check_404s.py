#!/usr/bin/env python3
"""
Script to find 404 broken product links in the Google Merchant Center feed.
Checks all product URLs in the GMC feed against leafanoo.com.
"""

import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

FEED_FILE = "catalog/google_merchant_center_feed.xml"
OUTPUT_FILE = "catalog/404_report.txt"
MAX_WORKERS = 10  # concurrent requests
TIMEOUT = 10  # seconds per request

def extract_urls(feed_path):
    with open(feed_path, "r", encoding="utf-8") as f:
        content = f.read()
    urls = re.findall(r'https://leafanoo\.com/products/[^\s<"\']+', content)
    return sorted(set(urls))

def check_url(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={
            "User-Agent": "Mozilla/5.0 (compatible; LinkChecker/1.0)"
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return url, resp.status
    except urllib.error.HTTPError as e:
        return url, e.code
    except Exception as e:
        return url, f"ERROR: {e}"

def main():
    print(f"📂 Reading feed: {FEED_FILE}")
    urls = extract_urls(FEED_FILE)
    total = len(urls)
    print(f"🔗 Found {total} unique product URLs to check\n")

    broken = []
    ok_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_url, url): url for url in urls}
        for i, future in enumerate(as_completed(futures), 1):
            url, status = future.result()
            if status == 200:
                ok_count += 1
                print(f"[{i}/{total}] ✅ {status} - {url}")
            else:
                broken.append((url, status))
                print(f"[{i}/{total}] ❌ {status} - {url}")

    print(f"\n{'='*60}")
    print(f"✅ OK:     {ok_count}")
    print(f"❌ Broken: {len(broken)}")
    print(f"{'='*60}\n")

    if broken:
        print("🚨 BROKEN LINKS:")
        for url, status in broken:
            print(f"  [{status}] {url}")

        with open(OUTPUT_FILE, "w") as f:
            f.write("BROKEN LINKS REPORT\n")
            f.write("="*60 + "\n\n")
            for url, status in broken:
                f.write(f"[{status}] {url}\n")
        print(f"\n📄 Report saved to: {OUTPUT_FILE}")
    else:
        print("🎉 All product URLs are working correctly!")

if __name__ == "__main__":
    main()
