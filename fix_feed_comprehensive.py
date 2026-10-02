#!/usr/bin/env python3
"""
Comprehensive GMC Feed Fix Script
- Fixes google_product_category to numeric IDs (required by Merchant API v1)
- Fixes miscategorized products (pergolas/gazebos/home items wrongly in Lawn Mowers)
- Enriches mower descriptions with cutting width
- Adds g:product_detail tags for cutting width on mowers
- Fixes pergola/outdoor structure categories
"""

import xml.etree.ElementTree as ET
import re
import shutil
from datetime import datetime

ET.register_namespace('', 'http://www.w3.org/2005/Atom')
ET.register_namespace('g', 'http://base.google.com/ns/1.0')

NS = 'http://base.google.com/ns/1.0'
G = f'{{{NS}}}'

INPUT_FILE = 'catalog/google_merchant_center_feed.xml'
OUTPUT_FILE = 'catalog/google_merchant_center_feed.xml'
LIVE_FILE = 'catalog/google_merchant_center_feed_live.xml'
BACKUP_FILE = f'catalog/google_merchant_center_feed_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml'

# ─── CATEGORY MAPPING (text → numeric ID) ────────────────────────────────────
# Source: https://support.google.com/merchants/answer/6324436
CATEGORY_MAP = {
    'Home & Garden > Lawn & Garden > Outdoor Power Equipment > Lawn Mowers': '3650',
    'Home & Garden > Lawn & Garden > Outdoor Living > Outdoor Structures > Sheds, Garages & Carports > Sheds': '6867',
    'Sporting Goods > Outdoor Recreation > Cycling > Bicycles > Electric Bikes': '3950',
    'Hardware > Power & Electrical Supplies > Generators > Portable Generators': '4595',
    'Toys & Games > Outdoor Play Equipment > Swing Sets & Playsets': '1249',
    'Toys & Games > Outdoor Play Equipment > Trampolines': '1251',
    'Sporting Goods > Fitness & General Exercise Equipment > Cardio > Cardio Machines > Treadmills': '499812',
    'Vehicles & Parts > Vehicle Parts & Accessories > Vehicle Maintenance, Care & Decor > Vehicle Repair & Specialty Tools > Vehicle Lifts & Stands > Vehicle Lifts': '8526',
}

# ─── CORRECT CATEGORIES FOR MISCATEGORIZED PRODUCT TYPES ─────────────────────
PRODUCT_TYPE_CATEGORY_FIXES = {
    # Outdoor structures — wrongly set to Lawn Mowers
    'Outdoor Spaces': '2473',       # Home & Garden > Patio, Lawn & Garden > Outdoor Living > Pergolas
    'Gazebo & Pergolas': '2473',    # Pergolas / Gazebos
    'Gazebo &amp;amp; Pergolas': '2473',
    'Garden Essentials': '2473',    # Outdoor structures / garden
    'Home Deals': '537',            # Home & Garden (general)
}

# ─── CUTTING WIDTH EXTRACTION ─────────────────────────────────────────────────
def extract_cutting_width(title, desc=''):
    """Extract cutting width in inches from product title or description.
    
    Priority order:
    1. Explicit 'Cutting Width' mention in description
    2. Title-based extraction (e.g., '42 in.' in title)
    """
    # Priority 1: Explicit "Cutting Width" field in description
    if desc:
        explicit = re.search(
            r'[Cc]utting\s+[Ww]idth\s*[:\-]?\s*(\d{2,3})\s*(?:inch|in\.?|")?',
            desc, re.IGNORECASE
        )
        if explicit:
            val = int(explicit.group(1))
            if 20 <= val <= 120:
                return str(val)
    
    # Priority 2: Title-based extraction (prefer numbers right before "in." in title)
    # Look for the pattern in title only — more reliable signal
    title_patterns = [
        r'(\d{2,3})["\']?\s*[–\-]?\s*(?:inch|in\.?)\s+(?:cutting|deck|cut|blade)',
        r'(\d{2,3})"\s+(?:cutting|deck)',
        r'(?:^|\s)(\d{2,3})\s+in\.\s',  # "42 in. " in title
        r'(?:^|\s)(\d{2,3})-in\.',       # "42-in." in title
        r'(\d{2,3})(?:in|")\s+(?:\d+.?hp|battery|gas|v\s)',  # 42in 22HP
    ]
    for p in title_patterns:
        m = re.search(p, title, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            if 20 <= val <= 120:
                return str(val)
    return None


def enrich_description_with_cutting_width(desc, cutting_width, title=''):
    """Add cutting width to description if not already present."""
    if not cutting_width:
        return desc
    if 'cutting width' in desc.lower():
        return desc
    
    cw_sentence = f' Features a {cutting_width}-inch cutting width for efficient mowing coverage.'
    return desc.rstrip() + cw_sentence


def add_product_detail(item, attribute_name, attribute_value, section_name='Specifications'):
    """Add a g:product_detail element if not already present."""
    # Check if already exists
    for pd in item.findall(f'{G}product_detail'):
        an = pd.find(f'{G}attribute_name')
        if an is not None and an.text and an.text.lower() == attribute_name.lower():
            return  # Already exists
    
    pd = ET.SubElement(item, f'{G}product_detail')
    sn = ET.SubElement(pd, f'{G}section_name')
    sn.text = section_name
    an = ET.SubElement(pd, f'{G}attribute_name')
    an.text = attribute_name
    av = ET.SubElement(pd, f'{G}attribute_value')
    av.text = attribute_value


def is_mower_product_type(product_type):
    """Return True if the product type is a mower (not outdoor structure)."""
    mower_types = {
        'Riding Lawn Mowers', 'Riding Mowers', 'Ride Mowers',
        'Robotic Mowers', 'Walk-Behind Lawn Mowers', 'Walk-Behind Mowers',
        'Self-Propelled Mowers', 'Tow-Behind Mowers', 'Lawn Mowers & Tractors',
        'Lawn Mowers'
    }
    return product_type in mower_types


# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print(f"Loading {INPUT_FILE}...")
    
    # Register namespaces to preserve them in output
    ET.register_namespace('', '')
    
    # Parse preserving namespaces
    tree = ET.parse(INPUT_FILE)
    root = tree.getroot()
    channel = root.find('channel')
    items = channel.findall('item')
    
    print(f"Processing {len(items)} items...")
    
    stats = {
        'category_fixed': 0,
        'miscategory_fixed': 0,
        'desc_enriched': 0,
        'product_detail_added': 0,
    }
    
    for item in items:
        gc_el = item.find(f'{G}google_product_category')
        pt_el = item.find(f'{G}product_type')
        title_el = item.find(f'{G}title')
        desc_el = item.find(f'{G}description')
        
        cat = gc_el.text.strip() if gc_el is not None and gc_el.text else ''
        product_type = pt_el.text.strip() if pt_el is not None and pt_el.text else ''
        title = title_el.text.strip() if title_el is not None and title_el.text else ''
        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ''
        
        # ── Fix miscategorized products ─────────────────────────────────────
        if 'Lawn Mowers' in cat and product_type in PRODUCT_TYPE_CATEGORY_FIXES:
            new_cat = PRODUCT_TYPE_CATEGORY_FIXES[product_type]
            if gc_el is not None:
                gc_el.text = new_cat
                stats['miscategory_fixed'] += 1
                cat = new_cat  # Update for further processing
        
        # ── Fix text-based categories to numeric IDs ─────────────────────────
        if gc_el is not None and gc_el.text and not gc_el.text.strip().isdigit():
            for text_cat, numeric_id in CATEGORY_MAP.items():
                if gc_el.text.strip() == text_cat:
                    gc_el.text = numeric_id
                    stats['category_fixed'] += 1
                    break
        
        # ── Enrich mower descriptions with cutting width ──────────────────────
        current_cat = gc_el.text.strip() if gc_el is not None and gc_el.text else ''
        is_mower_cat = current_cat == '3650' or 'Lawn Mowers' in cat
        is_mower_type = is_mower_product_type(product_type)
        
        if is_mower_cat or is_mower_type:
            cutting_width = extract_cutting_width(title, desc)
            
            if cutting_width:
                # Enrich description
                if desc_el is not None and 'cutting width' not in desc.lower():
                    new_desc = enrich_description_with_cutting_width(desc, cutting_width, title)
                    desc_el.text = new_desc
                    stats['desc_enriched'] += 1
                
                # Add product_detail tag
                add_product_detail(item, 'Cutting Width', f'{cutting_width} in', 'Specifications')
                stats['product_detail_added'] += 1
    
    # ─── Write output ─────────────────────────────────────────────────────────
    print(f"Writing output...")
    
    # Backup original
    shutil.copy(INPUT_FILE, BACKUP_FILE)
    print(f"  Backup: {BACKUP_FILE}")
    
    # Write main file
    tree.write(OUTPUT_FILE, encoding='UTF-8', xml_declaration=True)
    print(f"  Written: {OUTPUT_FILE}")
    
    # Write live file
    tree.write(LIVE_FILE, encoding='UTF-8', xml_declaration=True)
    print(f"  Written: {LIVE_FILE}")
    
    # ─── Print stats ──────────────────────────────────────────────────────────
    print(f"\n=== CHANGES MADE ===")
    print(f"  Miscategorized products fixed: {stats['miscategory_fixed']}")
    print(f"  Text categories → numeric IDs:  {stats['category_fixed']}")
    print(f"  Descriptions enriched (cutting width added): {stats['desc_enriched']}")
    print(f"  Product detail tags added:       {stats['product_detail_added']}")
    print(f"\nDone!")


if __name__ == '__main__':
    main()
