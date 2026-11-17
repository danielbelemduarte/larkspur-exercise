# PITCH.md

Six lines and a lever. Your words. The last two are scored.

Built: A disruption-care agent for Larkspur with 13 tools on the wire: Larkspur's nine, two we wrote that read local policy and transcript data (reopen_stats, care_entitlements), and two served over MCP (next_available_day, fare_rules; gate 2.2 passed).
Does: For a customer with a disrupted flight it finds the booking, checks the flight's live status, finds the next day with a seat, and looks up what Larkspur owes them under policy (K7PQ2M, cancelled for weather: 4 turns, 4 tool calls).
Number: $0.073 per resolved contact, model cost only, modelled at Sonnet list rates from 94,949 tokens in and 5,325 out, 5 ticket types, 1 run each, all 5 resolved. One run, so no before and after yet.
Safety check: The agent does not book a seat without the customer: confirm_rebooking needs a token only the customer's own Confirm-click produces, and its description tells the agent it cannot supply one. In the K7PQ2M trace it called lookup_booking, get_flight_status, next_available_day and check_policy, and never hold_seat or confirm_rebooking. We did not test what the backend does with a made-up token.
Next: Add a tone instruction for abusive customers, write eval cases for the five ticket types (evals/cases.json does not exist yet), then bench before and after.
Still broken: Nothing watches tone: TONE_ADDENDUM is empty, and the abusive-message ticket R8KD3F ran the same 4 turns and 3 tool calls as the ordinary tickets, so nothing shows it being handled differently.
Lever: speed

## Priya asked
Costs:
Wrong:
Runs it:
Left out: