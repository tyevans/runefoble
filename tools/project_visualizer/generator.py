"""Bundle generator for creating standalone or live HTML visualizer applications."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import tools.project_visualizer.assets_js as assets_js
from tools.project_visualizer.graph import ProjectGraphBuilder
from tools.project_visualizer.models import ProjectData
from tools.project_visualizer.parser import ProjectParser
from tools.project_visualizer.template import render_html_shell


class ProjectVisualizerGenerator:
    """Builds and bundles the dynamic project visualizer."""

    def __init__(self, root_dir: str | Path = "."):
        self.root_dir = Path(root_dir).resolve()
        self.parser = ProjectParser(self.root_dir)

    def get_data(self) -> ProjectData:
        data = self.parser.parse_all()
        builder = ProjectGraphBuilder(data)
        return builder.build()

    def generate_html(self, is_live_server: bool = False) -> str:
        if is_live_server:
            importlib.reload(assets_js)
        data = self.get_data()
        data_json = json.dumps(data.to_dict(), default=str)
        shell = render_html_shell(data_json, is_live_server=is_live_server)

        # Inject client script before </body>
        client_script = (
            f"<script>\n{assets_js.get_client_js(is_live_server=is_live_server)}\n</script>"
        )
        return shell.replace("</body>", f"{client_script}\n</body>")

    def build_file(self, output_path: str | Path, is_live_server: bool = False) -> Path:
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        html = self.generate_html(is_live_server=is_live_server)
        out.write_text(html, encoding="utf-8")
        return out
