import requests
import json
import os
import time
import subprocess
import urllib.parse  # Added for URL encoding the GET request

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MAX_BUDGET = 300000  # 3 Lakhs

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
            
        # Basic Info
        km_run = extract_attribute(attributes, 'distance_driven')
        fuel_type = extract_attribute(attributes, 'fuel_type').title()
        transmission = extract_attribute(attributes, 'transmission_type').title()
        owners = extract_attribute(attributes, 'number_of_owners')
        
        # Color, Variant, Warranty
        car_color = extract_attribute(attributes, 'color').title()
        variant = extract_attribute(attributes, 'car_variant').upper()
        
        certified_raw = extract_attribute(attributes, 'true_value_certified')
        certified = "Yes ✅" if certified_raw.lower() == 'yes' else "No ❌"
        
        warranty_raw = extract_attribute(attributes, 'warranty_info')
        if warranty_raw in ['0M', '0', 'N/A']:
            warranty = "None"
        else:
            warranty = warranty_raw

        # DEEP DETAILS EXTRACTION
        reg_date_raw = extract_attribute(attributes, 'registration_date')
        reg_date = reg_date_raw.split(' ')[0] if reg_date_raw != 'N/A' else 'N/A'
        
        engine = extract_attribute(attributes, 'engine_rating')
        engine = engine[:3] if engine != 'N/A' else 'N/A'
        
        exterior = extract_attribute(attributes, 'exterior_rating')
        exterior = exterior[:3] if exterior != 'N/A' else 'N/A'
        
        suspension = extract_attribute(attributes, 'suspension_rating')
        suspension = suspension[:3] if suspension != 'N/A' else 'N/A'
        
        functional = extract_attribute(attributes, 'functional_rating')
        functional = functional[:3] if functional != 'N/A' else 'N/A'
        
        # Location & RTO
        rto = extract_attribute(attributes, 'rto').upper()
        rto_city = extract_attribute(attributes, 'rto_code').title()
        reg_info = f"{rto} ({rto_city})" if rto != 'N/A' else "Unknown RTO"
        
        dealer_name = extract_attribute(attributes, 'dealer_name').title()
        dealer_address = extract_attribute(attributes, 'dealer_location').title()
        exact_location = dealer_address if dealer_address and dealer_address != 'N/A' else dealer_name
        
        # EXACT PHONE NUMBER EXTRACTION
        dealer_info_str = extract_attribute(attributes, 'dealer_additional_info')
        phone_number = "Not Provided"
        if dealer_info_str != 'N/A':
            try:
                dealer_json = json.loads(dealer_info_str)
                phone_number = dealer_json.get('phone', 'Not Provided')
            except json.JSONDecodeError:
                pass
                
        # --- 📸 ALL IMAGES EXTRACTION ---
        images = car_view.get('images', [])
        image_urls = [img.get('url') for img in images if img.get('url')]

        # Formatting
        formatted_price = f"₹ {int(price):,}" if price else "Price N/A"
        formatted_km = f"{int(km_run):,} km" if km_run != 'N/A' else "N/A km"
        
        url_key = car_view.get('urlKey', '')
        car_url = f"https://www.marutisuzukitruevalue.com/buy-car/{url_key}" if url_key else MAIN_PAGE_URL

        msg = (
            f"🚀 <b>NEW LISTING DETECTED!</b>\n\n"
            f"🏎️ <b>{model_name}</b>\n"
            f"🏷️ <b>Variant:</b> {variant}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> {formatted_price}\n"
            f"🛣️ <b>Mileage:</b> {formatted_km}\n"
            f"🎨 <b>Color:</b> {car_color}\n"
            f"📅 <b>Registered:</b> {reg_date}\n"
            f"⛽ <b>Fuel:</b> {fuel_type}  |  ⚙️ <b>Trans:</b> {transmission}\n"
            f"👤 <b>Owners:</b> {owners} Owner(s)\n"
            f"🆔 <b>RTO:</b> {reg_info}\n\n"
            f"🛡️ <b>Certified:</b> {certified}\n"
            f"📑 <b>Warranty:</b> {warranty}\n\n"
            f"🛠️ <b>MECHANICAL RATINGS:</b>\n"
            f"  • Engine: {engine} / 5.0\n"
            f"  • Exterior: {exterior} / 5.0\n"
            f"  • Suspension: {suspension} / 5.0\n"
            f"  • Functional: {functional} / 5.0\n\n"
            f"🏢 <b>Dealer:</b> {dealer_name}\n"
            f"📍 <b>Location:</b> {exact_location}\n"
            f"📞 <b>Contact:</b> <code>{phone_number}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "View Full Listing 🔗", "url": car_url}]
            ]
        }
        
        # --- 📡 TELEGRAM PAYLOAD ROUTING ---
        if image_urls:
            url_main = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            payload_main = {
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": image_urls[0],
                "caption": msg,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(reply_markup)
            }
            requests.post(url_main, data=payload_main, timeout=10)
            
            if len(image_urls) > 1:
                media_group = [{"type": "photo", "media": url} for url in image_urls[1:10]]
                url_gallery = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMediaGroup"
                payload_gallery = {
                    "chat_id": TELEGRAM_CHAT_ID,
                    "media": media_group
                }
                requests.post(url_gallery, json=payload_gallery, timeout=15)
        else:
            url_text = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload_text = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(reply_markup)
            }
            requests.post(url_text, data=payload_text, timeout=10)
            
        print(f"--> Rich Telegram alert & gallery sent for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram alert: {e}")

def check_true_value():
    print("1. Initializing browser session...")
    session = requests.Session()
    
    # Updated headers based on the actual network request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.marutisuzukitruevalue.com/used-cars-in-goa"
    }

    all_car_items = []
    current_page = 1
    page_size = 12

    try:
        print("2. Querying GraphQL API with dynamic pagination loop...")
        while True:
            # Updated GraphQL to use car_city filter and new sorting
            graphql_query = f"""
            query ProductSearch {{ 
                productSearch(
                    phrase: "" 
                    filter: [
                        {{ attribute: "price", range: {{ from: 0, to: {MAX_BUDGET} }} }}, 
                        {{ attribute: "car_city", in: ["Goa"] }}
                    ] 
                    sort: [
                        {{ attribute: "listing_score", direction: DESC }},
                        {{ attribute: "news_from_date", direction: DESC }}
                    ] 
                    page_size: {page_size} 
                    current_page: {current_page}
                ) {{ 
                    total_count
                    page_info {{
                        page_size
                        total_pages
                        current_page
                    }}
                    items {{ 
                        productView {{ 
                            inStock 
                            name 
                            sku 
                            externalId 
                            urlKey 
                            url 
                            images(roles: ["image"]) {{ url }} 
                            attributes(roles: []) {{ name value }} 
                            ... on SimpleProductView {{ 
                                price {{ 
                                    final {{ amount {{ value currency }} }} 
                                }} 
                            }} 
                        }} 
                    }} 
                }} 
            }}
            """

            # Build URL parameters for GET request
            params = {
                'query': graphql_query,
                'variables': '{"id":2}'
            }
            
            request_url = f"{API_URL}?{urllib.parse.urlencode(params)}"

            # Changed from POST to GET
            response = session.get(request_url, headers=headers, timeout=15)
            response.raise_for_status() 
            
            data = response.json()
            product_search_data = data.get('data', {}).get('productSearch', {})
            
            total_count = product_search_data.get('total_count', 0)
            page_info = product_search_data.get('page_info', {})
            total_pages = page_info.get('total_pages', 1)
            
            items = product_search_data.get('items', [])
            all_car_items.extend(items)
            
            print(f"    Fetched page {current_page} of {total_pages} (Items retrieved so far: {len(all_car_items)}/{total_count})")

            # Break loop if we have processed all available pages
            if current_page >= total_pages or not items:
                break
            
            current_page += 1
            time.sleep(1)  # Polite short delay between pagination requests

        print(f"3. Total unique inventory records collected: {len(all_car_items)}")

        seen_cars = get_seen_cars()
        is_first_run = len(seen_cars) == 0 
        new_cars_found = False

        for item in all_car_items:
            car_view = item.get('productView', {})
            car_id = car_view.get('sku') or car_view.get('externalId')
            
            if not car_id:
                continue
                
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

    except requests.exceptions.HTTPError as e:
        print(f"--> HTTP Error: {e.response.status_code} - {e.response.text}")
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
