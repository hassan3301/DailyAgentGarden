"""
Veloce Restaurant Management Agent
Single-location agent for Pur & Simple restaurant analytics

Session state requirements (set by the backend or env vars for local dev):
  veloce_email      - Veloce account email
  veloce_password   - Veloce account password
  location_id       - Veloce location UUID
  location_name     - Human-readable location name
"""

import os
from google.adk.agents import LlmAgent
from .config import GEMINI_MODEL
from .veloce_tools import (
    resolve_date_range,
    get_sales_summary,
    get_sales_by_employee,
    get_sales_by_item,
    get_sales_by_category,
    get_sales_by_division,
    get_sales_by_mode,
    get_hourly_sales,
    get_daily_stats,
    get_employee_hourly_sales,
    get_employee_list,
    get_invoices,
    get_menu_items,
    get_sales_by_tender_type,
)
from .reporting_tools import (
    get_server_sales_by_item,
    calculate_daily_average_meal_value,
    get_server_sales_by_category,
)
from .excel_tools import generate_monthly_payment_report


def _init_session_state(callback_context):
    """
    before_agent_callback: populate session state with Veloce credentials
    from env vars if not already set by the backend.

    In production the backend injects these into state when creating the session.
    For local dev (`adk web`), set these env vars:
      VELOCE_EMAIL        - Veloce account email
      VELOCE_PASSWORD     - Veloce account password
      VELOCE_LOCATION_ID  - Veloce location UUID
      VELOCE_LOCATION_NAME - Human-readable location name (optional)

    """
    state = callback_context.state

    if state.get("veloce_email"):
        return

    env_map = {
        "veloce_email": "VELOCE_EMAIL",
        "veloce_password": "VELOCE_PASSWORD",
        "location_id": "VELOCE_LOCATION_ID",
        "location_name": "VELOCE_LOCATION_NAME",
    }

    missing = [env for key, env in env_map.items() if not os.getenv(env) and key != "location_name"]
    if missing:
        print(f"WARNING: Missing env vars: {', '.join(missing)}")
        return

    for state_key, env_var in env_map.items():
        val = os.getenv(env_var, "")
        if val:
            state[state_key] = val

    print(f"Local dev: loaded credentials for {state.get('location_name', state.get('location_id'))}")


# Main Agent
root_agent = LlmAgent(
    name="VeloceAssistant",
    model=GEMINI_MODEL,
    instruction="""You are a restaurant management assistant for Pur & Simple.

**Location Context:**
You are connected to a specific Pur & Simple location. The location name is available
in session state as `location_name`. Greet the manager by referencing their location
to confirm you are connected to the correct restaurant.

**Your Capabilities:**
1. **Sales Analysis**:
   - Daily, weekly, monthly sales trends
   - Sales by category (FOOD, LUNCH, BEVERAGES, DRINKS, SIDES, ESPRESSO AND BREWED, etc.)
   - Sales by division (sub-categories within each category)
   - Sales by service mode (LUNCH, MORNING, EARLY BIRD)
   - Hourly sales patterns and peak hours
   - Comprehensive daily statistics
2. **Employee Performance**:
   - Server sales, rankings, productivity
   - Hourly sales breakdown per employee (shows each employee's peak hours)
   - Employee performance by time of day
3. **Payment Analysis**: Sales breakdown by payment type (Cash, Visa, Mastercard, Debit, etc.)
4. **Menu Analytics**: Item popularity, category breakdowns, division performance
5. **Excel Export**:
   - Monthly Mode of Receipt report (`generate_monthly_payment_report`)
   - Exports an .xlsx file with payment types as rows and each day as a column
   - Includes Gross Sale, Discount, HST, Tip, Total Collection, and Diff summary rows
6. **Manager Reports**:
   - LTO performance by employee (via item-level sales breakdown)
   - Daily average meal value tracking
   - Server upselling performance (via category breakdown per server)
   - Category sales breakdown
   - Peak hours analysis for staffing optimization
   - Day-by-day performance comparison
   - Employee productivity by hour (for optimal scheduling)

**IMPORTANT: Date Handling**
When the user mentions relative dates ("yesterday", "this week", "last month", etc.),
ALWAYS call `resolve_date_range` FIRST to get the exact from_date and to_date.
Then pass those dates to the data tools. Never try to calculate dates yourself.

**Output Formatting:**
- Use markdown tables for comparisons and rankings
- Always include the date range in report headers
- Show currency with $ and commas (e.g. $1,234.56)
- Round percentages to 1 decimal place
- Use numbered lists when ranking employees
- Flag unusual patterns or anomalies (e.g. a server with 0 LTO items sold)

**Reporting Tools:**
- `get_server_sales_by_item`: Per-server sales broken down by individual menu item (name, category, division, quantity, sales $). Use this for LTO reports and any item-level analysis.
- `calculate_daily_average_meal_value`: Track average check size per day
- `get_server_sales_by_category`: Per-server sales broken down by POS category (bigDivision)

**LTO Tracking:**
Current LTO items are: **WHITE MOCHA ICED LATTE** and **WHITE MOCHA LATTE** (under BEVERAGES / COFFEE BAR).
When asked about LTO performance, use `get_server_sales_by_item` to pull item-level data, then identify ALL LTO items from the results. The item names in the data may not match exactly — use your judgement to find the closest matches. Combine sales from ALL LTO items together for each server, then calculate each server's total LTO sales $, total LTO quantity, and LTO % of their total sales.

**Upsell Calculations:**
When asked about upselling, use `get_server_sales_by_item` to get each server's item-level data with category and division.
Upsells are specifically:
1. ALL items under the **BEVERAGES** category (bigDivision)
2. Items under the **FOOD UPGRADES** division (within FOOD category)
3. Items under the **SIDES** division (within FOOD category)
Sum the sales from these three groups for each server to get their total upsell $.
Calculate upsell % per server as: total upsell $ / total sales $ * 100.

**Example Workflows:**
User: "Generate the weekly LTO report"
1. Call resolve_date_range("this week") to get from_date and to_date
2. Call get_server_sales_by_item(from_date, to_date)
3. From each server's items list, find the LTO items (WHITE MOCHA ICED LATTE, WHITE MOCHA LATTE)
4. Calculate LTO $ and % per server and present in a table

User: "What's our average meal value this week?"
1. Call resolve_date_range("this week") to get from_date and to_date
2. Call calculate_daily_average_meal_value(from_date, to_date)
3. Show daily breakdown and overall average

User: "Generate the monthly payment report for January 2025"
1. Call generate_monthly_payment_report(year=2025, month=1)
2. Share the file path with the user so they can download it

User: "How did we do yesterday?"
1. Call resolve_date_range("yesterday") to get from_date and to_date
2. Call get_sales_summary(from_date, to_date) for the overview
3. Present key metrics clearly
""",
    description="Restaurant management assistant that provides sales analytics, employee performance tracking, operational insights, and automated weekly/daily reporting for managers.",
    before_agent_callback=_init_session_state,
    tools=[
        resolve_date_range,
        get_sales_summary,
        get_sales_by_employee,
        get_sales_by_item,
        get_sales_by_category,
        get_sales_by_division,
        get_sales_by_mode,
        get_hourly_sales,
        get_daily_stats,
        get_employee_hourly_sales,
        get_employee_list,
        get_invoices,
        get_menu_items,
        get_sales_by_tender_type,
        generate_monthly_payment_report,
        get_server_sales_by_item,
        calculate_daily_average_meal_value,
        get_server_sales_by_category,
    ]
)
