"""Dynamic development HTTP server for project visualizer."""

from __future__ import annotations

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from tools.project_visualizer.generator import ProjectVisualizerGenerator


class ProjectVisualizerHandler(BaseHTTPRequestHandler):
    generator: ProjectVisualizerGenerator

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
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = self.generator.get_data()
            self.wfile.write(json.dumps(data.to_dict(), default=str).encode("utf-8"))
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

        self.send_error(404, "Not Found")

    def log_message(self, format: str, *args: object) -> None:
        # Keep server quiet during operation
        pass


def run_server(root_dir: str | Path = ".", host: str = "127.0.0.1", port: int = 8787) -> None:
    """Run dynamic project visualizer server."""
    generator = ProjectVisualizerGenerator(root_dir)
    handler_class = type(
        "ConfiguredHandler",
        (ProjectVisualizerHandler,),
        {"generator": generator},
    )

    server = HTTPServer((host, port), handler_class)
    print(f"⚡ Runefoble Project Visualizer running at http://{host}:{port}/")
    print(f"   Root directory: {Path(root_dir).resolve()}")
    print("   Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping visualizer server...")
    finally:
        server.server_close()
