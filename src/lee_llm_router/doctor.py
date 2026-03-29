"""Doctor CLI - config validation, environment diagnostics, and source export.

Commands:
    lee-llm-router doctor --config <path> [--role <role>]
    lee-llm-router template
    lee-llm-router trace --last N
    lee-llm-router export-source --dest <path> [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_NAME = ".lee_llm_router_export.json"


def check_config(
    config_path: str,
    role: str | None = None,
) -> tuple[list[str], list[str]]:
    """Validate a config file and its environment.

    Returns:
        (errors, warnings) - errors are blocking; warnings are informational.
    """
    from lee_llm_router.config import ConfigError, load_config
    from lee_llm_router.providers.base import LLMRouterError
    from lee_llm_router.providers.registry import get as get_provider

    errors: list[str] = []
    warnings: list[str] = []

    try:
        config = load_config(config_path)
    except ConfigError as exc:
        return [f"Config invalid: {exc}"], []
    except Exception as exc:
        return [f"Unexpected error loading config: {exc}"], []

    for pname, pcfg in config.providers.items():
        try:
            provider = get_provider(pcfg.type)()
            provider.validate_config(pcfg.raw)
        except KeyError:
            warnings.append(
                f"Provider {pname!r}: unknown type {pcfg.type!r} - cannot validate"
            )
            continue
        except LLMRouterError as exc:
            errors.append(f"Provider {pname!r}: {exc}")
            continue

        if pcfg.type in ("openrouter_http", "openai_http"):
            api_key_env = pcfg.raw.get("api_key_env")
            if api_key_env and not os.environ.get(api_key_env):
                errors.append(f"Provider {pname!r}: env var {api_key_env!r} is not set")
            if not pcfg.raw.get("base_url"):
                warnings.append(
                    f"Provider {pname!r}: 'base_url' not set - will use default"
                )

        elif pcfg.type == "codex_cli":
            command = pcfg.raw.get("command", "codex")
            if not shutil.which(command):
                errors.append(
                    f"Provider {pname!r}: binary {command!r} not found in PATH"
                )

        elif pcfg.type in (
            "openai_codex_subscription_http",
            "openai_codex_http",
            "chatgpt_subscription_http",
        ):
            access_token_env = pcfg.raw.get("access_token_env")
            if access_token_env:
                if not os.environ.get(access_token_env):
                    errors.append(
                        f"Provider {pname!r}: env var {access_token_env!r} is not set"
                    )
            else:
                codex_home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()
                auth_path = codex_home / "auth.json"
                if not auth_path.exists():
                    warnings.append(
                        "Provider "
                        f"{pname!r}: no access_token_env set and no auth file found at "
                        f"{auth_path}"
                    )

        elif pcfg.type == "mock":
            pass

    target_role = role or config.default_role
    if target_role not in config.roles:
        errors.append(
            f"Role {target_role!r} not found in config. "
            f"Known roles: {', '.join(sorted(config.roles))}"
        )
        return errors, warnings

    try:
        role_cfg = config.roles[target_role]
        provider_cfg = config.providers[role_cfg.provider]
        get_provider(provider_cfg.type)
    except KeyError as exc:
        errors.append(f"Role {target_role!r} references an unknown provider: {exc}")

    return errors, warnings


def get_template() -> str:
    """Return the contents of the bundled llm.example.yaml."""
    template_path = Path(__file__).parent / "templates" / "llm.example.yaml"
    return template_path.read_text(encoding="utf-8")


def export_source(dest: str | Path, force: bool = False) -> dict[str, str | None]:
    """Export the package tree as a vendorable source snapshot."""
    from lee_llm_router import __version__

    package_root = Path(__file__).resolve().parent
    repo_root = package_root.parent.parent
    destination = Path(dest).expanduser().resolve()

    if destination.exists() and not destination.is_dir():
        raise ValueError(f"Destination exists and is not a directory: {destination}")

    if destination.exists() and any(destination.iterdir()):
        if not force:
            raise FileExistsError(
                f"Destination is not empty: {destination}. "
                "Re-run with --force to overwrite."
            )
        shutil.rmtree(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        package_root,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )

    manifest = {
        "package": "lee_llm_router",
        "version": __version__,
        "source_repo": str(repo_root),
        "source_subdir": "src/lee_llm_router",
        "source_commit": _get_git_commit(repo_root),
        "exported_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    manifest_path = destination / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    return {
        "destination": str(destination),
        "manifest": str(manifest_path),
        "version": __version__,
        "source_commit": manifest["source_commit"],
    }


def _get_git_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit or None


def _run_doctor(args: argparse.Namespace) -> int:
    config_path = args.config
    role = getattr(args, "role", None)

    print("Lee LLM Router Doctor")
    print(f"Config: {config_path}")
    print()

    errors, warnings = check_config(config_path, role)

    for warning in warnings:
        print(f"  !  {warning}")
    for error in errors:
        print(f"  x  {error}", file=sys.stderr)

    if not errors and not warnings:
        print("  OK  All checks passed")
    elif not errors:
        print(f"\n  OK  {len(warnings)} warning(s) - no blocking errors")

    if errors:
        print(f"\nStatus: {len(errors)} error(s) found", file=sys.stderr)
        return 1

    return 0


def _run_template(_args: argparse.Namespace) -> int:
    print(get_template(), end="")
    return 0


def _run_trace(args: argparse.Namespace) -> int:
    trace_dir = Path(args.dir) if args.dir else Path(".lee-llm-router") / "traces"
    n = args.last

    if not trace_dir.exists():
        print(f"No trace directory found: {trace_dir}", file=sys.stderr)
        return 1

    trace_files = sorted(
        trace_dir.rglob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if not trace_files:
        print("No traces found.")
        return 0

    for trace_file in trace_files[:n]:
        try:
            data = json.loads(trace_file.read_text(encoding="utf-8"))
            status = "ERROR" if data.get("error") else "OK"
            elapsed = f"{data.get('elapsed_ms') or 0:.0f}ms"
            attempt = int(data.get("attempt", 0) or 0)
            print(
                f"{str(data.get('request_id', '?'))[:8]}  "
                f"{str(data.get('started_at', '?'))[:19]}  "
                f"{str(data.get('role', '?')):<12}  "
                f"{str(data.get('provider', '?')):<20}  "
                f"a{attempt:<5}  "
                f"{str(data.get('model', '?')):<20}  "
                f"{status:<6}  {elapsed}"
            )
        except Exception as exc:
            print(f"  [could not parse {trace_file}: {exc}]", file=sys.stderr)

    return 0


def _run_export_source(args: argparse.Namespace) -> int:
    try:
        result = export_source(args.dest, force=args.force)
    except (FileExistsError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Lee LLM Router Source Export")
    print(f"Destination: {result['destination']}")
    print(f"Manifest: {result['manifest']}")
    print(f"Version: {result['version']}")
    print(f"Source commit: {result['source_commit'] or 'unknown'}")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="lee-llm-router",
        description="Lee LLM Router CLI tools",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Validate config file and environment; exit 0 if healthy",
    )
    doctor_parser.add_argument(
        "--config",
        required=True,
        metavar="PATH",
        help="Path to config YAML",
    )
    doctor_parser.add_argument(
        "--role",
        metavar="ROLE",
        help="Role to dry-run (default: config.default_role)",
    )
    doctor_parser.set_defaults(func=_run_doctor)

    template_parser = subparsers.add_parser(
        "template",
        help="Print example config YAML to stdout",
    )
    template_parser.set_defaults(func=_run_template)

    trace_parser = subparsers.add_parser(
        "trace",
        help="Show recent trace summaries",
    )
    trace_parser.add_argument(
        "--last",
        type=int,
        default=10,
        metavar="N",
        help="Number of traces to show (default: 10)",
    )
    trace_parser.add_argument(
        "--dir",
        metavar="DIR",
        default=None,
        help="Trace directory (default: .lee-llm-router/traces)",
    )
    trace_parser.set_defaults(func=_run_trace)

    export_parser = subparsers.add_parser(
        "export-source",
        help="Export the package as a vendorable source snapshot",
    )
    export_parser.add_argument(
        "--dest",
        required=True,
        metavar="PATH",
        help="Destination directory for the vendored lee_llm_router package",
    )
    export_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite a non-empty destination directory",
    )
    export_parser.set_defaults(func=_run_export_source)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
