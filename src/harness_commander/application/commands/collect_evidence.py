"""collect-evidence 命令应用层编排。"""

from __future__ import annotations

import logging
from pathlib import Path

from harness_commander.domain.models import CommandMessage, CommandResult, ResultStatus
from harness_commander.infrastructure.filesystem import (
    ensure_directory,
    next_available_path,
    slugify,
    utc_timestamp_precise,
    write_json,
)

LOGGER = logging.getLogger(__name__)


def run_collect_evidence(
    root: Path,
    *,
    command: str,
    exit_code: int,
    summary: str,
    status: str,
    log_lines: list[str],
    started_at: str | None,
    finished_at: str | None,
    artifact_paths: list[str],
    dry_run: bool,
) -> CommandResult:
    """生成命令执行证据文件。"""

    LOGGER.info(
        "开始执行 collect-evidence 命令 root=%s command=%s exit_code=%s status=%s dry_run=%s",
        root,
        command,
        exit_code,
        status,
        dry_run,
    )
    evidence_directory = root / "docs/generated/evidence"
    directory_artifact = ensure_directory(evidence_directory, dry_run=dry_run)
    recorded_started_at = started_at or utc_timestamp_precise()
    recorded_finished_at = finished_at or utc_timestamp_precise()
    safe_timestamp = recorded_started_at.replace(":", "-")
    evidence_name = f"{safe_timestamp}-{slugify(command, fallback='command')}.json"
    evidence_path = next_available_path(evidence_directory / evidence_name)
    payload = {
        "command": command,
        "status": status,
        "summary": summary,
        "exit_code": exit_code,
        "started_at": recorded_started_at,
        "finished_at": recorded_finished_at,
        "logs": log_lines,
        "artifacts": artifact_paths,
    }
    file_artifact = write_json(evidence_path, payload, dry_run=dry_run)
    result_status = ResultStatus.SUCCESS if exit_code == 0 else ResultStatus.WARNING
    result_summary = (
        "证据记录完成，已保留执行事实、时间范围、关键日志和产物路径。"
        if exit_code == 0
        else "证据记录完成，但被记录命令本身为失败状态。"
    )
    warnings = []
    if exit_code != 0:
        warnings.append(
            CommandMessage(
                code="captured_failed_execution",
                message="证据已保留，但被记录的命令返回了非零退出码。",
                detail={"exit_code": exit_code},
            )
        )
    LOGGER.info(
        "collect-evidence 命令执行完成 root=%s evidence_path=%s result_status=%s",
        root,
        evidence_path,
        result_status.value,
    )
    return CommandResult(
        command="collect-evidence",
        status=result_status,
        summary=result_summary,
        artifacts=[directory_artifact, file_artifact],
        warnings=warnings,
        meta={
            "root": str(root),
            "evidence_path": str(evidence_path),
            "dry_run": dry_run,
            "record": payload,
        },
    )
