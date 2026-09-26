"""Background process runner and job manager for Antigravity (AGY) CLI."""

from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class AgyJob:
    """Represents an Antigravity agent execution job."""

    job_id: str
    prompt: str
    command: list[str]
    status: str  # "pending", "running", "completed", "failed", "terminated"
    exit_code: int | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    output: str = ""
    target_entity_id: str | None = None
    continue_session: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class AgyRunnerManager:
    """Manages non-blocking background execution of bespoke agy commands."""

    def __init__(
        self,
        root_dir: str | Path = ".",
        agy_bin: str | None = None,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self._agy_bin = agy_bin
        self.jobs: dict[str, AgyJob] = {}
        self.processes: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def find_agy_binary(self) -> str:
        """Locates the agy CLI binary across system PATH and user environments."""
        if self._agy_bin:
            return self._agy_bin

        # Search standard PATH
        which_path = shutil.which("agy")
        if which_path:
            return which_path

        # Search standard user directories
        home = Path.home()
        candidates = [
            home / ".local" / "bin" / "agy",
            home / ".gemini" / "antigravity" / "bin" / "agy",
            Path("/usr/local/bin/agy"),
            Path("/usr/bin/agy"),
        ]
        for candidate in candidates:
            if candidate.exists() and os.access(candidate, os.X_OK):
                return str(candidate)

        return "agy"

    def launch_job(
        self,
        prompt: str,
        continue_session: bool = False,
        target_entity_id: str | None = None,
        cwd: str | Path | None = None,
        timeout_seconds: int = 1800,
    ) -> AgyJob:
        """Launches a bespoke agy execution job in a background thread."""
        clean_prompt = prompt.strip()
        if not clean_prompt:
            raise ValueError("Prompt cannot be empty")

        work_dir = Path(cwd).resolve() if cwd else self.root_dir
        agy_bin = self.find_agy_binary()

        cmd = [agy_bin, "--dangerously-skip-permissions"]
        if continue_session:
            cmd.append("-c")
        cmd.extend(["-p", clean_prompt])

        job_id = f"agy-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        job = AgyJob(
            job_id=job_id,
            prompt=clean_prompt,
            command=cmd,
            status="pending",
            target_entity_id=target_entity_id,
            continue_session=continue_session,
        )

        with self._lock:
            self.jobs[job_id] = job

        worker_thread = threading.Thread(
            target=self._execute_process,
            args=(job_id, cmd, work_dir, timeout_seconds),
            daemon=True,
        )
        worker_thread.start()
        return job

    def _execute_process(self, job_id: str, cmd: list[str], work_dir: Path, timeout: int) -> None:
        """Executes subprocess, capturing streaming output into job buffer."""
        job = self.jobs[job_id]
        job.status = "running"

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(work_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with self._lock:
                self.processes[job_id] = proc

            if proc.stdout:
                for line in iter(proc.stdout.readline, ""):
                    with self._lock:
                        job.output += line
                    if job.status == "terminated":
                        break
                proc.stdout.close()

            proc.wait(timeout=timeout)
            exit_code = proc.returncode

            with self._lock:
                job.end_time = time.time()
                job.exit_code = exit_code
                if job.status != "terminated":
                    job.status = "completed" if exit_code == 0 else "failed"

        except subprocess.TimeoutExpired:
            with self._lock:
                job.end_time = time.time()
                job.status = "failed"
                job.output += f"\n[Execution timed out after {timeout}s]\n"
        except Exception as exc:
            with self._lock:
                job.end_time = time.time()
                job.status = "failed"
                job.output += f"\n[Execution error: {exc}]\n"
        finally:
            with self._lock:
                self.processes.pop(job_id, None)

    def terminate_job(self, job_id: str) -> bool:
        """Terminates an active or pending agy job."""
        with self._lock:
            job = self.jobs.get(job_id)
            proc = self.processes.get(job_id)
            if not job:
                return False
            if job.status not in ("pending", "running"):
                return False

            job.status = "terminated"
            job.end_time = time.time()
            if proc and proc.poll() is None:
                with contextlib.suppress(Exception):
                    proc.terminate()
                    proc.wait(timeout=1.0)
                with contextlib.suppress(Exception):
                    if proc.poll() is None:
                        proc.kill()
            job.output += "\n[Process terminated by user]\n"
            return True

    def get_job(self, job_id: str) -> AgyJob | None:
        """Returns job by id if found."""
        with self._lock:
            return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> list[AgyJob]:
        """Returns recent jobs sorted by start_time descending."""
        with self._lock:
            sorted_jobs = sorted(self.jobs.values(), key=lambda j: j.start_time, reverse=True)
            return sorted_jobs[:limit]
