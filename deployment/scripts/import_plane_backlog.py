#!/usr/bin/env python3
"""Import Perfect Match Digital QMS planning artifacts into Plane.

The repository remains the source of truth. This importer reads the Markdown
files under plane/ and writes to Plane through the official REST API.
Secrets are read from PLANE_API_TOKEN or /opt/perfect-match/secrets/plane-api.env.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import requests

BASE_URL = os.getenv("PLANE_BASE_URL", "https://plane.cloudpixelstudio.agency").rstrip("/")
WORKSPACE_SLUG = os.getenv("PLANE_WORKSPACE_SLUG", "pfm")
EXTERNAL_SOURCE = "perfect-match-qms"
SECRET_FILE = Path("/opt/perfect-match/secrets/plane-api.env")

STATE_PLAN = [
    ("BACKLOG", "backlog", "#A3A3A3", 1000, ("Backlog",)),
    ("READY", "unstarted", "#64748B", 2000, ("Todo", "To Do")),
    ("IN DEVELOPMENT", "started", "#2563EB", 3000, ("In Progress",)),
    ("CODE REVIEW", "started", "#7C3AED", 4000, ()),
    ("TESTING", "started", "#F59E0B", 5000, ()),
    ("UAT", "started", "#0EA5E9", 6000, ()),
    ("DONE", "completed", "#16A34A", 7000, ("Done",)),
]

LABEL_COLORS = {
    "backend": "#2563EB",
    "frontend": "#0EA5E9",
    "odoo": "#714B67",
    "python": "#3776AB",
    "postgresql": "#336791",
    "docker": "#2496ED",
    "security": "#DC2626",
    "ai": "#7C3AED",
    "automation": "#0891B2",
    "documentation": "#64748B",
    "architecture": "#111827",
    "testing": "#16A34A",
    "bug": "#EF4444",
    "feature": "#22C55E",
    "enhancement": "#84CC16",
    "infrastructure": "#475569",
    "compliance": "#9333EA",
    "iso9001": "#0F766E",
    "iatf": "#B45309",
    "iso14001": "#15803D",
    "iso45001": "#BE123C",
    "as9120": "#0369A1",
    "cmmc": "#1D4ED8",
    "pilot": "#F97316",
    "high-risk": "#B91C1C",
    "technical-debt": "#A16207",
    "api": "#0284C7",
    "monitoring": "#4F46E5",
    "reporting": "#059669",
}

CYCLE_DATES = {
    "SPRINT 01 - Foundation": (date(2026, 8, 17), date(2026, 8, 28)),
    "SPRINT 02 - QMS Core": (date(2026, 8, 31), date(2026, 9, 11)),
    "SPRINT 03 - Controls and Evidence": (date(2026, 9, 14), date(2026, 9, 25)),
}


@dataclass(frozen=True)
class ProjectSpec:
    name: str
    identifier: str
    purpose: str
    modules: list[str]


@dataclass(frozen=True)
class WorkItemSpec:
    source_id: str
    title: str
    priority: str
    project: str
    module: str
    cycle: str
    labels: list[str]
    dependencies: str
    objective: str
    description: str
    acceptance: list[str]


def token() -> str:
    value = os.getenv("PLANE_API_TOKEN")
    if value:
        return value.strip()
    if SECRET_FILE.exists():
        match = re.search(r"^PLANE_API_TOKEN=(.+)$", SECRET_FILE.read_text(), re.M)
        if match:
            return match.group(1).strip()
    raise SystemExit("PLANE_API_TOKEN not found")


def ext_id(key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{EXTERNAL_SOURCE}:{key}"))


def value_after(prefix: str, text: str, default: str = "") -> str:
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return default


def section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$"
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start = i + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for i in range(start, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end]).strip()


def parse_projects(root: Path) -> dict[str, ProjectSpec]:
    specs: dict[str, ProjectSpec] = {}
    for path in sorted((root / "plane" / "projects").glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        name = text.splitlines()[0].removeprefix("# ").strip()
        modules = [
            line.removeprefix("- ").strip()
            for line in section(text, "Initial Modules").splitlines()
            if line.startswith("- ")
        ]
        specs[name] = ProjectSpec(
            name=name,
            identifier=value_after("Project Identifier:", text),
            purpose=value_after("Purpose:", text),
            modules=modules,
        )
    return specs


def parse_work_items(root: Path) -> list[WorkItemSpec]:
    items: list[WorkItemSpec] = []
    for path in sorted((root / "plane" / "work-items").glob("PMQMS-*.md")):
        text = path.read_text(encoding="utf-8")
        header = text.splitlines()[0].removeprefix("# ").strip()
        source_id, title = header.split(" - ", 1)
        labels = [label.strip() for label in value_after("Labels:", text).split(",") if label.strip()]
        acceptance = [
            line.removeprefix("- ").strip()
            for line in section(text, "Acceptance Criteria").splitlines()
            if line.startswith("- ")
        ]
        items.append(
            WorkItemSpec(
                source_id=source_id,
                title=title,
                priority=value_after("Priority:", text, "MEDIUM"),
                project=value_after("Project:", text),
                module=value_after("Module:", text),
                cycle=value_after("Cycle:", text, "Backlog"),
                labels=labels,
                dependencies=value_after("Dependencies:", text, "None"),
                objective=section(text, "Objective"),
                description=section(text, "Description"),
                acceptance=acceptance,
            )
        )
    return items


def all_label_names(root: Path, items: list[WorkItemSpec]) -> list[str]:
    labels_path = root / "plane" / "labels.md"
    labels = set()
    if labels_path.exists():
        for line in labels_path.read_text(encoding="utf-8").splitlines():
            if "," in line and not line.startswith("#"):
                labels.update(part.strip() for part in line.split(",") if part.strip())
    for item in items:
        labels.update(item.labels)
    return sorted(labels)


class Plane:
    def __init__(self, dry_run: bool = False) -> None:
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": token(), "Content-Type": "application/json"})
        self.dry_run = dry_run

    def request(self, method: str, path: str, ok: tuple[int, ...], **kwargs: Any) -> Any:
        if self.dry_run and method in {"POST", "PATCH", "DELETE"}:
            return {"id": f"dry-{abs(hash(path + str(kwargs.get('json', ''))))}", "name": kwargs.get("json", {}).get("name", "dry")}
        response = None
        for attempt in range(8):
            response = self.session.request(method, BASE_URL + path, timeout=30, **kwargs)
            if response.status_code != 429:
                break
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after and retry_after.isdigit() else min(30.0, 2.0 * (attempt + 1))
            print(f"rate limit hit; waiting {delay:.0f}s before retrying {method} {path}")
            time.sleep(delay)
        assert response is not None
        if response.status_code not in ok:
            body = response.text[:700].replace("\n", " ")
            raise RuntimeError(f"{method} {path} failed with {response.status_code}: {body}")
        if method in {"POST", "PATCH", "DELETE"}:
            time.sleep(0.15)
        if response.status_code == 204 or not response.text.strip():
            return None
        return response.json()

    def get(self, path: str) -> Any:
        return self.request("GET", path, (200,))

    def post(self, path: str, payload: dict[str, Any], ok: tuple[int, ...] = (200, 201)) -> Any:
        return self.request("POST", path, ok, json=payload)

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PATCH", path, (200,), json=payload)

    def list_all(self, path: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor = None
        while True:
            params = {"per_page": 100}
            if cursor:
                params["cursor"] = cursor
            data = self.request("GET", path, (200,), params=params)
            if not isinstance(data, dict) or "results" not in data:
                return data if isinstance(data, list) else []
            results.extend(data["results"])
            if not data.get("next_page_results") or not data.get("next_cursor"):
                return results
            cursor = data["next_cursor"]


def by_name(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("name", "")).casefold(): row for row in rows if row.get("name")}


def ensure_projects(api: Plane, specs: dict[str, ProjectSpec]) -> dict[str, dict[str, Any]]:
    existing = by_name(api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/"))
    projects = {}
    for spec in specs.values():
        found = existing.get(spec.name.casefold())
        if found:
            projects[spec.name] = found
            print(f"project exists: {spec.name}")
            continue
        payload = {
            "name": spec.name,
            "identifier": spec.identifier,
            "description": spec.purpose,
            "module_view": True,
            "cycle_view": True,
            "issue_views_view": True,
            "page_view": False,
            "intake_view": False,
            "timezone": "America/New_York",
        }
        projects[spec.name] = api.post(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/", payload)
        print(f"project created: {spec.name}")
    return projects


def ensure_states(api: Plane, project: dict[str, Any]) -> dict[str, dict[str, Any]]:
    project_id = project["id"]
    states = by_name(api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/states/"))
    for name, group, color, sequence, aliases in STATE_PLAN:
        existing = states.get(name.casefold())
        if existing:
            if existing.get("name") != name:
                updated = api.patch(
                    f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/states/{existing['id']}/",
                    {"name": name, "group": group, "color": color, "sequence": sequence},
                )
                states[name.casefold()] = updated
                print(f"state normalized: {project['name']} / {name}")
            continue
        alias = next((states.get(candidate.casefold()) for candidate in aliases if candidate.casefold() in states), None)
        payload = {"name": name, "group": group, "color": color, "sequence": sequence}
        if alias:
            updated = api.patch(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/states/{alias['id']}/", payload)
            states.pop(str(alias.get("name", "")).casefold(), None)
            states[name.casefold()] = updated
            print(f"state updated: {project['name']} / {name}")
        else:
            payload.update({"external_source": EXTERNAL_SOURCE, "external_id": ext_id(f"state:{project_id}:{name}")})
            created = api.post(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/states/", payload)
            states[name.casefold()] = created
            print(f"state created: {project['name']} / {name}")
    return states


def ensure_labels(api: Plane, project: dict[str, Any], label_names: list[str]) -> dict[str, dict[str, Any]]:
    project_id = project["id"]
    labels = by_name(api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/labels/"))
    for name in label_names:
        if name.casefold() in labels:
            continue
        created = api.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/labels/",
            {
                "name": name,
                "color": LABEL_COLORS.get(name, "#64748B"),
                "description": f"Perfect Match QMS label: {name}",
                "external_source": EXTERNAL_SOURCE,
                "external_id": ext_id(f"label:{project_id}:{name}"),
            },
        )
        labels[name.casefold()] = created
    print(f"labels ensured: {project['name']} ({len(label_names)})")
    return labels


def ensure_modules(api: Plane, project: dict[str, Any], spec: ProjectSpec) -> dict[str, dict[str, Any]]:
    project_id = project["id"]
    modules = by_name(api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/modules/"))
    for name in spec.modules:
        if name.casefold() in modules:
            continue
        created = api.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/modules/",
            {
                "name": name,
                "description": f"Perfect Match QMS module for {spec.name}: {name}.",
                "status": "planned",
                "external_source": EXTERNAL_SOURCE,
                "external_id": ext_id(f"module:{project_id}:{name}"),
            },
        )
        modules[name.casefold()] = created
        print(f"module created: {spec.name} / {name}")
    return modules


def ensure_cycles(api: Plane, project: dict[str, Any], project_name: str, items: list[WorkItemSpec]) -> dict[str, dict[str, Any]]:
    project_id = project["id"]
    needed = sorted({item.cycle for item in items if item.project == project_name and item.cycle in CYCLE_DATES})
    cycles = by_name(api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/cycles/"))
    for name in needed:
        if name.casefold() in cycles:
            continue
        start, end = CYCLE_DATES[name]
        created = api.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/cycles/",
            {
                "name": name,
                "description": "Two-week Perfect Match QMS development cycle.",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "timezone": "America/New_York",
                "external_source": EXTERNAL_SOURCE,
                "external_id": ext_id(f"cycle:{project_id}:{name}"),
            },
        )
        cycles[name.casefold()] = created
        print(f"cycle created: {project_name} / {name}")
    return cycles


def item_html(item: WorkItemSpec) -> str:
    criteria = "".join(f"<li>{html.escape(line)}</li>" for line in item.acceptance)
    return f"""
<h2>Objective</h2>
<p>{html.escape(item.objective)}</p>
<h2>Planning Metadata</h2>
<ul>
<li><strong>Source ID:</strong> {html.escape(item.source_id)}</li>
<li><strong>Project:</strong> {html.escape(item.project)}</li>
<li><strong>Module:</strong> {html.escape(item.module)}</li>
<li><strong>Cycle:</strong> {html.escape(item.cycle)}</li>
<li><strong>Priority:</strong> {html.escape(item.priority)}</li>
<li><strong>Labels:</strong> {html.escape(', '.join(item.labels))}</li>
<li><strong>Dependencies:</strong> {html.escape(item.dependencies)}</li>
</ul>
<h2>Description</h2>
<p>{html.escape(item.description)}</p>
<h2>Acceptance Criteria</h2>
<ul>{criteria}</ul>
""".strip()


def item_text(item: WorkItemSpec) -> str:
    criteria = "\n".join(f"- {line}" for line in item.acceptance)
    return f"""Objective:
{item.objective}

Planning Metadata:
- Source ID: {item.source_id}
- Project: {item.project}
- Module: {item.module}
- Cycle: {item.cycle}
- Priority: {item.priority}
- Labels: {', '.join(item.labels)}
- Dependencies: {item.dependencies}

Description:
{item.description}

Acceptance Criteria:
{criteria}"""


def ensure_work_items(
    api: Plane,
    projects: dict[str, dict[str, Any]],
    states: dict[str, dict[str, dict[str, Any]]],
    labels: dict[str, dict[str, dict[str, Any]]],
    items: list[WorkItemSpec],
) -> dict[str, dict[str, Any]]:
    issues = {}
    existing_by_project = {}
    for project_name, project in projects.items():
        rows = api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project['id']}/work-items/")
        names = by_name(rows)
        external = {
            str(row.get("external_id")): row
            for row in rows
            if row.get("external_source") == EXTERNAL_SOURCE and row.get("external_id")
        }
        existing_by_project[project_name] = (names, external)
    for item in items:
        project = projects[item.project]
        names, external = existing_by_project[item.project]
        found = external.get(ext_id(f"issue:{item.source_id}")) or names.get(f"{item.source_id} - {item.title}".casefold())
        if found:
            issues[item.source_id] = found
            continue
        state_name = "READY" if item.cycle in CYCLE_DATES else "BACKLOG"
        label_ids = [labels[item.project][label.casefold()]["id"] for label in item.labels if label.casefold() in labels[item.project]]
        payload = {
            "name": f"{item.source_id} - {item.title}",
            "description_html": item_html(item),
            "description_stripped": item_text(item),
            "priority": item.priority.lower(),
            "state": states[item.project][state_name.casefold()]["id"],
            "labels": label_ids,
            "external_source": EXTERNAL_SOURCE,
            "external_id": ext_id(f"issue:{item.source_id}"),
        }
        created = api.post(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project['id']}/work-items/", payload)
        issues[item.source_id] = created
        print(f"work item created: {item.source_id}")
    return issues


def linked_ids(api: Plane, project_id: str, kind: str, resource_id: str) -> set[str]:
    singular = "module" if kind == "modules" else "cycle"
    rows = api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/{kind}/{resource_id}/{singular}-issues/")
    ids = set()
    for row in rows:
        if row.get("issue"):
            ids.add(str(row["issue"]))
        elif row.get("id"):
            ids.add(str(row["id"]))
    return ids


def add_to_resource(api: Plane, project_id: str, kind: str, resource_id: str, issue_ids: list[str]) -> None:
    if not issue_ids:
        return
    singular = "module" if kind == "modules" else "cycle"
    missing = [issue_id for issue_id in issue_ids if issue_id not in linked_ids(api, project_id, kind, resource_id)]
    if missing:
        api.post(
            f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project_id}/{kind}/{resource_id}/{singular}-issues/",
            {"issues": missing},
        )


def assign_structure(
    api: Plane,
    projects: dict[str, dict[str, Any]],
    modules: dict[str, dict[str, dict[str, Any]]],
    cycles: dict[str, dict[str, dict[str, Any]]],
    issues: dict[str, dict[str, Any]],
    items: list[WorkItemSpec],
) -> None:
    module_groups = defaultdict(list)
    cycle_groups = defaultdict(list)
    for item in items:
        issue_id = issues[item.source_id]["id"]
        module_groups[(item.project, item.module)].append(issue_id)
        if item.cycle in CYCLE_DATES:
            cycle_groups[(item.project, item.cycle)].append(issue_id)
    for (project_name, module_name), issue_ids in module_groups.items():
        module = modules[project_name].get(module_name.casefold())
        if module:
            add_to_resource(api, projects[project_name]["id"], "modules", module["id"], issue_ids)
            print(f"module assignment ensured: {project_name} / {module_name} ({len(issue_ids)})")
    for (project_name, cycle_name), issue_ids in cycle_groups.items():
        cycle = cycles[project_name].get(cycle_name.casefold())
        if cycle:
            add_to_resource(api, projects[project_name]["id"], "cycles", cycle["id"], issue_ids)
            print(f"cycle assignment ensured: {project_name} / {cycle_name} ({len(issue_ids)})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    projects_spec = parse_projects(root)
    work_items = parse_work_items(root)
    label_names = all_label_names(root, work_items)

    api = Plane(dry_run=args.dry_run)
    current_user = api.get("/api/v1/users/me/")
    print(f"authenticated user: {current_user.get('email', 'unknown')}")
    projects = ensure_projects(api, projects_spec)

    states = {}
    labels = {}
    modules = {}
    cycles = {}
    for project_name, project in projects.items():
        states[project_name] = ensure_states(api, project)
        labels[project_name] = ensure_labels(api, project, label_names)
        modules[project_name] = ensure_modules(api, project, projects_spec[project_name])
        cycles[project_name] = ensure_cycles(api, project, project_name, work_items)

    issues = ensure_work_items(api, projects, states, labels, work_items)
    assign_structure(api, projects, modules, cycles, issues, work_items)

    total = 0
    for project_name, project in projects.items():
        rows = api.list_all(f"/api/v1/workspaces/{WORKSPACE_SLUG}/projects/{project['id']}/work-items/")
        total += sum(1 for row in rows if str(row.get("name", "")).startswith("PMQMS-"))
    print(f"validation: projects={len(projects)} work_items={total}")
    print("milestones: skipped; Plane v1.4.1 API returns 404 for milestone/initiative endpoints")


if __name__ == "__main__":
    main()
