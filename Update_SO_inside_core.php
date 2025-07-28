<?php
include('function.php');

$currentDate = date('d.m.Y');
$inpostOrders = Get_Ship_Order_From_inpost($currentDate);

// 1. Check for InPost orders
if (empty($inpostOrders['items'])) {
    error_log("No orders from InPost for $currentDate");
    die("No orders from InPost for $currentDate\n");
}

// 2. Process each InPost order
foreach ($inpostOrders['items'] as $order) {
    $saleOrderNumber = $order['externalId'] ?? null;
    $trackingInfo = $order['externalDeliveryIds'][0]['operators_data'][0] ?? null;

    if (!$saleOrderNumber || !$trackingInfo || empty($trackingInfo['package_id'])) {
        error_log("Missing tracking number or external ID");
        continue;
    }

    $trackingNumber = $trackingInfo['package_id'];
    $trackingURL = $trackingInfo['tracking_url'] ?? '';

    // 3. Get Sale Order ID
    $saleOrderLookup = search_SO_id_using_SO_nu($saleOrderNumber);
    $saleOrderID = $saleOrderLookup['SaleList'][0]['SaleID'] ?? null;

    if (!$saleOrderID) {
        error_log("Sale order not found in core: $saleOrderNumber");
        continue;
    }

    // Place the update call here!
    update_tracking_in_core($saleOrderID, $trackingNumber, $trackingURL);

    // 4. Get order data from core
    $orderData = get_data_using_sale_order_id($saleOrderID);
    $taskID = $orderData['ID'] ?? null;

    if (!$taskID || empty($orderData['Order']['Lines'])) {
        error_log("Missing task ID or no lines in core for order ID: $saleOrderID");
        continue;
    }

    $lines = $orderData['Order']['Lines'];
    $shippingAddress = $orderData['ShippingAddress'] ?? [];

    // 5. Build pick and pack arrays
    $pickLines = [];
    $packLines = [];

    foreach ($lines as $line) {
        if (empty($line['SKU'])) continue;

        $common = [
            "ProductID" => $line['ProductID'],
            "SKU" => $line['SKU'],
            "Name" => $line['Name'],
            "Location" => "InPost",
            "Quantity" => $line['Quantity']
        ];

        $pickLines[] = $common;
        $packLines[] = array_merge($common, ["Box" => "Box 1"]);
    }

    // 6. Prepare payloads
    $pickPayload = json_encode([
        "TaskID" => $taskID,
        "Status" => "AUTHORISED",
        "Lines" => $pickLines
    ], JSON_PRETTY_PRINT);

    $packPayload = json_encode([
        "TaskID" => $taskID,
        "Status" => "AUTHORISED",
        "Lines" => $packLines
    ], JSON_PRETTY_PRINT);

    $shipPayload = json_encode([
        "TaskID" => $taskID,
        "Status" => "AUTHORISED",
        "RequireBy" => null,
        "ShippingAddress" => [
            "DisplayAddressLine1" => $shippingAddress['DisplayAddressLine1'] ?? '',
            "DisplayAddressLine2" => $shippingAddress['DisplayAddressLine2'] ?? '',
            "Line1" => $shippingAddress['Line1'] ?? '',
            "Line2" => $shippingAddress['Line2'] ?? '',
            "City" => $shippingAddress['City'] ?? '',
            "State" => $shippingAddress['State'] ?? '',
            "Postcode" => $shippingAddress['Postcode'] ?? '',
            "Country" => $shippingAddress['Country'] ?? '',
            "Company" => $shippingAddress['Company'] ?? '',
            "Contact" => $shippingAddress['Contact'] ?? '',
            "ShipToOther" => $shippingAddress['ShipToOther'] ?? ''
        ],
        "ShippingNotes" => $orderData['ShippingNotes'] ?? '',
        "Lines" => [[
            "ShipmentDate" => $orderData['ShipBy'] ?? '',
            "Carrier" => $orderData['Carrier'] ?? '',
            "Box" => "Box 1",
            "TrackingNumber" => $trackingNumber,
            "TrackingURL" => $trackingURL,
            "IsShipped" => true
        ]]
    ], JSON_PRETTY_PRINT);

    // 7. Submit payloads
    SO_pick_authorized($pickPayload);
    SO_pack_authorized($packPayload);
    SO_ship_authorized($shipPayload);
}
