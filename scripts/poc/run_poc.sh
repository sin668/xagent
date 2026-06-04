#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

NODE_BIN="${NODE_BIN:-/Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node}"
PYTHON_BIN="${PYTHON_BIN:-/Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
NODE_MODULES_DIR="${NODE_MODULES_DIR:-/Users/linhuanbin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules}"

usage() {
  cat <<'USAGE'
PoC runner for 俄罗斯车辆采购 AI 获客系统

Usage:
  scripts/poc/run_poc.sh all
  scripts/poc/run_poc.sh build
  scripts/poc/run_poc.sh test
  scripts/poc/run_poc.sh check
  scripts/poc/run_poc.sh validate path/to/leads.csv [path/to/report.json]

Commands:
  all       Build all Excel artifacts, run tests, and check required docs.
  build     Regenerate PoC Excel artifacts.
  test      Run Python unit tests for CSV validation/dedupe.
  check     Verify required PoC docs, prompts, scripts, and outputs exist.
  validate  Validate a lead CSV and write JSON report.

Environment overrides:
  NODE_BIN          Path to Node.js.
  PYTHON_BIN        Path to Python 3.
  NODE_MODULES_DIR  Path to node_modules containing @oai/artifact-tool.
USAGE
}

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

ensure_runtime() {
  [[ -x "$NODE_BIN" ]] || die "Node.js not found or not executable: $NODE_BIN"
  [[ -x "$PYTHON_BIN" ]] || die "Python not found or not executable: $PYTHON_BIN"

  if [[ ! -e node_modules ]]; then
    ln -s "$NODE_MODULES_DIR" node_modules
    log "Linked node_modules -> $NODE_MODULES_DIR"
  fi
}

build_artifacts() {
  ensure_runtime
  log "Regenerating Feishu five-table seed workbooks"
  "$NODE_BIN" scripts/poc/build_feishu_seed_workbook.mjs

  log "Regenerating Russian keyword library workbook"
  "$NODE_BIN" scripts/poc/build_russian_keyword_library_workbook.mjs

  log "Regenerating FAQ and outreach workbook"
  "$NODE_BIN" scripts/poc/build_faq_outreach_workbook.mjs
}

run_tests() {
  ensure_runtime
  log "Running CSV validation unit tests"
  "$PYTHON_BIN" -m unittest tests/scripts/poc/test_validate_leads.py
}

validate_csv() {
  ensure_runtime
  local csv_path="${1:-}"
  local report_path="${2:-outputs/poc-validation/lead-validation-report.json}"
  [[ -n "$csv_path" ]] || die "validate requires a CSV path"
  [[ -f "$csv_path" ]] || die "CSV file not found: $csv_path"

  log "Validating lead CSV: $csv_path"
  "$PYTHON_BIN" scripts/poc/validate_leads.py "$csv_path" --output "$report_path"
  log "Validation report written to: $report_path"
}

check_required_files() {
  local required_files=(
    "docs/poc/feishu-fields.md"
    "docs/poc/channel-risk-register.md"
    "docs/poc/russian-keyword-library.md"
    "docs/poc/faq-and-outreach-templates.md"
    "docs/poc/ai-output-schema.md"
    "docs/poc/poc-retro-template.md"
    "docs/poc/manual-dashboard-metrics.md"
    "prompts/lead-extraction.md"
    "prompts/lead-grading.md"
    "scripts/poc/validate_leads.py"
    "tests/scripts/poc/test_validate_leads.py"
    "outputs/poc-feishu-seed/俄罗斯车辆采购AI获客PoC-飞书五张表Seed数据.xlsx"
    "outputs/poc-feishu-seed/客户线索.xlsx"
    "outputs/poc-feishu-seed/渠道来源.xlsx"
    "outputs/poc-feishu-seed/车源报价.xlsx"
    "outputs/poc-feishu-seed/触达记录.xlsx"
    "outputs/poc-feishu-seed/话术库.xlsx"
    "outputs/poc-keywords/俄罗斯车商线索关键词库初版.xlsx"
    "outputs/poc-faq/FAQ与俄语触达模板初版.xlsx"
  )

  log "Checking required PoC files"
  local missing=0
  for path in "${required_files[@]}"; do
    if [[ -f "$path" ]]; then
      printf 'OK      %s\n' "$path"
    else
      printf 'MISSING %s\n' "$path"
      missing=1
    fi
  done
  [[ "$missing" -eq 0 ]] || die "Required PoC files are missing"
}

main() {
  local command="${1:-}"
  case "$command" in
    all)
      build_artifacts
      run_tests
      check_required_files
      log "PoC local deployment bundle is ready"
      ;;
    build)
      build_artifacts
      ;;
    test)
      run_tests
      ;;
    check)
      check_required_files
      ;;
    validate)
      shift
      validate_csv "$@"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      usage
      die "Unknown command: $command"
      ;;
  esac
}

main "$@"
