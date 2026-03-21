"""
Customer and Vendor tools: list and create.
"""

from .helpers import _qbo_query, _qbo_post, format_error


def list_customers(tool_context, active_only: bool = True) -> dict:
    """List customers. Set active_only=False to include inactive."""
    try:
        sql = "SELECT * FROM Customer"
        if active_only:
            sql += " WHERE Active = true"
        sql += " MAXRESULTS 1000"
        customers = _qbo_query(tool_context, sql)
        results = []
        for c in customers:
            results.append({
                "Id": c.get("Id"),
                "DisplayName": c.get("DisplayName"),
                "PrimaryEmailAddr": c.get("PrimaryEmailAddr", {}).get("Address") if c.get("PrimaryEmailAddr") else None,
                "PrimaryPhone": c.get("PrimaryPhone", {}).get("FreeFormNumber") if c.get("PrimaryPhone") else None,
                "Balance": c.get("Balance"),
                "Active": c.get("Active"),
            })
        return {"status": "success", "count": len(results), "customers": results}
    except Exception as e:
        return format_error(e)


def create_customer(tool_context, display_name: str, email: str = None, phone: str = None) -> dict:
    """Create a new customer."""
    try:
        payload = {"DisplayName": display_name}
        if email:
            payload["PrimaryEmailAddr"] = {"Address": email}
        if phone:
            payload["PrimaryPhone"] = {"FreeFormNumber": phone}
        result = _qbo_post(tool_context, "customer", payload)
        cust = result.get("Customer", result)
        return {
            "status": "success",
            "customer": {
                "Id": cust.get("Id"),
                "DisplayName": cust.get("DisplayName"),
            },
        }
    except Exception as e:
        return format_error(e)


def list_vendors(tool_context, active_only: bool = True) -> dict:
    """List vendors. Set active_only=False to include inactive."""
    try:
        sql = "SELECT * FROM Vendor"
        if active_only:
            sql += " WHERE Active = true"
        sql += " MAXRESULTS 1000"
        vendors = _qbo_query(tool_context, sql)
        results = []
        for v in vendors:
            results.append({
                "Id": v.get("Id"),
                "DisplayName": v.get("DisplayName"),
                "PrimaryEmailAddr": v.get("PrimaryEmailAddr", {}).get("Address") if v.get("PrimaryEmailAddr") else None,
                "Balance": v.get("Balance"),
                "Active": v.get("Active"),
            })
        return {"status": "success", "count": len(results), "vendors": results}
    except Exception as e:
        return format_error(e)


def create_vendor(tool_context, display_name: str, email: str = None) -> dict:
    """Create a new vendor."""
    try:
        payload = {"DisplayName": display_name}
        if email:
            payload["PrimaryEmailAddr"] = {"Address": email}
        result = _qbo_post(tool_context, "vendor", payload)
        vendor = result.get("Vendor", result)
        return {
            "status": "success",
            "vendor": {
                "Id": vendor.get("Id"),
                "DisplayName": vendor.get("DisplayName"),
            },
        }
    except Exception as e:
        return format_error(e)
