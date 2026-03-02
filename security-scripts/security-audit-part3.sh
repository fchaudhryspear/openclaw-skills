#Check for git repos with secrets

echo " Checking for git repositories..."
GIT_REPO_PATH="/Users/faisalshomemacmini/.openclaw/workspace" # Assuming workspace is the main git repo
if [ -d "$GIT_REPO_PATH/.git" ]; then
if [ ! -f "$GIT_REPO_PATH/.gitignore" ]; then
echo " ❌ CRITICAL: Git repo exists but no .gitignore in workspace!"
ISSUES=$((ISSUES + 1))
else
if grep -q "credentials\|.env" "$GIT_REPO_PATH/.gitignore"; then
echo " ✅ Git repo has proper .gitignore in workspace"
else
echo " ⚠️ WARNING: .gitignore in workspace may be incomplete (missing credentials or .env exclusion)"
WARNINGS=$((WARNINGS + 1))
fi
fi
else
echo " ✅ No git repository detected in workspace: $GIT_REPO_PATH"
fi
echo ""

echo "========================================"
echo "AUDIT SUMMARY"
echo "========================================"
echo "❌ Critical Issues: $ISSUES"
echo "⚠️ Warnings: $WARNINGS"
echo ""

if [ "$ISSUES" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
echo "🎉 EXCELLENT! No security issues found!"
exit 0
elif [ "$ISSUES" -eq 0 ]; then
echo "✅ GOOD! No critical issues, but $WARNINGS warning(s)"
exit 0
else
echo "🚨 ACTION REQUIRED! $ISSUES critical issue(s) must be fixed!"
exit 1
fi


