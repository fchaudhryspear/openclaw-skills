#!/bin/bash
# Load Microsoft Graph OAuth secrets from macOS Keychain into environment

echo "🔑 Loading Microsoft Graph OAuth secrets..."

export OAUTH2_SECRET_FLOBASE=$(security find-generic-password -a 'optimus' -s 'msgraph-flobase-secret' -w 2>/dev/null)
export OAUTH2_SECRET_UTILITYVALET=$(security find-generic-password -a 'optimus' -s 'msgraph-utilityvalet-secret' -w 2>/dev/null)
export OAUTH2_SECRET_STARSHIP=$(security find-generic-password -a 'optimus' -s 'msgraph-starship-secret' -w 2>/dev/null)
export OAUTH2_SECRET_DALLASPARTNERS=$(security find-generic-password -a 'optimus' -s 'msgraph-dallaspartners-secret' -w 2>/dev/null)
export OAUTH2_SECRET_SPEARHEAD=$(security find-generic-password -a 'optimus' -s 'msgraph-spearhead-secret' -w 2>/dev/null)

# Verify we got them
loaded=0
[[ -n "$OAUTH2_SECRET_FLOBASE" ]] && ((loaded++)) || echo "⚠️  Flobase secret NOT loaded"
[[ -n "$OAUTH2_SECRET_UTILITYVALET" ]] && ((loaded++)) || echo "⚠️  Utility Valet secret NOT loaded"
[[ -n "$OAUTH2_SECRET_STARSHIP" ]] && ((loaded++)) || echo "⚠️  Starship secret NOT loaded"
[[ -n "$OAUTH2_SECRET_DALLASPARTNERS" ]] && ((loaded++)) || echo "⚠️  Dallas Partners secret NOT loaded"
[[ -n "$OAUTH2_SECRET_SPEARHEAD" ]] && ((loaded++)) || echo "⚠️  Spearhead secret NOT loaded"

echo "✅ Loaded $loaded/5 secrets"
echo ""
echo "To use in scripts, source this file:"
echo "  source ~/.openclaw/workspace/security-scripts/load-office365-secrets.sh"
