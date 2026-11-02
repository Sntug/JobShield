#!/usr/bin/env bash
# Local PostgreSQL 17 container drill; source DB is read-only, target is created per run.
set -euo pipefail
umask 077

POSTGRES_CONTAINER="jobshield-test-pg"
POSTGRES_USER="r11_review"
SOURCE_DB="${SOURCE_DB:-jobshield_r12_e2e_local}"
BACKUP_FILE="$(mktemp "${TMPDIR:-/tmp}/jobshield_drill.XXXXXXXX")"
TARGET_DRILL_DB="jobshield_restore_drill_${BACKUP_FILE##*.}"
TARGET_CREATED=0

psql_db() {
  docker exec --user postgres -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -X -qAt -v ON_ERROR_STOP=1 -d "$1" -c "$2"
}

cleanup() {
  local status=$?
  trap - EXIT
  echo -e "\n[CLEANUP] Đang dọn dẹp file dump và database thử nghiệm..."
  rm -f -- "$BACKUP_FILE" || true
  if (( TARGET_CREATED )); then
    psql_db postgres "DROP DATABASE \"$TARGET_DRILL_DB\";" >/dev/null 2>&1 || true
  fi
  echo "[CLEANUP] Hoàn tất dọn dẹp an toàn."
  exit "$status"
}
trap cleanup EXIT

echo "================================================================="
echo "    JobShield R6.2 Disaster Recovery & Restore Verification Drill"
echo " Container: $POSTGRES_CONTAINER"
echo " Source DB: $SOURCE_DB"
echo " Target Isolated DB: $TARGET_DRILL_DB"
echo "================================================================="

echo -e "\n[1/5] Đang xuất archive PostgreSQL custom format (pg_dump -Fc)..."
docker exec --user postgres -i "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$SOURCE_DB" -Fc --no-owner --no-privileges > "$BACKUP_FILE"
DUMP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
echo "  ✓ Xuất file dump thành công ($DUMP_SIZE bytes)"

echo -e "\n[2/5] Đang tạo database đích mới và phục hồi archive (pg_restore)..."
psql_db postgres "CREATE DATABASE \"$TARGET_DRILL_DB\";" >/dev/null
TARGET_CREATED=1
docker exec --user postgres -i "$POSTGRES_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$TARGET_DRILL_DB" --no-owner --no-privileges --single-transaction --exit-on-error < "$BACKUP_FILE"
echo "  ✓ Phục hồi hoàn tất với single-transaction an toàn"

echo -e "\n[3/5] Đang kiểm tra tính toàn vẹn dữ liệu..."
for table in analyses verified_employers risk_indicators; do
  source_count=$(psql_db "$SOURCE_DB" "SELECT COUNT(*) FROM public.\"$table\";")
  restored_count=$(psql_db "$TARGET_DRILL_DB" "SELECT COUNT(*) FROM public.\"$table\";")
  echo "  - $table: source=$source_count | restored=$restored_count"
  if [[ "$source_count" != "$restored_count" ]]; then
    echo "  ✗ LỖI: Số lượng bản ghi $table không khớp."
    exit 1
  fi
done

echo -e "\n[4/5] Đang so sánh khóa ngoại và kiểm tra bản ghi mồ côi..."
source_fk_count=$(psql_db "$SOURCE_DB" "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f' AND connamespace = 'public'::regnamespace;")
restored_fk_count=$(psql_db "$TARGET_DRILL_DB" "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f' AND connamespace = 'public'::regnamespace;")
if [[ "$source_fk_count" != "$restored_fk_count" ]]; then
  echo "  ✗ LỖI: Foreign key count không khớp (source=$source_fk_count, restored=$restored_fk_count)."
  exit 1
fi
orphan_claims=$(psql_db "$TARGET_DRILL_DB" "SELECT COUNT(*) FROM public.employer_claims ec LEFT JOIN public.verified_employers ve ON ve.id = ec.employer_id WHERE ec.employer_id IS NOT NULL AND ve.id IS NULL;")
if [[ "$orphan_claims" != "0" ]]; then
  echo "  ✗ LỖI: Phát hiện $orphan_claims claims mồ côi."
  exit 1
fi
echo "  ✓ Foreign keys: $restored_fk_count; orphan claims: 0"

echo -e "\n[5/5] Đang so sánh RLS và policy metadata..."
rls_sql=$(cat <<'SQL'
SELECT COALESCE(string_agg(
  format('%s|%s|%s|%s|%s|%s|%s|%s',
    c.relname, c.relrowsecurity, c.relforcerowsecurity, COALESCE(p.polname, ''),
    COALESCE(p.polcmd, ''),
    COALESCE((SELECT string_agg(
      CASE WHEN roles.role_oid = 0 THEN 'PUBLIC' ELSE pg_get_userbyid(roles.role_oid) END,
      ',' ORDER BY CASE WHEN roles.role_oid = 0 THEN 'PUBLIC' ELSE pg_get_userbyid(roles.role_oid) END
    ) FROM unnest(p.polroles) AS roles(role_oid)), ''),
    COALESCE(pg_get_expr(p.polqual, p.polrelid), ''),
    COALESCE(pg_get_expr(p.polwithcheck, p.polrelid), '')
  ), E'\n' ORDER BY c.relname, p.polname), '')
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_policy p ON p.polrelid = c.oid
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
  AND (c.relrowsecurity OR c.relforcerowsecurity OR p.oid IS NOT NULL);
SQL
)
source_rls=$(psql_db "$SOURCE_DB" "$rls_sql")
restored_rls=$(psql_db "$TARGET_DRILL_DB" "$rls_sql")
if [[ "$source_rls" != "$restored_rls" ]]; then
  echo "  ✗ LỖI: RLS/policy metadata không khớp."
  exit 1
fi
echo "  ✓ RLS và policy metadata khớp"

echo -e "\n================================================================="
echo "   KẾT QUẢ: DIỄN TẬP PHỤC HỒI THẢM HỌA R6.2 ĐẠT               "
echo "================================================================="
