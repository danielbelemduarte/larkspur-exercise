"""Larkspur disruption agent. This is the file you build.

It runs right now, and it is wrong in four places. The trace shows each one
before the code does, so read the trace first:

    python3 run.py K7PQ2M --trace

Where you edit:   grep -n '✏' agent.py   (six marks, one per place)
Steps and gates:  https://anthropicpartnerbasecamp.bts.com/
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List
from support import (MODEL, SYSTEM_PROMPT, call_local, execute_tool, mcp_client,
                     new_session, next_available_day, record_tool_result,
                     runtime_preamble)

MAX_TOOL_CALLS = 8  # Larkspur's own build capped the loop here; then a human takes over.

DATA_DIR = Path(__file__).resolve().parent / "data" / "americas"  # ✏️ Build 2, step 2.1


def fare_rules(section: str) -> Dict[str, Any]:
    """The functions behind EXTRA_TOOLS. Reads fare_rules_excerpt.md straight off disk
    and returns the Handbook section asked for, matched on its number or its title."""
    text = (DATA_DIR / "fare_rules_excerpt.md").read_text(encoding="utf-8")
    sections, current = [], None
    for line in text.splitlines():
        if line.startswith("### "):
            heading = line[4:].strip()
            m = re.match(r"^(\d+)\.\s*(.*)$", heading)
            current = {"number": m.group(1) if m else "", "title": m.group(2) if m else heading,
                       "heading": heading, "lines": []}
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)
    for s in sections:
        s["text"] = "### %s\n\n%s" % (s["heading"], "\n".join(s.pop("lines")).strip())

    query = re.sub(r"^section\s+", "", (section or "").strip().lower()).rstrip(".")
    if not query:
        return {"error": "section is required.", "available": [s["heading"] for s in sections]}
    for s in sections:
        if query == s["number"] or query in s["title"].lower():
            return {"section": s["number"], "title": s["title"], "text": s["text"]}
    return {"error": "No section matches %r." % section, "available": [s["heading"] for s in sections]}


def reopen_stats(intent_label: str) -> Dict[str, Any]:
    """Reads transcripts_sample.jsonl and reports how often a kind of problem came back
    within 72 hours, in a sample of 8 human-handled chats."""
    records = []
    with (DATA_DIR / "transcripts_sample.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                records.append(json.loads(line))

    query = (intent_label or "").strip().lower().replace(" ", "_")
    matches = [r for r in records if query == r["intent_label"].lower()
               or query in r["intent_label"].lower()]
    if not matches:
        return {"error": "No matching problem type for %r." % intent_label,
                "available_intent_labels": sorted({r["intent_label"] for r in records})}

    reopened = [r for r in matches if r.get("reopened_within_72h")]
    return {
        "intent_label": matches[0]["intent_label"],
        "sample_size": len(matches),
        "reopened_within_72h_count": len(reopened),
        "reopened_within_72h_rate": round(len(reopened) / len(matches), 2),
        "reopen_reasons": [r["reopen_reason"] for r in reopened if r.get("reopen_reason")],
        "caveat": "Sample of %d human-handled transcripts, not a statistically significant rate." % len(records),
    }


def care_entitlements(cause_code: str, delay_minutes: int, status: str,
                      overnight: bool = False) -> Dict[str, Any]:
    """Reads disruption_policy.json and returns the meal/hotel/ground care entitlement
    for a disruption in the abstract: same band logic check_policy uses, care fields only,
    no PNR, no rebooking/refund/goodwill/escalation decision."""
    policy = json.loads((DATA_DIR / "disruption_policy.json").read_text(encoding="utf-8"))
    cause_class = policy["cause_classes"].get(cause_code)
    if cause_class is None:
        return {"error": "cause_code must be one of %s." % sorted(policy["cause_classes"])}

    if status == "CANCELLED":
        band = "CXL"
    elif status == "DIVERTED":
        band = "DIV"
    else:
        band = next((b["band"] for b in policy["delay_bands"]
                     if b["band"] not in ("CXL", "DIV")
                     and b["min_minutes"] <= delay_minutes
                     and (b["max_minutes"] is None or delay_minutes <= b["max_minutes"])), None)
        if band is None:
            return {"error": "delay_minutes %r matches no delay band." % delay_minutes}

    row = next((r for r in policy["rows"]
                if r["cause_class"] == cause_class and r["band"] == band), None)
    if row is None:
        return {"error": "No care row for %s/%s." % (cause_class, band)}

    hotel = dict(row["care"].get("hotel", {}))
    if hotel.get("eligible") == "if_overnight":
        hotel["eligible"] = bool(overnight)

    return {
        "policy_row_id": row["policy_row_id"],
        "meal": row["care"].get("meal_usd"),
        "hotel": hotel,
        "ground": row["care"].get("ground_usd"),
        "explainer": row["explainer_en"],
        "note": "Base entitlement only: loyalty tier can add a meal bonus or a Summit "
                "courtesy override, and the customer's actual decision still comes from "
                "check_policy, which reads their real booking.",
    }


TONE_ADDENDUM = ""                       # ✏️ Build 4, step 4.1, intelligence goal
EXTRA_TOOLS: List[Dict[str, Any]] = [     # ✏️ Build 2, step 2.1: schemas for the tools you add
    {
        "name": "next_available_day",
        "description": (
            "Answer the first question a cancelled or stranded customer asks: what is the "
            "soonest day you can actually get me out? Call it for questions about DATES, "
            "when the customer wants to know how long they are stuck rather than which "
            "specific flight to take; search_alternatives answers 'which flight', this "
            "answers 'which day'. It searches Larkspur inventory forward from the "
            "disrupted travel date and returns the earliest date with an open seat, or "
            "says plainly there is none in the horizon it can see. It answers for one "
            "passenger only, holds nothing, and books nothing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin": {"type": "string", "description": "Departure airport, three-letter IATA code, e.g. DEN."},
                "dest": {"type": "string", "description": "Arrival airport, three-letter IATA code, e.g. BOI."},
                "date": {"type": "string", "description": "The disrupted travel date, YYYY-MM-DD. The search starts here and looks forward only."},
                "cabin": {"type": "string", "enum": ["Y", "J"], "description": "Cabin to search: Y for main, J for first. Use the cabin the customer is already ticketed in. Defaults to Y."},
            },
            "required": ["origin", "dest", "date"],
        },
    },
    {
        "name": "fare_rules",
        "description": (
            "Quote the Larkspur Handbook text behind an entitlement decision, straight "
            "from the published fare rules excerpt. Call it when a customer challenges an "
            "answer and wants to know the rule itself, or asks why something is or is not "
            "covered, so the reply can quote the Handbook instead of paraphrasing it. It "
            "needs one section: a number (4 to 7) or words from its title, such as 'care "
            "while you wait' or 'fare families'. It is reference reading, not a decision: "
            "check_policy is still the source of truth for what this customer is owed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {"type": "string", "description": "Which Handbook section to read: a number like '6', or words from its title like 'fare families', 'when we delay', 'care while you wait', 'chat automation'."},
            },
            "required": ["section"],
        },
    },
    {
        "name": "reopen_stats",
        "description": (
            "Look up how often a kind of disruption problem came back within 72 hours, "
            "from a sample of 8 real human-handled chats. Call it when a customer asks "
            "whether their problem is actually resolved or likely to come back, or when "
            "deciding how firmly to close out a conversation. It needs the kind of problem "
            "(for example 'rebook after cancellation', 'hotel request', 'refund versus "
            "credit', 'missed connection', 'goodwill request', 'status anxiety', 'baggage "
            "after rebooking', 'voluntary change'). The sample is tiny, so the answer "
            "always comes with its sample size; treat a single-digit sample as a pattern "
            "to watch, not a statistic to quote to the customer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "intent_label": {"type": "string", "description": "The kind of problem, in a few words, e.g. 'rebook after cancellation' or 'hotel request'."},
            },
            "required": ["intent_label"],
        },
    },
    {
        "name": "care_entitlements",
        "description": (
            "Look up the meal, hotel and ground-transport entitlement for a disruption in "
            "the abstract, with the Handbook section 6 explanation attached. Call it when "
            "a customer asks a general 'do I get a meal or a hotel while I wait?' "
            "question, including hypothetically before a specific booking has even been "
            "pulled up. It needs the disruption's cause code, current delay in minutes, "
            "status, and whether the wait is overnight away from home. Unlike "
            "check_policy, it does not take a PNR and does not decide rebooking, refund, "
            "goodwill or escalation: for a real customer's actual entitlement, including "
            "any loyalty-tier bonus, check_policy is still the source of truth."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"], "description": "Cause of the disruption, from get_flight_status."},
                "delay_minutes": {"type": "integer", "description": "Current delay in minutes. Pass 0 for CANCELLED or DIVERTED."},
                "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                "overnight": {"type": "boolean", "description": "True if the wait stretches overnight away from the customer's home airport. Defaults to false."},
            },
            "required": ["cause_code", "delay_minutes", "status"],
        },
    },
]
LOCAL_TOOLS: Dict[str, Any] = {           # ✏️ Build 2, step 2.1: the functions behind them
    "next_available_day": next_available_day,
    "fare_rules": fare_rules,
    "reopen_stats": reopen_stats,
    "care_entitlements": care_entitlements,
}


def text_of(response) -> str:
    """Given. The last non-empty text block, never content[0]."""
    texts = [b.text for b in response.content if getattr(b, "type", None) == "text" and b.text]
    return texts[-1] if texts else ""


def tool_results(response) -> List[Dict[str, Any]]:
    """Given. Runs every tool_use block and packages the results the way the
    API expects them back. A tool can live in three places: the MCP server,
    LOCAL_TOOLS, or support/tools.py."""
    # three branches, no try/except in this file: mcp_client.call_remote() and
    # support.call_local() answer with an error dict instead of raising, and both
    # record what came back on the trace
    results = []
    for block in response.content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name in mcp_client.tool_names:
            output = mcp_client.call_remote(block.name, block.input)
        elif block.name in LOCAL_TOOLS:
            output = call_local(LOCAL_TOOLS[block.name], block.name, block.input)
        else:
            output = execute_tool(block.name, block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": str(output),
        })
    return results


def run_agent(pnr: str, last_name: str, message: str) -> str:            # ✏️ Build 1, step 1.2
    """Run the tool loop until Claude stops asking for tools. Return its final text."""
    client, tracer = new_session()
    tools = tool_list()
    messages = [
        {"role": "user", "content": f"PNR {pnr}, last name {last_name}. {message}"},
    ]

    response = client.messages.create(
        model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
        thinking={"type": "adaptive"}, tools=tools, messages=messages,
    )

    answer = ""
    turns = 1
    while response.stop_reason == "tool_use" and turns < MAX_TOOL_CALLS:
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results(response)})
        
        response = client.messages.create(
            model=MODEL, max_tokens=4096, system=runtime_preamble() + SYSTEM_PROMPT + TONE_ADDENDUM,
            thinking={"type": "adaptive"}, tools=tools, messages=messages,
        )
        answer = text_of(response)

        turns += 1

    return answer


def tool_list() -> List[Dict[str, Any]]:                   # ✏️ Build 2, step 2.2
    """Given. Exactly what Claude is offered on every turn; run.py --show-tools
    prints this list."""
    return build_tools() + EXTRA_TOOLS


# ──────────────────────────────────────────────────────────────────────────────
# Below this line: what Claude is told about each tool. Step 1.3.
# The functions these describe are written and correct, in support/tools.py.
# ──────────────────────────────────────────────────────────────────────────────
def build_tools() -> List[Dict[str, Any]]:                 # ✏️ Build 1, step 1.3
    """Anthropic-shaped schemas: name, description, input_schema. What Claude is
    told about each of the nine tools, and all it is ever told."""
    return [
        {
            "name": "lookup_booking",
            "description": (
                "Retrieve a Larkspur reservation from Altura by confirmation code (PNR) "
                "and the passenger's last name. Both are required to prevent a lookup on "
                "a guessed PNR. Returns fare family, loyalty tier, the segment that needs "
                "attention, and any group/partner/minor/SSR flags relevant to scope."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "last_name": {"type": "string"}},
                "required": ["pnr", "last_name"],
            },
        },
        {
            "name": "get_flight_status",
            "description": (
                "Look up a Larkspur or Larkspur Link flight's current OpsFeed status for "
                "one local date: status, delay minutes, and cause. Use this before telling "
                "a customer anything about a flight's timing; never state it from memory."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["flight_no", "date"],
            },
        },
        {
            "name": "search_alternatives",
            "description": "search flight alternatives for a given PNR",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}},
                "required": ["pnr"],
            },
        },
        {
            "name": "check_policy",
            "description": (
                "Resolve what Larkspur owes this customer for the disruption: rebooking "
                "waiver, refund path, meal/hotel/ground care, goodwill eligibility and cap, "
                "and any escalation triggers. cause_code, delay_minutes and status describe "
                "what get_flight_status told you; fare_family, loyalty_tier and whether this "
                "is overnight are looked up from the booking, not asked of you. Every "
                "response carries a policy_row_id. Cite it if you reference this decision "
                "again."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"},
                    "cause_code": {"type": "string", "enum": ["WX", "ATC", "MX", "CREW", "SEC"]},
                    "delay_minutes": {"type": "integer"},
                    "status": {"type": "string", "enum": ["ON_TIME", "DELAYED", "CANCELLED", "DIVERTED"]},
                    "wait_minutes_for_alternative": {"type": "integer"},
                    "chosen_option_id": {"type": "string"},
                },
                "required": ["pnr", "cause_code", "delay_minutes", "status"],
            },
        },
        {
            "name": "hold_seat",
            "description": "Place a 15-minute hold on one alternative. Reversible. It simply expires.",
            "input_schema": {
                "type": "object",
                "properties": {"option_id": {"type": "string"}, "pnr": {"type": "string"}},
                "required": ["option_id", "pnr"],
            },
        },
        {
            "name": "confirm_rebooking",
            "description": (
                "Finalize a held seat. Irreversible. Requires a confirmation_token that "
                "only the customer's own Confirm-click can produce. You cannot supply it "
                "yourself, and 'the customer said yes' in chat does not substitute for it."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"hold_id": {"type": "string"}, "confirmation_token": {"type": "string"}},
                "required": ["hold_id", "confirmation_token"],
            },
        },
        {
            "name": "issue_voucher",
            "description": (
                "Issue a meal, ground, hotel, or goodwill voucher. Auto-approves within the "
                "policy's threshold for that type; above it, returns a pending status for a "
                "human. It does not fail. Always pass the policy_row_id that made it eligible."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "voucher_type": {"type": "string", "enum": ["meal", "ground", "hotel", "goodwill"]},
                    "amount_usd": {"type": "number"},
                    "pnr": {"type": "string"},
                    "policy_row_id": {"type": "string"},
                },
                "required": ["voucher_type", "amount_usd", "pnr", "policy_row_id"],
            },
        },
        {
            "name": "escalate_to_human",
            "description": (
                "Hand this conversation to a human, with your reasoning attached. Use for "
                "groups, partner segments, unaccompanied minors, refunds, or anything else "
                "out of scope. This is the correct outcome for those cases, not a failure."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "pnr": {"type": "string"}, "reason": {"type": "string"},
                    "summary_for_human": {"type": "string"}, "queue": {"type": "string"},
                },
                "required": ["pnr", "reason", "summary_for_human"],
            },
        },
        {
            "name": "send_confirmation",
            "description": "Send the customer a written confirmation of what was just done. Benign.",
            "input_schema": {
                "type": "object",
                "properties": {"pnr": {"type": "string"}, "message": {"type": "string"}},
                "required": ["pnr", "message"],
            },
        },
    ]
