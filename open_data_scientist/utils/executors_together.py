from __future__ import annotations

from typing import Any, Optional
import os

from open_data_scientist.utils.executors_internal import collect_files


def _get_together_client():
    try:
        from together import Client
    except ImportError as exc:
        raise RuntimeError(
            "Together SDK not installed. Install optional dependency with: pip install 'open-data-scientist[together]'"
        ) from exc
    return Client()


def create_tci_session_with_data(data_dir: Optional[str] = None) -> Optional[str]:
    session_id = None

    if data_dir and os.path.exists(data_dir):
        print(f"📁 Collecting files from {data_dir}...")
        files = collect_files(data_dir)

        if files:
            print(f"📤 Found {len(files)} files. Initializing session with uploaded files...")
            init_result = upload_files_tci(files)
            print(init_result)

            if init_result and "session_id" in init_result:
                session_id = init_result["session_id"]
                print(f"✅ Session initialized with ID: {session_id}")
            else:
                print("⚠️ Failed to get session ID, continuing without persistent session")
        else:
            print("📂 No valid files found in directory")

    return session_id


def execute_code_tci(code: str, session_id: Optional[str] = None) -> dict[str, Any]:
    try:
        code_interpreter = _get_together_client().code_interpreter
        additional_args: dict[str, Any] = {"code": code, "language": "python"}

        if session_id:
            additional_args["session_id"] = session_id

        response = code_interpreter.run(**additional_args)

        result: dict[str, Any] = {
            "session_id": response.data.session_id,
            "status": response.data.status,
            "outputs": [],
        }

        for output in response.data.outputs:
            result["outputs"].append({"type": output.type, "data": output.data})

        if response.data.errors:
            result["errors"] = response.data.errors

        return result
    except Exception as exc:
        return {"status": "error", "error_message": str(exc), "session_id": None}


def upload_files_tci(
    files: list[dict[str, str]], session_id: Optional[str] = None
) -> dict[str, Any]:
    try:
        code_interpreter = _get_together_client().code_interpreter
        additional_args: dict[str, Any] = {
            "code": 'print("Uploading files...")',
            "files": files,
            "language": "python",
        }

        if session_id:
            additional_args["session_id"] = session_id

        response = code_interpreter.run(**additional_args)

        result: dict[str, Any] = {
            "session_id": response.data.session_id,
            "status": response.data.status,
            "outputs": [],
        }

        for output in response.data.outputs:
            result["outputs"].append({"type": output.type, "data": output.data})

        if response.data.errors:
            result["errors"] = response.data.errors

        return result
    except Exception as exc:
        return {"status": "error", "error_message": str(exc), "session_id": None}
