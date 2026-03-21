"""
Specialized reporting tools for Pur & Simple manager metrics
These tools calculate weekly/daily KPIs that managers need to report
"""

import traceback
from datetime import datetime as dt
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


# LTO item names to match against (case-insensitive, substring match)
LTO_ITEMS = ["WHITE MOCHA ICED LATTE", "WHITE MOCHA LATTE"]


def _is_lto_item(item_name: str) -> bool:
    """Check if an item name matches any LTO item (case-insensitive)."""
    name_upper = item_name.upper().strip()
    return any(lto in name_upper for lto in LTO_ITEMS)


def get_lto_report(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
) -> dict:
    """
    Get LTO (Limited Time Offer) sales report per server.
    Pre-filters data to only LTO items and calculates totals, quantities,
    and LTO % of each server's total sales.
    """
    print(f"--- get_lto_report: {from_date} to {to_date} ---")

    try:
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        if len(active_employee_ids) == 0:
            return {
                "status": "no_data",
                "message": f"No employee sales found for {from_date} to {to_date}",
            }

        # Aggregate LTO items per employee
        emp_lto = {}  # emp_id -> {quantity, sales_amount, items: {name -> {qty, amt}}}
        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            item_name = sale.get("item", {}).get("name", "Unknown")
            if not _is_lto_item(item_name):
                continue

            quantity = sale.get("quantity", 0)
            sales_amount = sale.get("salesAmount", 0)

            if emp_id not in emp_lto:
                emp_lto[emp_id] = {"quantity": 0, "sales_amount": 0, "items": {}}

            emp_lto[emp_id]["quantity"] += quantity
            emp_lto[emp_id]["sales_amount"] += sales_amount

            if item_name not in emp_lto[emp_id]["items"]:
                emp_lto[emp_id]["items"][item_name] = {"quantity": 0, "sales_amount": 0}
            emp_lto[emp_id]["items"][item_name]["quantity"] += quantity
            emp_lto[emp_id]["items"][item_name]["sales_amount"] += sales_amount

        # Build results for ALL active employees (including those with 0 LTO)
        results = []
        for emp_id in active_employee_ids:
            totals = employee_totals[emp_id]
            total_sales = totals["sales_amount"]
            emp_name = employee_map.get(emp_id, "Unknown")
            lto = emp_lto.get(emp_id, {"quantity": 0, "sales_amount": 0, "items": {}})
            lto_pct = (lto["sales_amount"] / total_sales * 100) if total_sales > 0 else 0

            item_breakdown = [
                {
                    "item_name": name,
                    "quantity": vals["quantity"],
                    "sales_amount": format_currency(vals["sales_amount"]),
                }
                for name, vals in lto["items"].items()
            ]

            results.append({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "total_sales": format_currency(total_sales),
                "total_sales_raw": round(total_sales, 2),
                "lto_sales": format_currency(lto["sales_amount"]),
                "lto_sales_raw": round(lto["sales_amount"], 2),
                "lto_quantity": lto["quantity"],
                "lto_percent": round(lto_pct, 1),
                "lto_items": item_breakdown,
            })

        results.sort(key=lambda x: x["lto_sales_raw"], reverse=True)

        # Build markdown table
        lines = ["| Server | Net Sales | LTO Sales | LTO Qty | LTO % |"]
        lines.append("|---|---|---|---|---|")
        for r in results:
            lines.append(
                f"| {r['employee_name']} "
                f"| {r['total_sales']} "
                f"| {r['lto_sales']} "
                f"| {r['lto_quantity']} "
                f"| {r['lto_percent']}% |"
            )

        team_net = sum(r["total_sales_raw"] for r in results)
        team_lto = sum(r["lto_sales_raw"] for r in results)
        team_qty = sum(r["lto_quantity"] for r in results)
        team_pct = (team_lto / team_net * 100) if team_net > 0 else 0
        team_summary = (
            f"Team Total: {format_currency(team_net)} net sales, "
            f"{format_currency(team_lto)} LTO sales, "
            f"{team_qty} units ({round(team_pct, 1)}%)"
        )

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "lto_items_tracked": LTO_ITEMS,
            "markdown_table": "\n".join(lines),
            "team_summary": team_summary,
            "employee_count": len(results),
            "employees": results,
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get LTO report: {str(e)}",
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
    Get detailed sales breakdown by category AND division for each server.
    Returns per-employee totals with a category breakdown (by bigDivision),
    each containing a divisions sub-breakdown. Use this for upsell
    calculations — read the division-level totals directly instead of
    summing individual items.

    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in ISO format (YYYY-MM-DD)
        to_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        Dictionary with per-employee sales broken down by category and division
    """
    print(f"--- get_server_sales_by_category: {from_date} to {to_date} ---")

    try:
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        # Track per-employee: item counts, sales by category, and sales by (category, division)
        employee_item_counts = {emp_id: 0 for emp_id in active_employee_ids}
        employee_category_sales = {emp_id: {} for emp_id in active_employee_ids}
        employee_category_qty = {emp_id: {} for emp_id in active_employee_ids}
        employee_division_sales = {emp_id: {} for emp_id in active_employee_ids}
        employee_division_qty = {emp_id: {} for emp_id in active_employee_ids}

        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            quantity = sale.get("quantity", 0)
            sales_amount = sale.get("salesAmount", 0)
            employee_item_counts[emp_id] += quantity

            category = sale.get("bigDivision", {}).get("name", "OTHER")
            division = sale.get("division", {}).get("name", "OTHER")

            employee_category_sales[emp_id][category] = (
                employee_category_sales[emp_id].get(category, 0) + sales_amount
            )
            employee_category_qty[emp_id][category] = (
                employee_category_qty[emp_id].get(category, 0) + quantity
            )

            div_key = (category, division)
            employee_division_sales[emp_id][div_key] = (
                employee_division_sales[emp_id].get(div_key, 0) + sales_amount
            )
            employee_division_qty[emp_id][div_key] = (
                employee_division_qty[emp_id].get(div_key, 0) + quantity
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

            # Build category breakdown with nested divisions
            category_breakdown = []
            for cat_name, cat_sales in sorted(
                employee_category_sales[emp_id].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                pct = (cat_sales / sales_amount * 100) if sales_amount > 0 else 0

                # Build divisions within this category
                divisions = []
                for (c, d), div_sales in sorted(
                    employee_division_sales[emp_id].items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    if c != cat_name:
                        continue
                    div_pct = (div_sales / cat_sales * 100) if cat_sales > 0 else 0
                    divisions.append({
                        "division": d,
                        "sales_amount": format_currency(div_sales),
                        "sales_amount_raw": round(div_sales, 2),
                        "quantity": employee_division_qty[emp_id].get((c, d), 0),
                        "percentage_of_category": round(div_pct, 2),
                    })

                category_breakdown.append({
                    "category": cat_name,
                    "sales_amount": format_currency(cat_sales),
                    "sales_amount_raw": round(cat_sales, 2),
                    "quantity": employee_category_qty[emp_id].get(cat_name, 0),
                    "percentage": round(pct, 2),
                    "divisions": divisions,
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


def get_upsell_report(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
) -> dict:
    """
    Get a pre-calculated upsell performance report per server.
    Upsells = BEVERAGES (entire category) + FOOD UPGRADES division + SIDES division.
    Returns a ready-to-display markdown_table — present it directly without recalculating.

    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format

    Returns:
        Dictionary with markdown_table, team_summary, and per-employee data
    """
    print(f"--- get_upsell_report: {from_date} to {to_date} ---")

    try:
        data = get_cached_employee_detail_data(tool_context, from_date, to_date)
        employee_totals = data["employee_totals"]
        employee_map = data["employee_map"]
        detail_data = data["detail_data"]
        active_employee_ids = data["active_employee_ids"]

        if len(active_employee_ids) == 0:
            return {
                "status": "no_data",
                "message": f"No employee sales found for {from_date} to {to_date}",
            }

        # Aggregate upsell components per employee
        # Track: BEVERAGES category total, FOOD UPGRADES division, SIDES division
        emp_upsell = {}  # emp_id -> {beverages, food_upgrades, sides}
        for emp_id in active_employee_ids:
            emp_upsell[emp_id] = {"beverages": 0.0, "food_upgrades": 0.0, "sides": 0.0}

        for sale in detail_data:
            emp_id = sale.get("employeeId")
            if not emp_id or emp_id not in active_employee_ids:
                continue

            sales_amount = sale.get("salesAmount", 0)
            category = sale.get("bigDivision", {}).get("name", "").upper()
            division = sale.get("division", {}).get("name", "").upper()

            if category == "BEVERAGES":
                emp_upsell[emp_id]["beverages"] += sales_amount
            elif category == "FOOD":
                if division == "FOOD UPGRADES":
                    emp_upsell[emp_id]["food_upgrades"] += sales_amount
                elif division == "SIDES":
                    emp_upsell[emp_id]["sides"] += sales_amount

        # Build results
        results = []
        team_net_sales = 0.0
        team_upsell = 0.0

        for emp_id in active_employee_ids:
            totals = employee_totals[emp_id]
            net_sales = totals["sales_amount"]
            emp_name = employee_map.get(emp_id, "Unknown")
            u = emp_upsell[emp_id]
            upsell_total = u["beverages"] + u["food_upgrades"] + u["sides"]
            upsell_pct = (upsell_total / net_sales * 100) if net_sales > 0 else 0

            team_net_sales += net_sales
            team_upsell += upsell_total

            results.append({
                "employee_name": emp_name,
                "employee_id": emp_id,
                "net_sales": format_currency(net_sales),
                "net_sales_raw": round(net_sales, 2),
                "upsell_total": format_currency(upsell_total),
                "upsell_total_raw": round(upsell_total, 2),
                "upsell_percent": round(upsell_pct, 1),
                "beverages": format_currency(u["beverages"]),
                "beverages_raw": round(u["beverages"], 2),
                "food_upgrades": format_currency(u["food_upgrades"]),
                "food_upgrades_raw": round(u["food_upgrades"], 2),
                "sides": format_currency(u["sides"]),
                "sides_raw": round(u["sides"], 2),
            })

        results.sort(key=lambda x: x["upsell_total_raw"], reverse=True)

        # Build markdown table
        lines = ["| Server | Net Sales | Upsell $ | Upsell % | Beverages | Food Upgrades | Sides |"]
        lines.append("|---|---|---|---|---|---|---|")
        for r in results:
            lines.append(
                f"| {r['employee_name']} "
                f"| {r['net_sales']} "
                f"| {r['upsell_total']} "
                f"| {r['upsell_percent']}% "
                f"| {r['beverages']} "
                f"| {r['food_upgrades']} "
                f"| {r['sides']} |"
            )

        team_upsell_pct = (team_upsell / team_net_sales * 100) if team_net_sales > 0 else 0
        team_summary = (
            f"Team Total: {format_currency(team_net_sales)} net sales, "
            f"{format_currency(team_upsell)} upsell ({round(team_upsell_pct, 1)}%)"
        )

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "markdown_table": "\n".join(lines),
            "team_summary": team_summary,
            "employee_count": len(results),
            "employees": results,
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get upsell report: {str(e)}",
        }


def get_weekly_sales_report(
    tool_context: ToolContext,
    from_date: str,
    to_date: str,
) -> dict:
    """
    Get a pre-formatted weekly sales report with daily net sales, meal counts,
    and average meal values. Returns a markdown_table ready for display.
    Use this instead of calling get_daily_stats + calculate_daily_average_meal_value separately.

    Args:
        tool_context: ADK context with auth token and location ID
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format

    Returns:
        Dictionary with markdown_table, summary, and per-day data
    """
    print(f"--- get_weekly_sales_report: {from_date} to {to_date} ---")

    location_id = get_location_id(tool_context)
    from_datetime = f"{from_date}T00:00:00Z"
    to_datetime = f"{to_date}T23:59:59Z"

    try:
        response = _api_get(tool_context, f"{VELOCE_API_BASE}/sales/locations", {
            "locationIDs": [location_id],
            "from": from_datetime,
            "to": to_datetime,
            "groupByDate": True,
        })
        response.raise_for_status()
        data = response.json()

        if not data:
            return {
                "status": "no_data",
                "message": f"No sales data found for {from_date} to {to_date}",
            }

        days = []
        total_sales = 0.0
        total_meals = 0

        for day_data in data:
            sales = day_data.get("salesAmount", 0)
            meals = day_data.get("mealCount", 0)
            date_str = day_data.get("accountingTime", day_data.get("date", ""))[:10]

            day_of_week = ""
            if date_str:
                try:
                    day_of_week = dt.strptime(date_str, "%Y-%m-%d").strftime("%A")
                except Exception:
                    pass

            avg_meal = sales / meals if meals > 0 else 0

            days.append({
                "date": date_str,
                "day_of_week": day_of_week,
                "net_sales": format_currency(sales),
                "net_sales_raw": round(sales, 2),
                "meal_count": meals,
                "avg_meal_value": format_currency(avg_meal),
                "avg_meal_value_raw": round(avg_meal, 2),
            })

            total_sales += sales
            total_meals += meals

        days.sort(key=lambda x: x["date"])

        overall_avg = total_sales / total_meals if total_meals > 0 else 0
        num_days = len(days)
        avg_daily_sales = total_sales / num_days if num_days > 0 else 0

        # Build markdown table
        lines = ["| Date | Day | Net Sales | Meal Count | Avg Meal Value |"]
        lines.append("|---|---|---|---|---|")
        for d in days:
            lines.append(
                f"| {d['date']} "
                f"| {d['day_of_week']} "
                f"| {d['net_sales']} "
                f"| {d['meal_count']} "
                f"| {d['avg_meal_value']} |"
            )

        summary = (
            f"**{num_days} days** | "
            f"Total Sales: {format_currency(total_sales)} | "
            f"Total Meals: {total_meals} | "
            f"Avg Daily Sales: {format_currency(avg_daily_sales)} | "
            f"Avg Meal Value: {format_currency(overall_avg)}"
        )

        return {
            "status": "success",
            "period": f"{from_date} to {to_date}",
            "markdown_table": "\n".join(lines),
            "summary": summary,
            "days_count": num_days,
            "days": days,
        }

    except Exception as e:
        print(f"Error: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get weekly sales report: {str(e)}",
        }
