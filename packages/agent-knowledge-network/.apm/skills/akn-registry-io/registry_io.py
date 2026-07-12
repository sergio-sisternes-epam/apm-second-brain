#!/usr/bin/env python3
"""
registry_io.py -- Agent Knowledge Network registry I/O helper.

Accepts a JSON operation on stdin, performs the requested action on the
registry file, and returns a JSON result on stdout.

Usage:
    echo '{"op": "read", "payload": {}}' | python3 registry_io.py

Operations: read, list, upsert, delete
"""

from __future__ import annotations

import fcntl
import json
import os
import stat
import sys
import time
from pathlib import Path
from typing import Any

ALLOWED_OPS = frozenset({"read", "list", "upsert", "delete"})
SCHEMA_VERSION = "1"
LOCK_TIMEOUT = 5.0  # seconds


def registry_path() -> Path:
    apm_home = os.environ.get("APM_HOME", str(Path.home() / ".apm"))
    return Path(apm_home) / "agent-knowledge-network" / "registry.json"


def empty_registry() -> dict[str, Any]:
    return {"schemaVersion": SCHEMA_VERSION, "revision": 0, "agents": []}


def ok(result: Any) -> str:
    return json.dumps({"ok": True, "result": result})


def err(message: str) -> str:
    return json.dumps({"ok": False, "error": message})


def read_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_registry()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Failed to read registry: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Registry is not a JSON object")
    return data


def write_registry(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
        tmp.rename(path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"Failed to write registry: {exc}") from exc
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


class RegistryLock:
    """Advisory lock via a .lock file using fcntl for atomicity."""

    def __init__(self, path: Path, timeout: float = LOCK_TIMEOUT) -> None:
        self._lock_path = path.with_suffix(".lock")
        self._timeout = timeout
        self._fd: int | None = None

    def acquire(self) -> None:
        deadline = time.monotonic() + self._timeout
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                fd = os.open(
                    str(self._lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                os.write(fd, str(os.getpid()).encode())
                self._fd = fd
                return
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(
                        f"Could not acquire registry lock within {self._timeout}s"
                    )
                time.sleep(0.1)

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            self._lock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def __enter__(self) -> "RegistryLock":
        self.acquire()
        return self

    def __exit__(self, *_: Any) -> None:
        self.release()


def handle_read(path: Path, _payload: dict[str, Any]) -> str:
    data = read_registry(path)
    return ok(data)


def handle_upsert(path: Path, payload: dict[str, Any]) -> str:
    if "expectedRevision" not in payload:
        return err("upsert requires 'expectedRevision' in payload")
    if "agents" not in payload:
        return err("upsert requires 'agents' in payload")
    if not isinstance(payload["agents"], list):
        return err("'agents' must be a list")

    with RegistryLock(path):
        data = read_registry(path)

        schema = data.get("schemaVersion")
        if schema is not None and schema != SCHEMA_VERSION:
            return err(f"incompatible-schema: found '{schema}', expected '{SCHEMA_VERSION}'")

        stored_rev = data.get("revision", 0)
        expected_rev = payload["expectedRevision"]
        if stored_rev != expected_rev:
            return err(f"stale-revision: expected {expected_rev}, found {stored_rev}")

        data["schemaVersion"] = SCHEMA_VERSION
        data["revision"] = stored_rev + 1
        data["agents"] = payload["agents"]

        write_registry(path, data)
        return ok({"revision": data["revision"]})


def handle_delete(path: Path, payload: dict[str, Any]) -> str:
    if "expectedRevision" not in payload:
        return err("delete requires 'expectedRevision' in payload")
    if "agentId" not in payload:
        return err("delete requires 'agentId' in payload")

    agent_id = payload["agentId"]

    with RegistryLock(path):
        data = read_registry(path)

        schema = data.get("schemaVersion")
        if schema is not None and schema != SCHEMA_VERSION:
            return err(f"incompatible-schema: found '{schema}', expected '{SCHEMA_VERSION}'")

        stored_rev = data.get("revision", 0)
        expected_rev = payload["expectedRevision"]
        if stored_rev != expected_rev:
            return err(f"stale-revision: expected {expected_rev}, found {stored_rev}")

        agents = data.get("agents", [])
        original_count = len(agents)
        agents = [a for a in agents if a.get("agentId") != agent_id]
        if len(agents) == original_count:
            return err(f"agent-not-found: no agent with agentId '{agent_id}'")

        data["revision"] = stored_rev + 1
        data["agents"] = agents

        write_registry(path, data)
        return ok({"revision": data["revision"], "removed": agent_id})


def main() -> None:
    raw = sys.stdin.read().strip()
    if not raw:
        print(err("empty input"), flush=True)
        return

    try:
        operation = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(err(f"malformed JSON input: {exc}"), flush=True)
        return

    if not isinstance(operation, dict):
        print(err("input must be a JSON object"), flush=True)
        return

    op = operation.get("op")
    payload = operation.get("payload", {})

    if op not in ALLOWED_OPS:
        print(err(f"unknown op '{op}'; allowed: {sorted(ALLOWED_OPS)}"), flush=True)
        return

    if not isinstance(payload, dict):
        print(err("'payload' must be a JSON object"), flush=True)
        return

    path = registry_path()

    try:
        if op in ("read", "list"):
            result = handle_read(path, payload)
        elif op == "upsert":
            result = handle_upsert(path, payload)
        elif op == "delete":
            result = handle_delete(path, payload)
        else:
            result = err(f"unhandled op '{op}'")
    except TimeoutError as exc:
        result = err(str(exc))
    except ValueError as exc:
        result = err(str(exc))
    except Exception as exc:  # noqa: BLE001
        result = err(f"unexpected error: {exc}")

    print(result, flush=True)


if __name__ == "__main__":
    main()
