<?php
include('function.php');
echo "<pre>";
    $current_date = date('d.m.Y');
	 
    $PO_from_InPOST_delivery_status_closed = PO_from_InPOST_delivery_status_closed($current_date);
	
    foreach ($PO_from_InPOST_delivery_status_closed['items'] as $PO_item) {
        $client_order_number = $PO_item['client_order_number'];
        
            $PO_number = $client_order_number;
            $serach_PO_in_core = serach_PO_in_core($PO_number);
            $PO_id_from_core = $serach_PO_in_core['PurchaseList'][0]['ID'];
            $get_PO_using_id = get_PO_using_id($PO_id_from_core);
            
            $created_at = $get_PO_using_id['OrderDate'];
            $Location = $get_PO_using_id['Location'];
            
            $payload_array = [];
            foreach ($get_PO_using_id['Order']['Lines'] as $line_items) {
                $data = [
                    "Date" => $created_at,
                    "ProductID" => $line_items['ProductID'],
                    "SKU" => $line_items['SKU'],
                    "Name" => $line_items['Name'],
                    "Location" => $Location,
                    "Quantity" => $line_items['Quantity'],
                    "Price" => $line_items['Price'],
                    "Discount" => $line_items['Discount'],
                    "Tax" => $line_items['Tax'],
                    "TaxRule" => $line_items['TaxRule'],
                    "Account" => "", 
                    "Comment" => $line_items['Comment'],
                    "BatchSN" => "AP-1",
                    "Total" => $line_items['Total']
                ];
                $payload_array[] = $data;
            }
            
            $payload = json_encode($payload_array, JSON_PRETTY_PRINT);
            
            $PO_stock_received = PO_stock_received($PO_id_from_core,$payload);
  
    }
