import requests
import json
from datetime import datetime, timedelta

# === Credentials ===
CORE_ACCOUNT_ID = "3384f900-b8b1-41bc-8324-1e6000e897ec"
CORE_APP_KEY = "c1bf7dbf-5365-9d50-95a1-960ee4455445"
INPOST_API_KEY = "da3f39f46c9f473d29cc8ec40a0ae787"

core_headers = {
    "Content-Type": "application/json",
    "api-auth-accountid": CORE_ACCOUNT_ID,
    "api-auth-applicationkey": CORE_APP_KEY
}

inpost_headers = {
    "Content-Type": "application/json"
}

def get_core_sale(sale_id):
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale?ID={sale_id}&CombineAdditionalCharges=true"
    response = requests.get(url, headers=core_headers)
    
    if response.status_code != 200:
        print(f"❌ Error fetching sale {sale_id}: {response.status_code} - {response.text}")
        return {}
        
    return response.json()

def get_fulfillment_status(sale_id):
    """Get actual fulfillment status from the fulfillment endpoint."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment?SaleID={sale_id}"
    try:
        response = requests.get(url, headers=core_headers)
        print(f"📥 Fulfillment API response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📥 Fulfillment data: {json.dumps(data, indent=2)[:500]}...")  # Show first 500 chars
            return data
        else:
            print(f"❌ Fulfillment API error: {response.status_code} - {response.text}")
        return {}
    except Exception as e:
        print(f"❌ Error fetching fulfillment status: {str(e)}")
        return {}

def get_country_code(country_name):
    return {
        "Poland": "PL", "Germany": "DE", "France": "FR", "United Kingdom": "GB", "Ireland": "IE",
        "Italy": "IT", "Spain": "ES", "Netherlands": "NL", "Belgium": "BE", "Luxembourg": "LU", "Denmark": "DK"
    }.get(country_name, "PL")

def build_items(lines):
    items = []
    for line in lines:
        sku = line.get("SKU", line.get("Sku", ""))
        if sku == "" or line.get("ProductID") == "00000000-0000-0000-0000-000000000000":
            continue
        items.append({
            "sku": sku,
            "externalId": line["ProductID"],
            "ordered": line["Quantity"],
            "quantity": line["Quantity"],
            "description": line["Name"],
            "weight": float(line.get("ProductWeight", 0.1)) / 1000,
            "vat_code": 23,
            "price_gross": float(line["Price"]),
            "price_net": float(line["Total"])
        })
    return items

def build_payload_from_core(data):
    order_data = data["Order"]
    shipping = data.get("ShippingAddress", {})
    clientOrderNumber = order_data["SaleOrderNumber"]
    orderDate = data.get("SaleOrderDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    deliveryRecipient = data.get("Customer", "Unknown Customer")
    deliveryEmail = data.get("Email", "test@example.com")
    deliveryStreet = shipping.get("Line1", "Test Street 10")
    deliveryPostCode = shipping.get("Postcode", "00-001")
    deliveryCity = shipping.get("City", "Warszawa")
    deliveryCountry = get_country_code(shipping.get("Country", "Poland"))

    is_poland = shipping.get("Country") == "Poland"
    carrier = "Kurier InPost - ShipX" if is_poland else "FedEx"
    deliveryPointId = None if is_poland else (shipping.get("ID") or "KKZ01A")
    depotId = "556239"

    currency = order_data.get("SaleOrderCurrency") or order_data.get("Currency") or ("PLN" if is_poland else "EUR")
    phone = data.get("Phone", "+48500600700" if is_poland else "+441403740350")

    items = build_items(order_data["Lines"])
    priceGross = sum(item['price_gross'] for item in items)

    return {
        "clientOrderNumber": clientOrderNumber,
        "externalId": clientOrderNumber,
        "paymentMethod": currency,
        "currencySymbol": currency,
        "orderDate": orderDate,
        "carrier": carrier,
        "deliveryRecipient": deliveryRecipient,
        "deliveryPhone": phone,
        "deliveryEmail": deliveryEmail,
        "deliveryStreet": deliveryStreet,
        "deliveryPostCode": deliveryPostCode,
        "deliveryCity": deliveryCity,
        "deliveryCountry": deliveryCountry,
        "deliveryPointId": deliveryPointId,
        "depotId": depotId,
        "shipmentPrice": 0.00,
        "priceGross": priceGross,
        "items": items,
        "comments": "Created from test.py with Core SaleID"
    }

def send_to_inpost(payload):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}"
    response = requests.post(url, headers=inpost_headers, json=payload)
    print(f"📦 Sent to InPost: {payload['externalId']} | Status: {response.status_code}")
    
    # Check if it's a duplicate order error (409)
    if response.status_code == 409:
        print("ℹ️  Order already exists in InPost (duplicate), continuing...")
        return response  # Continue processing since order exists
    
    return response

def get_inpost_order_by_external_id(order_id):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}&filters[external_id]={order_id}"
    response = requests.get(url)
    return response.json().get("items", [])

def get_inpost_order_by_id(order_id):
    """Get InPost order by internal ID"""
    url = f"https://api-inpost.linker.shop/public-api/v1/orders/{order_id}?apikey={INPOST_API_KEY}"
    try:
        response = requests.get(url, headers=inpost_headers)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def cancel_order_in_inpost(inpost_order_id):
    """Cancel an order in InPost by updating its status to 'A'"""
    base_url = f"https://api-inpost.linker.shop/public-api/v1/orders"
    api_key_param = f"apikey={INPOST_API_KEY}"
    
    # Step 1: Get the complete order details
    print(f"📥 Fetching order details for {inpost_order_id}...")
    get_url = f"{base_url}/{inpost_order_id}?{api_key_param}"
    
    try:
        get_response = requests.get(get_url, headers=inpost_headers)
        if get_response.status_code != 200:
            print(f"❌ Failed to fetch order {inpost_order_id}: {get_response.status_code} - {get_response.text}")
            return False
            
        order_data = get_response.json()
        print(f"✅ Successfully fetched order details")
        
    except Exception as e:
        print(f"❌ Error fetching order {inpost_order_id}: {str(e)}")
        return False
    
    # Step 2: Update the order status to "A" (cancelled)
    # Keep all required fields and only change the orderStatus
    order_data["orderStatus"] = "A"
    
    # Remove any fields that shouldn't be included in the update or might cause issues
    fields_to_remove = ["id", "uuid", "createdAt", "updatedAt", "statusHistory", 
                       "externalDeliveryIds", "number", "wms_id", "origin"]
    for field in fields_to_remove:
        order_data.pop(field, None)
    
    put_url = f"{base_url}/{inpost_order_id}?{api_key_param}"
    print(f"📤 Updating order status to 'A' for order {inpost_order_id}...")
    
    try:
        put_response = requests.put(put_url, headers=inpost_headers, json=order_data)
        if put_response.status_code in [200, 204]:
            print(f"✅ Order {inpost_order_id} status updated to 'A' (cancelled) in InPost")
            return True
        else:
            print(f"❌ Failed to update order {inpost_order_id} status: {put_response.status_code} - {put_response.text}")
            # If we get validation errors, print them for debugging
            if put_response.status_code == 400:
                try:
                    error_details = put_response.json()
                    print(f"📝 Validation errors: {json.dumps(error_details, indent=2)}")
                except:
                    pass
            return False
    except Exception as e:
        print(f"❌ Error updating order {inpost_order_id} status: {str(e)}")
        return False

def check_and_sync_cancelled_orders():
    """Check for orders cancelled in CIN7 and cancel them in InPost"""
    print("🔍 Checking for cancelled orders that need to be synced to InPost...")
    
    # Get recently cancelled orders from CIN7 (last 7 days)
    cancelled_orders = get_recent_voided_orders(7)
    
    for order in cancelled_orders:
        order_number = order.get("OrderNumber", "")  # Fixed: was "SaleOrderNumber"
        sale_id = order.get("SaleID", "")
        
        if not order_number:
            continue
            
        print(f"📋 Checking cancelled order: {order_number}")
        
        # Check if order exists in InPost
        inpost_orders = get_inpost_order_by_external_id(order_number)
        if inpost_orders:
            inpost_order_id = inpost_orders[0].get("id")
            if inpost_order_id:
                # Cancel in InPost
                if cancel_order_in_inpost(inpost_order_id):
                    print(f"✅ Successfully synced cancellation for order {order_number}")
                else:
                    print(f"❌ Failed to cancel order {order_number} in InPost")
            else:
                print(f"⚠️  No InPost order ID found for {order_number}")
        else:
            print(f"✅ Order {order_number} not found in InPost (already cancelled or never sent)")

def get_recent_voided_orders(days_back=7):
    """Get recently voided orders from CIN7"""
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Get voided orders from the last X days
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/saleList?From={start_date}&Status=Voided&Limit=1000"
    
    try:
        response = requests.get(url, headers=core_headers)
        data = response.json()

        if not data.get("SaleList"):
            print("ℹ️  No recently voided orders found.")
            return []

        voided_orders = data["SaleList"]
        print(f"📥 Found {len(voided_orders)} recently voided orders in CIN7 (since {start_date})")
        return voided_orders
    except Exception as e:
        print(f"❌ Error fetching voided orders: {str(e)}")
        return []

def check_actual_fulfillment_status(data, sale_id):
    """Check actual fulfillment status from the fulfillment API and return fulfillment task ID and pack box info."""
    print(f"🔍 Checking fulfillment status for SaleID: {sale_id}")
    fulfillment_data = get_fulfillment_status(sale_id)
    
    pick_done = False
    pack_done = False
    ship_done = False
    fulfillment_task_id = None
    pack_box_name = "1"  # Default box name
    
    if fulfillment_data and "Fulfilments" in fulfillment_data and fulfillment_data["Fulfilments"]:
        # Get the first fulfillment (assuming there's only one)
        fulfillment = fulfillment_data["Fulfilments"][0]
        fulfillment_task_id = fulfillment.get("TaskID")
        fulfillment_number = fulfillment.get("FulfillmentNumber", "Unknown")
        
        print(f"📋 Processing fulfillment: {fulfillment_number} (TaskID: {fulfillment_task_id})")
        
        # Check Pick status
        if "Pick" in fulfillment and fulfillment["Pick"]:
            pick_status = fulfillment["Pick"].get("Status", "")
            pick_done = pick_status in ["AUTHORISED", "PICKED", "COMPLETED"]
            print(f"  📦 Pick Status: {pick_status} ({'✅ Done' if pick_done else '❌ Not Done'})")
        
        # Check Pack status and get box name
        if "Pack" in fulfillment and fulfillment["Pack"]:
            pack_status = fulfillment["Pack"].get("Status", "")
            pack_done = pack_status in ["AUTHORISED", "PACKED", "COMPLETED"]
            print(f"  📦 Pack Status: {pack_status} ({'✅ Done' if pack_done else '❌ Not Done'})")
            
            # Get the box name from the first pack line
            if "Lines" in fulfillment["Pack"] and fulfillment["Pack"]["Lines"]:
                first_pack_line = fulfillment["Pack"]["Lines"][0]
                pack_box_name = first_pack_line.get("Box", "1")
                print(f"  📦 Pack Box Name: {pack_box_name}")
        
        # Check Ship status
        if "Ship" in fulfillment and fulfillment["Ship"]:
            ship_status = fulfillment["Ship"].get("Status", "")
            ship_done = ship_status in ["AUTHORISED", "SHIPPED", "COMPLETED"]
            print(f"  📦 Ship Status: {ship_status} ({'✅ Done' if ship_done else '❌ Not Done'})")
    else:
        print("⚠️  No fulfillment data found or empty fulfillment list")
    
    print(f"📊 Final status - PICK: {'✅' if pick_done else '❌'}, PACK: {'✅' if pack_done else '❌'}, SHIP: {'✅' if ship_done else '❌'}")
    
    return pick_done, pack_done, ship_done, fulfillment_task_id, pack_box_name

def check_if_fulfillment_exists(task_id, fulfillment_type):
    """Check if fulfillment already exists for this task."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/{fulfillment_type}?TaskID={task_id}"
    try:
        response = requests.get(url, headers=core_headers)
        if response.status_code == 200:
            data = response.json()
            # If we get data back, fulfillment exists
            return len(data) > 0
        return False
    except:
        return False

def attempt_authorize_pick(task_id, lines):
    """Attempt to authorize picking for an order."""
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pick"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        print(f"📥 PICK response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ PICK AUTHORIZED | HTTP {response.status_code}")
            return True, True  # Success, no issues
        elif response.status_code == 400:
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ PICK already authorized")
                return True, True  # Success, already exists
            else:
                print(f"⚠️  PICK authorization issues: {response.text}")
                return True, False  # Success but with warnings
        else:
            response.raise_for_status()
            return True, True
    except Exception as e:
        print(f"❌ Error authorizing pick for task {task_id}: {str(e)}")
        return False, False  # Failed

def attempt_authorize_pack(task_id, lines):
    """Attempt to authorize packing for an order."""
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pack"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        print(f"📥 PACK response: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ PACK AUTHORIZED | HTTP {response.status_code}")
            return True, True  # Success, no issues
        elif response.status_code == 400:
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ PACK already authorized")
                return True, True  # Success, already exists
            else:
                print(f"⚠️  PACK authorization issues: {response.text}")
                return True, False  # Success but with warnings
        else:
            response.raise_for_status()
            return True, True
    except Exception as e:
        print(f"❌ Error authorizing pack for task {task_id}: {str(e)}")
        return False, False  # Failed

def authorize_ship(task_id, tracking_number, tracking_url, shipping_address, lines, box_name):
    """Authorize shipping for an order."""
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/ship"
    
    # Build the shipping lines properly using the correct box name
    shipping_lines = []
    if lines:
        # Take the first line as example and create shipping info
        shipping_lines.append({
            "ShipmentDate": datetime.now().strftime("%Y-%m-%d"),
            "Carrier": "InPost",  # Always use InPost for these orders
            "Box": box_name,  # Use the correct box name from PACK
            "TrackingNumber": tracking_number,
            "TrackingURL": tracking_url or "",
            "IsShipped": True
        })
    
    payload = {
        "TaskID": task_id,  # This should be the fulfillment task ID, not the sale task ID
        "Status": "AUTHORISED",
        "RequireBy": datetime.now().strftime("%Y-%m-%d"),
        "ShippingAddress": {
            "DisplayAddressLine1": shipping_address.get("DisplayAddressLine1", ""),
            "DisplayAddressLine2": shipping_address.get("DisplayAddressLine2", ""),
            "Line1": shipping_address.get("Line1", ""),
            "Line2": shipping_address.get("Line2", ""),
            "City": shipping_address.get("City", ""),
            "State": shipping_address.get("State", ""),
            "Postcode": shipping_address.get("Postcode", ""),
            "Country": shipping_address.get("Country", ""),
            "Company": shipping_address.get("Company", ""),
            "Contact": shipping_address.get("Contact", ""),
            "ShipToOther": shipping_address.get("ShipToOther", False)
        },
        "ShippingNotes": shipping_address.get("ShippingNotes", f"InPost tracking: {tracking_number}"),
        "Lines": shipping_lines
    }
    
    print(f"📤 SHIP payload: {json.dumps(payload, indent=2)}")  # Debug payload
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        print(f"📥 SHIP response: {response.status_code}")  # Debug response
        if response.status_code == 200:
            print(f"✅ SHIP AUTHORIZED | HTTP {response.status_code}")
            return True
        elif response.status_code == 400:
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ SHIP already authorized")
                return True
            else:
                print(f"❌ SHIP authorization failed: {response.text}")
                return False
        else:
            response.raise_for_status()
            return True
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error authorizing ship for task {task_id}: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print(f"❌ Error authorizing ship for task {task_id}: {str(e)}")
        return False

def update_tracking_in_core(sale_id, tracking_number, tracking_url):
    """Update tracking information in Cin7."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/{sale_id}/fulfilment/ship"
    payload = {
        "trackingNumber": tracking_number,
        "trackingURL": tracking_url or ""
    }
    
    try:
        response = requests.put(url, headers=core_headers, json=payload)
        response.raise_for_status()
        print(f"✅ TRACKING UPDATED | HTTP {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error updating tracking for order {sale_id}: {str(e)}")
        return False

def process_fulfillment(data, sale_id, tracking_number, tracking_url):
    """Process all fulfillment steps (PICK, PACK, SHIP) for an order."""
    order_data = data["Order"]
    sale_task_id = data["ID"]  # This is the sale task ID
    # sale_id is now passed in as parameter
    lines = order_data.get("Lines", [])
    shipping = data.get("ShippingAddress", {})
    
    # Check actual fulfillment status from fulfillment API and get fulfillment task ID and box name
    pick_done, pack_done, ship_done, fulfillment_task_id, pack_box_name = check_actual_fulfillment_status(data, sale_id)
    
    # Use fulfillment task ID for fulfillment operations, fallback to sale task ID if not found
    task_id_to_use = fulfillment_task_id if fulfillment_task_id else sale_task_id
    print(f"🔧 Using Task ID for fulfillment: {task_id_to_use}")
    print(f"📦 Using Box Name: {pack_box_name}")
    
    # Prepare fulfillment lines
    fulfillment_lines = []
    for line in lines:
        if line.get("SKU") and line.get("ProductID") != "00000000-0000-0000-0000-000000000000":
            fulfillment_lines.append({
                "ProductID": line["ProductID"],
                "SKU": line["SKU"],
                "Name": line["Name"],
                "Location": "InPost",
                "Quantity": line["Quantity"]
            })
    
    # Prepare pack lines with correct box information
    pack_lines = []
    for line in fulfillment_lines:
        pack_line = line.copy()
        pack_line["Box"] = pack_box_name  # Use the correct box name from PACK
        pack_lines.append(pack_line)
    
    success = True
    pick_success = True
    pack_success = True
    
    # Only attempt PICK if not already done
    if not pick_done:
        print("🔄 Attempting PICK authorization...")
        pick_ok, pick_clean = attempt_authorize_pick(task_id_to_use, fulfillment_lines)
        if not pick_ok:
            print("❌ PICK authorization failed completely")
            pick_success = False
            success = False
        elif not pick_clean:
            print("⚠️  PICK has inventory issues but continuing...")
        else:
            print("✅ PICK authorization successful")
    else:
        print("✅ PICK already authorized, skipping...")
        pick_success = True
    
    # Only attempt PACK if not already done and PICK is successful
    if not pack_done:
        if pick_success or pick_done:
            print("🔄 Attempting PACK authorization...")
            pack_ok, pack_clean = attempt_authorize_pack(task_id_to_use, pack_lines)
            if not pack_ok:
                print("❌ PACK authorization failed completely")
                pack_success = False
                success = False
            elif not pack_clean:
                print("⚠️  PACK has issues but continuing...")
            else:
                print("✅ PACK authorization successful")
        else:
            print("⏭️  Skipping PACK due to PICK failure")
            pack_success = False
            success = False
    else:
        print("✅ PACK already authorized, skipping...")
        pack_success = True
    
    # Update tracking (always try this)
    print("🔄 Updating tracking...")
    if not update_tracking_in_core(sale_id, tracking_number, tracking_url):
        print("❌ Tracking update failed")
        success = False
    else:
        print("✅ Tracking update successful")
    
    # Attempt SHIP authorization (only if both PICK and PACK are done)
    if (pick_done or pick_success) and (pack_done or pack_success):
        print("🔄 Attempting SHIP authorization...")
        if not authorize_ship(task_id_to_use, tracking_number, tracking_url, shipping, pack_lines, pack_box_name):
            print("❌ SHIP authorization failed")
            success = False
        else:
            print("✅ SHIP authorization successful")
    else:
        print("⏭️  Skipping SHIP due to PICK/PACK not being ready")
        success = False
    
    return success

def get_recent_sale_ids(days_back=1):
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/saleList?From={start_date}&Limit=1000"
    
    response = requests.get(url, headers=core_headers)
    data = response.json()

    if not data.get("SaleList"):
        print("❌ No sales found.")
        return []

    return [sale["SaleID"] for sale in data["SaleList"] if sale.get("Status") == "ORDERED"]


def validate_order_for_inpost(data):
    """Validate order data before sending to InPost"""
    order_data = data["Order"]
    shipping = data.get("ShippingAddress", {})
    
    errors = []
    
    # Check shipping country restrictions
    country = shipping.get("Country", "")
    restricted_countries = ["United Kingdom", "UK", "Norway", "Norweski", "Wielka Brytania"]
    if country in restricted_countries:
        errors.append(f"❌ Cannot ship to {country} - customs clearance not supported. FedEx shipments are within EU only.")
    
    # Check for required contact information
    phone = data.get("Phone", "") or shipping.get("Phone", "")
    email = data.get("Email", "") or shipping.get("Email", "")
    
    if not phone:
        errors.append("❌ No recipient contact telephone number provided")
    
    if not email:
        errors.append("❌ No recipient email address provided")
    
    # Check delivery point validity
    delivery_point = shipping.get("ID", "")
    if delivery_point == "KKZ01A" and country not in ["Poland", "Polska", ""]:
        errors.append(f"❌ Invalid delivery point KKZ01A for international shipment to {country}")
    
    # Check country vs delivery point consistency
    if country == "Sweden" and shipping.get("Postcode", "").startswith("52-"):  # Polish postcode format
        errors.append("❌ Country is Sweden but Polish postcode format detected")
    
    return errors

# === MAIN ===

# First, check and sync any cancelled orders
check_and_sync_cancelled_orders()

# Then process new orders
SALE_IDS = get_recent_sale_ids(1)

for sale_id in SALE_IDS:
    data = get_core_sale(sale_id)
    
    # Validate data before processing
    if not data or "Order" not in data:
        print(f"❌ Failed to retrieve valid data for sale {sale_id}")
        continue
        
    order_number = data["Order"]["SaleOrderNumber"]
    task_id = data["ID"]
    lines = data["Order"].get("Lines", [])
    shipping = data.get("ShippingAddress", {})
    carrier = data.get("Carrier", "")
    ship_by = data.get("ShipBy", "")

    print(f"\n🔄 Processing Core Sale: {order_number}")
    print(f"📋 Task ID: {task_id}")

    # ADD THIS VALIDATION STEP HERE:
    # Validate order before sending to InPost
    validation_errors = validate_order_for_inpost(data)
    if validation_errors:
        print(f"❌ Order {order_number} has validation errors:")
        for error in validation_errors:
            print(f"   {error}")
        print("⏭️  Skipping order due to validation errors")
        continue

    # Step 1: Send to InPost
    payload = build_payload_from_core(data)
    response = send_to_inpost(payload)
    
    # If it's a 409 error (duplicate), we can still continue processing
    if response.status_code not in [200, 201, 409]:
        print(f"❌ Failed to send to InPost, skipping order {order_number}")
        continue

    # Step 2: Check InPost status
    print(f"🔍 Checking InPost status for {order_number}...")
    inpost_order = get_inpost_order_by_external_id(order_number)
    if not inpost_order:
        print("❌ InPost order not found, skipping...")
        continue
        
    order_status = inpost_order[0].get("orderStatus")
    if order_status != "Y":
        print(f"❌ Not ready (InPost order status: {order_status}), skipping...")
        continue

    print("✅ InPost marked as sent. Proceeding to complete in Core...")

    tracking_info = inpost_order[0].get("externalDeliveryIds", [{}])[0].get("operators_data", [{}])[0]
    tracking_number = tracking_info.get("package_id", "")
    tracking_url = tracking_info.get("tracking_url", "")

    if not tracking_number:
        print("❌ No tracking number available, skipping fulfillment...")
        continue

    # Step 3: Process fulfillment (PICK, PACK, SHIP)
    print("🔄 Processing fulfillment authorization...")
    if process_fulfillment(data, sale_id, tracking_number, tracking_url):
        print(f"✅ Successfully completed all fulfillment steps for order {order_number}")
    else:
        print(f"⚠️  Some fulfillment steps may have failed for order {order_number}")

    print(f"✅ Completed processing for order: {order_number}")