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
    return response.json()

def get_country_code(country_name):
    return {
        "Poland": "PL", "Germany": "DE", "France": "FR", "United Kingdom": "GB", "Ireland": "IE",
        "Italy": "IT", "Spain": "ES", "Netherlands": "NL", "Belgium": "BE", "Luxembourg": "LU"
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

def check_fulfillment_status(data):
    """Check if PICK and PACK are already authorized or completed."""
    order_data = data["Order"]
    
    # Get detailed fulfillment status
    pick_status = order_data.get("CombinedPickingStatus", "")
    pack_status = order_data.get("CombinedPackingStatus", "")
    ship_status = order_data.get("CombinedShippingStatus", "")
    
    print(f"📊 Current status - PICK: {pick_status}, PACK: {pack_status}, SHIP: {ship_status}")
    
    # Check if already authorized or completed
    pick_done = pick_status in ["AUTHORISED", "PICKED", "COMPLETED"]
    pack_done = pack_status in ["AUTHORISED", "PACKED", "COMPLETED"]
    ship_done = ship_status in ["AUTHORISED", "SHIPPED", "COMPLETED"]
    
    return pick_done, pack_done, ship_done

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

def authorize_pick(task_id, lines):
    """Authorize picking for an order."""
    # First check if pick already exists
    if check_if_fulfillment_exists(task_id, "pick"):
        print("✅ PICK already exists, skipping authorization")
        return True
        
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pick"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        if response.status_code == 400:
            # Check if it's a "already exists" error
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ PICK already authorized (400 error indicates it exists)")
                return True
        response.raise_for_status()
        print(f"✅ PICK AUTHORIZED | HTTP {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error authorizing pick for task {task_id}: {str(e)}")
        # Try to check if it already exists despite the error
        if check_if_fulfillment_exists(task_id, "pick"):
            print("✅ PICK already exists despite error, continuing...")
            return True
        return False

def authorize_pack(task_id, lines):
    """Authorize packing for an order."""
    # First check if pack already exists
    if check_if_fulfillment_exists(task_id, "pack"):
        print("✅ PACK already exists, skipping authorization")
        return True
        
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/pack"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        if response.status_code == 400:
            # Check if it's a "already exists" error
            error_text = response.text.lower()
            if "already" in error_text or "exists" in error_text:
                print("✅ PACK already authorized (400 error indicates it exists)")
                return True
        response.raise_for_status()
        print(f"✅ PACK AUTHORIZED | HTTP {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error authorizing pack for task {task_id}: {str(e)}")
        # Try to check if it already exists despite the error
        if check_if_fulfillment_exists(task_id, "pack"):
            print("✅ PACK already exists despite error, continuing...")
            return True
        return False

def authorize_ship(task_id, tracking_number, tracking_url, shipping_address, lines):
    """Authorize shipping for an order."""
    url = "https://inventory.dearsystems.com/ExternalApi/v2/sale/fulfilment/ship"
    payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "RequireBy": None,
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
            "ShipToOther": shipping_address.get("ShipToOther", "")
        },
        "ShippingNotes": shipping_address.get("ShippingNotes", ""),
        "Lines": [{
            "ShipmentDate": datetime.now().strftime("%Y-%m-%d"),
            "Carrier": shipping_address.get("Carrier", "InPost"),
            "Box": "Box 1",
            "TrackingNumber": tracking_number,
            "TrackingURL": tracking_url,
            "IsShipped": True
        }]
    }
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        response.raise_for_status()
        print(f"✅ SHIP AUTHORIZED | HTTP {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error authorizing ship for task {task_id}: {str(e)}")
        return False

def update_tracking_in_core(sale_id, tracking_number, tracking_url):
    """Update tracking information in Cin7."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/{sale_id}/fulfilment/ship"
    payload = {
        "trackingNumber": tracking_number,
        "trackingURL": tracking_url
    }
    
    try:
        response = requests.put(url, headers=core_headers, json=payload)
        response.raise_for_status()
        print(f"✅ TRACKING UPDATED | HTTP {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error updating tracking for order {sale_id}: {str(e)}")
        return False

def process_fulfillment(data, tracking_number, tracking_url):
    """Process all fulfillment steps (PICK, PACK, SHIP) for an order."""
    order_data = data["Order"]
    task_id = data["ID"]
    sale_id = order_data["SaleID"]
    lines = order_data.get("Lines", [])
    shipping = data.get("ShippingAddress", {})
    
    # Check current fulfillment status
    pick_done, pack_done, ship_done = check_fulfillment_status(data)
    
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
    
    # Prepare pack lines with box information
    pack_lines = []
    for line in fulfillment_lines:
        pack_line = line.copy()
        pack_line["Box"] = "Box 1"
        pack_lines.append(pack_line)
    
    success = True
    
    # Authorize PICK if not already done
    if not pick_done:
        print("🔄 Authorizing PICK...")
        if not authorize_pick(task_id, fulfillment_lines):
            print("❌ PICK authorization failed")
            success = False
        else:
            print("✅ PICK authorization successful")
    else:
        print("✅ PICK already done, skipping...")
    
    # Authorize PACK if not already done
    if not pack_done:
        print("🔄 Authorizing PACK...")
        if not authorize_pack(task_id, pack_lines):
            print("❌ PACK authorization failed")
            success = False
        else:
            print("✅ PACK authorization successful")
    else:
        print("✅ PACK already done, skipping...")
    
    # Update tracking (always try this)
    print("🔄 Updating tracking...")
    if not update_tracking_in_core(sale_id, tracking_number, tracking_url):
        print("❌ Tracking update failed")
        success = False
    else:
        print("✅ Tracking update successful")
    
    # Authorize SHIP if not already done
    if not ship_done:
        print("🔄 Authorizing SHIP...")
        if not authorize_ship(task_id, tracking_number, tracking_url, shipping, pack_lines):
            print("❌ SHIP authorization failed")
            success = False
        else:
            print("✅ SHIP authorization successful")
    else:
        print("✅ SHIP already done, skipping...")
    
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

# === MAIN ===

SALE_IDS = get_recent_sale_ids(1)

for sale_id in SALE_IDS:
    data = get_core_sale(sale_id)
    order_number = data["Order"]["SaleOrderNumber"]
    task_id = data["ID"]
    lines = data["Order"].get("Lines", [])
    shipping = data.get("ShippingAddress", {})
    carrier = data.get("Carrier", "")
    ship_by = data.get("ShipBy", "")

    print(f"\n🔄 Processing Core Sale: {order_number}")
    print(f"📋 Task ID: {task_id}")

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
    if process_fulfillment(data, tracking_number, tracking_url):
        print(f"✅ Successfully completed all fulfillment steps for order {order_number}")
    else:
        print(f"⚠️  Some fulfillment steps may have failed for order {order_number}")

    print(f"✅ Completed processing for order: {order_number}")