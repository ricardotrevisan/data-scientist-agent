from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import base64
import requests


def collect_files(directory: str) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    path = Path(directory)

    if not path.exists():
        print(f"Directory '{directory}' does not exist, skipping file collection")
        return files

    for file_path in path.rglob("*"):
        if file_path.is_file() and not any(part.startswith(".") for part in file_path.parts):
            try:
                if file_path.suffix.lower() in [".csv", ".txt", ".json", ".py", ".log"]:
                    with open(file_path, "r", encoding="utf-8") as handle:
                        content = handle.read()
                    files.append(
                        {
                            "name": str(file_path.relative_to(directory)),
                            "encoding": "string",
                            "content": content,
                        }
                    )
                elif file_path.suffix.lower() in [".parquet"]:
                    with open(file_path, "rb") as handle:
                        content = base64.b64encode(handle.read()).decode("ascii")
                    files.append(
                        {
                            "name": str(file_path.relative_to(directory)),
                            "encoding": "base64",
                            "content": content,
                        }
                    )
                elif file_path.suffix.lower() in [".xlsx", ".xls"]:
                    print("Not uploading excel files")
            except (UnicodeDecodeError, PermissionError) as exc:
                print(f"Could not read file {file_path}: {exc}")

    return files


def execute_code_internal(
    code: str, session_id: str | None = None, files: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    if files:
        raise ValueError("Files are not supported for internal execution")

    base_url = os.getenv("CODE_INTERPRETER_URL", "http://localhost:8123")
    payload: dict[str, Any] = {"code": code}
    workdir = os.getenv("ODS_INTERNAL_WORKDIR")
    if workdir:
        payload["workdir"] = workdir

    if session_id:
        payload["session_id"] = session_id

    response = requests.post(f"{base_url}/execute", json=payload)
    response.raise_for_status()

    raw_response = response.json()

    execution_summary_input: dict[str, Any] = {}
    outputs_list: list[dict[str, Any]] = []
    errors_list: list[str] = []

    if raw_response.get("success"):
        execution_summary_input["status"] = "success"
        result_data = raw_response.get("result")

        if result_data is not None:
            if isinstance(result_data, dict) and any(
                k in result_data for k in ["image/png", "text/plain"]
            ):
                outputs_list.append({"type": "display_data", "data": result_data})
            elif isinstance(result_data, str) and result_data.startswith("data:image/png;base64,"):
                try:
                    b64_content = result_data.split(",", 1)[1]
                    outputs_list.append({"type": "display_data", "data": {"image/png": b64_content}})
                except IndexError:
                    outputs_list.append({"type": "stdout", "data": str(result_data)})
            else:
                outputs_list.append({"type": "stdout", "data": str(result_data)})
    else:
        execution_summary_input["status"] = "failure"
        error_message = raw_response.get("error")
        if error_message:
            errors_list.append(str(error_message))

    execution_summary_input["outputs"] = outputs_list
    execution_summary_input["errors"] = errors_list
    execution_summary_input["session_id"] = raw_response.get("session_id")

    return execution_summary_input


def upload_file_internal(
    files: list[dict[str, str]] | str, session_id: str | None = None
) -> dict[str, Any]:
    import base64
    import io

    if isinstance(files, str):
        directory_path = files
        files = collect_files(directory_path)

        if not files:
            return {
                "success": False,
                "uploaded_files": [],
                "error": f"No valid files found in directory: {directory_path}",
            }

    base_url = os.getenv("CODE_INTERPRETER_URL", "http://localhost:8123")
    url = f"{base_url}/upload"

    files_to_upload = []

    for file_info in files:
        file_name = file_info.get("name", "")
        file_encoding = file_info.get("encoding", "utf-8")
        file_content = file_info.get("content", "")

        if not file_name:
            continue

        if file_encoding == "base64":
            try:
                decoded_content = base64.b64decode(file_content)
                file_obj = io.BytesIO(decoded_content)
            except Exception as exc:
                return {
                    "success": False,
                    "uploaded_files": [],
                    "error": f"Failed to decode base64 content for {file_name}: {str(exc)}",
                }
        elif file_encoding == "string":
            file_obj = io.BytesIO(file_content.encode("utf-8"))
        else:
            file_obj = io.BytesIO(file_content.encode(file_encoding))

        files_to_upload.append(("files", (file_name, file_obj, "application/octet-stream")))

    try:
        response = requests.post(url, files=files_to_upload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        return {
            "success": False,
            "uploaded_files": [],
            "error": f"Upload request failed: {str(exc)}",
        }
    except Exception as exc:
        return {
            "success": False,
            "uploaded_files": [],
            "error": f"Upload failed: {str(exc)}",
        }
    finally:
        for _, file_tuple in files_to_upload:
            if len(file_tuple) >= 2:
                file_tuple[1].close()


def delete_session_internal(session_id: str) -> dict[str, Any]:
    base_url = os.getenv("CODE_INTERPRETER_URL", "http://localhost:8123")
    url = f"{base_url}/sessions/{session_id}"

    try:
        response = requests.delete(url)
        response.raise_for_status()

        return {
            "success": True,
            "message": "Session deleted successfully",
            "session_id": session_id,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": f"Failed to delete session: {str(exc)}",
            "session_id": session_id,
        }
