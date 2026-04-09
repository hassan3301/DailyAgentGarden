"""
Tools for the Insight Session Agent
"""

from google.adk.tools import FunctionTool

TOPIC_AREAS = {
    "firm_overview": "Firm Overview",
    "workflows": "Workflows & Pain Points",
    "tech_stack": "Technology Stack",
    "repetitive_tasks": "Repetitive Tasks & Automation Candidates",
    "client_communication": "Client Communication",
    "document_management": "Document Management",
    "improvements": "Growth Goals & AI Readiness",
}


def update_session_progress(
    topic_id: str, findings_summary: str, tool_context
) -> dict:
    """Record that a topic area has been covered and store the findings.

    Call this after gathering substantive information about a topic area
    during the interview.

    Args:
        topic_id: One of: firm_overview, workflows, tech_stack, repetitive_tasks,
                  client_communication, document_management, improvements
        findings_summary: A concise 2-4 sentence summary of what was learned
                         about this topic during the interview.
        tool_context: ADK tool context (injected automatically).

    Returns:
        dict with status and progress information.
    """
    if topic_id not in TOPIC_AREAS:
        return {
            "status": "error",
            "message": f"Unknown topic_id: {topic_id}. Must be one of: {', '.join(TOPIC_AREAS.keys())}",
        }

    state = tool_context.state

    # Initialize tracking structures if needed
    if "covered_topics" not in state:
        state["covered_topics"] = []
    if "topic_findings" not in state:
        state["topic_findings"] = {}

    covered = list(state["covered_topics"])
    findings = dict(state["topic_findings"])

    # Record the topic
    if topic_id not in covered:
        covered.append(topic_id)

    findings[topic_id] = findings_summary

    # Write back to state
    state["covered_topics"] = covered
    state["topic_findings"] = findings

    remaining = [
        TOPIC_AREAS[t] for t in TOPIC_AREAS if t not in covered
    ]

    return {
        "status": "success",
        "topic_recorded": TOPIC_AREAS[topic_id],
        "topics_covered": len(covered),
        "topics_total": len(TOPIC_AREAS),
        "remaining_topics": remaining if remaining else "All topics covered! Ready to generate report.",
    }


def generate_insight_report(tool_context) -> dict:
    """Generate the final AI Opportunity Insight Report based on all interview findings.

    Call this after all 7 topic areas have been covered. Returns a structured
    report template with the collected findings that you should fill in with
    specific, actionable recommendations based on the interview.

    Args:
        tool_context: ADK tool context (injected automatically).

    Returns:
        dict with report status and markdown report content.
    """
    state = tool_context.state

    covered = state.get("covered_topics", [])
    findings = state.get("topic_findings", {})

    if len(covered) < len(TOPIC_AREAS):
        missing = [TOPIC_AREAS[t] for t in TOPIC_AREAS if t not in covered]
        return {
            "status": "incomplete",
            "message": f"Cannot generate report yet. Missing topics: {', '.join(missing)}",
            "topics_covered": len(covered),
            "topics_total": len(TOPIC_AREAS),
        }

    # Build findings sections
    findings_sections = ""
    for topic_id, topic_name in TOPIC_AREAS.items():
        summary = findings.get(topic_id, "No findings recorded.")
        findings_sections += f"""
### {topic_name}

**Interview Findings:** {summary}

**AI Opportunities:** [Based on the findings above, identify 1-3 specific AI opportunities for this area. Be specific to what the interviewee described — reference their tools, workflows, and pain points by name.]

"""

    report = f"""# AI Opportunity Insight Report

## Executive Summary

[Write a 3-4 sentence executive summary that captures the firm's current state, key challenges, and the most impactful AI opportunities you identified. Be specific — reference the firm's practice areas, team size, and primary pain points.]

## Firm Profile

[Based on the firm_overview findings, write a brief profile: practice areas, team composition, client types, and revenue model.]

## Key Findings

{findings_sections}

## AI Opportunities — Ranked by Impact

| Priority | Opportunity | Area | Expected Impact | Implementation Effort | Details |
|----------|------------|------|----------------|----------------------|---------|
| 1 | [Highest impact opportunity] | [Topic area] | [Time saved / quality improved / revenue impact] | [Low/Medium/High] | [1-2 sentence description] |
| 2 | [Second opportunity] | [Topic area] | [Impact] | [Effort] | [Details] |
| 3 | [Third opportunity] | [Topic area] | [Impact] | [Effort] | [Details] |
| 4 | [Fourth opportunity] | [Topic area] | [Impact] | [Effort] | [Details] |
| 5 | [Fifth opportunity] | [Topic area] | [Impact] | [Effort] | [Details] |

## Recommended Next Steps

### Quick Wins (Next 2 weeks)
- [Specific, actionable items that can be implemented immediately with existing tools or minimal setup]

### Short-Term (1-3 months)
- [Items requiring some setup, training, or tool evaluation]

### Medium-Term (3-6 months)
- [Larger initiatives requiring planning, budget, and possibly custom development]

---

*Report generated from AI Discovery Insight Session*
*This report contains preliminary recommendations based on the interview discussion. A detailed implementation plan would follow as a next step.*
"""

    # Store the report in session state
    state["insight_report"] = report

    return {
        "status": "success",
        "message": "Report generated successfully. Present it to the interviewee and fill in all bracketed sections with specific details from your conversation.",
        "report": report,
    }
