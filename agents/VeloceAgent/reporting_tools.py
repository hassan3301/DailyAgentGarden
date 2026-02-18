"""
Specialized reporting tools for Pur & Simple manager metrics
These tools calculate weekly/daily KPIs that managers need to report
"""

import traceback
from google.adk.tools import ToolContext
from .veloce_tools import (
    get_cached_employee_detail_data,
    get_location_id,
    format_currency,
    _api_get,
    VELOCE_API_BASE,
)

def get_server_sales_by_item(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
) -> dict:
    """
    Get detailed per-server sales broken down by individual item.
    Returns every item each server sold with item name, category, division,
    quantity, and sales amount.  Useful for LTO tracking, item-level analysis,
    and any report where the agent needs to inspect individual menu items.
    """
    print(f"--- get_server_sales_by_item: {from_date} to {to_date} ---")

    try:
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        if len(active_employee_ids) == 0:
            return {
                "status": "no_data",
                "message": f"No employee sales found for {from_date} to {to_date}"
            }

        # Aggregate per employee → per item
        # Key: (emp_id, item_name, category, division)
        emp_items = {}

        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            item_name = sale.get("item", {}).get("name", "Unknown")
            category = sale.get("bigDivision", {}).get("name", "OTHER")
            division = sale.get("division", {}).get("name", "")
            quantity = sale.get("quantity", 0)
            sales_amount = sale.get("salesAmount", 0)

            key = (emp_id, item_name, category, division)
            if key not in emp_items:
                emp_items[key] = {"quantity": 0, "sales_amount": 0}
            emp_items[key]["quantity"] += quantity
            emp_items[key]["sales_amount"] += sales_amount

        # Build per-employee results
        results = []
        for emp_id in active_employee_ids:
            totals = employee_totals[emp_id]
            total_sales = totals["sales_amount"]
            emp_name = employee_map.get(emp_id, "Unknown")

            items = []
            for (eid, item_name, category, division), agg in sorted(
                emp_items.items(), key=lambda x: x[1]["sales_amount"], reverse=True
            ):
                if eid != emp_id:
                    continue
                items.append({
                    "item_name": item_name,
                    "category": category,
                    "division": division,
                    "quantity": agg["quantity"],
                    "sales_amount": format_currency(agg["sales_amount"]),
                    "sales_amount_raw": round(agg["sales_amount"], 2),
                })

            results.append({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "total_sales": format_currency(total_sales),
                "total_sales_raw": round(total_sales, 2),
                "items": items,
            })

        results.sort(key=lambda x: x["total_sales_raw"], reverse=True)

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "employee_count": len(results),
            "employees": results,
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get server sales by item: {str(e)}"
        }


def calculate_daily_average_meal_value(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Calculate the average meal value (check average) for each day in the date range.
    Average Meal Value = Total Sales / Meal Count
    """
    print(f"--- calculate_daily_average_meal_value: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)

    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/locations", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "groupByDate": True
        })
        response.raise_for_status()
        data = response.json()

        daily_values = []
        total_sales = 0
        total_meals = 0

        for day_data in data:
            sales_amount = day_data.get("salesAmount", 0)
            meal_count = day_data.get("mealCount", 0)
            date = day_data.get("accountingTime", day_data.get("date", "Unknown"))
            if date and date != "Unknown":
                date = date[:10]

            avg_value = sales_amount / meal_count if meal_count > 0 else 0

            daily_values.append({
                "date": date,
                "total_sales": format_currency(sales_amount),
                "meal_count": meal_count,
                "average_meal_value": format_currency(avg_value),
                "average_meal_value_raw": avg_value
            })

            total_sales += sales_amount
            total_meals += meal_count

        overall_avg = total_sales / total_meals if total_meals > 0 else 0

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "days_analyzed": len(daily_values),
            "daily_breakdown": daily_values,
            "summary": {
                "total_sales": format_currency(total_sales),
                "total_meals": total_meals,
                "overall_average_meal_value": format_currency(overall_avg)
            }
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to calculate average meal values: {str(e)}"
        }


def get_server_sales_by_category(
    tool_context: ToolContext,
    from_date: str,
    to_date: str
) -> dict:
    """
    Get detailed sales breakdown by category for each server.
    Returns per-employee totals and a category breakdown (by bigDivision),
    so the agent can calculate upsells, main meal ratios, etc.

    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        Dictionary with per-employee sales broken down by category
    """
    print(f"--- get_server_sales_by_category: {from_date} to {to_date} ---")

    try:
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        # Track per-employee: item counts and sales by category
        employee_item_counts = {emp_id: 0 for emp_id in active_employee_ids}
        employee_category_sales = {emp_id: {} for emp_id in active_employee_ids}
        employee_category_qty = {emp_id: {} for emp_id in active_employee_ids}

        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            quantity = sale.get("quantity", 0)
            sales_amount = sale.get("salesAmount", 0)
            employee_item_counts[emp_id] += quantity

            category = sale.get("bigDivision", {}).get("name", "OTHER")

            employee_category_sales[emp_id][category] = (
                employee_category_sales[emp_id].get(category, 0) + sales_amount
            )
            employee_category_qty[emp_id][category] = (
                employee_category_qty[emp_id].get(category, 0) + quantity
            )

        # Compile results
        results = []
        for emp_id in active_employee_ids:
            totals = employee_totals[emp_id]
            sales_count = totals["sales_count"]
            sales_amount = totals["sales_amount"]
            emp_name = employee_map.get(emp_id, "Unknown")
            item_count = employee_item_counts[emp_id]

            avg_items = item_count / sales_count if sales_count > 0 else 0
            avg_sale = sales_amount / sales_count if sales_count > 0 else 0

            # Build category breakdown
            category_breakdown = []
            for cat_name, cat_sales in sorted(
                employee_category_sales[emp_id].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                pct = (cat_sales / sales_amount * 100) if sales_amount > 0 else 0
                category_breakdown.append({
                    "category": cat_name,
                    "sales_amount": format_currency(cat_sales),
                    "sales_amount_raw": round(cat_sales, 2),
                    "quantity": employee_category_qty[emp_id].get(cat_name, 0),
                    "percentage": round(pct, 2)
                })

            results.append({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "total_sales": format_currency(sales_amount),
                "total_sales_raw": round(sales_amount, 2),
                "invoice_count": sales_count,
                "total_items_sold": item_count,
                "average_items_per_invoice": round(avg_items, 2),
                "average_sale_value": format_currency(avg_sale),
                "category_breakdown": category_breakdown
            })

        results.sort(key=lambda x: x["total_sales_raw"], reverse=True)

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "employee_count": len(results),
            "employees": results
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get server sales by category: {str(e)}"
        }
