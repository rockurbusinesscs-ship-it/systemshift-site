#!/bin/bash
# Deploy SystemShift site to Cloudflare Pages
# Usage: ./deploy.sh "commit message"

MSG="${1:-Update site}"

# Build blog (converts markdown posts to HTML, generates sitemap + llms.txt)
echo "Building blog..."
python build-blog.py

echo "Deploying..."
git add -A
git commit -m "$MSG"
git push origin master
npx wrangler pages deploy . --project-name systemshift-site --branch master --commit-dirty=true

echo ""
echo "Deployed to https://systemshifthq.com"
