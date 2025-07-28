<?php

// -------- MOCK FUNCTION: Get InPost Orders --------
function Get_Ship_Order_From_inpost($date) {
    return [
        'items' => [
            [
                'externalId' => 'SO-00123',
                'externalDeliveryIds' => [
                    [
                        'operators_data' => [
                            [
                                'package_id' => 'TRACK123456',
                                'tracking_url' => 'https://tracking.inpost.com/track123456'
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ];
}

// -------- MOCK FUNCTION: Search SO ID from SO Number --------
function search_SO_id_using_SO_nu($so_number) {
    return [
        'SaleList' => [
            [
                'SaleID' => 12345
            ]
        ]
    ];
}

// -------- MOCK FUNCTION: Get Order Data by Sale Order ID --------
function get_data_using_sale_order_id($sale_order_id) {
    return [
        'ID' => 12345,
        'SaleOrderDate' => '2025-06-02',
        'LastModifiedOn' => '2025-06-02',
        'ShippingAddress' => [
            'DisplayAddressLine1' => '123 Mock St',
            'DisplayAddressLine2' => '',
            'Line1' => '123 Mock St',
            'Line2' => '',
            'City' => 'Cape Town',
            'State' => '',
            'Postcode' => '8000',
            'Country' => 'ZA',
            'Company' => 'Mock Co',
            'Contact' => 'Test User',
            'ShipToOther' => false
        ],
        'ShippingNotes' => 'Test shipment',
        'ShipBy' => '2025-06-03',
        'Carrier' => 'InPost',
        'Order' => [
            'Lines' => [
                [
                    'ProductID' => 1,
                    'SKU' => 'PROD-001',
                    'Name' => 'Mock Product',
                    'Quantity' => 2
                ]
            ]
        ]
    ];
}

// -------- MOCK FUNCTION: Simulate API Call Results --------
function SO_pick_authorized($payload) {
    echo "✅ PICK Payload Sent:\n$payload\n\n";
    return true;
}

function SO_pack_authorized($payload) {
    echo "✅ PACK Payload Sent:\n$payload\n\n";
    return true;
}

function SO_ship_authorized($payload) {
    echo "✅ SHIP Payload Sent:\n$payload\n\n";
    return true;
}

// --------------- MAIN SCRIPT ---------------
$current_date = date('d.m.Y');
$Get_Ship_Order_From_inpost = Get_Ship_Order_From_inpost($current_date);

if (empty($Get_Ship_Order_From_inpost) || !isset($Get_Ship_Order_From_inpost['items'])) {
    die("❌ No orders found from InPost\n");
}

foreach ($Get_Ship_Order_From_inpost['items'] as $order) {
    $sale_order_number = $order['externalId'];

    if (!isset($order['externalDeliveryIds'][0]['operators_data'][0]['package_id'])) {
        echo "❌ Missing tracking number for $sale_order_number\n";
        continue;
    }

    $TrackingNumber = $order['externalDeliveryIds'][0]['operators_data'][0]['package_id'];
    $TrackingURL = $order['externalDeliveryIds'][0]['operators_data'][0]['tracking_url'];

    $search_SO_id_using_SO_no = search_SO_id_using_SO_nu($sale_order_number);
    if (empty($search_SO_id_using_SO_no['SaleList'])) {
        echo "❌ Sale order not found in core: $sale_order_number\n";
        continue;
    }

    $sale_order_id = $search_SO_id_using_SO_no['SaleList'][0]['SaleID'];
    $get_data_using_sale_order_id = get_data_using_sale_order_id($sale_order_id);

    if (!isset($get_data_using_sale_order_id['ID'])) {
        echo "❌ Failed to get order details for sale ID: $sale_order_id\n";
        continue;
    }

    $TaskID = $get_data_using_sale_order_id['ID'];
    $pick_line_item_array = [];
    $pack_line_item_array = [];

    foreach ($get_data_using_sale_order_id['Order']['Lines'] as $line) {
        if ($line['SKU'] !== '') {
            $pick_line_item_array[] = [
                "ProductID" => $line['ProductID'],
                "SKU" => $line['SKU'],
                "Name" => $line['Name'],
                "Location" => "InPost",
                "Quantity" => $line['Quantity'],
            ];
            $pack_line_item_array[] = [
                "ProductID" => $line['ProductID'],
                "SKU" => $line['SKU'],
                "Name" => $line['Name'],
                "Location" => "InPost",
                "Box" => "Box 1",
                "Quantity" => $line['Quantity'],
            ];
        }
    }

    $pick_payload = json_encode([
        "TaskID" => $TaskID,
        "Status" => "AUTHORISED",
        "Lines" => $pick_line_item_array
    ], JSON_PRETTY_PRINT);

    $pack_payload = json_encode([
        "TaskID" => $TaskID,
        "Status" => "AUTHORISED",
        "Lines" => $pack_line_item_array
    ], JSON_PRETTY_PRINT);

    $shipp_payload = json_encode([
        "TaskID" => $TaskID,
        "Status" => "AUTHORISED",
        "RequireBy" => null,
        "ShippingAddress" => $get_data_using_sale_order_id['ShippingAddress'],
        "ShippingNotes" => $get_data_using_sale_order_id['ShippingNotes'],
        "Lines" => [
            [
                "ShipmentDate" => $get_data_using_sale_order_id['ShipBy'],
                "Carrier" => $get_data_using_sale_order_id['Carrier'],
                "Box" => "Box 1",
                "TrackingNumber" => $TrackingNumber,
                "TrackingURL" => $TrackingURL,
                "IsShipped" => true
            ]
        ]
    ], JSON_PRETTY_PRINT);

    SO_pick_authorized($pick_payload);
    SO_pack_authorized($pack_payload);
    SO_ship_authorized($shipp_payload);
}

?>
