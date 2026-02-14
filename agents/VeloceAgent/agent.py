"""
Veloce Restaurant Management Agent
Single-location agent for Pur & Simple restaurant analytics
"""

import os
from google.adk.agents import LlmAgent
from .config import GEMINI_MODEL
from .location_config import LOCATION_CONFIG
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
)
from .reporting_tools import (
    calculate_lto_percentage_by_server,
    calculate_daily_average_meal_value,
    get_server_sales_by_category,
)

def _inject_local_credentials(callback_context):
    """
    before_agent_callback: populate session state with Veloce credentials
    if not already set (i.e. not injected by the web app backend).

    For local testing with `adk web`, set these env vars:
      VELOCE_EMAIL          - Veloce account email
      VELOCE_PASSWORD       - Veloce account password
      VELOCE_DEFAULT_LOCATION - location key (e.g. "appleby", "heartland")

    In production the backend injects these into state directly,
    so this callback is a no-op.
    """
    state = callback_context.state

    # If the backend already injected credentials, skip
    if state.get("veloce_email"):
        return

    email = os.getenv("VELOCE_EMAIL", "")
    password = os.getenv("VELOCE_PASSWORD", "")
    location_key = os.getenv("VELOCE_DEFAULT_LOCATION", "")

    if not email or not password or not location_key:
        print(
            "WARNING: Veloce credentials not in state and not in env vars. "
            "Set VELOCE_EMAIL, VELOCE_PASSWORD, and VELOCE_DEFAULT_LOCATION."
        )
        return

    if location_key not in LOCATION_CONFIG:
        print(f"WARNING: Unknown location key '{location_key}'. Valid: {list(LOCATION_CONFIG.keys())}")
        return

    loc = LOCATION_CONFIG[location_key]
    state["veloce_email"] = email
    state["veloce_password"] = password
    state["location_id"] = loc["location_id"]
    state["location_name"] = loc["name"]
    print(f"Local dev: injected credentials for {loc['name']} ({location_key})")


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
   - Sales by category (FOOD, LUNCH, LTO, DRINKS, SIDES, ESPRESSO AND BREWED, etc.)
   - Sales by division (sub-categories within each category)
   - Sales by service mode (LUNCH, MORNING, EARLY BIRD)
   - Hourly sales patterns and peak hours
   - Comprehensive daily statistics
2. **Employee Performance**:
   - Server sales, rankings, productivity
   - Hourly sales breakdown per employee (shows each employee's peak hours)
   - Employee performance by time of day
3. **Menu Analytics**: Item popularity, category breakdowns, division performance
4. **Manager Reports**:
   - LTO percentage by employee (tracks "LTO" division sales)
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
- Flag unusual patterns or anomalies (e.g. a server with 0% LTO)

**Reporting Tools:**
- `calculate_lto_percentage_by_server`: LTO sales breakdown by employee ($ and % for each server)
- `calculate_daily_average_meal_value`: Track average check size per day
- `get_server_sales_by_category`: Per-server sales broken down by POS category (bigDivision)

**Upsell Calculations:**
When asked about upselling, use `get_server_sales_by_category` to get each server's category breakdown.
Main meal categories are FOOD and LUNCH. Everything else (DRINKS, SIDES AND EXTRAS, ESPRESSO AND BREWED, LTO, etc.) counts as upsells.
Calculate upsell % per server as: (total sales - FOOD - LUNCH) / total sales * 100.

**Example Workflows:**
User: "Generate the weekly LTO report"
1. Call resolve_date_range("this week") to get from_date and to_date
2. Call calculate_lto_percentage_by_server(from_date, to_date)
3. Present LTO sales breakdown by employee with percentages in a table

User: "What's our average meal value this week?"
1. Call resolve_date_range("this week") to get from_date and to_date
2. Call calculate_daily_average_meal_value(from_date, to_date)
3. Show daily breakdown and overall average

User: "How did we do yesterday?"
1. Call resolve_date_range("yesterday") to get from_date and to_date
2. Call get_sales_summary(from_date, to_date) for the overview
3. Present key metrics clearly
""",
    description="Restaurant management assistant that provides sales analytics, employee performance tracking, operational insights, and automated weekly/daily reporting for managers.",
    before_agent_callback=_inject_local_credentials,
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
        calculate_lto_percentage_by_server,
        calculate_daily_average_meal_value,
        get_server_sales_by_category,
    ]
)
