"""Harness-Commander CLI 入口。

该模块负责解析命令行参数、初始化日志并把请求转发到应用层。
为了满足产品规格要求，所有命令都同时支持文本输出和 JSON 输出。
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from harness_commander.application.commands import (
    execute_command,
    run_check,
    run_collect_evidence,
    run_distill,
    run_init,
    run_plan_check,
    run_propose_plan,
    run_sync,
)
from harness_commander.domain.models import CommandResult

LOGGER = logging.getLogger(__name__)


def add_path_argument(
    parser: argparse.ArgumentParser, *, default: str | object
) -> None:
    """为解析器补充统一的执行路径参数。"""

    parser.add_argument(
        "-p",
        "--root",
        dest="root",
        default=default,
        help="命令执行路径，默认使用当前工作目录",
    )


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""

    parser = argparse.ArgumentParser(
        prog="harness", description="Harness-Commander 统一命令入口"
    )
    add_path_argument(parser, default=".")
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="输出 JSON 结果"
    )
    parser.add_argument("--verbose", action="store_true", help="输出详细日志")

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化核心目录结构")
    add_path_argument(init_parser, default=argparse.SUPPRESS)
    init_parser.add_argument(
        "--dry-run", action="store_true", help="仅展示变更，不实际写入"
    )

    plan_parser = subparsers.add_parser("propose-plan", help="生成执行计划")
    add_path_argument(plan_parser, default=argparse.SUPPRESS)
    plan_parser.add_argument("--input", required=True, help="需要转化为计划的需求描述")
    plan_parser.add_argument(
        "--dry-run", action="store_true", help="仅展示变更，不实际写入"
    )

    check_parser = subparsers.add_parser("plan-check", help="校验执行计划")
    add_path_argument(check_parser, default=argparse.SUPPRESS)
    check_parser.add_argument("plan_path", help="待校验的计划文件路径")

    evidence_parser = subparsers.add_parser("collect-evidence", help="记录执行证据")
    add_path_argument(evidence_parser, default=argparse.SUPPRESS)
    evidence_parser.add_argument(
        "--command",
        required=True,
        dest="recorded_command",
        help="被记录的命令文本",
    )
    evidence_parser.add_argument(
        "--exit-code", type=int, default=0, help="被记录命令的退出码"
    )
    evidence_parser.add_argument("--summary", required=True, help="结果摘要")
    evidence_parser.add_argument("--status", default="success", help="被记录命令的状态")
    evidence_parser.add_argument(
        "--log",
        action="append",
        default=[],
        dest="logs",
        help="关键日志片段，可重复传入多次",
    )
    evidence_parser.add_argument(
        "--dry-run", action="store_true", help="仅展示变更，不实际写入"
    )

    sync_parser = subparsers.add_parser("sync", help="同步重大变更到文档目录")
    add_path_argument(sync_parser, default=argparse.SUPPRESS)
    sync_parser.add_argument(
        "--dry-run", action="store_true", help="仅展示变更，不实际写入"
    )

    distill_parser = subparsers.add_parser("distill", help="调用大模型能力将长文档压缩为参考材料")
    add_path_argument(distill_parser, default=argparse.SUPPRESS)
    distill_parser.add_argument("source", help="源文档路径")
    distill_parser.add_argument(
        "--dry-run", action="store_true", help="仅展示变更，不实际写入"
    )

    check_parser = subparsers.add_parser("check", help="检查项目结构与文档一致性")
    add_path_argument(check_parser, default=argparse.SUPPRESS)
    check_parser.add_argument(
        "--dry-run", action="store_true", help="仅展示检查结果，不自动修复"
    )

    return parser


def configure_logging(verbose: bool) -> None:
    """初始化日志配置。"""

    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    LOGGER.info("日志初始化完成 verbose=%s", verbose)


def render_result(result: CommandResult, *, as_json: bool) -> None:
    """根据输出模式渲染命令结果。"""

    if as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return
    print(result.to_text())


def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。

    该函数返回退出码，便于脚本调用和测试断言。
    """

    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    root = Path(getattr(args, "root", ".")).resolve()
    LOGGER.info("接收到 CLI 请求 command=%s root=%s", args.command, root)

    if args.command == "init":
        result = execute_command("init", run_init, root=root, dry_run=args.dry_run)
    elif args.command == "propose-plan":
        result = execute_command(
            "propose-plan",
            run_propose_plan,
            root=root,
            request=args.input,
            dry_run=args.dry_run,
        )
    elif args.command == "plan-check":
        result = execute_command(
            "plan-check",
            run_plan_check,
            root=root,
            plan_path=(
                (root / args.plan_path).resolve()
                if not Path(args.plan_path).is_absolute()
                else Path(args.plan_path)
            ),
        )
    elif args.command == "sync":
        result = execute_command(
            "sync",
            run_sync,
            root=root,
            dry_run=args.dry_run,
        )
    elif args.command == "distill":
        result = execute_command(
            "distill",
            run_distill,
            root=root,
            source_path=args.source,
            dry_run=args.dry_run,
        )
    elif args.command == "check":
        result = execute_command(
            "check",
            run_check,
            root=root,
            dry_run=args.dry_run,
        )
    else:
        result = execute_command(
            "collect-evidence",
            run_collect_evidence,
            root=root,
            command=args.recorded_command,
            exit_code=args.exit_code,
            summary=args.summary,
            status=args.status,
            log_lines=args.logs,
            dry_run=args.dry_run,
        )
    render_result(result, as_json=args.json_output)
    exit_code: int = result.exit_code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
