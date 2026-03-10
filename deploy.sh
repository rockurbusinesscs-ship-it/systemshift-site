#!/bin/bash
# Deploy SystemShift site to Cloudflare Pages
# Usage: ./deploy.sh "commit message"
#
# This script:
# 1. Builds blog (markdown -> HTML, regenerates sitemap + llms.txt + robots.txt)
# 2. Commits and pushes to GitHub
# 3. Deploys to Cloudflare Pages
# 4. Pings Google to re-crawl the sitemap

MSG="${1:-Update site}"

# Build blog + sitemap
echo "Building blog & sitemap..."
python build-blog.py

# Deploy
echo "Deploying..."
git add -A
git commit -m "$MSG"
git push origin master
npx wrangler pages deploy . --project-name systemshift-site --branch master --commit-dirty=true

# Ping Google to re-crawl sitemap
echo ""
echo "Pinging Google to re-crawl sitemap..."
curl -s "https://www.google.com/ping?sitemap=https://systemshifthq.com/sitemap.xml" > /dev/null 2>&1 && echo "Google pinged." || echo "Google ping failed (non-critical)."

echo ""
echo "Deployed to https://systemshifthq.com"
echo "Sitemap: https://systemshifthq.com/sitemap.xml"
