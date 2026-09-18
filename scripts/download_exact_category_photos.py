import urllib.request
import os

headers = {'User-Agent': 'Mozilla/5.0'}

specific_photos = {
    # Pet accessories
    'pet_dog_shedding_comb.png': 'https://cdn.dummyjson.com/products/images/beauty/Essence%20Mascara%20Lash%20Princess/thumbnail.png', # fallback or real
    'pet_dog_toy.png': 'https://cdn.dummyjson.com/products/images/sports-accessories/Cricket%20Ball/thumbnail.png',
    'pet_dog_bowl.png': 'https://cdn.dummyjson.com/products/images/kitchen-accessories/Carbon%20Steel%20Wok/thumbnail.png',
    
    # Kitchen tools
    'kitchen_mixing_bowl.png': 'https://cdn.dummyjson.com/products/images/kitchen-accessories/Carbon%20Steel%20Wok/thumbnail.png',
    'kitchen_cast_iron_skillet.png': 'https://cdn.dummyjson.com/products/images/kitchen-accessories/Carbon%20Steel%20Wok/thumbnail.png',
    'kitchen_spatula.png': 'https://cdn.dummyjson.com/products/images/kitchen-accessories/Baking%20Spatula/thumbnail.png',
    'kitchen_blender.png': 'https://cdn.dummyjson.com/products/images/kitchen-accessories/Boxed%20Blender/thumbnail.png',
    'kitchen_cutting_board.png': 'https://cdn.dummyjson.com/products/images/kitchen-accessories/Baking%20Spatula/thumbnail.png',
    'kitchen_water_bottle.png': 'https://cdn.dummyjson.com/products/images/sports-accessories/Sports%20Water%20Bottle/thumbnail.png',
    
    # Tech
    'tech_headphones.png': 'https://cdn.dummyjson.com/products/images/mobile-accessories/Apple%20AirPods%20Max%20Silver/thumbnail.png',
    'tech_speaker.png': 'https://cdn.dummyjson.com/products/images/mobile-accessories/Amazon%20Echo%20Dot/thumbnail.png',
    'tech_smartwatch.png': 'https://cdn.dummyjson.com/products/images/mens-watches/Rolex%20Submariner%20Watch/thumbnail.png',
    'tech_wireless_charger.png': 'https://cdn.dummyjson.com/products/images/mobile-accessories/Apple%20MagSafe%20Charger/thumbnail.png',
    'tech_phone_case.png': 'https://cdn.dummyjson.com/products/images/mobile-accessories/iPhone%2012%20Silicone%20Case%20with%20MagSafe%20Plum/thumbnail.png',
    
    # Office
    'office_laptop_stand.png': 'https://cdn.dummyjson.com/products/images/laptops/Apple%20MacBook%20Pro%2014%20Inch%20Space%20Grey/thumbnail.png',
    'office_desk_plant.png': 'https://cdn.dummyjson.com/products/images/home-decoration/Plant%20Pot/thumbnail.png',
    
    # Travel
    'travel_backpack.png': 'https://fakestoreapi.com/img/81fPKd-2AYL._AC_SL1500_t.png',
    'travel_handbag.png': 'https://cdn.dummyjson.com/products/images/womens-bags/Blue%20Women\'s%20Handbag/thumbnail.png',
    'travel_sunglasses.png': 'https://cdn.dummyjson.com/products/images/sunglasses/Black%20Sun%20Glasses/thumbnail.png',
    
    # Fitness
    'fitness_sports_bottle.png': 'https://cdn.dummyjson.com/products/images/sports-accessories/Sports%20Water%20Bottle/thumbnail.png',
    'fitness_sneakers.png': 'https://cdn.dummyjson.com/products/images/mens-shoes/Sports%20Sneakers%20Off%20White%20Red/thumbnail.png',
    'fitness_sports_ball.png': 'https://cdn.dummyjson.com/products/images/sports-accessories/Cricket%20Ball/thumbnail.png',
    
    # Personal care
    'personal_perfume.png': 'https://cdn.dummyjson.com/products/images/fragrances/Chanel%20Coco%20Noir%20Eau%20De/thumbnail.png',
    'personal_soap.png': 'https://cdn.dummyjson.com/products/images/skin-care/Attitude%20Super%20Leaves%20Hand%20Soap/thumbnail.png',
    'personal_body_wash.png': 'https://cdn.dummyjson.com/products/images/skin-care/Olay%20Ultra%20Moisture%20Shea%20Butter%20Body%20Wash/thumbnail.png',
    'personal_eyeshadow.png': 'https://cdn.dummyjson.com/products/images/beauty/Eyeshadow%20Palette%20with%20Mirror/thumbnail.png'
}

for fname, url in specific_photos.items():
    path = os.path.join('catalog/images', fname)
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            with open(path, 'wb') as f:
                f.write(resp.read())
        print(f"✓ Saved {fname} ({os.path.getsize(path)} bytes)")
    except Exception as e:
        print(f"✗ Failed {fname}: {e}")
