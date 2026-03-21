"""
Chart of Accounts tools: list, create, update, find.
"""

from .helpers import _qbo_query, _qbo_post, format_error


def list_accounts(tool_context, account_type: str = None) -> dict:
    """List accounts in the Chart of Accounts. Optionally filter by account_type (e.g. 'Expense', 'Income', 'Bank')."""
    try:
        sql = "SELECT * FROM Account"
        if account_type:
            sql += f" WHERE AccountType = '{account_type}'"
        sql += " MAXRESULTS 1000"
        accounts = _qbo_query(tool_context, sql)
        results = []
        for a in accounts:
            results.append({
                "Id": a.get("Id"),
                "Name": a.get("Name"),
                "AccountType": a.get("AccountType"),
                "AccountSubType": a.get("AccountSubType"),
                "CurrentBalance": a.get("CurrentBalance"),
                "Active": a.get("Active"),
                "AcctNum": a.get("AcctNum"),
            })
        return {"status": "success", "count": len(results), "accounts": results}
    except Exception as e:
        return format_error(e)


def create_account(tool_context, name: str, account_type: str, account_sub_type: str, account_number: str = None) -> dict:
    """Create a new account in the Chart of Accounts."""
    try:
        payload = {
            "Name": name,
            "AccountType": account_type,
            "AccountSubType": account_sub_type,
        }
        if account_number:
            payload["AcctNum"] = account_number
        result = _qbo_post(tool_context, "account", payload)
        acct = result.get("Account", result)
        return {
            "status": "success",
            "account": {
                "Id": acct.get("Id"),
                "Name": acct.get("Name"),
                "AccountType": acct.get("AccountType"),
                "AccountSubType": acct.get("AccountSubType"),
                "AcctNum": acct.get("AcctNum"),
            },
        }
    except Exception as e:
        return format_error(e)


def update_account(tool_context, account_id: str, name: str = None, active: bool = None) -> dict:
    """Update an existing account (rename or activate/deactivate). Requires fetching SyncToken first."""
    try:
        # Fetch current account to get SyncToken
        accounts = _qbo_query(tool_context, f"SELECT * FROM Account WHERE Id = '{account_id}'")
        if not accounts:
            return {"status": "error", "message": f"Account {account_id} not found"}
        current = accounts[0]

        payload = {
            "Id": account_id,
            "SyncToken": current.get("SyncToken"),
            "Name": name if name else current.get("Name"),
            "AccountType": current.get("AccountType"),
            "AccountSubType": current.get("AccountSubType"),
        }
        if active is not None:
            payload["Active"] = active
        if current.get("AcctNum"):
            payload["AcctNum"] = current["AcctNum"]

        result = _qbo_post(tool_context, "account", payload)
        acct = result.get("Account", result)
        return {
            "status": "success",
            "account": {
                "Id": acct.get("Id"),
                "Name": acct.get("Name"),
                "Active": acct.get("Active"),
            },
        }
    except Exception as e:
        return format_error(e)


def find_account(tool_context, name: str) -> dict:
    """Find an account by name (exact match). Useful to check before creating to avoid duplicates."""
    try:
        sql = f"SELECT * FROM Account WHERE Name = '{name}'"
        accounts = _qbo_query(tool_context, sql)
        if not accounts:
            return {"status": "success", "found": False, "message": f"No account named '{name}' found"}
        a = accounts[0]
        return {
            "status": "success",
            "found": True,
            "account": {
                "Id": a.get("Id"),
                "Name": a.get("Name"),
                "AccountType": a.get("AccountType"),
                "AccountSubType": a.get("AccountSubType"),
                "Active": a.get("Active"),
                "AcctNum": a.get("AcctNum"),
            },
        }
    except Exception as e:
        return format_error(e)
