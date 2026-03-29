"""Subprocess provider for Codex CLI."""

from __future__ import annotations

import json
import subprocess
from json import JSONDecodeError
from typing import Any

from lee_llm_router.providers.base import FailureType, LLMRouterError
from lee_llm_router.response import LLMRequest, LLMResponse, LLMUsage


class CodexCLIProvider:
    """Invokes the Codex CLI via subprocess and returns its stdout."""

    name = "codex_cli"
    supported_types = {"codex_cli"}

    def validate_config(self, config: dict[str, Any]) -> None:
        command = config.get("command")
        if not isinstance(command, str) or not command.strip():
            raise LLMRouterError(
                "codex_cli provider missing required config key: 'command'",
                failure_type=FailureType.PROVIDER_ERROR,
            )
        args = config.get("args", [])
        if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
            raise LLMRouterError(
                "codex_cli provider key 'args' must be a list of strings",
                failure_type=FailureType.PROVIDER_ERROR,
            )
        response_format = str(config.get("response_format", "text"))
        if response_format not in {"text", "json"}:
            raise LLMRouterError(
                "codex_cli provider key 'response_format' must be 'text' or 'json'",
                failure_type=FailureType.PROVIDER_ERROR,
            )
        text_field = config.get("text_field")
        if text_field is not None and not isinstance(text_field, str):
            raise LLMRouterError(
                "codex_cli provider key 'text_field' must be a string",
                failure_type=FailureType.PROVIDER_ERROR,
            )
        for key in ("model_flag", "output_flag"):
            value = config.get(key)
            if value is not None and not isinstance(value, str):
                raise LLMRouterError(
                    f"codex_cli provider key {key!r} must be a string or null",
                    failure_type=FailureType.PROVIDER_ERROR,
                )

    def complete(self, request: LLMRequest, config: dict[str, Any]) -> LLMResponse:
        self.validate_config(config)

        command = config["command"]
        extra_args = list(config.get("args", []))
        model_flag = config.get("model_flag", "--model")
        output_flag = config.get("output_flag", "--output-last-message")
        timeout = request.timeout or float(config.get("timeout", 120.0))
        response_format = str(config.get("response_format", "text"))

        # Build prompt from last user message
        user_messages = [m for m in request.messages if m.get("role") == "user"]
        prompt = user_messages[-1]["content"] if user_messages else ""

        cmd = [command, *extra_args]
        if request.model and model_flag:
            cmd.extend([model_flag, request.model])
        if output_flag:
            cmd.append(output_flag)
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise LLMRouterError(
                f"Codex CLI timed out after {timeout}s",
                failure_type=FailureType.TIMEOUT,
                cause=exc,
            ) from exc
        except FileNotFoundError as exc:
            raise LLMRouterError(
                f"Codex CLI binary not found: {command!r}",
                failure_type=FailureType.PROVIDER_ERROR,
                cause=exc,
            ) from exc

        if result.returncode != 0:
            detail = _snippet(result.stderr) or _snippet(result.stdout) or "no output"
            raise LLMRouterError(
                f"Codex CLI exited {result.returncode}: {detail}",
                failure_type=FailureType.PROVIDER_ERROR,
            )

        return _build_response(
            request=request,
            result=result,
            command=cmd,
            response_format=response_format,
            text_field=config.get("text_field"),
        )


def _build_response(
    *,
    request: LLMRequest,
    result: subprocess.CompletedProcess[str],
    command: list[str],
    response_format: str,
    text_field: str | None,
) -> LLMResponse:
    stdout = result.stdout.strip()
    raw: dict[str, Any] = {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
        "command": command,
    }

    if response_format == "json":
        payload = _parse_json_payload(stdout)
        text = _extract_text(payload, text_field)
        raw["parsed"] = payload
        usage = _usage_from_payload(payload)
        model = str(payload.get("model") or request.model or "")
    else:
        if not stdout:
            raise LLMRouterError(
                "Codex CLI returned empty output",
                failure_type=FailureType.INVALID_RESPONSE,
            )
        text = stdout
        usage = LLMUsage()
        model = request.model

    return LLMResponse(
        text=text,
        raw=raw,
        usage=usage,
        request_id=request.request_id,
        model=model,
        provider="codex_cli",
    )


def _parse_json_payload(stdout: str) -> dict[str, Any]:
    if not stdout:
        raise LLMRouterError(
            "Codex CLI returned empty JSON output",
            failure_type=FailureType.CONTRACT_VIOLATION,
        )
    try:
        payload = json.loads(stdout)
    except JSONDecodeError as exc:
        raise LLMRouterError(
            "Codex CLI returned malformed JSON output",
            failure_type=FailureType.CONTRACT_VIOLATION,
            cause=exc,
        ) from exc
    if not isinstance(payload, dict):
        raise LLMRouterError(
            "Codex CLI JSON output must be an object",
            failure_type=FailureType.CONTRACT_VIOLATION,
        )
    return payload


def _extract_text(payload: dict[str, Any], text_field: str | None) -> str:
    candidate_fields = [text_field] if text_field else ["output_text", "text"]
    for field in candidate_fields:
        if not field:
            continue
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise LLMRouterError(
        "Codex CLI JSON output missing a non-empty response text field",
        failure_type=FailureType.CONTRACT_VIOLATION,
    )


def _usage_from_payload(payload: dict[str, Any]) -> LLMUsage:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return LLMUsage()
    prompt_tokens = _coerce_usage_value(
        usage.get("prompt_tokens", usage.get("input_tokens", 0)),
        field_name="prompt_tokens",
    )
    completion_tokens = _coerce_usage_value(
        usage.get("completion_tokens", usage.get("output_tokens", 0)),
        field_name="completion_tokens",
    )
    total_tokens = _coerce_usage_value(
        usage.get("total_tokens", prompt_tokens + completion_tokens),
        field_name="total_tokens",
    )
    return LLMUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def _coerce_usage_value(value: Any, *, field_name: str) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError) as exc:
        raise LLMRouterError(
            f"Codex CLI JSON usage field {field_name!r} must be an integer",
            failure_type=FailureType.CONTRACT_VIOLATION,
            cause=exc,
        ) from exc


def _snippet(text: str, limit: int = 200) -> str:
    normalized = " ".join(text.split())
    return normalized[:limit]
