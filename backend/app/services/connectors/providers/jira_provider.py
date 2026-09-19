"""Jira Enterprise Connector Provider.

Handles Jira Software project discovery, issue queries, sprint summaries,
and write operation proposals (with human-in-the-loop confirmation requirement).
"""
from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.models import ConnectorItem

log = logging.getLogger("novatech.connectors.jira")


class JiraProvider:
    @staticmethod
    def get_projects(company_id: str) -> list[dict[str, Any]]:
        return [
            {
                "key": "NOVA",
                "name": "NovaTech Enterprise Core",
                "lead": "Alex Chen",
                "issue_count": 42,
                "current_sprint": "Sprint 44",
                "category": "Software Engineering",
            },
            {
                "key": "SEC",
                "name": "Security & Compliance Governance",
                "lead": "Priya Sharma",
                "issue_count": 18,
                "current_sprint": "Continuous Security",
                "category": "InfoSec",
            },
            {
                "key": "DEVOPS",
                "name": "Cloud Infrastructure & Platform",
                "lead": "David Kim",
                "issue_count": 29,
                "current_sprint": "Infra Sprint 12",
                "category": "Platform",
            },
        ]

    @staticmethod
    def search_issues(
        db: Session,
        company_id: str,
        query: str | None = None,
        project: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        stmt = select(ConnectorItem).where(
            ConnectorItem.company_id == company_id,
            ConnectorItem.provider == "jira",
            ConnectorItem.item_type == "jira_issue",
        )
        items = db.scalars(stmt).all()
        results: list[dict[str, Any]] = []

        for item in items:
            meta = item.metadata_json or {}
            # filters
            if project and not item.external_id.startswith(project):
                continue
            if status and meta.get("status", "").lower() != status.lower():
                continue
            if priority and meta.get("priority", "").lower() != priority.lower():
                continue
            if query:
                q = query.lower()
                matched = (
                    q in item.title.lower()
                    or q in item.content.lower()
                    or q in item.external_id.lower()
                    or any(q in c.lower() for c in meta.get("components", []))
                )
                if not matched:
                    continue

            results.append({
                "key": item.external_id,
                "title": item.title,
                "summary": item.content,
                "status": meta.get("status", "Open"),
                "priority": meta.get("priority", "Medium"),
                "assignee": meta.get("assignee", "Unassigned"),
                "reporter": meta.get("reporter", "Unknown"),
                "sprint": meta.get("sprint", "Current"),
                "epic": meta.get("epic", ""),
                "components": meta.get("components", []),
                "url": item.url,
            })
            if len(results) >= limit:
                break

        return results

    @staticmethod
    def get_issue(db: Session, company_id: str, issue_key: str) -> dict[str, Any] | None:
        item = db.scalar(
            select(ConnectorItem).where(
                ConnectorItem.company_id == company_id,
                ConnectorItem.external_id == issue_key.upper(),
            )
        )
        if not item:
            return None
        meta = item.metadata_json or {}
        return {
            "key": item.external_id,
            "title": item.title,
            "description": item.content,
            "status": meta.get("status", "Open"),
            "priority": meta.get("priority", "Medium"),
            "assignee": meta.get("assignee", "Unassigned"),
            "sprint": meta.get("sprint", "Sprint 44"),
            "epic": meta.get("epic", ""),
            "components": meta.get("components", []),
            "url": item.url,
        }

    @staticmethod
    def prepare_create_issue_proposal(
        project: str,
        title: str,
        description: str,
        priority: str = "High",
        issue_type: str = "Bug",
        assignee: str = "Alex Chen",
    ) -> dict[str, Any]:
        """Prepares an explicit human confirmation proposal for creating a Jira ticket.

        Never writes directly without user confirmation.
        """
        return {
            "title": f"Create Jira Issue ({project})",
            "summary": f"Create {issue_type} ticket in project {project}",
            "fields": [
                ("Project", project),
                ("Issue Type", issue_type),
                ("Priority", priority),
                ("Assignee", assignee),
                ("Summary", title),
            ],
            "body": description,
            "warning": "Creating this ticket will notify project assignees and log a Jira audit event.",
            "editable": ["Summary", "body"],
        }
