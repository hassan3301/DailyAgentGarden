"""
Report tools: P&L, Balance Sheet, A/R Aging, A/P Aging, Trial Balance.

QBO reports return a nested column/row format. These tools parse that into
readable summary dicts.
"""

from .helpers import _qbo_get, format_error, format_currency


def _parse_report_rows(rows, depth=0):
    """Recursively parse QBO report rows into flat list of dicts."""
    results = []
    for row in rows:
        row_type = row.get("type", "")
        header = row.get("Header", {})
        summary = row.get("Summary", {})
        cols_data = row.get("ColData", [])

        if row_type == "Section":
            section_name = ""
            if header and header.get("ColData"):
                section_name = header["ColData"][0].get("value", "")

            # Recurse into sub-rows
            sub_rows = row.get("Rows", {}).get("Row", [])
            if sub_rows:
                results.extend(_parse_report_rows(sub_rows, depth + 1))

            # Add summary line
            if summary and summary.get("ColData"):
                cols = summary["ColData"]
                label = cols[0].get("value", "") if cols else section_name
                values = [c.get("value", "") for c in cols[1:]]
                if label:
                    results.append({"label": label, "values": values, "depth": depth, "is_summary": True})

        elif row_type == "Data" and cols_data:
            label = cols_data[0].get("value", "")
            values = [c.get("value", "") for c in cols_data[1:]]
            if label:
                results.append({"label": label, "values": values, "depth": depth, "is_summary": False})

    return results


def _format_report_as_markdown(report_json):
    """Convert QBO report JSON to a markdown summary."""
    header = report_json.get("Header", {})
    title = header.get("ReportName", "Report")
    period = header.get("DateMacro", "")
    start = header.get("StartPeriod", "")
    end = header.get("EndPeriod", "")

    columns = report_json.get("Columns", {}).get("Column", [])
    col_names = [c.get("ColTitle", "") for c in columns]

    rows_data = report_json.get("Rows", {}).get("Row", [])
    parsed = _parse_report_rows(rows_data)

    lines = [f"## {title}"]
    if start and end:
        lines.append(f"Period: {start} to {end}")
    elif period:
        lines.append(f"Period: {period}")
    lines.append("")

    # Build markdown table
    if col_names:
        header_line = "| " + " | ".join(col_names) + " |"
        sep_line = "| " + " | ".join(["---"] * len(col_names)) + " |"
        lines.append(header_line)
        lines.append(sep_line)

    for row in parsed:
        indent = "  " * row["depth"]
        label = indent + ("**" + row["label"] + "**" if row["is_summary"] else row["label"])
        vals = row["values"]
        if col_names:
            row_cells = [label] + vals + [""] * max(0, len(col_names) - 1 - len(vals))
            lines.append("| " + " | ".join(row_cells[:len(col_names)]) + " |")
        else:
            lines.append(f"{label}: {', '.join(vals)}")

    return "\n".join(lines)


def get_profit_and_loss(tool_context, from_date: str, to_date: str) -> dict:
    """Get Profit and Loss report for the given date range (YYYY-MM-DD)."""
    try:
        params = {
            "start_date": from_date,
            "end_date": to_date,
        }
        result = _qbo_get(tool_context, "reports/ProfitAndLoss", params)
        summary = _format_report_as_markdown(result)
        return {"status": "success", "report": summary}
    except Exception as e:
        return format_error(e)


def get_balance_sheet(tool_context, as_of_date: str = None) -> dict:
    """Get Balance Sheet report. Defaults to today if as_of_date not specified."""
    try:
        params = {}
        if as_of_date:
            params["start_date"] = as_of_date
            params["end_date"] = as_of_date
        result = _qbo_get(tool_context, "reports/BalanceSheet", params)
        summary = _format_report_as_markdown(result)
        return {"status": "success", "report": summary}
    except Exception as e:
        return format_error(e)


def get_ar_aging(tool_context) -> dict:
    """Get Accounts Receivable Aging Summary report."""
    try:
        result = _qbo_get(tool_context, "reports/AgedReceivables")
        summary = _format_report_as_markdown(result)
        return {"status": "success", "report": summary}
    except Exception as e:
        return format_error(e)


def get_ap_aging(tool_context) -> dict:
    """Get Accounts Payable Aging Summary report."""
    try:
        result = _qbo_get(tool_context, "reports/AgedPayables")
        summary = _format_report_as_markdown(result)
        return {"status": "success", "report": summary}
    except Exception as e:
        return format_error(e)


def get_trial_balance(tool_context, as_of_date: str = None) -> dict:
    """Get Trial Balance report."""
    try:
        params = {}
        if as_of_date:
            params["start_date"] = as_of_date
            params["end_date"] = as_of_date
        result = _qbo_get(tool_context, "reports/TrialBalance", params)
        summary = _format_report_as_markdown(result)
        return {"status": "success", "report": summary}
    except Exception as e:
        return format_error(e)
