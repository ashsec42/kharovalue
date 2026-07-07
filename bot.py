import requests
import json
import os
import time
import subprocess

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 300000 # Updated to 3L

MAIN_PAGE_URL = "https://www.marutisuzukitruevalue.com/used-cars-in-goa"
API_URL = "https://www.marutisuzukitruevalue.com/truevalue/api/graphql"
SEEN_CARS_FILE = "seen_cars.json"

def get_seen_cars():
    if not os.path.exists(SEEN_CARS_FILE) or os.path.getsize(SEEN_CARS_FILE) == 0:
        return []
    with open(SEEN_CARS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_and_sync_cars(cars_list):
    with open(SEEN_CARS_FILE, 'w') as f:
        json.dump(cars_list, f)
    
    try:
        subprocess.run(["git", "config", "--global", "user.name", "GitHub Actions Bot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
        subprocess.run(["git", "add", SEEN_CARS_FILE], check=True)
        
        check_diff = subprocess.run(["git", "diff", "--staged", "--quiet"])
        if check_diff.returncode != 0:
            subprocess.run(["git", "commit", "-m", "Radar Sync: Updated baseline trackers"], check=True)
            subprocess.run(["git", "push"], check=True)
            print("--> State synchronized and pushed to GitHub repository.")
    except Exception as e:
        print(f"--> Git push warning: {e}")

def extract_attribute(attributes_list, target_name):
    for attr in attributes_list:
        if attr.get('name') == target_name:
            return attr.get('value', 'N/A')
    return 'N/A'

def send_telegram_alert(car_view):
    try:
        model_name = car_view.get('name', 'Unknown Model').title()
        attributes = car_view.get('attributes', [])
        
        try:
            price = car_view['price']['final']['amount']['value']
        except KeyError:
            price = 0
            
        mf_year = extract_attribute(attributes, 'make_year') 
        km_run = extract_attribute(attributes, 'distance_driven')
        fuel_type = extract_attribute(attributes, 'fuel_type').title()
        transmission = extract_attribute(attributes, 'transmission_type').title()
        owners = extract_attribute(attributes, 'number_of_owners')
        
        rto = extract_attribute(attributes, 'rto').upper()
        rto_city = extract_attribute(attributes, 'rto_code').title()
        reg_info = f"{rto} ({rto_city})" if rto != 'N/A' else "Unknown RTO"
        
        dealer_name = extract_attribute(attributes, 'dealer_name').title()
        dealer_address = extract_attribute(attributes, 'dealer_location').title()
        
        exact_location = dealer_address if dealer_address and dealer_address != 'N/A' else dealer_name
        
        formatted_price = f"₹ {int(price):,}" if price else "Price N/A"
        formatted_km = f"{int(km_run):,} km" if km_run != 'N/A' else "N/A km"
        
        url_key = car_view.get('urlKey', '')
        car_url = f"https://www.marutisuzukitruevalue.com/buy-car/{url_key}" if url_key else MAIN_PAGE_URL

        msg = (
            f"🚀 <b>NEW LISTING DETECTED UNDER BUDGET!</b>\n\n"
            f"🏎️ <b>{model_name} ({mf_year})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> {formatted_price}\n"
            f"🛣️ <b>Mileage:</b> {formatted_km}\n"
            f"⛽ <b>Fuel:</b> {fuel_type}  |  ⚙️ <b>Transmission:</b> {transmission}\n"
            f"👤 <b>Owners:</b> {owners} Owner(s)\n"
            f"🆔 <b>RTO:</b> {reg_info}\n\n"
            f"🏢 <b>Dealer:</b> {dealer_name}\n"
            f"📍 <b>Location:</b> {exact_location}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "View Full Listing 🔗", "url": car_url}]
            ]
        }
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(reply_markup)
        }
        
        requests.post(url, data=payload, timeout=10)
        print(f"--> Rich Telegram alert sent for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram alert: {e}")

def check_true_value():
    print("1. Initializing browser session...")
    session = requests.Session()
    
    # NEW Magento Security Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Magento-Environment-Id": "7293d6a7-a379-4715-bbad-9eebf535818f",
        "Magento-Store-Code": "main_website_store",
        "X-Api-Key": "0a3aab21269e4943b319cee6e59b2a63",
        "Origin": "https://www.marutisuzukitruevalue.com",
        "Referer": "https://www.marutisuzukitruevalue.com/"
    }

    # EXACT GraphQL payload targeting Goa dealers
    payload = {
        "query": "query productSearchByDealers($currentPage: Int = 1, $pageSize: Int = 100, $dealerIds: [String!]) { productSearch( current_page: $currentPage, page_size: $pageSize, phrase: \"\", filter: [ { attribute: \"dealer_code\" in: $dealerIds } ], sort: [{ attribute: \"inStock\", direction: DESC }, { attribute: \"distance_driven\", direction: ASC }] ) { items { productView { __typename sku externalId name urlKey url shortDescription description metaDescription metaKeyword metaTitle lastModifiedAt inStock images(roles: [\"image\"]) { url } attributes(roles: []) { name value } ... on SimpleProductView { price { ...priceFields } } ... on ComplexProductView { priceRange { maximum { ...priceFields } minimum { ...priceFields } } } } } page_info { current_page page_size total_pages } total_count } } fragment priceFields on ProductViewPrice { regular { amount { currency value } } final { amount { currency value } } } ",
        "variables": {
            "current_page": 1,
            "page_size": 100,
            "dealerIds": [
                "50668-MGA-CHOWG", 
                "50366-VRN-SAI"
            ]
        }
    }

    try:
        print("2. Sending GraphQL POST request...")
        
        response = session.post(API_URL, headers=headers, json=payload, timeout=15)
        print(f"   HTTP Status Code: {response.status_code}")
        response.raise_for_status() 
        
        data = response.json()
        
        # Traverse the new Magento structure
        car_list = data.get('data', {}).get('productSearch', {}).get('items', [])
        print(f"3. Number of cars identified: {len(car_list)}")

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for item in car_list:
            car_view = item.get('productView', {})
            car_id = car_view.get('sku') or car_view.get('id')
            
            if not car_id:
                continue
                
            # Skip cars that are already marked out of stock
            if not car_view.get('inStock', False):
                continue

            try:
                car_price = int(car_view['price']['final']['amount']['value'])
            except (KeyError, ValueError, TypeError):
                car_price = 9999999
            
            if car_id not in seen_cars and car_price <= MAX_BUDGET:
                if not is_first_run:
                    send_telegram_alert(car_view)
                seen_cars.append(car_id)
                new_cars_found = True

        if is_first_run or new_cars_found:
            save_and_sync_cars(seen_cars)
            print("4. Local tracking database updated.")
        else:
            print("4. No new inventory updates detected.")

    except requests.exceptions.Timeout:
        print("--> Connection timed out waiting for server response. Skipping this cycle.")
    except Exception as e:
        print(f"CRITICAL SYSTEM ERROR: {e}")

if __name__ == "__main__":
    print("🚀 TARGET ACQUIRED: Launching constant live loop tracking (5m intervals)...")
    while True:
        check_true_value()
        print("💤 Sleeping for 5 minutes...")
        time.sleep(300)
