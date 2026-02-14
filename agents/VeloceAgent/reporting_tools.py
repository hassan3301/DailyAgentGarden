"""
Specialized reporting tools for Pur & Simple manager metrics
These tools calculate weekly/daily KPIs that managers need to report
"""

import traceback
from google.adk.tools import ToolContext
from typing import Optional, List

from .veloce_tools import (
    get_cached_employee_detail_data,
    get_location_id,
    format_currency,
    _api_get,
    VELOCE_API_BASE,
)


def calculate_lto_percentage_by_server(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    lto_category_name: Optional[str] = "LTO"
) -> dict:
    """
    Calculate what percentage of each server's sales came from LTO items.
    Checks both bigDivision (category) and division (sub-category) for LTO.
    """
    print(f"\n{'='*60}")
    print(f"LTO PERCENTAGE CALCULATION")
    print(f"{'='*60}")
    print(f"Date range: {from_date} to {to_date}")
    print(f"Looking for LTO in: '{lto_category_name}'")

    try:
        # Use shared data layer (cached if already fetched by another report)
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        print(f"Found {len(active_employee_ids)} employees who worked")

        if len(active_employee_ids) == 0:
            return {
                "status": "no_data",
                "message": f"No employee sales found for {from_date} to {to_date}"
            }

        print(f"Received {len(detail_data)} total sales records")

        # Initialize tracking
        employee_lto_sales = {emp_id: 0 for emp_id in active_employee_ids}
        employee_lto_qty = {emp_id: 0 for emp_id in active_employee_ids}
        big_divisions_seen = set()
        divisions_seen = set()
        lto_records_found = 0

        # Process ALL sales records
        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            big_division_name = sale.get("bigDivision", {}).get("name", "")
            division_name = sale.get("division", {}).get("name", "")

            big_divisions_seen.add(big_division_name)
            divisions_seen.add(division_name)

            # Check if this is LTO - check BOTH bigDivision and division
            is_lto = (
                big_division_name.upper() == lto_category_name.upper() or
                division_name.upper() == lto_category_name.upper()
            )

            if is_lto:
                sales_amount = sale.get("salesAmount", 0)
                quantity = sale.get("quantity", 0)
                employee_lto_sales[emp_id] += sales_amount
                employee_lto_qty[emp_id] += quantity
                lto_records_found += 1

        print(f"LTO records found: {lto_records_found}")

        # Calculate percentages
        results = []
        for emp_id in active_employee_ids:
            total = employee_totals[emp_id]["sales_amount"]
            lto_sales = employee_lto_sales[emp_id]
            lto_qty = employee_lto_qty[emp_id]
            lto_percentage = (lto_sales / total * 100) if total > 0 else 0

            results.append({
                "employee_name": employee_map.get(emp_id, f"Employee {emp_id[:8]}"),
                "employee_id": emp_id,
                "total_sales": format_currency(total),
                "total_sales_raw": total,
                "lto_sales": format_currency(lto_sales),
                "lto_sales_raw": lto_sales,
                "lto_quantity": lto_qty,
                "lto_percentage": round(lto_percentage, 2)
            })

        results.sort(key=lambda x: x["lto_percentage"], reverse=True)

        total_all_sales = sum(t["sales_amount"] for t in employee_totals.values())
        total_lto_sales = sum(employee_lto_sales.values())
        total_lto_qty = sum(employee_lto_qty.values())

        print(f"\nFinal Summary:")
        print(f"  Total Sales: ${total_all_sales:.2f}")
        print(f"  Total LTO Sales: ${total_lto_sales:.2f}")
        print(f"  Overall LTO %: {(total_lto_sales/total_all_sales*100 if total_all_sales > 0 else 0):.2f}%")
        print(f"{'='*60}\n")

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "employee_count": len(results),
            "lto_category_tracked": lto_category_name,
            "big_divisions_found": sorted(big_divisions_seen),
            "divisions_found": sorted(divisions_seen),
            "employees": results,
            "summary": {
                "total_sales_all_employees": format_currency(total_all_sales),
                "total_lto_sales": format_currency(total_lto_sales),
                "total_lto_quantity": total_lto_qty,
                "overall_lto_percentage": round(total_lto_sales / total_all_sales * 100, 2) if total_all_sales > 0 else 0
            }
        }

    except Exception as e:
        print(f"\nERROR: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to calculate LTO percentages: {str(e)}"
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


def calculate_server_upselling_metrics(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
    main_meal_categories: Optional[List[str]] = None
) -> dict:
    """
    Calculate upselling performance for each server.
    Upsells = Everything EXCEPT main meal categories (BREAKFAST, LUNCH)
    """
    print(f"--- calculate_server_upselling_metrics: {from_date} to {to_date} ---")

    if main_meal_categories is None:
        main_meal_categories = ["BREAKFAST", "LUNCH"]

    try:
        # Use shared data layer (cached if already fetched by LTO report)
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        # Process by employee
        employee_item_counts = {emp_id: 0 for emp_id in active_employee_ids}
        employee_upsell_sales = {emp_id: 0 for emp_id in active_employee_ids}
        employee_main_meal_sales = {emp_id: 0 for emp_id in active_employee_ids}

        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            quantity = sale.get("quantity", 0)
            sales_amount = sale.get("salesAmount", 0)
            employee_item_counts[emp_id] += quantity

            division_name = sale.get("division", {}).get("name", "")
            big_division_name = sale.get("bigDivision", {}).get("name", "")

            is_main_meal = any(
                cat.upper() in big_division_name.upper() or cat.upper() in division_name.upper()
                for cat in main_meal_categories
            )

            if is_main_meal:
                employee_main_meal_sales[emp_id] += sales_amount
            else:
                employee_upsell_sales[emp_id] += sales_amount

        # Compile results
        results = []
        for emp_id in active_employee_ids:
            totals = employee_totals[emp_id]
            sales_count = totals["sales_count"]
            sales_amount = totals["sales_amount"]
            emp_name = employee_map.get(emp_id, "Unknown")
            item_count = employee_item_counts[emp_id]
            upsell_amount = employee_upsell_sales[emp_id]
            main_meal_amount = employee_main_meal_sales[emp_id]

            avg_items_per_invoice = item_count / sales_count if sales_count > 0 else 0
            upsell_percentage = (upsell_amount / sales_amount * 100) if sales_amount > 0 else 0
            main_meal_percentage = (main_meal_amount / sales_amount * 100) if sales_amount > 0 else 0
            avg_sale_value = sales_amount / sales_count if sales_count > 0 else 0

            results.append({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "total_sales": format_currency(sales_amount),
                "invoice_count": sales_count,
                "total_items_sold": item_count,
                "average_items_per_invoice": round(avg_items_per_invoice, 2),
                "average_sale_value": format_currency(avg_sale_value),
                "main_meal_sales": format_currency(main_meal_amount),
                "main_meal_percentage": round(main_meal_percentage, 2),
                "upsell_sales": format_currency(upsell_amount),
                "upsell_percentage": round(upsell_percentage, 2)
            })

        results.sort(key=lambda x: x["upsell_percentage"], reverse=True)

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "employee_count": len(results),
            "main_meal_categories": main_meal_categories,
            "calculation_method": "Upsells = Total Sales - BREAKFAST - LUNCH",
            "employees": results
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to calculate upselling metrics: {str(e)}"
        }
