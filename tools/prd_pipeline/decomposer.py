"""PRD decomposition engine: generates ADR spikes and vertically sliced backlog tasks."""

from __future__ import annotations

import re
from pathlib import Path

from tools.project_visualizer.markdown_utils import detect_target_bc

from .models import (
    PRD,
    DecompositionPlan,
    SliceType,
    TaskDraft,
    UserStoryDraft,
)


class PRDDecomposer:
    """Decomposes PRDs into granular, single-pass vertical slices and architectural spikes."""

    def __init__(self, repo_root: Path | str):
        self.repo_root = Path(repo_root).resolve()
        self.backlog_dir = self.repo_root / "docs" / "project" / "backlog"
        self.stories_dir = self.repo_root / "docs" / "project" / "user_stories" / "accepted"

    def get_max_task_number(self) -> int:
        """Finds the highest existing task number across all backlog folders."""
        max_num = 0
        for subdir in ["complete", "refined", "proposed"]:
            dir_path = self.backlog_dir / subdir
            if dir_path.exists():
                for f in dir_path.glob("*.md"):
                    m = re.search(r"(\d{4})", f.stem)
                    if m:
                        max_num = max(max_num, int(m.group(1)))
        return max_num

    def get_max_story_number(self) -> int:
        """Finds the highest existing user story number."""
        max_num = 0
        if self.stories_dir.exists():
            for f in self.stories_dir.glob("*.md"):
                m = re.search(r"(\d{4})", f.stem)
                if m:
                    max_num = max(max_num, int(m.group(1)))
        return max_num

    def plan_decomposition(self, prd: PRD) -> DecompositionPlan:
        """Analyzes a PRD and formulates a plan of spikes and vertical slices."""
        current_task_num = self.get_max_task_number()
        current_story_num = self.get_max_story_number()

        plan = DecompositionPlan(prd_id=prd.canonical_id, prd_title=prd.title)
        bc = prd.target_bc if prd.target_bc != "platform" else detect_target_bc(prd.title.lower())

        # Determine if an Architectural Spike is needed
        needs_spike = self._requires_architectural_spike(prd)
        spike_id = None
        if needs_spike:
            current_task_num += 1
            spike_id = f"TASK-{str(current_task_num).zfill(4)}"
            plan.spikes.append(
                self._create_spike_draft(
                    task_id=spike_id,
                    task_num=current_task_num,
                    prd=prd,
                    target_bc=bc,
                )
            )

        created_story_ids: list[str] = list(prd.linked_stories)

        # Generate a supporting user story if none exist
        if not created_story_ids:
            current_story_num += 1
            story_id = f"US-{str(current_story_num).zfill(4)}"
            created_story_ids.append(story_id)
            plan.stories.append(
                UserStoryDraft(
                    id=story_id,
                    number=current_story_num,
                    title=f"{prd.title} Experience",
                    persona=prd.who_for.split()[0] if prd.who_for else "Adventurer",
                    prd_id=prd.canonical_id,
                    role=prd.who_for.split()[0] if prd.who_for else "Adventurer",
                    action=f"interact with {prd.title.lower()}",
                    benefit="experience seamless and immersive gameplay",
                    acceptance_criteria=prd.checkable_outcomes
                    or ["Executes within performance limits."],
                )
            )

        # Slice 1: Domain Aggregate & Event Sourcing
        current_task_num += 1
        t1_id = f"TASK-{str(current_task_num).zfill(4)}"
        plan.slices.append(
            self._create_domain_slice_draft(
                task_id=t1_id,
                task_num=current_task_num,
                prd=prd,
                target_bc=bc,
                dependencies=[spike_id] if spike_id else [],
                governing_stories=created_story_ids,
            )
        )

        # Slice 2: REST API & SpiceDB Zanzibar Authorization
        current_task_num += 1
        t2_id = f"TASK-{str(current_task_num).zfill(4)}"
        plan.slices.append(
            self._create_api_slice_draft(
                task_id=t2_id,
                task_num=current_task_num,
                prd=prd,
                target_bc=bc,
                dependencies=[t1_id],
                governing_stories=created_story_ids,
            )
        )

        # Slice 3: Lit Web Component Microfrontend (if applicable)
        if self._requires_ui_component(prd):
            current_task_num += 1
            t3_id = f"TASK-{str(current_task_num).zfill(4)}"
            plan.slices.append(
                self._create_ui_slice_draft(
                    task_id=t3_id,
                    task_num=current_task_num,
                    prd=prd,
                    target_bc=bc,
                    dependencies=[t2_id],
                    governing_stories=created_story_ids,
                )
            )

        # Slice 4: Async Engine / Redis Streams Worker (if real-time or background processing required)
        if self._requires_worker_slice(prd):
            current_task_num += 1
            t4_id = f"TASK-{str(current_task_num).zfill(4)}"
            plan.slices.append(
                self._create_worker_slice_draft(
                    task_id=t4_id,
                    task_num=current_task_num,
                    prd=prd,
                    target_bc=bc,
                    dependencies=[t1_id],
                    governing_stories=created_story_ids,
                )
            )

        return plan

    def _requires_architectural_spike(self, prd: PRD) -> bool:
        """Determines if novel technologies or boundaries warrant an ADR spike."""
        keywords = [
            "3d",
            "webgl",
            "relic",
            "alchem",
            "crafting",
            "stl",
            "printable",
            "mesh",
            "particle",
            "leitmotif",
            "dsp",
            "atlas",
        ]
        combined = f"{prd.title} {prd.body}".lower()
        return any(k in combined for k in keywords)

    def _requires_ui_component(self, prd: PRD) -> bool:
        """Determines if the PRD includes user-facing presentation."""
        keywords = [
            "ui",
            "component",
            "modal",
            "inspector",
            "hud",
            "viewer",
            "canvas",
            "workbench",
            "dashboard",
            "visualizer",
            "standee",
        ]
        combined = f"{prd.title} {prd.body}".lower()
        return any(k in combined for k in keywords)

    def _requires_worker_slice(self, prd: PRD) -> bool:
        """Determines if async stream processing or calculation engine is needed."""
        keywords = [
            "stream",
            "redis",
            "projection",
            "engine",
            "worker",
            "synthesis",
            "realtime",
            "live",
            "websocket",
        ]
        combined = f"{prd.title} {prd.body}".lower()
        return any(k in combined for k in keywords)

    def _create_spike_draft(
        self, task_id: str, task_num: int, prd: PRD, target_bc: str
    ) -> TaskDraft:
        title = f"SPIKE: Architectural Spike and ADR for {prd.title}"
        summary = f"Investigate architectural options and author an ADR for {prd.title} integration within `{target_bc}`."
        return TaskDraft(
            id=task_id,
            number=task_num,
            title=title,
            status="Proposed",
            dependencies=[],
            governing_adrs=["ADR-0001", "ADR-0003", "ADR-0011"],
            governing_prds=[prd.canonical_id],
            governing_stories=list(prd.linked_stories),
            summary=summary,
            problem_statement=f"Integrating {prd.title} introduces novel technical interfaces that require architectural evaluation before implementation.",
            scope_of_work=[
                f"1. Research technical constraints and integration patterns for {prd.title}.",
                "2. Prototype minimal interface spike verifying data flow.",
                "3. Draft governing ADR in docs/project/adrs/proposed/.",
            ],
            invest_evaluation={
                "Independent": "Self-contained spike investigating design options.",
                "Negotiable": "Explores trade-offs before locking specifications.",
                "Valuable": "Eliminates technical uncertainty for subsequent vertical slices.",
                "Estimable": "Single spike pass with bounded scope.",
                "Small": "Scoped strictly to ADR proposal and contract verification (< 500 lines, target < 300 lines, executable in one agy -p pass).",
                "Testable": "Verified via contract tests and ADR review.",
            },
            definition_of_done=[
                "Governing ADR document authored in docs/project/adrs/.",
                "Contract verification tests pass locally via uv run pytest.",
                "Passes line count checks (<500 lines).",
            ],
            slice_type=SliceType.SPIKE,
            is_spike=True,
            target_bc=target_bc,
        )

    def _create_domain_slice_draft(
        self,
        task_id: str,
        task_num: int,
        prd: PRD,
        target_bc: str,
        dependencies: list[str],
        governing_stories: list[str],
    ) -> TaskDraft:
        title = f"{prd.title} Domain Aggregate and Event Sourcing"
        return TaskDraft(
            id=task_id,
            number=task_num,
            title=title,
            status="Proposed",
            dependencies=dependencies,
            governing_adrs=["ADR-0003", "ADR-0006", "ADR-0011"],
            governing_prds=[prd.canonical_id],
            governing_stories=governing_stories,
            summary=f"Implement core domain events and DeclarativeAggregate state handlers for {prd.title} in `services/{target_bc}`.",
            problem_statement=f"Domain state transitions for {prd.title} must follow strict event sourcing via eventsource-py per ADR-0011.",
            scope_of_work=[
                f"1. Define CloudEvents domain events in libs/runefoble_events or services/{target_bc}.",
                "2. Implement DeclarativeAggregate subclass with @handles mutation methods.",
                "3. Configure AggregateRepository integration with PostgreSQL event store.",
                "4. Frontdoor blackbox unit/integration tests validating state transitions.",
            ],
            invest_evaluation={
                "Independent": "Independent domain state slice without UI dependencies.",
                "Negotiable": "State schema can adjust to domain feedback.",
                "Valuable": "Provides immutable source-of-truth for the capability.",
                "Estimable": "Standard eventsource-py aggregate pattern.",
                "Small": "Focused strictly on domain models and handlers (< 500 lines, target < 400 lines, single agy -p pass).",
                "Testable": "Blackbox test assertions on emitted domain events.",
            },
            definition_of_done=[
                f"DeclarativeAggregate implemented in services/{target_bc}/src/{target_bc}/domain/.",
                "Domain events registered with @register_event.",
                "Frontdoor tests verify event application and state mutation.",
                "Zero files exceed 500 lines.",
            ],
            slice_type=SliceType.DOMAIN_AGGREGATE,
            is_spike=False,
            target_bc=target_bc,
        )

    def _create_api_slice_draft(
        self,
        task_id: str,
        task_num: int,
        prd: PRD,
        target_bc: str,
        dependencies: list[str],
        governing_stories: list[str],
    ) -> TaskDraft:
        title = f"{prd.title} REST API and SpiceDB Authorization"
        return TaskDraft(
            id=task_id,
            number=task_num,
            title=title,
            status="Proposed",
            dependencies=dependencies,
            governing_adrs=["ADR-0001", "ADR-0003", "ADR-0005"],
            governing_prds=[prd.canonical_id],
            governing_stories=governing_stories,
            summary=f"Expose public API endpoints for {prd.title} with Zitadel JWT auth and SpiceDB Zanzibar access control.",
            problem_statement=f"Clients require secure, authorized REST/WebSocket interfaces to interact with {prd.title}.",
            scope_of_work=[
                f"1. Implement APIRouter endpoints in services/{target_bc}.",
                "2. Integrate SpiceDB Zanzibar permissions checking against runefoble.zed.",
                "3. Wire Zitadel authentication dependency.",
                "4. Frontdoor blackbox HTTP test suite exercising endpoints.",
            ],
            invest_evaluation={
                "Independent": "Thin HTTP frontdoor slice over existing domain aggregate.",
                "Negotiable": "Route endpoints and payload structures are flexible.",
                "Valuable": "Unlocks external interaction for players and clients.",
                "Estimable": "Pattern matches existing decomposed APIRouters.",
                "Small": "Isolated router and schema definitions (< 500 lines, target < 350 lines, single agy -p pass).",
                "Testable": "Blackbox HTTP test client verification.",
            },
            definition_of_done=[
                f"Public APIRouter exposed in services/{target_bc}/src/{target_bc}/routers/.",
                "SpiceDB Zanzibar checks enforced for all mutating actions.",
                "Blackbox HTTP tests pass with 200 OK and 403 Forbidden checks.",
                "File lengths strictly < 500 lines.",
            ],
            slice_type=SliceType.API_AUTH,
            is_spike=False,
            target_bc=target_bc,
        )

    def _create_ui_slice_draft(
        self,
        task_id: str,
        task_num: int,
        prd: PRD,
        target_bc: str,
        dependencies: list[str],
        governing_stories: list[str],
    ) -> TaskDraft:
        slug = re.sub(r"[^a-z0-9]+", "-", prd.title.lower()).strip("-")
        tag_name = f"runefoble-{slug[:20].strip('-')}"
        title = f"{prd.title} Lit Microfrontend and Storybook Studio"
        return TaskDraft(
            id=task_id,
            number=task_num,
            title=title,
            status="Proposed",
            dependencies=dependencies,
            governing_adrs=["ADR-0004", "ADR-0013"],
            governing_prds=[prd.canonical_id],
            governing_stories=governing_stories,
            summary=f"Build Lit Web Component `<{tag_name}>` vendored in `services/{target_bc}/ui/` with Storybook stories.",
            problem_statement=f"Users need a responsive, Bauhaus-styled interface to interact with {prd.title} per ADR-0013.",
            scope_of_work=[
                f"1. Scaffold Lit Web Component <{tag_name}> in services/{target_bc}/ui/src/.",
                "2. Apply Bauhaus geometric design tokens with dark/light mode contrast.",
                "3. Author interactive Storybook stories in services/{target_bc}/ui/src/stories/.",
                f"4. Vendor microfrontend manifest at services/{target_bc}/ui/manifest.json.",
                "5. Frontdoor blackbox test verifying element mounting and manifest.",
            ],
            invest_evaluation={
                "Independent": "Decoupled presentation slice communicating via properties/events.",
                "Negotiable": "Styling tokens and UI controls can iterate.",
                "Valuable": "Direct user interaction on the frontend canvas.",
                "Estimable": "Follows established microfrontend packaging.",
                "Small": "Self-contained Lit component and story (< 500 lines, target < 400 lines, single agy -p pass).",
                "Testable": "Storybook stories and frontend build validation.",
            },
            definition_of_done=[
                f"Component <{tag_name}> implemented with Shadow DOM encapsulation.",
                "Interactive Storybook stories pass without console errors.",
                "Manifest exposed via /ui/manifest per ADR-0013.",
                "Frontend build passes cleanly via pnpm run build.",
            ],
            slice_type=SliceType.MICROFRONTEND,
            is_spike=False,
            target_bc=target_bc,
        )

    def _create_worker_slice_draft(
        self,
        task_id: str,
        task_num: int,
        prd: PRD,
        target_bc: str,
        dependencies: list[str],
        governing_stories: list[str],
    ) -> TaskDraft:
        title = f"{prd.title} Redis Streams Event Worker and Projection Engine"
        return TaskDraft(
            id=task_id,
            number=task_num,
            title=title,
            status="Proposed",
            dependencies=dependencies,
            governing_adrs=["ADR-0006", "ADR-0010", "ADR-0011"],
            governing_prds=[prd.canonical_id],
            governing_stories=governing_stories,
            summary=f"Implement asynchronous Redis Streams event consumer group worker for {prd.title} projections.",
            problem_statement=f"High-throughput events for {prd.title} must be processed asynchronously without blocking HTTP requests.",
            scope_of_work=[
                f"1. Implement consumer group stream listener in services/{target_bc}/src/{target_bc}/worker.py.",
                "2. Maintain read model projections and WebSocket broadcast triggers.",
                "3. Instrument OpenTelemetry trace propagation across stream events.",
                "4. Frontdoor blackbox test verifying stream event consumption.",
            ],
            invest_evaluation={
                "Independent": "Independent async worker reacting to stream events.",
                "Negotiable": "Batching size and projection retention are configurable.",
                "Valuable": "Provides resilient real-time background processing.",
                "Estimable": "Pattern matches existing Redis Streams consumers.",
                "Small": "Focused worker module (< 500 lines, target < 350 lines, single agy -p pass).",
                "Testable": "Blackbox test with synthetic stream events.",
            },
            definition_of_done=[
                "Consumer group worker listening on designated stream topic.",
                "Distributed tracing propagated over event metadata.",
                "Blackbox test suite validates event consumption and projection.",
                "File lengths strictly < 500 lines.",
            ],
            slice_type=SliceType.WORKER_INTEGRATION,
            is_spike=False,
            target_bc=target_bc,
        )
