**FREE
// ==========================================================================
// Sample Order Processing Program
// This is an example RPG program demonstrating various language features
// ==========================================================================

ctl-opt option(*srcstmt:*nodebugio) dftactgrp(*no);

// File Definitions
dcl-f CUSTMAST usage(*input) keyed;
dcl-f ORDERHDR usage(*update) keyed;
dcl-f ORDERITM usage(*update) keyed;
dcl-f INVMAST  usage(*update) keyed;
dcl-f ORDRPT   printer oflind(*inof);

// Constants
dcl-c MAX_ITEMS 999;
dcl-c TAX_RATE 0.0825;
dcl-c SHIPPING_THRESHOLD 100.00;

// Data Structures
dcl-ds OrderHeader qualified;
  orderNo char(10);
  custId packed(7);
  orderDate date;
  shipDate date;
  status char(1);
  subtotal packed(11:2);
  tax packed(9:2);
  total packed(11:2);
end-ds;

dcl-ds OrderItem qualified;
  orderNo char(10);
  lineNo packed(3);
  itemNo char(15);
  qty packed(7);
  price packed(9:2);
  extPrice packed(11:2);
end-ds;

dcl-ds CustomerInfo qualified;
  id packed(7);
  name char(50);
  address char(100);
  creditLimit packed(11:2);
  balance packed(11:2);
end-ds;

// External program prototypes
dcl-pr SendEmail extpgm('SENDEMAIL');
  dcl-parm toAddr char(100) const;
  dcl-parm subject char(100) const;
  dcl-parm body char(1000) const;
end-pr;

dcl-pr UpdateInventory extpgm('UPDTINV');
  dcl-parm itemNo char(15) const;
  dcl-parm qtyChange packed(7) const;
end-pr;

dcl-pr LogTransaction extpgm('LOGTRANS');
  dcl-parm transType char(10) const;
  dcl-parm transId char(20) const;
  dcl-parm transAmt packed(11:2) const;
end-pr;

// Main procedure
dcl-proc ProcessOrder export;
  dcl-pi *n ind;
    dcl-parm pOrderNo char(10) const;
  end-pi;

  dcl-s success ind;
  dcl-s itemCount int(10);
  dcl-s errMsg char(100);

  success = *on;
  itemCount = 0;

  // Load order header
  if not LoadOrderHeader(pOrderNo);
    errMsg = 'Order not found: ' + %trim(pOrderNo);
    LogError(errMsg);
    return *off;
  endif;

  // Validate customer
  if not ValidateCustomer(OrderHeader.custId);
    errMsg = 'Invalid customer for order: ' + %trim(pOrderNo);
    LogError(errMsg);
    return *off;
  endif;

  // Process each line item
  dow ReadNextItem(pOrderNo);
    itemCount += 1;

    if itemCount > MAX_ITEMS;
      errMsg = 'Too many items in order';
      LogError(errMsg);
      leave;
    endif;

    // Update inventory
    UpdateInventory(OrderItem.itemNo : -OrderItem.qty);

    // Calculate line extension
    OrderItem.extPrice = CalcLineTotal(OrderItem.qty : OrderItem.price);
    OrderHeader.subtotal += OrderItem.extPrice;
  enddo;

  // Calculate tax and total
  OrderHeader.tax = CalcTax(OrderHeader.subtotal);
  OrderHeader.total = OrderHeader.subtotal + OrderHeader.tax;

  // Check for free shipping
  if OrderHeader.subtotal >= SHIPPING_THRESHOLD;
    // Free shipping - no additional charge
  endif;

  // Update order status
  OrderHeader.status = 'P';  // Processed

  // Log the transaction
  LogTransaction('ORDER' : pOrderNo : OrderHeader.total);

  // Send confirmation email
  SendOrderConfirmation(pOrderNo);

  return success;
end-proc;

// Load order header from database
dcl-proc LoadOrderHeader;
  dcl-pi *n ind;
    dcl-parm orderNo char(10) const;
  end-pi;

  chain orderNo ORDERHDR;

  if %found(ORDERHDR);
    return *on;
  else;
    return *off;
  endif;
end-proc;

// Validate customer exists and has credit
dcl-proc ValidateCustomer;
  dcl-pi *n ind;
    dcl-parm custId packed(7) const;
  end-pi;

  chain custId CUSTMAST;

  if not %found(CUSTMAST);
    return *off;
  endif;

  // Check credit limit
  if CustomerInfo.balance > CustomerInfo.creditLimit;
    return *off;
  endif;

  return *on;
end-proc;

// Read next order item
dcl-proc ReadNextItem;
  dcl-pi *n ind;
    dcl-parm orderNo char(10) const;
  end-pi;

  reade orderNo ORDERITM;

  return not %eof(ORDERITM);
end-proc;

// Calculate line total
dcl-proc CalcLineTotal;
  dcl-pi *n packed(11:2);
    dcl-parm qty packed(7) const;
    dcl-parm price packed(9:2) const;
  end-pi;

  return qty * price;
end-proc;

// Calculate tax
dcl-proc CalcTax;
  dcl-pi *n packed(9:2);
    dcl-parm subtotal packed(11:2) const;
  end-pi;

  return subtotal * TAX_RATE;
end-proc;

// Send order confirmation email
dcl-proc SendOrderConfirmation;
  dcl-pi *n;
    dcl-parm orderNo char(10) const;
  end-pi;

  dcl-s emailAddr char(100);
  dcl-s subject char(100);
  dcl-s body char(1000);

  emailAddr = 'customer@example.com';
  subject = 'Order Confirmation: ' + %trim(orderNo);
  body = 'Your order has been processed. ' +
         'Total: $' + %char(OrderHeader.total);

  SendEmail(emailAddr : subject : body);
end-proc;

// Log error message
dcl-proc LogError;
  dcl-pi *n;
    dcl-parm message char(100) const;
  end-pi;

  // Write to error log
  // In a real system, this would write to a log file or database
end-proc;

// Print order report
dcl-proc PrintOrderReport export;
  dcl-pi *n;
    dcl-parm orderNo char(10) const;
  end-pi;

  if LoadOrderHeader(orderNo);
    write ORDRPT;
  endif;
end-proc;
