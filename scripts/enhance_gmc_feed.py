#!/usr/bin/env python3
"""
Enhance GMC XML feed:
1. Prepend brand to titles missing brand prefix.
2. Add delivery speed attributes (handling: 1-2 days, transit: 3-5 days).
3. Extract missing GTINs from descriptions if available.
4. Set shipping service to 'Free Freight with Liftgate Delivery'.
"""
import xml.etree.ElementTree as ET
import re

ET.register_namespace('', 'http://www.w3.org/2005/Atom')
ET.register_namespace('g', 'http://base.google.com/ns/1.0')

NS = 'http://base.google.com/ns/1.0'
G = f'{{{NS}}}'

FEED_FILES = [
    'catalog/google_merchant_center_feed_live.xml',
    'catalog/google_merchant_center_feed.xml'
]

def enhance_feeds():
    for feed_path in FEED_FILES:
        print(f"\nProcessing {feed_path}...")
        tree = ET.parse(feed_path)
        root = tree.getroot()
        channel = root.find('channel')
        items = channel.findall('item')

        titles_updated = 0
        delivery_added = 0
        gtin_added = 0

        for item in items:
            brand_elem = item.find(f'{G}brand')
            title_elem = item.find(f'{G}title')
            desc_elem = item.find(f'{G}description')
            gtin_elem = item.find(f'{G}gtin')
            ident_elem = item.find(f'{G}identifier_exists')

            brand = brand_elem.text.strip() if (brand_elem is not None and brand_elem.text) else ""
            title = title_elem.text.strip() if (title_elem is not None and title_elem.text) else ""
            desc = desc_elem.text.strip() if (desc_elem is not None and desc_elem.text) else ""

            # 1. Optimize Title if missing brand
            if brand and title and not title.lower().startswith(brand.lower()):
                # E.g. "Z315e 42 in..." -> "John Deere Z315E 42 in..."
                new_title = f"{brand} {title}"
                # If length exceeds 150, trim
                if len(new_title) > 150:
                    new_title = new_title[:147] + "..."
                title_elem.text = new_title
                titles_updated += 1

            # 2. Extract GTIN from description if missing
            if (gtin_elem is None or not gtin_elem.text) and desc:
                upc_match = re.search(r'UPC(?:-A)?:\s*(\d{12})', desc)
                if upc_match:
                    upc = upc_match.group(1)
                    if gtin_elem is None:
                        gtin_elem = ET.SubElement(item, f'{G}gtin')
                    gtin_elem.text = upc
                    if ident_elem is not None:
                        ident_elem.text = "yes"
                    gtin_added += 1

            # 3. Add or update handling time
            min_hand = item.find(f'{G}min_handling_time')
            if min_hand is None:
                min_hand = ET.SubElement(item, f'{G}min_handling_time')
            min_hand.text = "1"

            max_hand = item.find(f'{G}max_handling_time')
            if max_hand is None:
                max_hand = ET.SubElement(item, f'{G}max_handling_time')
            max_hand.text = "2"

            # 4. Enhance shipping element with transit times & descriptive service
            shipping_elem = item.find(f'{G}shipping')
            if shipping_elem is None:
                shipping_elem = ET.SubElement(item, f'{G}shipping')
                country = ET.SubElement(shipping_elem, f'{G}country')
                country.text = "US"
                price = ET.SubElement(shipping_elem, f'{G}price')
                price.text = "0.00 USD"

            service_elem = shipping_elem.find(f'{G}service')
            if service_elem is None:
                service_elem = ET.SubElement(shipping_elem, f'{G}service')
            service_elem.text = "Free LTL Freight with Liftgate Service"

            min_trans = shipping_elem.find(f'{G}min_transit_time')
            if min_trans is None:
                min_trans = ET.SubElement(shipping_elem, f'{G}min_transit_time')
            min_trans.text = "3"

            max_trans = shipping_elem.find(f'{G}max_transit_time')
            if max_trans is None:
                max_trans = ET.SubElement(shipping_elem, f'{G}max_transit_time')
            max_trans.text = "5"

            delivery_added += 1

        tree.write(feed_path, encoding='utf-8', xml_declaration=True)
        print(f"✅ {feed_path} updated:")
        print(f"   • Titles optimized with Brand: {titles_updated}")
        print(f"   • GTINs recovered: {gtin_added}")
        print(f"   • Items with 3-5 day delivery & liftgate freight: {delivery_added}")

if __name__ == '__main__':
    enhance_feeds()
