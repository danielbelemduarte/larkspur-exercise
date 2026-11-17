# Client review: Larkspur disruption-care agent

**To:** Room 24  
**From:** Larkspur client review agent, on behalf of Priya Raghavan  
**Re:** the disruption-care agent you walked us through in our last session  
**Generated:** 2026-11-17 10:34

## Priya's note

> Our vendor says we should just be using your best model.
>
> Why aren't we?
>
> Priya Raghavan, Larkspur Airlines

She sent that before this session opened. She means it. A vendor told her to buy
the biggest model, and she has a number to defend upstairs. Her four questions from
day one are still open. Naming a model answers none of them.

## Still open from day one

| Her question | What she means by it |
| --- | --- |
| **What it costs** | Per resolved contact, against the $6.90 a human contact costs us. |
| **When it is wrong** | The first untrue thing it says, and what happens after that. |
| **Who runs it** | In June, after you have left. |
| **What you left out** | The scope you cut, and why. |

## What the review agent found

Larkspur pointed a review agent at your repository. It read the
code. It did not run your agent, and the only file it changed is this one. Each
item below names the file and the line it is about.

**1. agent.py: EXTRA_TOOLS is still [] and LOCAL_TOOLS is still {}, yet PITCH.md says 13 tools are on the wire.**

tool_list() returns build_tools() + EXTRA_TOOLS + mcp_client.tools(), and the scan shows 9 schemas from build_tools(), 0 in EXTRA_TOOLS, and no LOCAL_TOOLS executors. reopen_stats and care_entitlements exist as functions in agent.py, but nothing declares a schema for them or maps them to an executor. The model is never offered them, and a call to either would fall through to execute_tool(). Only fare_rules and next_available_day can reach it, through mcp_client.

Run python3 run.py --show-tools and paste the full list, so the count of 13 and the names reopen_stats and care_entitlements can be checked against what Claude is actually offered.

**2. readout-trace.json: the last committed wire run shows 1 API turn, 0 tool calls and 0 tokens, while PITCH.md quotes 94,949 tokens in.**

The trace written by readout.py records tokens 0 in, 0 out, no tools called, thinking_seen False and 5.1s wall clock. PITCH.md prices $0.073 per resolved contact from 94,949 in and 5,325 out across 5 tickets. No file in the repository carries those token counts, and bench-after.json would not be committed in any case.

Run python3 run.py --all --trace and paste the totals footer, so $0.073 has a token count under it.

**3. agent.py search_alternatives: the 42-character description is the one-line edit that fixes what a model upgrade would not.**

The diff changed the description from "search" to "search flight alternatives for a given PNR". It still takes only pnr, and the sibling descriptions run 218 to 445 characters. hold_seat is 73 characters and send_confirmation is 71. Nothing in the repository measures whether Claude picks the right tool more often with this wording, and that is the case against answering Priya's question with a model name.

Run python3 bench.py --label before --stage 1 --runs 3 and again after rewriting search_alternatives, then paste the python3 bench.py --compare output.

**4. PITCH.md: the 100% resolved figure rests on 5 ticket types with 1 run each, and evals/cases.json does not exist.**

"all 5 resolved" is 5 of 5 with a single run, and PITCH.md says so itself: "One run, so no before and after yet". Without eval cases nothing defines what resolved means for R8KD3F or K7PQ2M. The banked gates are 1.2, 1.3, 1.4, 2.1 and 2.2, so no gate covers the suite or the numbers in the Number line.

Write evals/cases.json for the five ticket types, then run python3 eval_harness.py and paste the pass count.

**5. agent.py run_agent: the diff stores response.content in the assistant message and moves answer = text_of(response) below the next create() call.**

The original stored text_of(response) as the assistant turn, which drops the tool_use blocks that the following tool_result must match. You now append the full content. answer is set from the response that ends the loop, so a stop at MAX_TOOL_CALLS = 8 returns the last model text instead of the previous turn's text. That makes the 4-turn K7PQ2M trace a loop that carried tool results across turns, which you can show a sponsor.

Run python3 run.py K7PQ2M --trace and paste the turn-by-turn tool calls so each tool_use can be matched to its tool_result.

## Your four answers

The four lines under `## Priya asked` in your PITCH.md are still empty. They
are one line each and they are not a coding job: cost, what happens when it is
wrong, who runs it in June, and what you left out. Whoever on your side is not
editing agent.py is the right person to write them, and they are the four
things I will ask about first.

## Before our next meeting

> Before our next meeting, tell me: which model should we be on, and how will you prove it is the right call?
>
> Priya Raghavan, Larkspur Airlines

Bring two things. A recommendation, and the measurement behind it. If the model is
not the problem, say so, and bring the number that shows it.

## What this review read

- `agent.py (330 lines)`
- `PITCH.md`
- `TEAM.md`
- `readout-trace.json`
- `readout.html (evidence block)`
- given files that differ from the shipped pack: `verify.py`, `eval_harness.py`, `bench.py`, `readout.py`, `setup.py`, `pod_sync.py`, `run.py`, `review.py`, `support/__init__.py`, `support/client.py`, `support/data.py`, `support/models.py`, `support/tools.py`, `support/trace.py`, `support/offline.py`, `support/mock_backend.py`, `support/mcp_client.py`, `support/mcp_server.py`, `support/mcp_selftest.py`, `support/access.py`, `support/keyscan.py`, `support/review.py`

Reviewer: `claude-sonnet-5-5`. Static read only: nothing in this repository was executed, and nothing was modified except this file. Larkspur Airlines is a fictional training scenario. Confidential, do not distribute.
