import requests
import json

def get_car_details(sku):
    API_URL = "https://www.marutisuzukitruevalue.com/truevalue/api/graphql"
    
    # The required Magento security headers you discovered
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Magento-Environment-Id": "7293d6a7-a379-4715-bbad-9eebf535818f",
        "Magento-Store-Code": "main_website_store",
        "X-Api-Key": "0a3aab21269e4943b319cee6e59b2a63",
        "Origin": "https://www.marutisuzukitruevalue.com"
    }

    # The exact GraphQL query for Deep Details
    payload = {
        "query": "query GET_PRODUCT_DATA($skus: [String]) { products(skus: $skus) { ...PRODUCT_FRAGMENT } } fragment PRODUCT_FRAGMENT on ProductView { __typename id sku name shortDescription metaDescription metaKeyword metaTitle description inStock addToCartAllowed url urlKey externalId images(roles: []) { url label roles } attributes(roles: []) { name label value roles } ... on SimpleProductView { price { roles regular { amount { value currency } } final { amount { value currency } } } } ... on ComplexProductView { options { ...PRODUCT_OPTION_FRAGMENT } ...PRICE_RANGE_FRAGMENT } } fragment PRODUCT_OPTION_FRAGMENT on ProductViewOption { id title required multi values { id title inStock __typename ... on ProductViewOptionValueProduct { title quantity isDefault __typename product { sku shortDescription metaDescription metaKeyword metaTitle name price { final { amount { value currency } } regular { amount { value currency } } roles } } } ... on ProductViewOptionValueSwatch { id title type value inStock } } } fragment PRICE_RANGE_FRAGMENT on ComplexProductView { priceRange { maximum { final { amount { value currency } } regular { amount { value currency } } roles } minimum { final { amount { value currency } } regular { amount { value currency } } roles } } }",
        "variables": {
            "skus": [sku]
        }
    }

    print(f"Fetching full dossier for SKU: {sku}...\n")
    response = requests.post(API_URL, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        products = data.get('data', {}).get('products', [])
        
        if not products:
            print("❌ Car not found or removed from database.")
            return

        car = products[0]
        name = car.get('name', 'Unknown')
        price = car.get('price', {}).get('final', {}).get('amount', {}).get('value', 0)
        
        # Convert the attributes list into a searchable dictionary
        attributes = {attr['name']: attr['value'] for attr in car.get('attributes', [])}
        
        print(f"==================================================")
        print(f" 🏎️  {name.upper()} | ₹{price:,.0f}")
        print(f"==================================================")
        print(f" 📅 Registration:  {attributes.get('registration_date', 'N/A').split(' ')[0]}")
        print(f" 👤 Owners:        {attributes.get('ownership', 'N/A')}")
        print(f" 🏢 Dealer:        {attributes.get('dealer_name', 'N/A')} ({attributes.get('car_city', 'N/A')})")
        print(f" 📍 RTO:           {attributes.get('rto', 'N/A')} - {attributes.get('rto_code', 'N/A')}")
        print(f"\n 🛠️  MECHANICAL RATINGS (Out of 5.0):")
        print(f"    Engine:       {attributes.get('engine_rating', 'N/A')}")
        print(f"    Exterior:     {attributes.get('exterior_rating', 'N/A')}")
        print(f"    Suspension:   {attributes.get('suspension_rating', 'N/A')}")
        print(f"    Functional:   {attributes.get('functional_rating', 'N/A')}  <-- Take note of this!")
        
        print(f"\n 📸 RAW IMAGE LINKS:")
        for img in car.get('images', [])[:3]: # Print first 3 images
            print(f"    - {img.get('url')}")
        print(f"==================================================")
        
    else:
        print(f"❌ API Request Failed. Status: {response.status_code}")

# Test the script with the exact SKU you found
get_car_details("B26019437933")
