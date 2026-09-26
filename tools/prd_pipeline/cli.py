"""Command-line interface for the PRD creation, maintenance, and decomposition pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent_prompts import build_agent_decomposition_prompt
from .decomposer import PRDDecomposer
from .models import PRD
from .prd_manager import PRDManager
from .registry_sync import RegistrySynchronizer
from .writer import PlanWriter


def find_repo_root() -> Path:
    """Finds the root directory of the git repository."""
    curr = Path.cwd()
    while curr != curr.parent:
        if (curr / ".git").exists() or (curr / "pyproject.toml").exists():
            return curr
        curr = curr.parent
    return Path.cwd()


def cmd_audit(args: argparse.Namespace, repo_root: Path) -> int:
    """Audits PRDs, detecting undecomposed records and backlog health."""
    mgr = PRDManager(repo_root)
    audit = mgr.audit_prds()

    print("=== Runefoble PRD & Backlog Audit ===")
    print(f"Total PRD Records: {audit['total_prds']}")
    print(f"Backlog Ready Buffer: {audit['buffer']['refined']} (Target: ~10)")
    print(f"Proposed Task Pool: {audit['buffer']['proposed']}")
    print(f"Completed Tasks: {audit['buffer']['complete']}")
    print()

    if audit["buffer"]["ready_buffer_low"]:
        print("⚠️ WARNING: Ready buffer is low (< 8 items). Refinement needed.")
    else:
        print("✅ Ready buffer is healthy.")

    print()
    if audit["undecomposed_prds"]:
        print(f"🚨 Undecomposed Accepted PRDs ({len(audit['undecomposed_prds'])}):")
        for pid in audit["undecomposed_prds"]:
            print(f"   - {pid}")
    else:
        print("✅ Zero completely undecomposed accepted PRDs.")

    if audit["underdecomposed_prds"]:
        print(f"\n⚡ Underdecomposed PRDs ({len(audit['underdecomposed_prds'])}):")
        for pid in audit["underdecomposed_prds"]:
            print(f"   - {pid}")

    if audit["epic_proposed_tasks"]:
        print(f"\n⚠️ Oversized / Epic Proposed Tasks ({len(audit['epic_proposed_tasks'])}):")
        for t in audit["epic_proposed_tasks"]:
            print(f"   - {t['id']}: {t['title']} ({t['scope_count']} scope items)")
        print(
            "   👉 Recommendation: Run 'decompose' or 'split-epic' to break into single-pass slices."
        )

    if audit["stale_task_links"]:
        print(f"\n⚠️ Stale PRD Task Links ({len(audit['stale_task_links'])}):")
        for s in audit["stale_task_links"]:
            print(
                f"   - {s['prd']} links {s['task']} as '{s['referenced']}', but actual is '{s['actual']}'"
            )
        print("   👉 Run 'sync' to automatically repair stale links.")
    else:
        print("\n✅ Zero stale PRD task links.")

    return 0


def cmd_create(args: argparse.Namespace, repo_root: Path) -> int:
    """Creates a new PRD document and syncs registries."""
    mgr = PRDManager(repo_root)
    prd = mgr.create_prd(
        title=args.title,
        persona=args.persona or "Adventurer",
        target_bc=args.bc or "platform",
        summary=args.summary or f"Need for {args.title} in Runefoble.",
        status=args.status or "Accepted",
    )
    print(f"✅ Created {prd.canonical_id}: {prd.title}")
    print(f"   File: {prd.file_path}")

    sync = RegistrySynchronizer(repo_root)
    res = sync.sync_all()
    print(f"   Updated registries: {res['prds_synced']} PRDs registered.")
    return 0


def cmd_decompose(args: argparse.Namespace, repo_root: Path) -> int:
    """Decomposes a specified PRD into spikes and vertical slices."""
    mgr = PRDManager(repo_root)
    decomposer = PRDDecomposer(repo_root)
    writer = PlanWriter(repo_root)
    sync = RegistrySynchronizer(repo_root)

    prds = mgr.load_prds()
    target_prd: PRD | None = None

    clean_arg = args.prd.upper()
    if not clean_arg.startswith("PRD-"):
        clean_arg = f"PRD-{clean_arg.zfill(4)}"

    target_prd = prds.get(clean_arg)
    if not target_prd:
        print(f"❌ Error: PRD '{args.prd}' not found.")
        return 1

    plan = decomposer.plan_decomposition(target_prd)

    print(f"=== Decomposition Plan for {plan.prd_id}: '{plan.prd_title}' ===")
    if plan.spikes:
        print(f"Architectural Spikes ({len(plan.spikes)}):")
        for s in plan.spikes:
            print(f"  ⚡ {s.canonical_id}: {s.title}")
    print(f"Vertical Slices ({len(plan.slices)}):")
    for sl in plan.slices:
        print(f"  🔹 {sl.canonical_id} [{sl.slice_type}]: {sl.title}")
    if plan.stories:
        print(f"User Stories to Create ({len(plan.stories)}):")
        for st in plan.stories:
            print(f"  📖 {st.canonical_id}: {st.title} ({st.persona})")

    if args.plan_only:
        print("\n(Dry-run mode: no files written)")
        return 0

    # Write files
    written_tasks: list[tuple[str, str, str]] = []
    for t in plan.all_tasks:
        fp = writer.write_task(t)
        written_tasks.append((t.canonical_id, t.title, f"../../backlog/proposed/{fp.name}"))
        print(f"✅ Created proposed task: {t.canonical_id} -> {fp.name}")

    written_stories: list[tuple[str, str, str]] = []
    for st in plan.stories:
        sp = writer.write_user_story(st)
        written_stories.append(
            (st.canonical_id, st.title, f"../../user_stories/accepted/{sp.name}")
        )
        print(f"✅ Created user story: {st.canonical_id} -> {sp.name}")

    # Combine with existing tasks in PRD
    all_prd_tasks = list(written_tasks)
    mgr.update_prd_links(target_prd, all_prd_tasks, written_stories if written_stories else None)
    print(f"✅ Updated {target_prd.canonical_id} file links.")

    # Sync registries and priority index
    res = sync.sync_all()
    print(f"✅ Synchronized registries: {res['tasks_synced']} tasks in priority index.")
    return 0


def cmd_decompose_all(args: argparse.Namespace, repo_root: Path) -> int:
    """Decomposes all accepted PRDs that lack granular vertical slices."""
    mgr = PRDManager(repo_root)
    audit = mgr.audit_prds()
    candidates = audit["undecomposed_prds"] + audit["underdecomposed_prds"]

    if not candidates:
        print("✅ No undecomposed or underdecomposed PRDs found.")
        return 0

    print(f"Found {len(candidates)} candidate PRDs for decomposition: {', '.join(candidates)}")
    for pid in candidates:
        args.prd = pid
        cmd_decompose(args, repo_root)
        print("-" * 50)
    return 0


def cmd_sync(args: argparse.Namespace, repo_root: Path) -> int:
    """Synchronizes all documentation registries."""
    sync = RegistrySynchronizer(repo_root)
    res = sync.sync_all()
    print("=== Registry Synchronization Complete ===")
    print(f"  PRDs Registered: {res['prds_synced']}")
    print(f"  User Stories Registered: {res['stories_synced']}")
    print(f"  Backlog Tasks Indexed: {res['tasks_synced']}")
    return 0


def cmd_prompt(args: argparse.Namespace, repo_root: Path) -> int:
    """Generates the agy -p decomposition prompt for a PRD."""
    mgr = PRDManager(repo_root)
    decomposer = PRDDecomposer(repo_root)
    prds = mgr.load_prds()

    clean_arg = args.prd.upper()
    if not clean_arg.startswith("PRD-"):
        clean_arg = f"PRD-{clean_arg.zfill(4)}"

    target_prd = prds.get(clean_arg)
    if not target_prd:
        print(f"❌ Error: PRD '{args.prd}' not found.", file=sys.stderr)
        return 1

    next_task = f"TASK-{str(decomposer.get_max_task_number() + 1).zfill(4)}"
    next_story = f"US-{str(decomposer.get_max_story_number() + 1).zfill(4)}"

    prompt = build_agent_decomposition_prompt(target_prd, next_task, next_story)
    print(prompt)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Runefoble PRD Creation, Maintenance, and Task Decomposition Pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # audit
    p_audit = subparsers.add_parser("audit", help="Audit PRDs, buffer health, and granularity")
    p_audit.set_defaults(func=cmd_audit)

    # create
    p_create = subparsers.add_parser("create", help="Create a new PRD document")
    p_create.add_argument("--title", required=True, help="Title of the PRD")
    p_create.add_argument("--persona", help="Target user persona (e.g. Bram, Rowan, Evelyn)")
    p_create.add_argument("--bc", help="Target bounded context")
    p_create.add_argument("--summary", help="Short summary of user problem")
    p_create.add_argument(
        "--status", default="Accepted", help="Lifecycle status (Idea, Shaped, Accepted)"
    )
    p_create.set_defaults(func=cmd_create)

    # decompose
    p_dec = subparsers.add_parser(
        "decompose", help="Decompose a PRD into spikes and vertical slices"
    )
    p_dec.add_argument("--prd", required=True, help="Canonical PRD ID (e.g. PRD-0014 or 0014)")
    p_dec.add_argument(
        "--plan-only", action="store_true", help="Print decomposition plan without writing files"
    )
    p_dec.set_defaults(func=cmd_decompose)

    # decompose-all
    p_decall = subparsers.add_parser(
        "decompose-all", help="Decompose all undecomposed accepted PRDs"
    )
    p_decall.add_argument(
        "--plan-only", action="store_true", help="Print plan without writing files"
    )
    p_decall.set_defaults(func=cmd_decompose_all)

    # sync
    p_sync = subparsers.add_parser("sync", help="Synchronize registries and priority index")
    p_sync.set_defaults(func=cmd_sync)

    # prompt
    p_prompt = subparsers.add_parser("prompt", help="Print agy -p agent prompt for decomposition")
    p_prompt.add_argument("--prd", required=True, help="Target PRD ID")
    p_prompt.set_defaults(func=cmd_prompt)

    args = parser.parse_args(argv)
    repo_root = find_repo_root()
    return args.func(args, repo_root)


if __name__ == "__main__":
    sys.exit(main())
