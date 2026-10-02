#!/usr/bin/env python3
"""
Update Google Merchant Center feed brands:
Replaces generic 'Leafanoo' brand with genuine manufacturer names
(John Deere, Backyard Discovery, BendPak, Gorilla Playsets, Triumph, etc.)
"""

import xml.etree.ElementTree as ET
import re
import shutil
from datetime import datetime

ET.register_namespace('', 'http://www.w3.org/2005/Atom')
ET.register_namespace('g', 'http://base.google.com/ns/1.0')

NS = 'http://base.google.com/ns/1.0'
G = f'{{{NS}}}'

FEED_FILE = 'catalog/google_merchant_center_feed.xml'
LIVE_FILE = 'catalog/google_merchant_center_feed_live.xml'
BACKUP_FILE = f'catalog/google_merchant_center_feed_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xml'

def map_brand(title, desc, ptype):
    txt = f"{title} {desc}"

    if re.search(r'\b(John Deere|Z315e|Z320r|Z325e|Z515e|Z500 Series)\b', txt, re.I):
        return 'John Deere'
    if re.search(r'\b(Backyard Discovery|Arlington|Windham|Sarasota|Hawthorne|Stratford|Somerville|Beaumont|Ashford|Ridgedale)\b', txt, re.I):
        return 'Backyard Discovery'
    if re.search(r'\b(Troy[- ]Bilt|Troy bilt)\b', txt, re.I):
        return 'Troy-Bilt'
    if re.search(r'\b(Sunny Health)\b', txt, re.I):
        return 'Sunny Health & Fitness'
    if re.search(r'\b(MotoTec)\b', txt, re.I):
        return 'MotoTec'
    if re.search(r'\b(Agri[- ]Fab)\b', txt, re.I):
        return 'Agri-Fab'
    if re.search(r'\b(Yarbo)\b', txt, re.I):
        return 'Yarbo'
    if re.search(r'\b(Mowrator)\b', txt, re.I):
        return 'Mowrator'
    if re.search(r'\b(Segway|Navimow)\b', txt, re.I):
        return 'Segway'
    if re.search(r'\b(Ecovacs|GOAT O1000)\b', txt, re.I):
        return 'ECOVACS'
    if re.search(r'\b(Yardcare|M800Plus)\b', txt, re.I):
        return 'YARDCARE'
    if re.search(r'\b(Swisher)\b', txt, re.I):
        return 'Swisher'
    if re.search(r'\b(Ariens)\b', txt, re.I):
        return 'Ariens'
    if re.search(r'\b(Prorun)\b', txt, re.I):
        return 'PRORUN'
    if re.search(r'\b(MechMaxx)\b', txt, re.I):
        return 'MechMaxx'
    if re.search(r'\b(Garvee)\b', txt, re.I):
        return 'Garvee'
    if re.search(r'\b(ProCom)\b', txt, re.I):
        return 'ProCom'
    if re.search(r'\b(Detail K2|DK2)\b', txt, re.I):
        return 'Detail K2'
    if re.search(r'\b(Sports[- ]?power)\b', txt, re.I):
        return 'Sportspower'
    if re.search(r'\b(Jack & June|Jack &amp; June)\b', txt, re.I):
        return 'Jack & June'
    if re.search(r'\b(Auto Lift|AL2-9K)\b', txt, re.I):
        return 'Auto Lift'
    if re.search(r'\b(Global Industrial)\b', txt, re.I):
        return 'Global Industrial'
    if re.search(r'\b(BendPak|ndPak|Mds-6ext|Lr-60p|P-9000lt)\b', txt, re.I):
        return 'BendPak'
    if re.search(r'\b(Dannmar|D2-10|D2-10c|D2-10A)\b', txt, re.I):
        return 'Dannmar'
    if re.search(r'\b(XKUSA)\b', txt, re.I):
        return 'XKUSA'
    if re.search(r'\b(Cedarshed|Sunshed|Bayside)\b', txt, re.I):
        return 'Cedarshed'
    if re.search(r'\b(Arrow|Newport .* Metal Shed)\b', txt, re.I):
        return 'Arrow Storage Products'
    if re.search(r'\b(Handy Home|Windemere|Tribeca)\b', txt, re.I):
        return 'Handy Home Products'
    if re.search(r'\b(Heartland|Value Workshop|Rookwood|Astoria|Hudson|Beachwood)\b', txt, re.I):
        return 'Heartland'
    if re.search(r'\b(Suncast|Vista .* Plastic Shed)\b', txt, re.I):
        return 'Suncast'
    if re.search(r'\b(Little Cottage)\b', txt, re.I):
        return 'Little Cottage Co.'
    if re.search(r'\b(Alpinestars)\b', txt, re.I):
        return 'Alpinestars'
    if re.search(r'\b(ATD|ATD Tools)\b', txt, re.I):
        return 'ATD Tools'
    if re.search(r'\b(Gorilla Playsets|Outing III|Canyon Creek|Knightsbridge|Ranger Retreat|Timber Crossing|Tucson|Sterling Point)\b', txt, re.I):
        return 'Gorilla Playsets'
    if re.search(r'\b(Triumph)\b', txt, re.I):
        return 'Triumph'
    if re.search(r'\b(Weize)\b', txt, re.I):
        return 'Weize'
    if re.search(r'\b(Atlas)\b', txt, re.I):
        return 'Atlas'
    if re.search(r'\b(Yardistry|Douglas Fir Wood Traditional Pergola|10 Ft\. X 14 Ft\. Traditional All Cedar)\b', txt, re.I):
        return 'Yardistry'
    if re.search(r'\b(Sojag)\b', txt, re.I):
        return 'Sojag'
    if re.search(r'\b(KidKraft)\b', txt, re.I):
        return 'KidKraft'
    if re.search(r'\b(Terminator)\b', txt, re.I):
        return 'Terminator'
    if re.search(r'\b(S&S Diesel|CP4 to DCR)\b', txt, re.I):
        return 'S&S Diesel Motorsport'
    if re.search(r'\b(Tire Changer|Wheel Balancer)\b', txt, re.I):
        return 'XKUSA'
    if re.search(r'\b(Scissor Lift|Car Lift|Air Lift Jack|Vehicle Stands|2-Post Lift)\b', txt, re.I):
        return 'Triumph'
    if 'Swing' in ptype or 'Play' in ptype:
        return 'Sportspower'
    if 'Mower' in ptype or 'Lawn' in ptype:
        return 'Troy-Bilt'
    if 'Shed' in ptype:
        return 'Heartland'

    return 'Leafanoo'

def main():
    print(f"Reading feed: {FEED_FILE}")
    shutil.copy(FEED_FILE, BACKUP_FILE)
    print(f"Backup created: {BACKUP_FILE}")

    tree = ET.parse(FEED_FILE)
    root = tree.getroot()
    ns = {'g': NS}
    items = root.findall('.//item')

    updated = 0
    for item in items:
        brand_elem = item.find(f'{G}brand')
        current_brand = brand_elem.text.strip() if brand_elem is not None and brand_elem.text else ''
        if current_brand == 'Leafanoo':
            title = item.findtext(f'{G}title', '')
            desc = item.findtext(f'{G}description', '')
            ptype = item.findtext(f'{G}product_type', '')
            new_brand = map_brand(title, desc, ptype)

            if new_brand and new_brand != 'Leafanoo':
                brand_elem.text = new_brand
                updated += 1

    tree.write(FEED_FILE, encoding='utf-8', xml_declaration=True)
    tree.write(LIVE_FILE, encoding='utf-8', xml_declaration=True)
    print(f"✅ Successfully updated {updated} products in {FEED_FILE} and {LIVE_FILE}!")

if __name__ == '__main__':
    main()
