"""
Expense and Bill tools: create expenses, list/create/pay bills.
"""

from .helpers import _qbo_query, _qbo_post, format_error


def create_expense(tool_context, account_id: str, amount: float,
                   vendor_id: str = None, payment_type: str = "Cash",
                   memo: str = None) -> dict:
    """
    Record an expense (QBO Purchase).
    account_id: the expense account to categorize to.
    payment_type: 'Cash', 'Check', or 'CreditCard'.
    """
    try:
        line = {
            "DetailType": "AccountBasedExpenseLineDetail",
            "Amount": amount,
            "AccountBasedExpenseLineDetail": {
                "AccountRef": {"value": account_id},
            },
        }
        if memo:
            line["Description"] = memo

        payload = {
            "PaymentType": payment_type,
            "Line": [line],
            "TotalAmt": amount,
        }
        if vendor_id:
            payload["EntityRef"] = {"value": vendor_id, "type": "Vendor"}
        # QBO requires AccountRef for the payment account (bank/credit card)
        # For simplicity, we let QBO use defaults; the agent can specify if needed

        result = _qbo_post(tool_context, "purchase", payload)
        purchase = result.get("Purchase", result)
        return {
            "status": "success",
            "expense": {
                "Id": purchase.get("Id"),
                "TotalAmt": purchase.get("TotalAmt"),
                "PaymentType": purchase.get("PaymentType"),
            },
        }
    except Exception as e:
        return format_error(e)


def list_bills(tool_context, vendor_name: str = None, status: str = None) -> dict:
    """List bills. Optionally filter by vendor_name or status ('Unpaid'/'Paid')."""
    try:
        conditions = []
        if vendor_name:
            conditions.append(f"VendorRef.name = '{vendor_name}'")

        sql = "SELECT * FROM Bill"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " MAXRESULTS 1000"

        bills = _qbo_query(tool_context, sql)

        # Client-side status filter
        if status:
            status_lower = status.lower()
            filtered = []
            for b in bills:
                balance = float(b.get("Balance", 0))
                if status_lower == "unpaid" and balance > 0:
                    filtered.append(b)
                elif status_lower == "paid" and balance == 0:
                    filtered.append(b)
                elif status_lower not in ("paid", "unpaid"):
                    filtered.append(b)
            bills = filtered

        results = []
        for b in bills:
            results.append({
                "Id": b.get("Id"),
                "DocNumber": b.get("DocNumber"),
                "VendorRef": b.get("VendorRef", {}).get("name"),
                "TxnDate": b.get("TxnDate"),
                "DueDate": b.get("DueDate"),
                "TotalAmt": b.get("TotalAmt"),
                "Balance": b.get("Balance"),
            })
        return {"status": "success", "count": len(results), "bills": results}
    except Exception as e:
        return format_error(e)


def create_bill(tool_context, vendor_id: str, line_items: list,
                due_date: str = None) -> dict:
    """
    Create a bill from a vendor.
    line_items: list of dicts [{"description": "...", "amount": 500, "account_id": "..."}]
    """
    try:
        lines = []
        for item in line_items:
            line = {
                "DetailType": "AccountBasedExpenseLineDetail",
                "Amount": item.get("amount", 0),
                "Description": item.get("description", ""),
                "AccountBasedExpenseLineDetail": {
                    "AccountRef": {"value": item.get("account_id", "")},
                },
            }
            lines.append(line)

        payload = {
            "VendorRef": {"value": vendor_id},
            "Line": lines,
        }
        if due_date:
            payload["DueDate"] = due_date

        result = _qbo_post(tool_context, "bill", payload)
        bill = result.get("Bill", result)
        return {
            "status": "success",
            "bill": {
                "Id": bill.get("Id"),
                "DocNumber": bill.get("DocNumber"),
                "TotalAmt": bill.get("TotalAmt"),
                "Balance": bill.get("Balance"),
                "DueDate": bill.get("DueDate"),
            },
        }
    except Exception as e:
        return format_error(e)


def pay_bill(tool_context, bill_id: str, amount: float, bank_account_id: str) -> dict:
    """Pay a bill. Requires the bill ID and the bank account to pay from."""
    try:
        # Fetch the bill to get VendorRef
        bills = _qbo_query(tool_context, f"SELECT * FROM Bill WHERE Id = '{bill_id}'")
        if not bills:
            return {"status": "error", "message": f"Bill {bill_id} not found"}
        bill = bills[0]

        payload = {
            "VendorRef": bill.get("VendorRef"),
            "TotalAmt": amount,
            "PayType": "Check",
            "CheckPayment": {
                "BankAccountRef": {"value": bank_account_id},
            },
            "Line": [{
                "Amount": amount,
                "LinkedTxn": [{
                    "TxnId": bill_id,
                    "TxnType": "Bill",
                }],
            }],
        }

        result = _qbo_post(tool_context, "billpayment", payload)
        bp = result.get("BillPayment", result)
        return {
            "status": "success",
            "bill_payment": {
                "Id": bp.get("Id"),
                "TotalAmt": bp.get("TotalAmt"),
                "VendorRef": bp.get("VendorRef", {}).get("name"),
            },
        }
    except Exception as e:
        return format_error(e)
