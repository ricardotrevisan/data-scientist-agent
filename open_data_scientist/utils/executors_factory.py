from __future__ import annotations

import os
import requests
from typing import Any, Callable
from pathlib import Path

from open_data_scientist.utils.executors_internal import (
    delete_session_internal,
    execute_code_internal,
    upload_file_internal,
)


def execute_code_factory(executor_type: str, provider: str = "openai") -> Callable:
    if executor_type == "internal":
        base_url = os.getenv("CODE_INTERPRETER_URL", "http://localhost:8123")
        try:
            health_response = requests.get(f"{base_url}/health", timeout=5)
            if health_response.status_code != 200:
                raise requests.exceptions.RequestException("Health check failed")
        except requests.exceptions.RequestException:
            print(
                "No docker container available. Use '--executor tci --provider together' "
                "if you don't want to run the local container."
            )
            raise SystemExit(1)
        return execute_code_internal

    if executor_type == "tci":
        if provider != "together":
            raise ValueError(
                "Executor 'tci' requires provider 'together'."
            )
        from open_data_scientist.utils.executors_together import execute_code_tci

        return execute_code_tci

    raise ValueError(f"Unsupported code type: {executor_type}")


def create_session_with_data(
    executor_type: str,
    provider: str,
    data_dir: str | None,
) -> str | None:
    if not data_dir:
        return None

    if executor_type == "tci":
        if provider != "together":
            raise ValueError("Executor 'tci' requires provider 'together'.")
        from open_data_scientist.utils.executors_together import create_tci_session_with_data

        return create_tci_session_with_data(data_dir=data_dir)

    resolved_data = Path(data_dir).resolve()
    cwd = Path.cwd().resolve()

    mounted_workdir: str | None = None
    try:
        data_root = (cwd / "data").resolve()
        rel = resolved_data.relative_to(data_root)
        mounted_workdir = str(Path("/app/data") / rel)
    except ValueError:
        mounted_workdir = None

    if mounted_workdir:
        os.environ["ODS_INTERNAL_WORKDIR"] = mounted_workdir
        return None

    os.environ.pop("ODS_INTERNAL_WORKDIR", None)
    upload_result = upload_file_internal(data_dir)
    if not upload_result.get("success", False):
        error = upload_result.get("error", "Unknown upload error")
        raise ValueError(
            f"Failed to upload data directory '{data_dir}' to internal executor: {error}"
        )
    return None


def delete_session(executor_type: str, provider: str, session_id: str) -> dict[str, Any]:
    if executor_type == "internal":
        return delete_session_internal(session_id)

    if executor_type == "tci" and provider == "together":
        # Together TCI sessions are managed server-side.
        return {"success": True, "message": "TCI session cleanup delegated to provider", "session_id": session_id}

    return {"success": False, "error": "Unsupported session deletion path", "session_id": session_id}
