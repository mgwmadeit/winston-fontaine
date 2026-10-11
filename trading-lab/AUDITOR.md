# The Auditor (independent strategy checker), set up 2026-10-11
Why: the 2026-10-11 honest test showed mass-picked strategies were LUCK (real picks ~= random picks out of sample), and an earlier bug (the ORB entry-bar stop rule)
inflated results by 10x. A second, independent checker catches both.

## How it works
1. Researcher (Claude, main chat) writes a plain-English rules sheet: trading\specs\<NAME>.md (copy SPEC-TEMPLATE.md). Rules only, no code.
2. Run the auditor agent: in Claude Code say "use the strategy-auditor agent on trading\specs\<NAME>.md".
   Agent definition: C:\Users\moses\auratar\.claude\agents\strategy-auditor.md (only works when the session is opened in the auratar folder).
3. The auditor writes its OWN code (trading\audits\<NAME>_audit.py) using only bot\audit_harness.py (data, 1-min fills, costs, random controls, scoring).
4. It must beat the 95th percentile of 200 random strategies in every period, survive ±25% nudges, and match the spec's claims. It writes trading\audits\<NAME>_AUDIT.md: PASS / WATCH / FAIL.
5. Only PASS goes to the paper farm. Only strategies that also stay positive in LIVE PAPER (trading\journal\) go to real money.

## Locked holdout
FORWARD = everything after 2026-10-12. The researcher must NOT tune anything on it. The paper farm's journal is the forward record.

## Cost
Each audit = one extra agent run (uses Claude usage). Only audit strategies about to be promoted.
