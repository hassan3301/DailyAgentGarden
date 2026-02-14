"""
Veloce API Tools for ADK Agent
Functions that call the Veloce API endpoints
Credentials are passed through session state by the backend
"""

from google.adk.tools import ToolContext
from typing import Optional, List
import requests
from datetime import datetime, timedelta
import time

from .config import VELOCE_API_BASE


def resolve_date_range(tool_context: ToolContext, period: str) -> dict:
    """
    Resolve a natural-language time period into from_date and to_date strings.
    ALWAYS call this first when the user mentions relative dates.

    Args:
        period: One of: "today", "yesterday", "this week", "last week",
                "this month", "last month", or an explicit range like
                "2025-06-01 to 2025-06-07"

    Returns:
        Dictionary with from_date, to_date (YYYY-MM-DD), and a human description.
        Pass these dates directly to the other sales/reporting tools.
    """
    now = datetime.now()
    period_lower = period.strip().lower()

    if " to " in period_lower:
        parts = period_lower.split(" to ")
        from_date = parts[0].strip()
        to_date = parts[1].strip()
        description = f"{from_date} to {to_date}"
    elif period_lower == "today":
        from_date = to_date = now.strftime("%Y-%m-%d")
        description = f"Today ({now.strftime('%A, %B %d, %Y')})"
    elif period_lower == "yesterday":
        yesterday = now - timedelta(days=1)
        from_date = to_date = yesterday.strftime("%Y-%m-%d")
        description = f"Yesterday ({yesterday.strftime('%A, %B %d, %Y')})"
    elif period_lower == "this week":
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)
        from_date = week_start.strftime("%Y-%m-%d")
        to_date = week_end.strftime("%Y-%m-%d")
        description = f"This week ({from_date} to {to_date})"
    elif period_lower == "last week":
        last_week_end = now - timedelta(days=now.weekday() + 1)
        last_week_start = last_week_end - timedelta(days=6)
        from_date = last_week_start.strftime("%Y-%m-%d")
        to_date = last_week_end.strftime("%Y-%m-%d")
        description = f"Last week ({from_date} to {to_date})"
    elif period_lower == "this month":
        from_date = now.replace(day=1).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")
        description = f"This month ({from_date} to {to_date})"
    elif period_lower == "last month":
        first_of_this_month = now.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        from_date = last_month_start.strftime("%Y-%m-%d")
        to_date = last_month_end.strftime("%Y-%m-%d")
        description = f"Last month ({from_date} to {to_date})"
    else:
        return {
            "status": "error",
            "message": f"Unrecognized period: '{period}'. Use: today, yesterday, this week, last week, this month, last month, or 'YYYY-MM-DD to YYYY-MM-DD'."
        }

    result = {
        "status": "success",
        "from_date": from_date,
        "to_date": to_date,
        "description": description
    }

    tool_context.state["app:last_date_range"] = result
    return result


def get_auth_token(tool_context: ToolContext) -> str:
    """
    Get the Veloce API auth token, authenticating if necessary.
    Token is cached in session state to avoid repeated authentication.
    
    Credentials are passed through session state (already fetched by the backend).
    """
    # Check if we already have a valid token that hasn't expired
    token = tool_context.state.get("veloce_token")
    token_time = tool_context.state.get("veloce_token_time")
    if token and token_time:
        age_minutes = (time.time() - token_time) / 60
        if age_minutes < 50:  # Re-auth before typical 60min JWT expiry
            return token
        print("--- Token expired (>50 min), re-authenticating ---")
        tool_context.state["veloce_token"] = None
    
    print("--- No token found, authenticating with Veloce API ---")
    
    # Get credentials from session state (passed from backend)
    veloce_email = tool_context.state.get("veloce_email")
    veloce_password = tool_context.state.get("veloce_password")
    location_id = tool_context.state.get("location_id")
    location_name = tool_context.state.get("location_name")
    
    if not veloce_email or not veloce_password:
        raise ValueError(
            "Veloce credentials not found in session state. "
            "Backend must pass veloce_email and veloce_password when creating session."
        )
    
    try:
        # Import auth function
        try:
            from .auth import authenticate_veloce
        except ImportError:
            from VeloceAgent.auth import authenticate_veloce
        
        # Authenticate with Veloce API
        print(f"🔐 Authenticating for location: {location_name}")
        auth_data = authenticate_veloce(veloce_email, veloce_password)
        token = auth_data["token"]
        
        # Store token and timestamp in session state
        tool_context.state["veloce_token"] = token
        tool_context.state["veloce_token_time"] = time.time()
        tool_context.state["user:veloce_user_id"] = auth_data.get("user_id")
        tool_context.state["user:manager_name"] = f"{auth_data.get('first_name', '')} {auth_data.get('last_name', '')}".strip()
        
        print(f"✅ Authenticated for {location_name}")
        print(f"✅ Logged in as {tool_context.state.get('user:manager_name', 'user')}")
        
        return token
        
    except Exception as e:
        raise ValueError(f"Failed to authenticate with Veloce API: {str(e)}")


def get_location_id(tool_context: ToolContext) -> str:
    """
    Get the location ID from session state (set during authentication).
    Location ID is set when the agent authenticates based on location_key.
    """
    location_id = tool_context.state.get("location_id")
    if not location_id:
        # Trigger authentication which will set the location_id
        get_auth_token(tool_context)
        location_id = tool_context.state.get("location_id")
    
    if not location_id:
        raise ValueError(
            "Location ID not found in session state. "
            "Ensure session was created with a valid location_key."
        )
    
    return location_id


def format_currency(amount: float, currency: str = "$") -> str:
    """Format currency amounts consistently"""
    return f"{currency}{amount:,.2f}"


def _api_get(tool_context: ToolContext, url: str, params: dict = None) -> requests.Response:
    """
    Wrapper around requests.get that handles 401 token expiry.
    On a 401, clears the cached token, re-authenticates, and retries once.
    """
    token = get_auth_token(tool_context)
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params
    )
    if response.status_code == 401:
        print("--- Got 401, clearing token and re-authenticating ---")
        tool_context.state["veloce_token"] = None
        token = get_auth_token(tool_context)
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params
        )
    return response


def get_cached_employee_detail_data(tool_context: ToolContext, from_date: str, to_date: str) -> dict:
    """
    Fetch and cache the three datasets that reporting tools need:
    employee sales aggregate, employee names, and detailed per-item sales.
    Caches in session state so multiple reporting tools don't repeat API calls.
    """
    cache_key = f"temp:emp_detail_{from_date}_{to_date}"
    cached = tool_context.state.get(cache_key)
    if cached:
        print(f"--- Using cached employee detail data for {from_date} to {to_date} ---")
        return cached

    print(f"--- Fetching employee detail data for {from_date} to {to_date} ---")
    location_id = get_location_id(tool_context)
    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    # 1. Employee sales aggregate
    emp_sales_resp = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/locations/employees", {
        "locationIDs": [location_id],
        "from": from_datetime,
        "to": to_datetime
    })
    emp_sales_resp.raise_for_status()
    emp_sales_data = emp_sales_resp.json()

    employee_totals = {}
    active_employee_ids = []
    if "content" in emp_sales_data and len(emp_sales_data["content"]) > 0:
        for emp in emp_sales_data["content"][0].get("employees", []):
            emp_id = emp.get("id")
            if emp_id:
                employee_totals[emp_id] = {
                    "sales_amount": emp.get("salesAmount", 0),
                    "sales_count": emp.get("salesCount", 0),
                    "employee_obj": emp.get("employee")
                }
                active_employee_ids.append(emp_id)

    # 2. Employee names
    emp_list_resp = _api_get(tool_context, f"{VELOCE_API_BASE}/employees", {
        "locationIDs": [location_id]
    })
    emp_list_resp.raise_for_status()
    employee_map = {}
    for emp in emp_list_resp.json():
        if emp["id"] in active_employee_ids:
            employee_map[emp["id"]] = emp.get("name", "Unknown")

    # 3. Detailed per-item sales
    detail_resp = _api_get(tool_context, f"{VELOCE_API_BASE}/locations/{location_id}/employees/sales", {
        "from": from_datetime,
        "to": to_datetime
    })
    detail_resp.raise_for_status()
    detail_data = detail_resp.json()

    result = {
        "employee_totals": employee_totals,
        "employee_map": employee_map,
        "detail_data": detail_data,
        "active_employee_ids": active_employee_ids
    }

    tool_context.state[cache_key] = result
    return result


def get_sales_summary(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    include_taxes: Optional[bool] = True
) -> dict:
    """
    Get aggregated sales summary for a date range.
    
    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)
        include_taxes: Whether to include tax breakdown
        
    Returns:
        Dictionary containing sales summary with key metrics
        
    Example:
        get_sales_summary(context, "2025-01-15", "2025-01-15")
        # Returns today's sales summary
    """
    print(f"--- get_sales_summary: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    # Convert dates to ISO datetime format for API
    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        # Use /sales/locations endpoint for aggregated summary
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/locations", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "consolidated": True
        })
        response.raise_for_status()
        data = response.json()
        
        # Format the response for the LLM
        if data and len(data) > 0:
            location_sales = data[0]
            
            # Extract key metrics
            total_sales = location_sales.get("salesAmount", 0)
            quantity = location_sales.get("quantity", 0)
            invoice_count = location_sales.get("invoiceCount", 0)
            customer_count = location_sales.get("customerCount", 0)
            
            result = {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "location_name": location_sales.get("locationName", "Unknown"),
                "total_sales": format_currency(total_sales),
                "total_sales_raw": total_sales,
                "quantity_sold": quantity,
                "invoice_count": invoice_count,
                "customer_count": customer_count,
                "average_per_invoice": format_currency(total_sales / invoice_count) if invoice_count > 0 else "$0.00",
                "currency": location_sales.get("currency", "$")
            }
            
            # Add tax info if available
            if "taxes" in location_sales:
                taxes = location_sales["taxes"]
                result["tax_total"] = format_currency(sum(tax.get("amount", 0) for tax in taxes))
                if include_taxes:
                    result["tax_breakdown"] = [
                        {
                            "name": tax.get("name", "Unknown"),
                            "amount": format_currency(tax.get("amount", 0))
                        }
                        for tax in taxes
                    ]
            
            # Add discount info if available
            if "discountAmount" in location_sales:
                result["discount_amount"] = format_currency(location_sales["discountAmount"])
            
            # Save to session state for potential follow-up queries
            tool_context.state["temp:last_sales_query"] = result
            
            return result
        else:
            return {
                "status": "no_data",
                "message": f"No sales data found for {from_date} to {to_date}",
                "period": f"{from_date} to {to_date}"
            }
            
    except requests.exceptions.HTTPError as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to fetch sales data: {e.response.status_code}"
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "message": "Unexpected error fetching sales data"
        }


def get_sales_by_employee(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    limit: Optional[int] = 50
) -> dict:
    """
    Get sales broken down by employee for a date range.
    
    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)
        limit: Maximum number of employees to return
        
    Returns:
        Dictionary containing employee sales data
    """
    print(f"--- get_sales_by_employee: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/locations/employees", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "limit": limit,
            "include": "employee"
        })
        response.raise_for_status()
        data = response.json()
        
        # API returns: {'content': [{'locationId': '...', 'employees': [...]}]}
        if data and "content" in data and len(data["content"]) > 0:
            location_data = data["content"][0]
            employees_sales = location_data.get("employees", [])
            
            # Get employee roster to map IDs to names
            employee_map = tool_context.state.get("app:employee_map", {})
            if not employee_map:
                try:
                    emp_response = _api_get(tool_context, f"{VELOCE_API_BASE}/employees", {
                        "locationIDs": [location_id]
                    })
                    emp_response.raise_for_status()
                    employees_list = emp_response.json()
                    employee_map = {emp["id"]: emp.get("name", "Unknown") for emp in employees_list}
                    tool_context.state["app:employee_map"] = employee_map
                except Exception:
                    print("Warning: Could not fetch employee names")
            
            # Format employee sales for easy reading
            employees = []
            for emp_data in employees_sales:
                emp_id = emp_data.get("id")
                emp_name = employee_map.get(emp_id, f"Employee {emp_id[:8]}")
                
                employees.append({
                    "name": emp_name,
                    "sales_amount": format_currency(emp_data.get("salesAmount", 0)),
                    "sales_amount_raw": emp_data.get("salesAmount", 0),
                    "sales_count": emp_data.get("salesCount", 0),
                    "employee_id": emp_id
                })
            
            # Sort by sales amount (descending)
            employees.sort(key=lambda x: x["sales_amount_raw"], reverse=True)
            
            result = {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "employee_count": len(employees),
                "employees": employees
            }
            
            # Save to state
            tool_context.state["temp:employee_sales"] = result
            
            return result
        else:
            return {
                "status": "no_data",
                "message": f"No employee sales data found for {from_date} to {to_date}",
                "period": f"{from_date} to {to_date}"
            }
            
    except requests.exceptions.HTTPError as e:
        error_detail = f"{e.response.status_code}"
        try:
            error_detail += f" - {e.response.text}"
        except:
            pass
        return {
            "status": "error",
            "error": error_detail,
            "message": f"HTTP Error: {error_detail}"
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in get_sales_by_employee: {error_trace}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "message": f"Failed to fetch employee sales data: {str(e)}"
        }


def get_sales_by_item(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    limit: Optional[int] = 50,
    sort_by: Optional[str] = "sales"
) -> dict:
    """
    Get sales broken down by menu item.
    
    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)
        limit: Maximum number of items to return
        sort_by: Sort by 'sales' (amount) or 'quantity'
        
    Returns:
        Dictionary containing item sales data
    """
    print(f"--- get_sales_by_item: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/items", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "limit": limit
        })
        response.raise_for_status()
        data = response.json()
        
        if data:
            items = []
            for item_data in data:
                items.append({
                    "name": item_data.get("name", "Unknown"),
                    "sales_amount": format_currency(item_data.get("salesAmount", 0)),
                    "quantity_sold": item_data.get("quantity", 0),
                    "item_id": item_data.get("id")
                })
            
            # Sort based on preference
            if sort_by == "quantity":
                items.sort(key=lambda x: x["quantity_sold"], reverse=True)
            else:
                items.sort(key=lambda x: float(x["sales_amount"].replace("$", "").replace(",", "")), reverse=True)
            
            result = {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "item_count": len(items),
                "items": items,
                "sorted_by": sort_by
            }
            
            tool_context.state["temp:item_sales"] = result
            
            return result
        else:
            return {
                "status": "no_data",
                "message": f"No item sales data found for {from_date} to {to_date}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to fetch item sales data"
        }


def get_employee_list(
    tool_context: ToolContext,
    active_only: Optional[bool] = True
) -> dict:
    """
    Get list of employees at the location.
    
    Args:
        tool_context: ADK context with auth token and location ID
        active_only: If True, only return active employees
        
    Returns:
        Dictionary containing employee roster
    """
    print(f"--- get_employee_list: active_only={active_only} ---")

    location_id = get_location_id(tool_context)

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/employees", {
            "locationIDs": [location_id]
        })
        response.raise_for_status()
        data = response.json()
        
        if data:
            employees = []
            for emp in data:
                # Filter by active status if requested
                if active_only and not emp.get("isActive", False):
                    continue
                    
                employees.append({
                    "name": emp.get("name", "Unknown"),
                    "employee_id": emp.get("id"),
                    "remote_id": emp.get("remoteId"),
                    "is_active": emp.get("isActive", False)
                })
            
            result = {
                "status": "success",
                "employee_count": len(employees),
                "employees": employees
            }
            
            # Cache in session state
            tool_context.state["app:employee_roster"] = employees
            
            return result
        else:
            return {
                "status": "no_data",
                "message": "No employees found"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to fetch employee list"
        }


def get_invoices(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    limit: Optional[int] = 100,
    include_items: Optional[bool] = False
) -> dict:
    """
    Get invoices/transactions for a date range.
    
    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)
        limit: Maximum number of invoices to return
        include_items: Whether to include line items in each invoice
        
    Returns:
        Dictionary containing invoice data
    """
    print(f"--- get_invoices: {from_date} to {to_date}, include_items={include_items} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    params = {
        "locationIDs": [location_id],
        "from": from_datetime,
        "to": to_datetime,
        "limit": limit
    }

    if include_items:
        params["include"] = ["items"]

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/invoices", params)
        response.raise_for_status()
        data = response.json()
        
        if data:
            invoices = []
            total_amount = 0
            
            for inv in data:
                invoice_info = {
                    "invoice_number": inv.get("invoiceNumber"),
                    "total_amount": format_currency(inv.get("totalAmount", 0)),
                    "invoice_time": inv.get("invoiceTime"),
                    "customers": inv.get("customers", 1),
                    "is_voided": inv.get("isVoided", False)
                }
                
                if include_items and "items" in inv:
                    invoice_info["items"] = inv["items"]
                
                invoices.append(invoice_info)
                total_amount += inv.get("totalAmount", 0)
            
            result = {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "invoice_count": len(invoices),
                "total_sales": format_currency(total_amount),
                "invoices": invoices
            }
            
            return result
        else:
            return {
                "status": "no_data",
                "message": f"No invoices found for {from_date} to {to_date}"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to fetch invoices"
        }


def get_menu_items(
    tool_context: ToolContext,
    active_only: Optional[bool] = True,
    search: Optional[str] = None
) -> dict:
    """
    Get menu items from the location.
    
    Args:
        tool_context: ADK context with auth token and location ID
        active_only: If True, only return active items
        search: Optional search term to filter items by name
        
    Returns:
        Dictionary containing menu items
    """
    print(f"--- get_menu_items: active_only={active_only}, search={search} ---")

    location_id = get_location_id(tool_context)

    params = {"locationIDs": [location_id]}
    if search:
        params["search"] = search

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/items", params)
        response.raise_for_status()
        data = response.json()
        
        if data:
            items = []
            for item in data:
                # Filter by active status if requested
                if active_only and not item.get("isActive", False):
                    continue
                
                items.append({
                    "name": item.get("name", "Unknown"),
                    "alternative_name": item.get("alternativeName"),
                    "price": format_currency(item.get("price", 0)),
                    "cost": format_currency(item.get("cost", 0)) if item.get("cost") else None,
                    "item_id": item.get("id"),
                    "barcode": item.get("barcode")
                })
            
            result = {
                "status": "success",
                "item_count": len(items),
                "items": items
            }
            
            # Cache menu in session state
            tool_context.state["app:menu_items"] = items
            
            return result
        else:
            return {
                "status": "no_data",
                "message": "No menu items found"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to fetch menu items"
        }


def get_sales_by_category(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Get sales broken down by major categories (BigDivisions).
    Categories include: BREAKFAST, LUNCH, LTO, ESPRESSO AND BREWED, SIDES AND EXTRAS, etc.
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with category sales breakdown including totals and percentages
    """
    print(f"--- get_sales_by_category: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        # Note: Using singular locationID (deprecated parameter) because locationIDs array doesn't work
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/bigDivisions", {
            "locationID": location_id,
            "from": from_datetime,
            "to": to_datetime
        })
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "total_categories": 0,
                "categories": [],
                "message": "No category data found for this period"
            }
        
        # Process categories
        categories = []
        total_sales = 0
        
        for cat in data:
            sales_amount = cat.get("salesAmount", 0)
            quantity = cat.get("quantity", 0)
            
            # Get category name from bigDivision object
            big_div = cat.get("bigDivision", {})
            category_name = big_div.get("descriptionMain", "Unknown")
            category_name_alt = big_div.get("descriptionAlt", "")
            
            total_sales += sales_amount
            
            categories.append({
                "name": category_name,
                "name_alt": category_name_alt,
                "sales_amount": format_currency(sales_amount),
                "sales_amount_raw": sales_amount,
                "quantity": quantity
            })
        
        # Sort by sales amount descending
        categories.sort(key=lambda x: x["sales_amount_raw"], reverse=True)
        
        # Add percentages
        for cat in categories:
            pct = (cat["sales_amount_raw"] / total_sales * 100) if total_sales > 0 else 0
            cat["percentage"] = round(pct, 2)
        
        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "total_categories": len(categories),
            "total_sales": format_currency(total_sales),
            "total_sales_raw": total_sales,
            "categories": categories
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get sales by category: {str(e)}"
        }


def get_sales_by_division(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Get sales broken down by sub-categories (Divisions).
    Shows detailed breakdown within each major category.
    For example: BREAKFAST -> BENEDICTS, PANCAKES, WAFFLES, etc.
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with division sales breakdown grouped by category
    """
    print(f"--- get_sales_by_division: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/divisions", {
            "locationID": location_id,
            "from": from_datetime,
            "to": to_datetime
        })
        response.raise_for_status()
        data = response.json()
        
        big_divisions = data.get('content', [])
        
        if not big_divisions:
            return {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "total_divisions": 0,
                "divisions": [],
                "categories": [],
                "message": "No division data found for this period"
            }
        
        # Flatten the nested structure
        all_divisions = []
        category_totals = {}
        total_sales = 0
        
        for big_div in big_divisions:
            big_div_name = big_div.get('name', 'Unknown')
            
            # Initialize category totals
            if big_div_name not in category_totals:
                category_totals[big_div_name] = {
                    "sales_amount": 0,
                    "division_count": 0,
                    "divisions": []
                }
            
            for division in big_div.get('divisions', []):
                div_name = division.get('name', 'Unknown')
                sales_amount = division.get('amount', 0)
                quantity = division.get('quantity', 0)
                
                total_sales += sales_amount
                category_totals[big_div_name]["sales_amount"] += sales_amount
                category_totals[big_div_name]["division_count"] += 1
                
                division_data = {
                    "division_name": div_name,
                    "category_name": big_div_name,
                    "sales_amount": format_currency(sales_amount),
                    "sales_amount_raw": sales_amount,
                    "quantity": quantity
                }
                
                all_divisions.append(division_data)
                category_totals[big_div_name]["divisions"].append(division_data)
        
        # Sort divisions by sales
        all_divisions.sort(key=lambda x: x["sales_amount_raw"], reverse=True)
        
        # Add percentages
        for div in all_divisions:
            pct = (div["sales_amount_raw"] / total_sales * 100) if total_sales > 0 else 0
            div["percentage"] = round(pct, 2)
        
        # Format categories for response
        categories = []
        for cat_name, cat_data in category_totals.items():
            cat_sales = cat_data["sales_amount"]
            cat_pct = (cat_sales / total_sales * 100) if total_sales > 0 else 0
            
            # Sort divisions within category
            cat_data["divisions"].sort(key=lambda x: x["sales_amount_raw"], reverse=True)
            
            categories.append({
                "category_name": cat_name,
                "sales_amount": format_currency(cat_sales),
                "sales_amount_raw": cat_sales,
                "percentage": round(cat_pct, 2),
                "division_count": cat_data["division_count"],
                "divisions": cat_data["divisions"]
            })
        
        # Sort categories by sales
        categories.sort(key=lambda x: x["sales_amount_raw"], reverse=True)
        
        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "total_sales": format_currency(total_sales),
            "total_sales_raw": total_sales,
            "total_divisions": len(all_divisions),
            "total_categories": len(categories),
            "divisions": all_divisions,
            "categories": categories
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get sales by division: {str(e)}"
        }


def get_sales_by_mode(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Get sales broken down by service mode (LUNCH, MORNING, EARLY BIRD, etc.).
    Shows customer counts, meal counts, and average check per service type.
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with mode sales breakdown
    """
    print(f"--- get_sales_by_mode: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/modes", {
            "locationID": location_id,
            "from": from_datetime,
            "to": to_datetime
        })
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "total_modes": 0,
                "modes": [],
                "message": "No mode data found for this period"
            }
        
        # Process modes
        modes = []
        total_sales = 0
        total_customers = 0
        total_meals = 0
        
        for mode in data:
            mode_name = mode.get('nameMain', 'Unknown')
            sales_amount = mode.get('salesAmount', 0)
            customers = mode.get('customers', 0)
            meals = mode.get('meals', 0)
            avg_per_customer = mode.get('averagePerCustomer', 0)
            
            total_sales += sales_amount
            total_customers += customers
            total_meals += meals
            
            modes.append({
                "mode_name": mode_name,
                "sales_amount": format_currency(sales_amount),
                "sales_amount_raw": sales_amount,
                "customers": customers,
                "meals": meals,
                "average_per_customer": round(avg_per_customer, 2)
            })
        
        # Sort by sales
        modes.sort(key=lambda x: x["sales_amount_raw"], reverse=True)
        
        # Add percentages
        for mode in modes:
            pct = (mode["sales_amount_raw"] / total_sales * 100) if total_sales > 0 else 0
            mode["percentage"] = round(pct, 2)
        
        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "total_modes": len(modes),
            "total_sales": format_currency(total_sales),
            "total_sales_raw": total_sales,
            "total_customers": total_customers,
            "total_meals": total_meals,
            "overall_average_per_customer": round(total_sales / total_customers, 2) if total_customers > 0 else 0,
            "modes": modes
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get sales by mode: {str(e)}"
        }


def get_hourly_sales(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Get sales broken down by hour of day for peak hours analysis.
    Shows which hours are busiest for staffing optimization.
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with hourly sales breakdown and peak hours
    """
    print(f"--- get_hourly_sales: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/hourly", {
            "locationID": location_id,
            "from": from_datetime,
            "to": to_datetime
        })
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "total_hours": 0,
                "hourly_data": [],
                "message": "No hourly data found for this period"
            }
        
        # Aggregate by hour (parse from invoiceLocalTime)
        from collections import defaultdict
        hourly_totals = defaultdict(lambda: {"sales": 0, "quantity": 0})
        
        for record in data:
            timestamp = record.get('invoiceLocalTime', '')
            if timestamp:
                # Parse hour from timestamp (format: 2026-01-12T07:00:00Z)
                hour = int(timestamp.split('T')[1].split(':')[0])
                
                sales = record.get('salesAmount', 0)
                qty = record.get('quantity', 0)
                
                hourly_totals[hour]["sales"] += sales
                hourly_totals[hour]["quantity"] += qty
        
        # Format hourly data
        hourly_data = []
        total_sales = sum(h["sales"] for h in hourly_totals.values())
        
        for hour in sorted(hourly_totals.keys()):
            sales = hourly_totals[hour]["sales"]
            qty = hourly_totals[hour]["quantity"]
            pct = (sales / total_sales * 100) if total_sales > 0 else 0
            
            # Format hour in 12-hour format
            hour_12 = hour % 12 if hour % 12 != 0 else 12
            am_pm = "AM" if hour < 12 else "PM"
            hour_label = f"{hour_12}:00 {am_pm}"
            
            hourly_data.append({
                "hour": hour,
                "hour_label": hour_label,
                "sales_amount": format_currency(sales),
                "sales_amount_raw": sales,
                "quantity": qty,
                "percentage": round(pct, 2)
            })
        
        # Find peak hours (top 5)
        peak_hours = sorted(hourly_data, key=lambda x: x["sales_amount_raw"], reverse=True)[:5]
        
        # Calculate time period totals
        morning_sales = sum(h["sales_amount_raw"] for h in hourly_data if 6 <= h["hour"] < 12)
        afternoon_sales = sum(h["sales_amount_raw"] for h in hourly_data if 12 <= h["hour"] < 17)
        evening_sales = sum(h["sales_amount_raw"] for h in hourly_data if 17 <= h["hour"] < 22)
        
        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "total_sales": format_currency(total_sales),
            "total_sales_raw": total_sales,
            "hourly_data": hourly_data,
            "peak_hours": peak_hours,
            "time_periods": {
                "morning_6am_12pm": {
                    "sales": format_currency(morning_sales),
                    "percentage": round((morning_sales / total_sales * 100) if total_sales > 0 else 0, 2)
                },
                "afternoon_12pm_5pm": {
                    "sales": format_currency(afternoon_sales),
                    "percentage": round((afternoon_sales / total_sales * 100) if total_sales > 0 else 0, 2)
                },
                "evening_5pm_10pm": {
                    "sales": format_currency(evening_sales),
                    "percentage": round((evening_sales / total_sales * 100) if total_sales > 0 else 0, 2)
                }
            }
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get hourly sales: {str(e)}"
        }


def get_daily_stats(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Get comprehensive daily statistics including sales, meals, customers, and orders.
    Useful for identifying trends and best/worst performing days.
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary with daily statistics breakdown
    """
    print(f"--- get_daily_stats: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/locations", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "groupByDate": "true"
        })
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "total_days": 0,
                "daily_data": [],
                "message": "No daily data found for this period"
            }
        
        # Process daily data
        from datetime import datetime as dt
        daily_data = []
        total_sales = 0
        total_meals = 0
        total_customers = 0
        total_orders = 0
        
        for day in data:
            # Extract date from accountingTime
            date_str = day.get('accountingTime', '')[:10]  # YYYY-MM-DD
            
            sales = day.get('salesAmount', 0)
            meals = day.get('mealCount', 0)
            customers = day.get('customerCount', 0)
            orders = day.get('orderCount', 0)
            
            avg_per_meal = sales / meals if meals > 0 else 0
            avg_per_order = orders / orders if orders > 0 else 0
            
            total_sales += sales
            total_meals += meals
            total_customers += customers
            total_orders += orders
            
            # Parse date to get day of week
            day_of_week = ""
            if date_str:
                try:
                    date_obj = dt.strptime(date_str, '%Y-%m-%d')
                    day_of_week = date_obj.strftime('%A')
                except:
                    pass
            
            daily_data.append({
                "date": date_str,
                "day_of_week": day_of_week,
                "sales_amount": format_currency(sales),
                "sales_amount_raw": sales,
                "meal_count": meals,
                "customer_count": customers,
                "order_count": orders,
                "average_per_meal": round(avg_per_meal, 2),
                "average_per_order": round(avg_per_order, 2)
            })
        
        # Sort by date
        daily_data.sort(key=lambda x: x["date"])
        
        # Find best and worst days
        best_day = max(daily_data, key=lambda x: x["sales_amount_raw"]) if daily_data else None
        worst_day = min(daily_data, key=lambda x: x["sales_amount_raw"]) if daily_data else None
        
        # Calculate averages
        num_days = len(daily_data)
        avg_daily_sales = total_sales / num_days if num_days > 0 else 0
        avg_daily_meals = total_meals / num_days if num_days > 0 else 0
        avg_daily_customers = total_customers / num_days if num_days > 0 else 0
        
        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "total_days": num_days,
            "total_sales": format_currency(total_sales),
            "total_sales_raw": total_sales,
            "total_meals": total_meals,
            "total_customers": total_customers,
            "total_orders": total_orders,
            "average_daily_sales": round(avg_daily_sales, 2),
            "average_daily_meals": round(avg_daily_meals, 2),
            "average_daily_customers": round(avg_daily_customers, 2),
            "best_day": best_day,
            "worst_day": worst_day,
            "daily_data": daily_data
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get daily stats: {str(e)}"
        }


def get_employee_hourly_sales(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    employee_id: Optional[str] = None
) -> dict:
    """
    Get sales broken down by hour for each employee.
    Shows which hours each employee performs best for optimal scheduling.
    
    Args:
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
        employee_id: Optional - specific employee ID to filter (shows all if not provided)
    
    Returns:
        Dictionary with hourly sales breakdown per employee
    """
    print(f"--- get_employee_hourly_sales: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        # Note: Using limit=250 (max), may need pagination for longer periods
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/invoices", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "limit": 250
        })
        response.raise_for_status()
        invoices = response.json()
        
        if not invoices:
            return {
                "status": "success",
                "period": f"{from_date} to {to_date}",
                "total_employees": 0,
                "employees": [],
                "message": "No invoice data found for this period"
            }
        
        # Aggregate by employee and hour
        from collections import defaultdict
        employee_hourly = defaultdict(lambda: defaultdict(lambda: {"sales": 0, "invoices": 0}))
        employee_ids = set()
        
        for invoice in invoices:
            emp_id = invoice.get('sellingEmployeeId')
            
            if not emp_id:
                continue
            
            # Filter by specific employee if requested
            if employee_id and emp_id != employee_id:
                continue
            
            employee_ids.add(emp_id)
            
            # Get timestamp
            timestamp = invoice.get('invoiceLocalTime') or invoice.get('invoiceTime')
            
            if timestamp:
                try:
                    hour = int(timestamp.split('T')[1].split(':')[0])
                except:
                    hour = 0
            else:
                hour = 0
            
            sales = invoice.get('subTotal', 0)
            
            employee_hourly[emp_id][hour]["sales"] += sales
            employee_hourly[emp_id][hour]["invoices"] += 1
        
        # Fetch employee names
        employee_names = {}
        emp_response = _api_get(tool_context, f"{VELOCE_API_BASE}/employees", {
            "locationIDs": [location_id]
        })

        if emp_response.status_code == 200:
            employees_list = emp_response.json()
            for emp in employees_list:
                emp_id = emp.get('id')
                if emp_id in employee_ids:
                    employee_names[emp_id] = emp.get('name', f"Employee {emp_id[:8]}")
        
        # Build response data
        employees_data = []
        
        for emp_id in employee_hourly.keys():
            hourly_data = employee_hourly[emp_id]
            emp_name = employee_names.get(emp_id, f"Employee {emp_id[:8]}")
            
            # Calculate totals
            total_sales = sum(h["sales"] for h in hourly_data.values())
            total_invoices = sum(h["invoices"] for h in hourly_data.values())
            
            # Format hourly breakdown
            hourly_breakdown = []
            for hour in sorted(hourly_data.keys()):
                sales = hourly_data[hour]["sales"]
                invoices = hourly_data[hour]["invoices"]
                avg_per_invoice = sales / invoices if invoices > 0 else 0
                
                # Format hour label
                hour_12 = hour % 12 if hour % 12 != 0 else 12
                am_pm = "AM" if hour < 12 else "PM"
                hour_label = f"{hour_12}:00 {am_pm}"
                
                hourly_breakdown.append({
                    "hour": hour,
                    "hour_label": hour_label,
                    "sales_amount": format_currency(sales),
                    "sales_amount_raw": sales,
                    "invoice_count": invoices,
                    "average_per_invoice": round(avg_per_invoice, 2)
                })
            
            # Find peak hour
            peak_hour_data = max(hourly_data.items(), key=lambda x: x[1]["sales"]) if hourly_data else (0, {"sales": 0})
            peak_hour = peak_hour_data[0]
            peak_hour_12 = peak_hour % 12 if peak_hour % 12 != 0 else 12
            peak_am_pm = "AM" if peak_hour < 12 else "PM"
            peak_hour_label = f"{peak_hour_12}:00 {peak_am_pm}"
            
            employees_data.append({
                "employee_id": emp_id,
                "employee_name": emp_name,
                "total_sales": format_currency(total_sales),
                "total_sales_raw": total_sales,
                "total_invoices": total_invoices,
                "average_per_invoice": round(total_sales / total_invoices, 2) if total_invoices > 0 else 0,
                "peak_hour": peak_hour_label,
                "peak_hour_sales": format_currency(peak_hour_data[1]["sales"]),
                "hourly_breakdown": hourly_breakdown
            })
        
        # Sort by total sales
        employees_data.sort(key=lambda x: x["total_sales_raw"], reverse=True)
        
        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "total_employees": len(employees_data),
            "employees": employees_data
        }
        
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get employee hourly sales: {str(e)}"
        }