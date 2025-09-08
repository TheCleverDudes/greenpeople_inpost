import requests
import json
from datetime import datetime, timedelta
import time

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

# === New Functions for Order Completion Sync ===

def get_shipped_orders_from_inpost(hours_back=24):
    """Get orders that are shipped/completed in InPost but may not be updated in Core."""
    since_time = (datetime.now() - timedelta(hours=hours_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}&updatedSince={since_time}&status=COMPLETED,SHIPPED"
    
    try:
        response = requests.get(url, headers=inpost_headers)
        response.raise_for_status()
        data = response.json()
        return data.get("items", [])
    except Exception as e:
        print(f"❌ Error fetching shipped orders from InPost: {str(e)}")
        return []

def check_core_order_status(sale_id):
    """Check the current status of an order in Core."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale?ID={sale_id}"
    try:
        response = requests.get(url, headers=core_headers)
        response.raise_for_status()
        data = response.json()
        return data["Order"].get("Status"), data["Order"].get("CombinedShippingStatus")
    except Exception as e:
        print(f"❌ Error checking Core order status: {str(e)}")
        return None, None

def complete_order_in_core(sale_id, tracking_number, tracking_url):
    """Mark an order as completed/shipped in Core."""
    # First update tracking
    update_tracking_in_core(sale_id, tracking_number, tracking_url)
    
    # Then mark as shipped
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale/{sale_id}/fulfilment/ship"
    payload = {
        "Status": "SHIPPED",
        "Lines": [{
            "IsShipped": True,
            "TrackingNumber": tracking_number,
            "TrackingURL": tracking_url
        }]
    }
    
    try:
        response = requests.post(url, headers=core_headers, json=payload)
        response.raise_for_status()
        print(f"✅ Order {sale_id} marked as SHIPPED in Core")
        return True
    except Exception as e:
        print(f"❌ Error marking order as shipped in Core: {str(e)}")
        return False

def sync_completed_orders():
    """Sync orders that are completed in InPost but not in Core."""
    print("\n" + "="*60)
    print("🔄 SYNCING COMPLETED ORDERS FROM INPOST TO CORE")
    print("="*60)
    
    # Get recently completed orders from InPost
    completed_orders = get_shipped_orders_from_inpost(48)  # Last 48 hours
    
    if not completed_orders:
        print("✅ No completed orders found in InPost that need syncing")
        return
    
    print(f"📦 Found {len(completed_orders)} completed orders in InPost")
    
    synced_count = 0
    for order in completed_orders:
        external_id = order.get("externalId")
        inpost_status = order.get("status")
        tracking_info = order.get("externalDeliveryIds", [{}])[0].get("operators_data", [{}])[0]
        tracking_number = tracking_info.get("package_id", "")
        tracking_url = tracking_info.get("tracking_url", "")
        
        if not external_id:
            continue
        
        print(f"\n🔍 Checking order {external_id} (InPost status: {inpost_status})")
        
        # Find the Core sale ID for this order
        sale_id = find_core_sale_id_by_order_number(external_id)
        if not sale_id:
            print(f"❌ Could not find Core order for {external_id}")
            continue
        
        # Check current status in Core
        core_status, shipping_status = check_core_order_status(sale_id)
        print(f"📊 Core status: {core_status}, Shipping status: {shipping_status}")
        
        # If order is not already shipped in Core, update it
        if core_status != "SHIPPED" and shipping_status != "SHIPPED":
            print(f"🔄 Order {external_id} needs to be marked as shipped in Core")
            if complete_order_in_core(sale_id, tracking_number, tracking_url):
                synced_count += 1
                print(f"✅ Successfully synced order {external_id} to Core")
            else:
                print(f"❌ Failed to sync order {external_id} to Core")
        else:
            print(f"✅ Order {external_id} already shipped in Core")
    
    print(f"\n📈 Sync completed: {synced_count} orders updated in Core")

def find_core_sale_id_by_order_number(order_number):
    """Find Core sale ID by order number."""
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/saleList?SaleOrderNumber={order_number}"
    try:
        response = requests.get(url, headers=core_headers)
        response.raise_for_status()
        data = response.json()
        if data.get("SaleList"):
            return data["SaleList"][0]["SaleID"]
        return None
    except Exception as e:
        print(f"❌ Error finding Core order for {order_number}: {str(e)}")
        return None

# === Existing Functions (with minor enhancements) ===

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
    
    if response.status_code == 409:
        print("ℹ️  Order already exists in InPost (duplicate), continuing...")
    return response

def get_inpost_order_by_external_id(order_id):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}&filters[external_id]={order_id}"
    response = requests.get(url)
    return response.json().get("items", [])

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

def main():
    # First, sync any completed orders from InPost to Core
    sync_completed_orders()
    
    # Then process new orders as before
    print("\n" + "="*60)
    print("🔄 PROCESSING NEW ORDERS")
    print("="*60)
    
    SALE_IDS = get_recent_sale_ids(1)

    for sale_id in SALE_IDS:
        data = get_core_sale(sale_id)
        order_number = data["Order"]["SaleOrderNumber"]
        task_id = data["ID"]
        lines = data["Order"].get("Lines", [])
        shipping = data.get("ShippingAddress", {})

        print(f"\n🔄 Processing Core Sale: {order_number}")

        # Step 1: Send to InPost
        payload = build_payload_from_core(data)
        response = send_to_inpost(payload)
        
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

        print("✅ InPost marked as sent. Updating tracking in Core...")

        tracking_info = inpost_order[0].get("externalDeliveryIds", [{}])[0].get("operators_data", [{}])[0]
        tracking_number = tracking_info.get("package_id", "")
        tracking_url = tracking_info.get("tracking_url", "")

        if not tracking_number:
            print("❌ No tracking number available, skipping...")
            continue

        # Update tracking in Core
        if update_tracking_in_core(sale_id, tracking_number, tracking_url):
            print(f"✅ Successfully updated tracking for order {order_number}")
        else:
            print(f"❌ Failed to update tracking for order {order_number}")

        print(f"✅ Completed processing for order: {order_number}")

if __name__ == "__main__":
    main()