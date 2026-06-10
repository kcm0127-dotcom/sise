#!/bin/bash
# 일일 수집 + 빌드 + 배포 (cron 등록용)
# crontab 예시: 0 3 * * * /bin/bash "$HOME/Claude/Projects/App Develops/sise/deploy.sh" >> "$HOME/sise-deploy.log" 2>&1
set -e
cd "$(dirname "$0")"
python3 collector.py
python3 stats.py
python3 site_gen.py
git add -A
git diff --cached --quiet || git commit -m "daily build $(date +%F)"
git push
