<?php
include('function.php');

   echo  $current_date = date('d.m.Y');
	 
     $Get_Ship_Order_From_inpost = Get_Ship_Order_From_inpost($current_date);
	 print_r($Get_Ship_Order_From_inpost);die();
    foreach ($Get_Ship_Order_From_inpost['items'] as $Get_Ship_Order_From_inpostttttt){
	
		$sale_order_number = $Get_Ship_Order_From_inpostttttt['externalId'];
		  $TrackingNumber = $Get_Ship_Order_From_inpostttttt['externalDeliveryIds'][0]['operators_data'][0]['package_id'];
		  $TrackingURL = $Get_Ship_Order_From_inpostttttt['externalDeliveryIds'][0]['operators_data'][0]['tracking_url'];
		
				$search_SO_id_using_SO_no = search_SO_id_using_SO_nu($sale_order_number);
	
				 $sale_order_id = $search_SO_id_using_SO_no['SaleList'][0]['SaleID'];
					
				 $get_data_using_sale_order_id = get_data_using_sale_order_id($sale_order_id);

				 $TaskID = $get_data_using_sale_order_id['ID'];
				 $InvoiceDate=$get_data_using_sale_order_id['SaleOrderDate'];
				 $InvoiceDueDate=$get_data_using_sale_order_id['LastModifiedOn'];
		
			   $pick_line_item_array = [];
			   $pack_line_item_array = [];
       
			 foreach($get_data_using_sale_order_id['Order']['Lines'] as $get_saleorder_from_coreeeee){
					
				 if($get_saleorder_from_coreeeee['SKU'] != ''){
					 
								$pick_line_item_array[] = [   
									"ProductID" =>  $get_saleorder_from_coreeeee['ProductID'],
									"SKU" =>  $get_saleorder_from_coreeeee['SKU'],
									"Name" =>  $get_saleorder_from_coreeeee['Name'],
									"Location" =>  "InPost",
									"Quantity" =>  $get_saleorder_from_coreeeee['Quantity'],
								   ];
								   
									$pack_line_item_array[] = [   
									"ProductID" =>  $get_saleorder_from_coreeeee['ProductID'],
									"SKU" =>  $get_saleorder_from_coreeeee['SKU'],
									"Name" =>  $get_saleorder_from_coreeeee['Name'],
									"Location" =>  "InPost",
									"Box" => "Box 1",
									"Quantity" =>  $get_saleorder_from_coreeeee['Quantity'],
								   ];
								   
							}
			 }
     
		$pick_payload = json_encode(array(
						"TaskID" => $TaskID,
						"Status" => "AUTHORISED",
						"Lines" => $pick_line_item_array
					), JSON_PRETTY_PRINT); 
		  $pack_payload = json_encode(array(
						"TaskID" => $TaskID,
						"Status" => "AUTHORISED",
						"Lines" => $pack_line_item_array
					), JSON_PRETTY_PRINT);            
				
		 
		 $shipp_payload = json_encode(array(
					   "TaskID" => $TaskID,
						"Status" => "AUTHORISED",
						"RequireBy" => null,
						"ShippingAddress" => array(
                        "DisplayAddressLine1" => $get_data_using_sale_order_id['ShippingAddress']['DisplayAddressLine1'],
                        "DisplayAddressLine2" => $get_data_using_sale_order_id['ShippingAddress']['DisplayAddressLine2'],
                        "Line1" => $get_data_using_sale_order_id['ShippingAddress']['Line1'],
                        "Line2" => $get_data_using_sale_order_id['ShippingAddress']['Line2'],
                        "City" => $get_data_using_sale_order_id['ShippingAddress']['City'],
                        "State" => $get_data_using_sale_order_id['ShippingAddress']['State'],
                        "Postcode" => $get_data_using_sale_order_id['ShippingAddress']['Postcode'],
                        "Country" => $get_data_using_sale_order_id['ShippingAddress']['Country'],
                        "Company" => $get_data_using_sale_order_id['ShippingAddress']['Company'],
                        "Contact" => $get_data_using_sale_order_id['ShippingAddress']['Contact'],
                        "ShipToOther" => $get_data_using_sale_order_id['ShippingAddress']['ShipToOther'],
						),
						"ShippingNotes" => $get_data_using_sale_order_id['ShippingNotes'],
						"Lines" => [
							array(
								"ShipmentDate" => $get_data_using_sale_order_id['ShipBy'],
								"Carrier" => $get_data_using_sale_order_id['Carrier'],
								"Box" => "Box 1",
								"TrackingNumber" => $TrackingNumber,
								"TrackingURL" => $TrackingURL,
								"IsShipped" => true
							)
                    ]
         ), JSON_PRETTY_PRINT);
         
          $SO_pick_authorized = SO_pick_authorized($pick_payload);
     print_r($SO_pick_authorized);
          $SO_pack_authorized = SO_pack_authorized($pack_payload);
         print_r($SO_pack_authorized);
          $SO_ship_authorized = SO_ship_authorized($shipp_payload);
		  print_r($SO_ship_authorized);
	}