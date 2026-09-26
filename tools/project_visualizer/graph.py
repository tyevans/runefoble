"""Graph construction and traceability linking for project visualizer."""

from __future__ import annotations

import re

from tools.project_visualizer.models import (
    ProjectData,
    ProjectHealthMetrics,
    TraceabilityEdge,
)


class ProjectGraphBuilder:
    """Builds relational edges, reverse links, and health metrics."""

    def __init__(self, data: ProjectData):
        self.data = data

    def build(self) -> ProjectData:
        self._link_personas_to_stories()
        self._link_tasks_to_entities()
        self._link_stories_to_prds()
        self._link_features_to_prds()
        self._generate_traceability_edges()
        self._compute_health_metrics()
        return self.data

    def _link_personas_to_stories(self) -> None:
        persona_by_id = {p.id: p for p in self.data.personas}

        for story in self.data.stories:
            matched_persona = None
            for p in self.data.personas:
                if p.name.lower() in story.persona.lower() or p.id in story.persona.lower():
                    matched_persona = p
                    break
            if not matched_persona:
                # Default to first word match
                first_word = story.persona.split()[0].lower() if story.persona else ""
                matched_persona = persona_by_id.get(first_word)

            if matched_persona and story.id not in matched_persona.story_ids:
                matched_persona.story_ids.append(story.id)

    def _link_tasks_to_entities(self) -> None:
        adr_by_id = {adr.id: adr for adr in self.data.adrs}
        prd_by_id = {prd.id: prd for prd in self.data.prds}
        story_by_id = {s.id: s for s in self.data.stories}
        task_by_id = {t.id: t for t in self.data.tasks}

        # Sync PRD-declared tasks
        for prd in self.data.prds:
            for t_id in prd.implementing_tasks:
                if t_id in task_by_id and prd.id not in task_by_id[t_id].governing_prds:
                    task_by_id[t_id].governing_prds.append(prd.id)

        for task in self.data.tasks:
            # Extract PRD links from markdown body or frontmatter (case-insensitive)
            prds_found = [
                f"PRD-{p.split('-')[-1].zfill(4)}"
                for p in re.findall(r"PRD-\d+", task.raw_markdown, re.IGNORECASE)
            ]
            for prd_id in prds_found:
                if prd_id not in task.governing_prds:
                    task.governing_prds.append(prd_id)

            for prd_id in task.governing_prds:
                if prd_id in prd_by_id and task.id not in prd_by_id[prd_id].implementing_tasks:
                    prd_by_id[prd_id].implementing_tasks.append(task.id)

            # Extract User Story links from markdown body (case-insensitive)
            stories_found = [
                f"US-{s.split('-')[-1].zfill(4)}"
                for s in re.findall(r"US-\d+", task.raw_markdown, re.IGNORECASE)
            ]
            for s_id in stories_found:
                if s_id not in task.governing_stories:
                    task.governing_stories.append(s_id)

            for s_id in task.governing_stories:
                if s_id in story_by_id and task.id not in story_by_id[s_id].implementing_tasks:
                    story_by_id[s_id].implementing_tasks.append(task.id)

            # Link governing ADRs to task (case-insensitive)
            adrs_found = [
                f"ADR-{a.split('-')[-1].zfill(4)}"
                for a in re.findall(r"ADR-\d+", task.raw_markdown, re.IGNORECASE)
            ]
            for adr_id in adrs_found:
                if adr_id not in task.governing_adrs:
                    task.governing_adrs.append(adr_id)

            for adr_id in task.governing_adrs:
                if adr_id in adr_by_id and task.id not in adr_by_id[adr_id].implementing_tasks:
                    adr_by_id[adr_id].implementing_tasks.append(task.id)

    def _link_stories_to_prds(self) -> None:
        prd_by_id = {prd.id: prd for prd in self.data.prds}
        task_by_id = {t.id: t for t in self.data.tasks}
        story_by_id = {s.id: s for s in self.data.stories}

        # 0. Sync PRD-declared stories
        for prd in self.data.prds:
            for s_id in prd.linked_stories:
                if s_id in story_by_id and not story_by_id[s_id].governing_prd:
                    story_by_id[s_id].governing_prd = prd.id

        # 1. Direct mention in story markdown or frontmatter
        for story in self.data.stories:
            prds_in_story = [
                f"PRD-{p.split('-')[-1].zfill(4)}"
                for p in re.findall(r"PRD-\d+", story.raw_markdown, re.IGNORECASE)
            ]
            adrs_in_story = [
                f"ADR-{a.split('-')[-1].zfill(4)}"
                for a in re.findall(r"ADR-\d+", story.raw_markdown, re.IGNORECASE)
            ]

            for p_id in prds_in_story:
                if not story.governing_prd:
                    story.governing_prd = p_id
                if p_id in prd_by_id and story.id not in prd_by_id[p_id].linked_stories:
                    prd_by_id[p_id].linked_stories.append(story.id)

            if (
                story.governing_prd
                and story.governing_prd in prd_by_id
                and story.id not in prd_by_id[story.governing_prd].linked_stories
            ):
                prd_by_id[story.governing_prd].linked_stories.append(story.id)

            for a_id in adrs_in_story:
                if a_id not in story.governing_adrs:
                    story.governing_adrs.append(a_id)

            # 2. Bridge via implementing tasks if no direct PRD found
            if not story.governing_prd and story.implementing_tasks:
                for t_id in story.implementing_tasks:
                    task = task_by_id.get(t_id)
                    if task and task.governing_prds:
                        p_id = task.governing_prds[0]
                        story.governing_prd = p_id
                        if p_id in prd_by_id and story.id not in prd_by_id[p_id].linked_stories:
                            prd_by_id[p_id].linked_stories.append(story.id)
                        break

            # 3. Fallback heuristic matching numbers: US-0001 -> PRD-0001, US-0002 -> PRD-0002
            if not story.governing_prd:
                s_num = story.id.split("-")[-1]
                candidate_prd = f"PRD-{s_num}"
                if candidate_prd in prd_by_id:
                    story.governing_prd = candidate_prd
                    if story.id not in prd_by_id[candidate_prd].linked_stories:
                        prd_by_id[candidate_prd].linked_stories.append(story.id)

    def _link_features_to_prds(self) -> None:
        # Match features with PRD bodies and tasks
        for feat in self.data.features:
            for prd in self.data.prds:
                if feat.id in prd.raw_markdown or feat.name.lower() in prd.raw_markdown.lower():
                    # matched feature in PRD
                    pass

    def _generate_traceability_edges(self) -> None:
        edges: list[TraceabilityEdge] = []

        # Persona -> Story (desires)
        for persona in self.data.personas:
            for s_id in persona.story_ids:
                edges.append(
                    TraceabilityEdge(
                        source_type="persona",
                        source_id=persona.id,
                        target_type="story",
                        target_id=s_id,
                        relation="desires",
                    )
                )

        # Story -> PRD (specifies)
        for story in self.data.stories:
            if story.governing_prd:
                edges.append(
                    TraceabilityEdge(
                        source_type="story",
                        source_id=story.id,
                        target_type="prd",
                        target_id=story.governing_prd,
                        relation="specifies",
                    )
                )

        # PRD -> Task (implements)
        for prd in self.data.prds:
            for t_id in prd.implementing_tasks:
                edges.append(
                    TraceabilityEdge(
                        source_type="prd",
                        source_id=prd.id,
                        target_type="task",
                        target_id=t_id,
                        relation="implements",
                    )
                )

        # Task -> ADR (governed_by)
        for task in self.data.tasks:
            for adr_id in task.governing_adrs:
                edges.append(
                    TraceabilityEdge(
                        source_type="task",
                        source_id=task.id,
                        target_type="adr",
                        target_id=adr_id,
                        relation="governed_by",
                    )
                )

            # Task -> Target BC (deploys_to)
            if task.target_bc:
                edges.append(
                    TraceabilityEdge(
                        source_type="task",
                        source_id=task.id,
                        target_type="bc",
                        target_id=task.target_bc,
                        relation="deploys_to",
                    )
                )

            # Task -> Task (depends_on)
            for dep_id in task.dependencies:
                dep_norm = f"TASK-{dep_id.split('-')[-1].zfill(4)}"
                edges.append(
                    TraceabilityEdge(
                        source_type="task",
                        source_id=task.id,
                        target_type="task",
                        target_id=dep_norm,
                        relation="depends_on",
                    )
                )

        self.data.edges = edges

    def _compute_health_metrics(self) -> None:
        tasks = self.data.tasks
        completed = sum(1 for t in tasks if t.status == "Complete")
        refined = sum(1 for t in tasks if t.status == "Refined")
        proposed = sum(1 for t in tasks if t.status == "Proposed")

        # Ready buffer status
        ready_status = "optimal"
        if refined < 2:
            ready_status = "under_buffered"
        elif refined > 5:
            ready_status = "over_buffered"

        # Tasks without ADR links
        tasks_no_adr = [t.id for t in tasks if not t.governing_adrs]

        # Orphaned stories (not linked to PRDs or Tasks)
        orphans = [
            s.id for s in self.data.stories if not s.governing_prd and not s.implementing_tasks
        ]

        mvp_features = sum(1 for f in self.data.features if "P0" in f.tier or "MVP" in f.tier)

        self.data.metrics = ProjectHealthMetrics(
            total_adrs=len(self.data.adrs),
            total_prds=len(self.data.prds),
            total_stories=len(self.data.stories),
            total_tasks=len(tasks),
            completed_tasks=completed,
            refined_tasks=refined,
            proposed_tasks=proposed,
            total_features=len(self.data.features),
            mvp_p0_features=mvp_features,
            total_personas=len(self.data.personas),
            orphaned_stories=orphans,
            tasks_without_adr=tasks_no_adr,
            ready_buffer_status=ready_status,
            ready_buffer_count=refined,
        )
