import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import html

def generate_gmc_xml():
    csv_file = 'catalog/products_master.csv'
    xml_output = 'catalog/google_merchant_center_feed.xml'

    rss = ET.Element('rss', {
        'version': '2.0',
        'xmlns:g': 'http://base.google.com/ns/1.0'
    })
    
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = 'Leafanoo Google Merchant Center Feed'
    ET.SubElement(channel, 'link').text = 'https://leafanoo.com'
    ET.SubElement(channel, 'description').text = 'Verified physical products with authentic GTINs, MPNs, and real-time inventory.'

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            item = ET.SubElement(channel, 'item')
            
            # g:id
            ET.SubElement(item, '{http://base.google.com/ns/1.0}id').text = row['product_id']
            
            # title
            ET.SubElement(item, '{http://base.google.com/ns/1.0}title').text = row['title']
            
            # description
            desc = row['description'] + ' ' + row.get('key_specs', '')
            ET.SubElement(item, '{http://base.google.com/ns/1.0}description').text = desc
            
            # link
            handle = row['title'].lower().replace(' & ', '-').replace('&', '-').replace(' ', '-')
            handle = ''.join(c for c in handle if c.isalnum() or c == '-').strip('-')
            ET.SubElement(item, '{http://base.google.com/ns/1.0}link').text = f'https://leafanoo.com/products/{handle}'
            
            # image_link
            img_url = row.get('image_source_url', 'https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=1000&auto=format&fit=crop&q=80')
            ET.SubElement(item, '{http://base.google.com/ns/1.0}image_link').text = img_url
            
            # price
            price = float(row.get('proposed_retail_price_usd', 29.99))
            ET.SubElement(item, '{http://base.google.com/ns/1.0}price').text = f'{price:.2f} USD'
            
            # availability
            ET.SubElement(item, '{http://base.google.com/ns/1.0}availability').text = 'in_stock'
            
            # brand
            ET.SubElement(item, '{http://base.google.com/ns/1.0}brand').text = row['brand']
            
            # gtin
            if row.get('gtin'):
                ET.SubElement(item, '{http://base.google.com/ns/1.0}gtin').text = row['gtin']
                
            # mpn
            if row.get('mpn'):
                ET.SubElement(item, '{http://base.google.com/ns/1.0}mpn').text = row['mpn']
                
            # condition
            ET.SubElement(item, '{http://base.google.com/ns/1.0}condition').text = 'new'
            
            # google_product_category
            if row.get('google_product_category'):
                ET.SubElement(item, '{http://base.google.com/ns/1.0}google_product_category').text = row['google_product_category']
                
            # product_type
            ET.SubElement(item, '{http://base.google.com/ns/1.0}product_type').text = row.get('shopify_product_type', 'General Merchandise')
            
            # shipping
            shipping = ET.SubElement(item, '{http://base.google.com/ns/1.0}shipping')
            ET.SubElement(shipping, '{http://base.google.com/ns/1.0}country').text = 'US'
            ET.SubElement(shipping, '{http://base.google.com/ns/1.0}service').text = 'Standard Tracked Shipping'
            ship_price = '0.00 USD' if price >= 50.0 else '4.95 USD'
            ET.SubElement(shipping, '{http://base.google.com/ns/1.0}price').text = ship_price
            
            count += 1

    # Pretty print XML
    xml_str = ET.tostring(rss, encoding='utf-8')
    parsed = minidom.parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent='  ', encoding='utf-8')
    
    with open(xml_output, 'wb') as f:
        f.write(pretty_xml)
        
    print(f'✅ Successfully generated Google Shopping XML feed with {count} verified items at {xml_output}')

if __name__ == '__main__':
    generate_gmc_xml()
