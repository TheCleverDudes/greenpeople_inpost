<?php
include('function.php');
    
         $json = file_get_contents('php://input'); 
         // If input is empty (like from CLI) AND our test file exists, use the test file.
         if (empty($json) && file_exists('core_PO.json')) {
            $json = file_get_contents('core_PO.json');
         } else {
            // Otherwise, use the input from the webhook and save it.
            file_put_contents('core_PO.json', $json);
         }
      
        $get_file = json_decode($json,1); 
        
     $PO_id = $get_file['TaskID'];
     $PurchaseOrderNumber = $get_file['PurchaseOrderNumber'];
     
     $get_PO_using_id = get_PO_using_id($PO_id);
    
    // Exit if we didn't get valid PO data from the API
    if (empty($get_PO_using_id) || !isset($get_PO_using_id['ID'])) {
        die("Error: Could not retrieve valid PO data from Cin7 for ID: " . $PO_id);
    }

    // Use the data from the detailed API response
    $PurchaseOrderNumber = $get_PO_using_id['OrderNumber'];
    $OrderDate = $get_PO_using_id['OrderDate'];
    $supplier_id = $get_PO_using_id['SupplierID'];
    
    $get_suppllier_data = get_suppllier_data($supplier_id);
    $supplier_name = !empty($get_suppllier_data['SupplierList'][0]['Name']) ? $get_suppllier_data['SupplierList'][0]['Name'] : 'Default Supplier';
    $supplier_email = null;
    $supplier_fullName = null;
    $supplier_postCode = null;
    $supplier_city = null;
    $countryName = null;

    // Safely get supplier details
    if (isset($get_suppllier_data['SupplierList'][0])) {
        $supplier_info = $get_suppllier_data['SupplierList'][0];
        if (isset($supplier_info['Contacts'][0])) {
            $supplier_email = $supplier_info['Contacts'][0]['Email'];
            $supplier_fullName = $supplier_info['Contacts'][0]['Name'];
        }

        if (isset($supplier_info['Addresses'][0])) {
            $supplier_postCode = $supplier_info['Addresses'][0]['Postcode'];
            $supplier_city = $supplier_info['Addresses'][0]['City'];
            $countryName = $supplier_info['Addresses'][0]['Country'];
        }
    }
   
   //fetch coutry code using coutry name
    $countryCode = getCountryCode($countryName, $countryNameToCode);
	
	$item_array = [];
	// Safely get line items from the nested 'Order' object
	if (isset($get_PO_using_id['Order']['Lines']) && is_array($get_PO_using_id['Order']['Lines'])) {
	    foreach($get_PO_using_id['Order']['Lines'] as $line_itemssss){
			 $core_sku = $line_itemssss['SKU'];
	         $ordered = $line_itemssss['Quantity'];
	         $description = $line_itemssss['Name'];
			 $product_id = $line_itemssss['ProductID'];
			 
			 $Get_Product_details_using_P_ID = Get_Product_details_using_P_ID($product_id);
			 $Barcode = null; // Default to null
			 if (isset($Get_Product_details_using_P_ID['BarCode'])) {
				$Barcode = $Get_Product_details_using_P_ID['BarCode'];
			 }
			 
			 $item_array[] = array(
                              //"externalId" => $externalId,
                                "ordered" => $ordered,
                                "description" => $description,
                                "sku" => $core_sku,
                                "ean" => $Barcode
                         );
		}
	}
   
     
     $payload_array = array(
                "orderDate" => $OrderDate,
                "supplierObject" => array(
                    "code" => "0 ",
                    "name" => $supplier_name,
                    "email" => $supplier_email,
                    "fullName" => $supplier_fullName,
                    "postCode" => $supplier_postCode,
                    "city" => $supplier_city,
                    "street" => $supplier_city,
                    "country" => $countryCode
                ),
                "clientOrderNumber" => $PurchaseOrderNumber,
                "depot_id" => 556239,
                "items" => $item_array
                       );
                         
        $encode_payload = json_encode($payload_array);
        //create PO inside the InPost as delivery notification supplier order
        if (!check_inpost_po_exists($PurchaseOrderNumber)) {
            $create_PO_inside_InPost = create_PO_inside_InPost($encode_payload);
            
            // --- DEBUG: Print the API response ---
            echo "\n--- InPost API Response ---\n";
            print_r($create_PO_inside_InPost);
            echo "\n---------------------------\n\n";

            echo "✅ PO Created in InPost: $PurchaseOrderNumber\n";
        } else {
            echo "⚠️ PO Already Exists in InPost: $PurchaseOrderNumber — Skipping creation.\n";
        }
        