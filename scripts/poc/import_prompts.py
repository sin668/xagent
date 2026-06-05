#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.prompt_import import PromptImportService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 prompts/*.md 幂等导入 llm_prompt_templates。")
    parser.add_argument("--prompt-dir", default=str(REPO_ROOT / "prompts"), help="Prompt markdown 目录。")
    parser.add_argument("--provider", default="file-baseline", help="写入 llm_prompt_templates.provider。")
    parser.add_argument("--model", default="prompt-md", help="写入 llm_prompt_templates.model。")
    parser.add_argument("--batch-id", default="phase5-file-prompt-baseline", help="写入 migration_batch_id。")
    parser.add_argument("--dry-run", action="store_true", help="只输出迁移报告，不写入数据库。")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    async with AsyncSessionLocal() as async_session:
        def run(sync_session):
            result = PromptImportService(sync_session).import_prompt_directory(
                Path(args.prompt_dir),
                repo_root=REPO_ROOT,
                provider=args.provider,
                model=args.model,
                migration_batch_id=args.batch_id,
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                sync_session.commit()
            return result

        result = await async_session.run_sync(run)

    print("迁移报告")
    print(
        json.dumps(
            {
                "dry_run": result.dry_run,
                "migration_batch_id": result.migration_batch_id,
                "scanned_count": result.scanned_count,
                "planned_count": result.planned_count,
                "created_count": result.created_count,
                "skipped_count": result.skipped_count,
                "items": [item.__dict__ for item in result.items],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(main()))
