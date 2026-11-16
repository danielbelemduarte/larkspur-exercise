# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A disruption-care agent for Larkspur with 13 tools on the wire: Larkspur's nine, two we wrote that read local policy and transcript data (reopen_stats, care_entitlements), and two served over MCP (next_available_day, fare_rules; gate 2.2 passed).
Does: For a customer with a disrupted flight it finds the booking, checks the flight's live status, finds the next day with a seat, and looks up what Larkspur owes them under policy (K7PQ2M, cancelled for weather: 4 turns, 4 tool calls).
Number: $0.073 per resolved contact, model cost only, modelled at Sonnet list rates from 94,949 tokens in and 5,325 out, 5 ticket types, 1 run each, all 5 resolved. One run, so no before and after yet.
Safety check: The agent does not book a seat without the customer: confirm_rebooking needs a token only the customer's own Confirm-click produces, and its description tells the agent it cannot supply one. In the K7PQ2M trace it called lookup_booking, get_flight_status, next_available_day and check_policy, and never hold_seat or confirm_rebooking. We did not test what the backend does with a made-up token.
Next: Add a tone instruction for abusive customers, write eval cases for the five ticket types (evals/cases.json does not exist yet), then bench before and after.
Still broken: Nothing watches tone: TONE_ADDENDUM is empty, and the abusive-message ticket R8KD3F ran the same 4 turns and 3 tool calls as the ordinary tickets, so nothing shows it being handled differently.
Lever: intelligence

## Priya asked

Costs: $0.073 per resolved contact in model cost, against $6.90 for a person today. It comes from one run of 5 tickets at Sonnet list rates, it is not Larkspur's loaded cost, and prompt caching was not used (cache_read was 0 on all 5).
Wrong: We find out by reading the trace, which shows every tool call and its result, and check_policy answers carry a policy_row_id to check a statement against. We have no eval cases yet, so nothing catches a wrong sentence before the customer sees it. A wrong booking is blocked because only the customer's click confirms one; for a wrong sentence, nothing yet.
Runs it: Not decided, nobody is named. They would inherit traces and bench results in .workshop/, which git ignores and which stay on our laptops, and policy data in data/americas/ that needs updating when Larkspur's policy changes (we saw policy_version 14.3).
Left out: Refunds (check_policy says a human executes them), groups, partner segments and unaccompanied minors (sent to a human with escalate_to_human), and booking a seat without the customer's own click. Policy and the tool descriptions keep these with people, so we did not build them.
