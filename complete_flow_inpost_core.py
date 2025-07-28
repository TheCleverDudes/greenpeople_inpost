import requests
import json
from datetime import datetime, timedelta, timezone
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cin7_inpost_sync_simple.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Cin7 Core (DEAR) API credentials ===
CORE_ACCOUNT_ID = "3384f900-b8b1-41bc-8324-1e6000e897ec"
CORE_APP_KEY = "c1bf7dbf-5365-9d50-95a1-960ee4455445"

# === InPost API key ===
INPOST_API_KEY = "da3f39f46c9f473d29cc8ec40a0ae787"

# === Depot ID for InPost ===
DEPOT_ID = "556239"

# === Date range: last 24 hours ===
END_DATE = datetime.now(timezone.utc)
START_DATE = END_DATE - timedelta(hours=24)

# === Default values ===
DEFAULT_WEIGHT_KG = 0.5
DEFAULT_ITEM_WEIGHT_KG = 0.1
TRACKING_URL_TEMPLATE = "https://www.fedex.com/wtrk/track/?trknbr={}"
DEFAULT_LOCATION = "InPost"
DEFAULT_BOX = "Box 1"

# === Helper: Country code mapping ===
def get_country_code(country_name):
    country_codes = {
        "Poland": "PL", "Germany": "DE", "France": "FR", "United Kingdom": "GB",
        "Ireland": "IE", "Italy": "IT", "Spain": "ES", "Netherlands": "NL",
        "Belgium": "BE", "Luxembourg": "LU"
    }
    return country_codes.get(country_name, "PL")

# === Helper: Normalize phone ===
def normalize_phone(phone: str, country_code: str) -> str:
    if not phone:
        return "+48500600700" if country_code == "PL" else "+441403740350"
    digits = ''.join(c for c in phone if c.isdigit())
    if not digits.startswith('48') and country_code == "PL":
        digits = "48" + digits
    elif not digits.startswith('44') and country_code == "GB":
        digits = "44" + digits
    return "+" + digits

# === Step 1: Fetch list of orders from Cin7 (with pagination) ===
def fetch_cin7_orders(start_date, end_date):
    base_url = "https://inventory.dearsystems.com/ExternalApi/v2"
    headers = {
        "Content-Type": "application/json",
        "api-auth-accountid": CORE_ACCOUNT_ID,
        "api-auth-applicationkey": CORE_APP_KEY
    }
    all_orders = []
    page = 1
    limit = 50
    logger.info(f"🔍 Fetching orders updated between {start_date} and {end_date}...")
    while True:
        params = {
            "Page": page,
            "Limit": limit,
            "UpdatedSince": start_date.strftime("%Y-%m-%dT%H:%M:%S"),
            "UpdatedTo": end_date.strftime("%Y-%m-%dT%H:%M:%S")
        }
        url = f"{base_url}/saleList"
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            orders = data.get("SaleList", [])
            if not orders:
                break  # No more orders
            all_orders.extend(orders)
            logger.info(f"📄 Fetched {len(orders)} orders on page {page}")
            if len(orders) < limit:
                break  # Last page
            page += 1
        except Exception as e:
            logger.error(f"❌ Failed to fetch orders (page {page}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response text: {e.response.text}")
            break
    logger.info(f"✅ Total orders fetched: {len(all_orders)}")
    if all_orders:
        # Use .get() and a fallback to prevent KeyError
        sample_order_numbers = [o.get('SaleOrderNumber', 'MISSING_SO_NUMBER') for o in all_orders[:3]]
        logger.info(f"Sample order numbers: {sample_order_numbers}")
    return all_orders

# === Step 2: Get full order details from Cin7 ===
def get_order_details(sale_id):
    url = f"https://inventory.dearsystems.com/ExternalApi/v2/sale?ID={sale_id}&CombineAdditionalCharges=true"
    headers = {
        "Content-Type": "application/json",
        "api-auth-accountid": CORE_ACCOUNT_ID,
        "api-auth-applicationkey": CORE_APP_KEY
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Failed to get details for {sale_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response text: {e.response.text}")
        return None

# === Step 3: Build InPost payload (Improved customer data) ===
def build_inpost_payload(order_data, shipping, country_code):
    items = []
    total_weight = 0.0
    for line in order_data["Lines"]:
        sku = line.get("SKU") or line.get("Sku", "")
        if not sku or line.get("ProductID") == "00000000-0000-0000-0000-000000000000":
            continue
        weight = float(line.get("ProductWeight", DEFAULT_ITEM_WEIGHT_KG * 1000)) / 1000
        qty = float(line["Quantity"])
        total_weight += weight * qty
        items.append({
            "sku": sku,
            "externalId": line["ProductID"],
            "ordered": qty,
            "quantity": qty,
            "description": line["Name"],
            "weight": weight,
            "vat_code": 23,
            "price_gross": float(line["Price"]),
            "price_net": float(line["Total"])
        })
    total_weight = max(total_weight, DEFAULT_WEIGHT_KG)
    street = shipping.get("Line1", "Unknown Street")
    postcode = shipping.get("Postcode", "00-001") if country_code == "PL" else shipping.get("Postcode", "00000")
    city = shipping.get("City", "Unknown City")
    carrier = "Kurier InPost - ShipX" if country_code == "PL" else "FedEx"
    currency = order_data.get("SaleOrderCurrency") or ("PLN" if country_code == "PL" else "EUR")

    # --- Improved Customer Data Extraction ---
    # Try primary fields first
    customer_name = order_data.get("Customer")
    customer_email = order_data.get("Email")
    customer_phone = order_data.get("Phone") # Use main phone if available

    # Fallback to Billing Address if primary fields are missing
    if not customer_name or not customer_email:
        billing_address = order_data.get("BillingAddress", {})
        if not customer_name:
            # Combine first and last name if available
            first_name = billing_address.get("FirstName", "")
            last_name = billing_address.get("LastName", "")
            customer_name = f"{first_name} {last_name}".strip() or "Unknown Customer"

        if not customer_email:
            customer_email = billing_address.get("Email", "no-email@example.com")

        # Use billing phone if main phone is missing
        if not customer_phone:
             customer_phone = billing_address.get("Phone", "")

    # --- End of Improvement ---

    return {
        "clientOrderNumber": order_data["SaleOrderNumber"],
        "externalId": order_data["SaleOrderNumber"],
        "paymentMethod": currency,
        "currencySymbol": currency,
        "orderDate": order_data.get("SaleOrderDate", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        "carrier": carrier,
        "deliveryRecipient": customer_name, # Use improved name
        "deliveryPhone": normalize_phone(customer_phone, country_code), # Use improved phone
        "deliveryEmail": customer_email, # Use improved email
        "deliveryStreet": street,
        "deliveryPostCode": postcode,
        "deliveryCity": city,
        "deliveryCountry": country_code,
        "depotId": DEPOT_ID,
        "shipmentPrice": 0.00,
        "priceGross": sum(item["price_gross"] for item in items),
        "weight": total_weight,
        "items": items,
        "comments": f"Synced from Cin7 order {order_data['SaleOrderNumber']}",
        "service": "courier"
    }

# === Step 4: Create order in InPost (Handle 409 Conflict) ===
def create_inpost_order(payload):
    url = f"https://api-inpost.linker.shop/public-api/v1/orders?apikey={INPOST_API_KEY}"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=payload)
        # Handle 409 Conflict specifically
        if response.status_code == 409:
            try:
                error_data = response.json()
                message = error_data.get("message", "")
                logger.info(f"Order already exists in InPost. Message: {message}")
                # Return a specific marker for conflict handling
                return {"status": "conflict", "message": message, "exists": True}
            except json.JSONDecodeError:
                logger.warning("409 Conflict received, but response body is not valid JSON.")
                return False
        response.raise_for_status() # Raise for other 4xx/5xx
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ InPost creation failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response text: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"💥 Unexpected error during InPost creation: {e}")
        return False

# === Step 5: Get InPost Order Details (for status check) ===
def get_inpost_order_details(inpost_order_id):
    """Fetches details of an existing InPost order to check its status."""
    url = f"https://api-inpost.linker.shop/public-api/v1/orders/{inpost_order_id}?apikey={INPOST_API_KEY}"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Failed to get InPost order details for {inpost_order_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response text: {e.response.text}")
        return None

# === Step 6: Authorize PICK, PACK, SHIP in Cin7 ===
def authorize_fulfillment(cin7_order_id, task_id, lines, tracking_number, tracking_url, shipping_address):
    headers = {
        "Content-Type": "application/json",
        "api-auth-accountid": CORE_ACCOUNT_ID,
        "api-auth-applicationkey": CORE_APP_KEY
    }
    base_url = "https://inventory.dearsystems.com/ExternalApi/v2"

    # ✅ Authorize Pick
    pick_payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": lines
    }
    try:
        pick_response = requests.post(f"{base_url}/sale/fulfilment/pick", headers=headers, json=pick_payload)
        pick_response.raise_for_status()
        logger.info(f"✅ Pick authorized for {cin7_order_id}")
    except Exception as e:
        logger.error(f"❌ Failed to authorize pick for {cin7_order_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response text: {e.response.text}")
        return False

    # ✅ Authorize Pack
    pack_lines = [{**line, "Box": DEFAULT_BOX} for line in lines]
    pack_payload = {
        "TaskID": task_id,
        "Status": "AUTHORISED",
        "Lines": pack_lines
    }
    try:
        pack_response = requests.post(f"{base_url}/sale/fulfilment/pack", headers=headers, json=pack_payload)
        pack_response.raise_for_status()
        logger.info(f"✅ Pack authorized for {cin7_order_id}")
    except Exception as e:
        logger.error(f"❌ Failed to authorize pack for {cin7_order_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response text: {e.response.text}")
        return False

    # ✅ Authorize Ship
    ship_payload = {
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
            "ShipmentDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "Carrier": "InPost", # Assuming InPost for courier
            "Box": DEFAULT_BOX,
            "TrackingNumber": tracking_number,
            "TrackingURL": tracking_url,
            "IsShipped": True
        }]
    }
    try:
        ship_response = requests.post(f"{base_url}/sale/fulfilment/ship", headers=headers, json=ship_payload)
        ship_response.raise_for_status()
        logger.info(f"✅ Ship authorized for {cin7_order_id}")
    except Exception as e:
        logger.error(f"❌ Failed to authorize ship for {cin7_order_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response text: {e.response.text}")
        return False

    # ✅ Update tracking in Cin7 (PUT request)
    update_tracking_url = f"{base_url}/sale/{cin7_order_id}/fulfilment/ship"
    track_payload = {
        "trackingNumber": tracking_number,
        "trackingURL": tracking_url or TRACKING_URL_TEMPLATE.format(tracking_number)
    }
    try:
        # Use PUT for updating tracking
        track_response = requests.put(update_tracking_url, headers=headers, json=track_payload)
        track_response.raise_for_status()
        logger.info(f"✅ Tracking updated for {cin7_order_id}")
    except Exception as e:
        logger.warning(f"⚠️ Warning: Failed to update tracking number for {cin7_order_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
             logger.warning(f"Response text: {e.response.text}")
        # Decide if this should fail the whole process or just log a warning
        # For now, let's warn but continue

    return True

# === Main Execution ===
if __name__ == "__main__":
    # Step 1: Fetch all orders
    orders = fetch_cin7_orders(START_DATE, END_DATE)
    if not orders:
        logger.info("📭 No orders to process.")
        exit()

    success_count = 0
    for order in orders:
        try:
            # Use .get() for safety
            sale_id = order.get("SaleID")
            order_number = order.get("SaleOrderNumber", f"MISSING_SO_{sale_id[:8] if sale_id else 'ID'}")

            if not sale_id:
                 logger.warning(f"Skipping order, missing SaleID: {order}")
                 continue

            logger.info(f"🚀 Processing order: {order_number} (SaleID: {sale_id})")

            # Step 2: Get full order details
            order_details = get_order_details(sale_id)
            if not order_details or "Order" not in order_details:
                logger.error(f"❌ Invalid or missing data for {order_number}")
                continue

            order_data = order_details["Order"]
            shipping = order_details.get("ShippingAddress", {})

            # Step 3: Determine country
            country_name = shipping.get("Country", "Poland")
            country_code = get_country_code(country_name)

            # Step 4: Build InPost payload
            payload = build_inpost_payload(order_data, shipping, country_code)

            # Step 5: Create in InPost
            inpost_response = create_inpost_order(payload)

            # Handle specific 409 conflict response
            if isinstance(inpost_response, dict) and inpost_response.get("status") == "conflict":
                logger.info(f"InPost order for Cin7 {order_number} already exists. Details: {inpost_response.get('message')}")
                # Optional Enhancement: Parse the message or query InPost GET /orders to get the ID.
                # For now, treat as successful to prevent retry loop.
                success_count += 1
                logger.info(f"✅ Marked as processed (already exists): {order_number}")
                continue # Move to next order

            if not inpost_response:
                logger.error(f"❌ Network error or unexpected issue creating order {order_number} in InPost")
                continue

            # Check if order was created successfully (original logic for 200 OK)
            if inpost_response.get("status", "").lower() != "ok":
                logger.error(f"❌ Failed to create order {order_number} in InPost: {inpost_response.get('message', 'Unknown error')}")
                continue

            inpost_order_id = inpost_response["id"]
            tracking_number = inpost_response.get("trackingNumber", f"TEMP-{order_number}")
            tracking_url = inpost_response.get("trackingURL")
            logger.info(f"✅ Created InPost order: {inpost_order_id} | Tracking: {tracking_number}")

            # --- NEW: Wait for InPost Order to be "Closed" (Y, P, D) ---
            logger.info(f"⏳ Waiting for InPost order {inpost_order_id} to reach 'closed' status (Y/P/D)...")
            max_checks = 12 # Check up to 12 times (e.g., 2 mins if interval is 10s)
            check_interval = 10 # seconds
            inpost_order_closed = False
            checks = 0
            while checks < max_checks and not inpost_order_closed:
                 time.sleep(check_interval)
                 checks += 1
                 inpost_order_details = get_inpost_order_details(inpost_order_id)
                 if inpost_order_details:
                      status = inpost_order_details.get("orderStatus")
                      logger.debug(f"InPost order {inpost_order_id} status check {checks}/{max_checks}: '{status}'")
                      # Consider Y (Sent), P (On the way), D (Delivered) as "Closed"
                      if status in ["Y", "P", "D"]:
                           tracking_number = inpost_order_details.get("trackingNumber", tracking_number) # Refresh if needed
                           tracking_url = inpost_order_details.get("trackingURL", tracking_url)
                           inpost_order_closed = True
                           logger.info(f"✅ InPost order {inpost_order_id} is closed (status: {status}). Proceeding with fulfillment.")
                      elif status in ["A", "DC", "X"]: # Canceled statuses
                           logger.warning(f"⚠️ InPost order {inpost_order_id} was canceled (status: {status}). Skipping fulfillment.")
                           break # Stop checking, don't fulfill
                 else:
                      logger.warning(f"⚠️ Could not fetch InPost order details for {inpost_order_id} during status check {checks}. Retrying...")
            if not inpost_order_closed:
                 logger.warning(f"⚠️ InPost order {inpost_order_id} did not reach 'closed' status within the timeout period. Skipping fulfillment for now.")
                 continue # Don't proceed with fulfillment if not closed
            # --- END OF NEW WAIT LOGIC ---

            # Step 6: Prepare fulfillment lines
            lines = []
            for line in order_data["Lines"]:
                if line.get("SKU") and line.get("ProductID") != "00000000-0000-0000-0000-000000000000":
                    lines.append({
                        "ProductID": line["ProductID"],
                        "SKU": line["SKU"],
                        "Name": line["Name"],
                        "Location": DEFAULT_LOCATION,
                        "Quantity": line["Quantity"]
                    })
            if not lines:
                logger.warning(f"⚠️ No valid items to fulfill for {order_number}")
                continue

            # Step 7: Authorize Pick → Pack → Ship
            # Use the ID from the detailed order response as TaskID
            task_id = order_details.get("ID")
            if not task_id:
                 logger.error(f"❌ Missing TaskID for Cin7 order {order_number}. Cannot authorize fulfillment.")
                 continue

            if authorize_fulfillment(sale_id, task_id, lines, tracking_number, tracking_url, shipping):
                success_count += 1
                logger.info(f"✅ FULLY PROCESSED: {order_number}")
            else:
                logger.error(f"❌ Failed full fulfillment for {order_number}")

        except Exception as e:
            logger.error(f"💥 Error processing order {order.get('SaleOrderNumber', 'UNKNOWN')}: {e}", exc_info=True)

    logger.info(f"🎉 Sync complete. Successfully processed {success_count}/{len(orders)} orders.")
