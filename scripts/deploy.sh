#!/bin/bash
# deploy.sh — 抓取内容 → 推送到 GitHub → Vercel 自动部署
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO="eileenics129-ops/neuron-daily"

echo "🧠 Neuron Daily — 开始更新 $(date '+%Y-%m-%d %H:%M:%S')"

cd "$PROJECT_DIR"

# 1. 抓取内容
echo "📡 Fetching content..."
python3 scripts/fetch.py

# 2. 检查是否有变化
if git diff --quiet public/data/latest.json 2>/dev/null; then
  echo "ℹ️  No changes in data, pushing anyway to trigger deploy."
fi

# 3. Git commit & push
echo "📦 Committing..."
git add public/data/ public/index.html
git commit -m "daily: $(date '+%Y-%m-%d') update" --allow-empty

echo "🚀 Pushing to GitHub..."
git push "https://${GITHUB_TOKEN}@github.com/${REPO}.git" main

echo "✅ Done! Vercel will auto-deploy in ~30s"
echo "   https://neuron-daily.vercel.app"
