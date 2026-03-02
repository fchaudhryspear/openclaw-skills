#!/bin/bash
# Multi-Company Switch Helper
# Usage: company [command] [args]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPANY_SCRIPT="${SCRIPT_DIR}/scripts/company.py"

if ! [[ -f "$COMPANY_SCRIPT" ]]; then
    echo "❌ Error: company.py not found at $COMPANY_SCRIPT"
    exit 1
fi

# If no arguments, show help
if [[ $# -eq 0 ]]; then
    echo "Multi-Company Context Switcher"
    echo ""
    echo "Usage: company <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list              List all companies"
    echo "  set <company>     Set active company"
    echo "  show              Show current context"
    echo "  reset             Reset to default (Credologi)"
    echo "  init              Initialize company profiles"
    echo "  env               Export environment variables"
    echo "  creds <subcmd>    Manage credentials (see creds --help)"
    echo ""
    echo "Examples:"
    echo "  company list"
    echo "  company set Credologi"
    echo "  company show"
    echo "  company env"
    echo ""
    echo "Available Companies:"
    python3 "$COMPANY_SCRIPT" --list | tail -n +4
    exit 0
fi

case "$1" in
    list)
        python3 "$COMPANY_SCRIPT" --list
        ;;
    
    set)
        if [[ -z "$2" ]]; then
            echo "❌ Error: Company name required"
            echo "Usage: company set <company>"
            exit 1
        fi
        python3 "$COMPANY_SCRIPT" --set "$2"
        # Also export environment
        eval "$(python3 "${SCRIPT_DIR}/scripts/env_loader.py" export)"
        ;;
    
    show)
        python3 "$COMPANY_SCRIPT" --show
        ;;
    
    reset)
        python3 "$COMPANY_SCRIPT" --reset
        eval "$(python3 "${SCRIPT_DIR}/scripts/env_loader.py" export)"
        ;;
    
    init)
        python3 "$COMPANY_SCRIPT" --init
        ;;
    
    env)
        eval "$(python3 "${SCRIPT_DIR}/scripts/env_loader.py" export)"
        echo "✅ Environment loaded for $(python3 "${SCRIPT_DIR}/scripts/env_loader.py" list 2>/dev/null | grep 'ACTIVE' | grep -oP '\(.*\)' | tr -d '()')"
        ;;
    
    creds)
        shift
        python3 "${SCRIPT_DIR}/scripts/credential_manager.py" "$@"
        ;;
    
    *)
        echo "❌ Unknown command: $1"
        echo "Usage: company <command>"
        echo "Run 'company' without arguments for help"
        exit 1
        ;;
esac
