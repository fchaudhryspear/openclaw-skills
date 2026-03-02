
import sys

lines = sys.stdin.readlines()
filtered_lines = []

# Keywords for the old automation section to remove
old_automation_keywords = [
    "# ============================================",
    "# Clawdbot Automation - Dallas, TX Timezone (Existing Jobs - Retained)",
    "# Calendar Sync - Every 10 minutes",
    "*/10 * * * * cd /Users/faisalshomemacmini/clawd/calendar-sync",
    "# Daily Summary Email - 7am CST",
    "0 7 * * * cd /Users/faisalshomemacmini/clawd/daily-summary",
    "# Email-to-Task - 7:05am CST",
    "5 7 * * * cd /Users/faisalshomemacmini/clawd/email-to-tasks",
    "# Email-to-Task - 1pm CST",
    "0 13 * * * cd /Users/faisalshomemacmini/clawd/email-to-tasks",
    "# Email Response Generator - 5pm CST",
    "0 17 * * * cd /Users/faisalshomemacmini/clawd/email-response-generator",
]

for line in lines:
    # Only add the line if it's not in the list of keywords to remove
    if not any(keyword in line for keyword in old_automation_keywords):
        # Also filter out empty lines that might have been left from removed cron jobs
        if line.strip() != "" or not filtered_lines or filtered_lines[-1].strip() != "":
            filtered_lines.append(line)

with open("./updated_crontab.txt", "w") as f:
    f.writelines(filtered_lines)
