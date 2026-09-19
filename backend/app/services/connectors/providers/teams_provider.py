"""Microsoft Teams Enterprise Connector Provider.

Handles channels, conversations, meeting discussions, and channel message posting
(requiring explicit confirmation for write actions).
"""
from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.models import ConnectorItem

log = logging.getLogger("novatech.connectors.teams")


class TeamsProvider:
    @staticmethod
    def get_channels(company_id: str) -> list[dict[str, Any]]:
        return [
            {"name": "#general", "team": "NovaTech Engineering", "purpose": "Company-wide engineering announcements", "members": 85},
            {"name": "#backend-platform", "team": "NovaTech Engineering", "purpose": "Core backend, database, and API discussions", "members": 24},
            {"name": "#security-eng", "team": "InfoSec & Governance", "purpose": "Vulnerability management, incident response, and audit triage", "members": 16},
        ]

    @staticmethod
    def search_messages(
        db: Session,
        company_id: str,
        query: str | None = None,
        channel: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        stmt = select(ConnectorItem).where(
            ConnectorItem.company_id == company_id,
            ConnectorItem.provider == "teams",
            ConnectorItem.item_type == "teams_message",
        )
        items = db.scalars(stmt).all()
        results: list[dict[str, Any]] = []

        for item in items:
            meta = item.metadata_json or {}
            if channel and channel.lower() not in meta.get("channel", "").lower():
                continue
            if query:
                q = query.lower()
                matched = q in item.title.lower() or q in item.content.lower() or q in item.author.lower()
                if not matched:
                    continue

            results.append({
                "id": item.external_id,
                "channel": meta.get("channel", "#general"),
                "team": meta.get("team", "NovaTech Engineering"),
                "author": item.author,
                "message": item.content,
                "thread_id": meta.get("thread_id", ""),
                "replies_count": meta.get("replies_count", 0),
                "url": item.url,
            })
            if len(results) >= limit:
                break

        return results

    @staticmethod
    def prepare_post_message_proposal(
        channel: str,
        message: str,
        team: str = "NovaTech Engineering",
    ) -> dict[str, Any]:
        """Prepares a human confirmation proposal for posting a message to Teams."""
        return {
            "title": f"Post message to Teams ({channel})",
            "summary": f"Post notification to {channel} in {team}",
            "fields": [
                ("Team", team),
                ("Channel", channel),
            ],
            "body": message,
            "warning": "This message will be visible to all members of the channel.",
            "editable": ["body"],
        }
