#!/usr/bin/env bash
# VENOM Site Factory — 멀티사이트 1회 초기화
# 사용:  cd venom-wordpress/docker && ./multisite-setup.sh
set -euo pipefail

DC="docker compose"
WPCLI="$DC run --rm wp-cli"

echo "▶ 1) 컨테이너 기동"
$DC up -d db wordpress

echo "▶ 2) WordPress 코어 설치 대기"
until $WPCLI db check >/dev/null 2>&1; do sleep 3; done

echo "▶ 3) 코어 설치 (멀티사이트)"
$WPCLI core multisite-install \
  --url='localhost:8080' \
  --title='VENOM Network' \
  --admin_user='admin' \
  --admin_password='venom-admin-2024' \
  --admin_email='admin@venom.local' \
  --skip-config || echo '(이미 설치됨)'

echo "▶ 4) 베놈 테마 네트워크 활성화"
$WPCLI theme enable venom-theme --network --activate || true

echo ""
echo "✅ 멀티사이트 준비 완료"
echo "   관리자:  http://localhost:8080/wp-admin/network/  (admin / venom-admin-2024)"
echo ""
echo "다음: 고객 사이트 찍어내기"
echo "   node ../../auto-site-factory/engine/wp-adapter.js <spec>.json --write"
echo "   $DC run --rm wp-cli bash < ../../auto-site-factory/output/<slug>/provision.sh"
