"""
Invoice tools: list, create, send invoices; receive payments; create sales receipts.
"""

from .helpers import _qbo_query, _qbo_post, _qbo_get, format_error, format_currency


def list_invoices(tool_context, status: str = None, customer_name: str = None,
                  from_date: str = None, to_date: str = None) -> dict:
    """List invoices with optional filters. status can be 'Paid', 'Unpaid', etc."""
    try:
        conditions = []
        if customer_name:
            conditions.append(f"CustomerRef.name = '{customer_name}'")
        if from_date:
            conditions.append(f"TxnDate >= '{from_date}'")
        if to_date:
            conditions.append(f"TxnDate <= '{to_date}'")

        sql = "SELECT * FROM Invoice"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " MAXRESULTS 1000"

        invoices = _qbo_query(tool_context, sql)

        # Client-side filter for status since QBOQL doesn't support Balance filter directly
        if status:
            status_lower = status.lower()
            filtered = []
            for inv in invoices:
                balance = float(inv.get("Balance", 0))
                if status_lower == "unpaid" and balance > 0:
                    filtered.append(inv)
                elif status_lower == "paid" and balance == 0:
                    filtered.append(inv)
                elif status_lower not in ("paid", "unpaid"):
                    filtered.append(inv)
            invoices = filtered

        results = []
        for inv in invoices:
            results.append({
                "Id": inv.get("Id"),
                "DocNumber": inv.get("DocNumber"),
                "CustomerRef": inv.get("CustomerRef", {}).get("name"),
                "TxnDate": inv.get("TxnDate"),
                "DueDate": inv.get("DueDate"),
                "TotalAmt": inv.get("TotalAmt"),
                "Balance": inv.get("Balance"),
            })
        return {"status": "success", "count": len(results), "invoices": results}
    except Exception as e:
        return format_error(e)


def create_invoice(tool_context, customer_id: str, line_items: list,
                   due_date: str = None, memo: str = None) -> dict:
    """
    Create an invoice.
    line_items: list of dicts [{"description": "...", "amount": 500, "account_id": "..."}]
    """
    try:
        lines = []
        for i, item in enumerate(line_items, 1):
            line = {
                "DetailType": "SalesItemLineDetail",
                "Amount": item.get("amount", 0),
                "Description": item.get("description", ""),
                "SalesItemLineDetail": {
                    "UnitPrice": item.get("amount", 0),
                    "Qty": item.get("quantity", 1),
                },
            }
            if item.get("account_id"):
                line["SalesItemLineDetail"]["ItemAccountRef"] = {"value": item["account_id"]}
            lines.append(line)

        payload = {
            "CustomerRef": {"value": customer_id},
            "Line": lines,
        }
        if due_date:
            payload["DueDate"] = due_date
        if memo:
            payload["PrivateNote"] = memo

        result = _qbo_post(tool_context, "invoice", payload)
        inv = result.get("Invoice", result)
        return {
            "status": "success",
            "invoice": {
                "Id": inv.get("Id"),
                "DocNumber": inv.get("DocNumber"),
                "TotalAmt": inv.get("TotalAmt"),
                "Balance": inv.get("Balance"),
                "DueDate": inv.get("DueDate"),
            },
        }
    except Exception as e:
        return format_error(e)


def send_invoice(tool_context, invoice_id: str, email: str = None) -> dict:
    """Send an invoice by email. If email is not provided, uses the customer's email on file."""
    try:
        import requests as req
        from .auth import ensure_fresh_token
        from .config import QBO_API_BASE, MINOR_VERSION

        access_token, realm_id = ensure_fresh_token(tool_context)
        endpoint = f"invoice/{invoice_id}/send"
        url = f"{QBO_API_BASE}/{realm_id}/{endpoint}"
        p = {"minorversion": MINOR_VERSION}
        if email:
            p["sendTo"] = email
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/octet-stream",
        }

        resp = req.post(url, headers=headers, params=p, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        inv = result.get("Invoice", result)
        return {
            "status": "success",
            "message": f"Invoice {inv.get('DocNumber', invoice_id)} sent successfully.",
            "invoice_id": inv.get("Id"),
        }
    except Exception as e:
        return format_error(e)


def receive_payment(tool_context, customer_id: str, amount: float,
                    invoice_id: str = None) -> dict:
    """Record a payment received from a customer."""
    try:
        payload = {
            "CustomerRef": {"value": customer_id},
            "TotalAmt": amount,
        }
        if invoice_id:
            payload["Line"] = [{
                "Amount": amount,
                "LinkedTxn": [{
                    "TxnId": invoice_id,
                    "TxnType": "Invoice",
                }],
            }]

        result = _qbo_post(tool_context, "payment", payload)
        pmt = result.get("Payment", result)
        return {
            "status": "success",
            "payment": {
                "Id": pmt.get("Id"),
                "TotalAmt": pmt.get("TotalAmt"),
                "CustomerRef": pmt.get("CustomerRef", {}).get("name"),
            },
        }
    except Exception as e:
        return format_error(e)


def create_sales_receipt(tool_context, customer_id: str, line_items: list,
                         memo: str = None) -> dict:
    """
    Create a sales receipt (immediate payment, no A/R).
    line_items: list of dicts [{"description": "...", "amount": 500, "account_id": "..."}]
    """
    try:
        lines = []
        for item in line_items:
            line = {
                "DetailType": "SalesItemLineDetail",
                "Amount": item.get("amount", 0),
                "Description": item.get("description", ""),
                "SalesItemLineDetail": {
                    "UnitPrice": item.get("amount", 0),
                    "Qty": item.get("quantity", 1),
                },
            }
            if item.get("account_id"):
                line["SalesItemLineDetail"]["ItemAccountRef"] = {"value": item["account_id"]}
            lines.append(line)

        payload = {
            "CustomerRef": {"value": customer_id},
            "Line": lines,
        }
        if memo:
            payload["PrivateNote"] = memo

        result = _qbo_post(tool_context, "salesreceipt", payload)
        sr = result.get("SalesReceipt", result)
        return {
            "status": "success",
            "sales_receipt": {
                "Id": sr.get("Id"),
                "DocNumber": sr.get("DocNumber"),
                "TotalAmt": sr.get("TotalAmt"),
            },
        }
    except Exception as e:
        return format_error(e)
