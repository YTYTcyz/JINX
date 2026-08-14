#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
docker compose -f docker/docker-compose.yml up --build -d

echo
echo "JINX 已启动"
echo "访问地址：http://localhost:3788"
