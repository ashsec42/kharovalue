def send_telegram_alert(item):
    try:
        car = item.get('_source', {})
        
        # Extract rich details from the Burp log schema
        model_name = car.get('name', 'Unknown Model').title()
        mf_year = car.get('mfYear', 'Unknown Year')
        price = car.get('price', 0)
        km_run = car.get('kmRun', 0)
        fuel_type = car.get('fuelType', 'N/A').title()
        transmission = car.get('transmissionType', 'N/A').title()
        owners = car.get('numberOfOwner', 'N/A')
        reg_num = car.get('registrationNumber', 'N/A').upper()
        
        # --- NEW LOCATION DATA ---
        dealer_name = car.get('dealerName', 'True Value Dealer').title()
        dealer_address = car.get('dealerAddress', 'Unknown Address').title()
        
        # Formatting
        formatted_price = f"₹ {price:,}" if isinstance(price, (int, float)) else f"₹ {price}"
        formatted_km = f"{km_run:,} km" if isinstance(km_run, (int, float)) else f"{km_run} km"
        
        # Build URL
        detail_url = car.get('detailUrl', '')
        car_url = f"https://www.marutisuzukitruevalue.com/buy-car/{detail_url}" if detail_url else MAIN_PAGE_URL

        # Sleek HTML Layout with Full Address
        msg = (
            f"🚀 <b>NEW LISTING DETECTED UNDER BUDGET!</b>\n\n"
            f"🏎️ <b>{model_name} ({mf_year})</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Price:</b> {formatted_price}\n"
            f"🛣️ <b>Mileage:</b> {formatted_km}\n"
            f"⛽ <b>Fuel:</b> {fuel_type}  |  ⚙️ <b>Transmission:</b> {transmission}\n"
            f"👤 <b>Owners:</b> {owners} Owner(s)\n"
            f"🆔 <b>Reg No:</b> {reg_num}\n\n"
            f"🏢 <b>Dealer:</b> {dealer_name}\n"
            f"📍 <b>Location:</b> {dealer_address}\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )
        
        # Create a premium inline button payload
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
        
        requests.post(url, data=payload)
        print(f"--> Rich Telegram alert sent for: {model_name}")
    except Exception as e:
        print(f"--> Failed to send Telegram alert: {e}")
