"""Dynamic development HTTP server for project visualizer with AGY runner."""

from __future__ import annotations

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path

from tools.project_visualizer.agy_runner import AgyRunnerManager
from tools.project_visualizer.generator import ProjectVisualizerGenerator

__all__ = [
    "BaseHTTPRequestHandler",
    "HTTPServer",
    "ThreadingHTTPServer",
    "ProjectVisualizerHandler",
    "run_server",
]


class ProjectVisualizerHandler(BaseHTTPRequestHandler):
    generator: ProjectVisualizerGenerator
    agy_runner: AgyRunnerManager | None = None

    def get_agy_runner(self) -> AgyRunnerManager:
        if self.agy_runner is None:
            self.agy_runner = AgyRunnerManager(self.generator.root_dir)
        return self.agy_runner

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = self.generator.generate_html(is_live_server=True)
            self.wfile.write(html.encode("utf-8"))
            return

        elif path == "/api/data":
            data = self.generator.get_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            if data.data_hash:
                self.send_header("ETag", f'"{data.data_hash}"')
            self.end_headers()
            self.wfile.write(json.dumps(data.to_dict(), default=str).encode("utf-8"))
            return

        elif path == "/api/version":
            data = self.generator.get_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "data_hash": data.data_hash,
                        "last_updated": data.last_updated,
                    }
                ).encode("utf-8")
            )
            return

        elif path == "/api/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = self.generator.get_data()
            self.wfile.write(
                json.dumps({"status": "ok", "metrics": data.metrics.__dict__}).encode("utf-8")
            )
            return

        elif path == "/api/file":
            target_file = query.get("path", [""])[0]
            if not target_file:
                self.send_error(400, "Missing path parameter")
                return

            full_path = (self.generator.root_dir / target_file).resolve()
            if not str(full_path).startswith(str(self.generator.root_dir)):
                self.send_error(403, "Access denied")
                return

            if not full_path.exists():
                self.send_error(404, "File not found")
                return

            content = full_path.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
            return

        elif path == "/api/agy/jobs":
            runner = self.get_agy_runner()
            jobs = [j.to_dict() for j in runner.list_jobs()]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"jobs": jobs}, default=str).encode("utf-8"))
            return

        elif path == "/api/agy/status":
            job_id = query.get("job_id", [""])[0]
            if not job_id:
                self.send_error(400, "Missing job_id parameter")
                return
            runner = self.get_agy_runner()
            job = runner.get_job(job_id)
            if not job:
                self.send_error(404, "Job not found")
                return
            try:
                offset = int(query.get("offset", ["0"])[0])
            except ValueError:
                offset = 0

            chunk = job.output[offset:]
            payload = {
                "job": job.to_dict(),
                "output_chunk": chunk,
                "next_offset": len(job.output),
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload, default=str).encode("utf-8"))
            return

        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self.send_error(400, "Invalid JSON payload")
            return

        if path == "/api/agy/launch":
            prompt = data.get("prompt", "")
            if not prompt or not isinstance(prompt, str) or not prompt.strip():
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Prompt cannot be empty"}).encode("utf-8"))
                return

            runner = self.get_agy_runner()
            try:
                job = runner.launch_job(
                    prompt=prompt,
                    continue_session=bool(data.get("continue_session", False)),
                    target_entity_id=data.get("target_entity_id"),
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"status": "ok", "job": job.to_dict()}, default=str).encode("utf-8")
                )
            except Exception as exc:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(exc)}).encode("utf-8"))
            return

        elif path == "/api/agy/terminate":
            job_id = data.get("job_id", "")
            if not job_id:
                self.send_error(400, "Missing job_id parameter")
                return

            runner = self.get_agy_runner()
            job = runner.get_job(job_id)
            if not job:
                self.send_error(404, "Job not found")
                return

            terminated = runner.terminate_job(job_id)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "ok",
                        "terminated": terminated,
                        "job": job.to_dict(),
                    },
                    default=str,
                ).encode("utf-8")
            )
            return

        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args: object) -> None:
        # Keep server quiet during operation
        pass


def run_server(root_dir: str | Path = ".", host: str = "127.0.0.1", port: int = 8787) -> None:
    """Run dynamic project visualizer server with ThreadingHTTPServer."""
    generator = ProjectVisualizerGenerator(root_dir)
    agy_runner = AgyRunnerManager(root_dir)
    handler_class = type(
        "ConfiguredHandler",
        (ProjectVisualizerHandler,),
        {"generator": generator, "agy_runner": agy_runner},
    )

    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"⚡ Runefoble Project Visualizer running at http://{host}:{port}/")
    print(f"   Root directory: {Path(root_dir).resolve()}")
    print("   Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping visualizer server...")
    finally:
        server.server_close()
