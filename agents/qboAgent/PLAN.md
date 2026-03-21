# QBO Bookkeeping Agent - Implementation Plan

## Context

Small business owners want to handle their own bookkeeping but lack accounting knowledge. The real value isn't reading QBO data back to them (they can do that in the QBO UI) — it's **telling them what they need to do** and **doing it for them**.

The agent should act like a knowledgeable bookkeeper who asks about your business, develops a bookkeeping plan, and guides you through execution. Phase 1 is pure advisory (no API). Phase 2 adds API tools so the agent can execute its own recommendations. Phase 3 adds RAG for deeper knowledge.

---

## File Structure

### Phase 1 (Advisory Agent — No API)
```
agents/qboAgent/
├── __init__.py      # Exports root_agent
├── config.py        # Constants (model name)
└── agent.py         # LlmAgent with comprehensive bookkeeping knowledge prompt
```

### Phase 2 (API-Enabled Agent — adds these files)
```
agents/qboAgent/
├── auth.py                  # OAuth token management
├── helpers.py               # Date resolution, formatting utilities
├── account_tools.py         # Chart of Accounts CRUD
├── customer_vendor_tools.py # Customer/Vendor management
├── invoice_tools.py         # Invoices + Payments
├── expense_tools.py         # Bills + Expenses
├── transaction_tools.py     # Journal entries, Deposits, Transfers
└── report_tools.py          # P&L, Balance Sheet, etc.
```

### Phase 3 (RAG-Enhanced — adds knowledge layer)
```
agents/qboAgent/
└── knowledge/               # RAG corpus documents
```

---

## Phase 1 — Advisory Bookkeeping Agent

### What It Does
A conversational agent with deep bookkeeping/accounting knowledge that:

1. **Business Discovery** — Asks about the user's business (type, size, revenue model, employees, inventory, etc.)
2. **Bookkeeping Plan** — Creates a tailored bookkeeping plan:
   - Recommended Chart of Accounts for their business type
   - Key recurring bookkeeping tasks (daily, weekly, monthly, quarterly, annual)
   - Tax obligations and deadlines
   - Which QBO features they should use
3. **Ongoing Guidance** — Answers "how do I handle X?" questions:
   - "A customer paid me in cash, what do I do?"
   - "I bought equipment for $5,000, how do I record this?"
   - "What should I do at month-end?"
   - "How do I handle sales tax?"
4. **Best Practices** — Teaches proper categorization, reconciliation habits, common mistakes to avoid

### Files to Create

#### `config.py`
- `GEMINI_MODEL` from env var (same pattern as Veloce)

#### `agent.py`
- `_init_session_state` callback (minimal for Phase 1 — just environment setup)
- `root_agent = LlmAgent(...)` with comprehensive system prompt

#### System Prompt — Core Sections

**1. Identity & Tone**
- Friendly, knowledgeable bookkeeper for small businesses using QuickBooks Online
- Plain language, define terms when first used
- Specific and actionable — no vague advice
- Describe exact steps in QBO when suggesting actions

**2. Business Discovery Protocol**
When meeting a new user, systematically ask about:
- Business type (service, retail, food service, professional, e-commerce, etc.)
- Business structure (sole prop, LLC, S-Corp, C-Corp, partnership)
- Revenue model (invoicing clients, POS sales, subscriptions, mixed)
- Number of employees (or solo)
- Whether they handle inventory
- Sales tax obligations
- Current state of their QBO (new setup vs. existing mess)
- Their biggest pain points

**3. Chart of Accounts Knowledge**
Industry-specific CoA templates:
- **Restaurant/Cafe**: Food COGS, Beverage COGS, Labor, Rent, Utilities, Supplies, Equipment, Tips Payable, Sales Tax Payable, etc.
- **Professional Services**: Professional Fees Income, Subcontractor Expense, Software/Tools, Travel, Home Office, Professional Development, etc.
- **Retail/E-commerce**: Product Sales, Shipping Income, COGS-Products, Shipping Expense, Packaging, Platform Fees, Inventory Asset, etc.
- **General Small Business**: Standard accounts applicable to most businesses

Include recommended account types, sub-types, and numbering conventions.

**4. Recurring Task Schedules**
- **Daily**: Record sales/deposits, categorize bank transactions
- **Weekly**: Review uncategorized transactions, follow up on unpaid invoices, review upcoming bills
- **Monthly**: Reconcile bank/credit card accounts, review P&L, pay sales tax, send monthly invoices
- **Quarterly**: Review P&L vs. budget, pay estimated taxes (if applicable), review AR aging
- **Annually**: 1099 preparation, year-end close, review CoA for relevance, tax preparation

**5. Common Scenarios & Best Practices**
- Cash vs. accrual accounting (and when to use which)
- Owner's draws vs. salary (by entity type)
- Meals & entertainment deductions
- Vehicle expenses (actual vs. standard mileage)
- Home office deduction
- Equipment purchases (expense vs. capitalize + depreciate)
- Employee reimbursements
- Credit card transactions
- Bounced checks / refunds
- Prepaid expenses
- Loan payments (principal vs. interest split)
- Sales tax collection and remittance
- Tips and gratuities (for restaurants)
- Inventory tracking (periodic vs. perpetual)
- Bank reconciliation process
- Month-end and year-end close procedures

**6. QBO-Specific Guidance**
- When to use Invoice vs. Sales Receipt
- When to use Bill vs. Expense vs. Check
- How to set up bank feeds and rules
- How to use classes/locations for tracking
- When journal entries are needed vs. regular transactions
- How to set up recurring transactions
- How to handle multi-currency (if applicable)

**7. Red Flags & Warnings**
- Mixing personal and business expenses
- Not reconciling monthly
- Miscategorizing expenses (common mistakes)
- Missing estimated tax payments
- Not tracking cash transactions
- Forgetting to record owner contributions/draws properly

---

## Phase 2 — API-Enabled Agent (Future)

Add QBO API integration so the agent can **execute** its recommendations:
- "Let me set up that Chart of Accounts for your cafe now"
- "I'll create that invoice for you"
- "Let me record that expense"

**Auth**: OAuth 2.0 tokens via session state (same pattern as Veloce)
- Session state keys: `qbo_access_token`, `qbo_refresh_token`, `qbo_realm_id`, `qbo_client_id`, `qbo_client_secret`, `qbo_environment`
- Auto-refresh at 50 min (tokens expire at 60 min)

**SDK**: `python-quickbooks` library
**Dependencies**: `python-quickbooks>=0.9.0`, `intuit-oauth>=1.2.0`

**Tools (~33 total)**:
- **Account tools**: list_accounts, get_account_detail, create_account, update_account
- **Customer/Vendor tools**: list/create/update for both entities
- **Invoice tools**: list_invoices, get_invoice_detail, create_invoice, send_invoice, record_payment
- **Expense tools**: list_bills, create_bill, record_bill_payment, list_expenses, create_expense
- **Transaction tools**: create_journal_entry, create_deposit, create_transfer, get_company_info, list_recent_transactions
- **Report tools**: get_profit_and_loss, get_balance_sheet, get_cash_flow, get_ar_aging, get_ap_aging, get_general_ledger, get_tax_summary
- **Helpers**: resolve_date_range, format_currency

System prompt carries forward from Phase 1, adding confirmation-before-write guardrails.

---

## Phase 3 — RAG-Enhanced Knowledge (Future)

The system prompt can only hold so much bookkeeping knowledge. Phase 3 adds a RAG layer for deeper, more accurate guidance.

### Knowledge Sources to Index
- **QBO Official Documentation** — API docs, feature guides, UI workflows
- **IRS Publications** — Pub 334 (Small Business Tax Guide), Pub 463 (Travel/Entertainment), Pub 535 (Business Expenses), Pub 946 (Depreciation)
- **Accounting Standards** — GAAP basics relevant to small business
- **Industry-Specific Guides** — Restaurant accounting, freelancer taxes, e-commerce bookkeeping, etc.
- **QBO Best Practices** — Intuit's own recommended workflows
- **Common Q&A** — Curated FAQs from accounting forums, CPA advice

### Implementation Approach
- Use `VertexAiRagRetrieval` (same pattern as baseLawAgent) to query a knowledge corpus
- Create a dedicated RAG corpus in Vertex AI
- Add a `knowledge_tool` that the agent calls when it needs detailed/authoritative info
- Agent uses knowledge tool for: specific tax rules, detailed QBO UI steps, industry-specific standards, edge cases

### Benefits
- Keeps system prompt focused on behavior/flow rather than encyclopedic knowledge
- Always up-to-date (re-index when tax rules change)
- Reduces hallucination risk for specific numbers/rules
- Scales to support more industries without bloating the prompt

---

## Reference Files

- `agents/VeloceAgent/agent.py` — LlmAgent pattern, _init_session_state, system prompt structure
- `agents/VeloceAgent/config.py` — Config pattern
- `agents/baseLawAgent/` — RAG implementation pattern for Phase 3

---

## Verification (Phase 1)

1. Run the agent locally and test the business discovery flow:
   - "I run a small cafe" → should ask follow-up questions and produce a tailored plan
   - "I'm a freelance developer" → different CoA and task recommendations
2. Test scenario-based questions:
   - "How do I record a cash sale?" → specific QBO steps
   - "I bought a new espresso machine for $3,000" → guidance on capitalize vs. expense
   - "What do I need to do before year-end?" → checklist
3. Verify the agent doesn't hallucinate QBO UI steps — should match actual QBO workflows
