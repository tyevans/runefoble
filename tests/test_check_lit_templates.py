"""Behaviour tests for the Lit template gate (scripts/check_lit_templates.py).

Governed by ADR-0004 and ADR-0013 (TASK-0904). The tests run the public CLI against a
temporary repository tree. They never scan the real tree.
"""

import subprocess
import sys
from pathlib import Path

from tests.helpers.process import run_command

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_lit_templates.py"

ELEMENT = "services/demo/ui/src/runefoble-demo.ts"
VIEW = "frontend/src/views/demo-view.ts"
DOM_TEST = "services/demo/ui/test-dom/demo.test.ts"

ELEMENT_SOURCE = """
import { LitElement, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('runefoble-demo')
export class RunefobleDemo extends LitElement {
  @property({ type: String, attribute: 'campaign-id' }) campaignId = '';
  @property({ type: String }) sessionId = '';
  @property({ type: Boolean, attribute: false }) isDm = false;
  @property({ type: Object, hasChanged: (a: unknown, b: unknown) => a !== b }) draft = {};
  @property({ type: String }) title = '';
}
"""


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return run_command(
        [sys.executable, str(SCRIPT), "--root", str(root)], check=False, timeout=60.0
    )


def _view(body: str) -> str:
    return f"import {{ html, svg }} from 'lit';\nexport const view = () => {body};\n"


def test_passes_when_kebab_attributes_match_declared_attributes(tmp_path: Path) -> None:
    _write(tmp_path, ELEMENT, ELEMENT_SOURCE)
    _write(
        tmp_path,
        VIEW,
        _view(
            'html`<runefoble-demo campaign-id=${\'c\'} title="t" data-test-id="x" '
            ".sessionId=${'s'} @select=${(e: Event) => e.type > ''}></runefoble-demo>`"
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout
    assert "passed" in result.stdout


def test_fails_on_kebab_attribute_for_property_without_attribute_option(
    tmp_path: Path,
) -> None:
    _write(tmp_path, ELEMENT, ELEMENT_SOURCE)
    _write(
        tmp_path,
        VIEW,
        _view("html`<runefoble-demo\n  campaign-id=\"c\"\n  session-id=${'s'}></runefoble-demo>`"),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert f"{VIEW}:4" in result.stdout
    assert "session-id" in result.stdout
    assert "sessionId" in result.stdout
    assert "campaign-id" not in result.stdout


def test_fails_on_kebab_attribute_for_property_with_attribute_false(tmp_path: Path) -> None:
    _write(tmp_path, ELEMENT, ELEMENT_SOURCE)
    _write(tmp_path, VIEW, _view("html`<runefoble-demo ?is-dm=${true}></runefoble-demo>`"))

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "is-dm" in result.stdout


def test_fails_on_kebab_attribute_set_in_a_dom_test(tmp_path: Path) -> None:
    _write(tmp_path, ELEMENT, ELEMENT_SOURCE)
    _write(
        tmp_path,
        DOM_TEST,
        "const el = document.createElement('runefoble-demo');\n"
        "el.setAttribute('session-id', 's');\n",
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert f"{DOM_TEST}:2" in result.stdout
    assert "session-id" in result.stdout


def test_fails_on_svg_children_written_with_the_html_tag(tmp_path: Path) -> None:
    _write(
        tmp_path,
        VIEW,
        _view('html`<svg>${html`\n  <g class="pin"><text>A</text></g>`}</svg>`'),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert f"{VIEW}:3" in result.stdout
    assert "<g>" in result.stdout
    assert "svg" in result.stdout


def test_passes_on_svg_children_written_with_the_svg_tag(tmp_path: Path) -> None:
    _write(
        tmp_path,
        VIEW,
        _view('html`<svg>${svg`<g class="pin"><text>A</text></g>`}</svg><p>text</p>`'),
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout
