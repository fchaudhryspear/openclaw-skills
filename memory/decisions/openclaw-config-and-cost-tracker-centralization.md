# Decision: Centralize AI Cost Tracker Scripts

- **Date:** February 28th, 2026
- **Context:** Persistent issues with AI cost tracking showing $0, and path mismatches for log files across multiple scripts.
- **Decision:** To improve manageability and resolve pathing conflicts, centralize `daily-token-report.js` and `cost-tracker.js` into a dedicated directory: `/Users/faisalshomemacmini/.openclaw/workspace/ai-cost-tracker/`.
- **Outcome:** Successfully moved and updated internal paths within these scripts, as well as the importing script `daily-summary.js`. This resolved the pathing issues but highlighted the underlying limitation of OpenClaw lacking a global hook for automatic token usage logging.

# Decision: Telegram `groupPolicy` and `dmPolicy` Configuration Adjustment

- **Date:** February 28th, 2026
- **Context:** User experiencing "not authorized" errors for commands in Telegram group chats despite `groupPolicy: "allowlist"` and user ID being in `allowFrom`.
- **Decision:**
    1. Change all instances of `groupPolicy: "allowlist"` to `groupPolicy: "open"` in `openclaw.json`.
    2. Change `dmPolicy: "pairing"` to `dmPolicy: "open"` to prevent group messages from being treated as direct messages.
    3. Include `"*"` in `allowFrom` when `dmPolicy` or `groupPolicy` is `"open"`.
    4. **Critical Diagnosis:** Advise user to disable "Group Privacy" for the bot in BotFather, as this was determined to be the root cause of the bot not seeing messages.
- **Outcome:** The configuration changes and the BotFather privacy setting adjustment were crucial in resolving the Telegram authorization issues. It exposed a significant learning about Telegram Bot API interactions.
