"""Microsoft Outlook Enterprise Connector Provider.

Handles mailbox searches, email threads, calendar events, and draft/send operations.
Sending emails always requires explicit human confirmation.
"""
from __future__ import annotations

import logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ....db.models import ConnectorItem

log = logging.getLogger("novatech.connectors.outlook")


class OutlookProvider:
    @staticmethod
    def search_emails(
        db: Session,
        company_id: str,
        query: str | None = None,
        sender: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        stmt = select(ConnectorItem).where(
            ConnectorItem.company_id == company_id,
            ConnectorItem.provider == "outlook",
            ConnectorItem.item_type == "email",
        )
        items = db.scalars(stmt).all()
        results: list[dict[str, Any]] = []

        for item in items:
            meta = item.metadata_json or {}
            if sender and sender.lower() not in meta.get("sender", "").lower():
                continue
            if query:
                q = query.lower()
                matched = q in item.title.lower() or q in item.content.lower() or q in item.author.lower()
                if not matched:
                    continue

            results.append({
                "id": item.external_id,
                "subject": item.title,
                "body_preview": item.content[:240] + ("..." if len(item.content) > 240 else ""),
                "full_body": item.content,
                "sender": meta.get("sender", item.author),
                "recipients": meta.get("recipients", []),
                "thread_id": meta.get("thread_id", ""),
                "url": item.url,
            })
            if len(results) >= limit:
                break

        return results

    @staticmethod
    def get_calendar_events(
        db: Session,
        company_id: str,
        query: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        stmt = select(ConnectorItem).where(
            ConnectorItem.company_id == company_id,
            ConnectorItem.provider == "outlook",
            ConnectorItem.item_type == "meeting",
        )
        items = db.scalars(stmt).all()
        results: list[dict[str, Any]] = []

        for item in items:
            meta = item.metadata_json or {}
            if query and query.lower() not in item.title.lower() and query.lower() not in item.content.lower():
                continue
            results.append({
                "id": item.external_id,
                "title": item.title,
                "agenda": item.content,
                "starts_at": meta.get("starts_at", ""),
                "duration_minutes": meta.get("duration_minutes", 30),
                "organizer": meta.get("organizer", item.author),
                "location": meta.get("location", "Microsoft Teams Meeting"),
                "url": item.url,
            })
            if len(results) >= limit:
                break

        return results

    @staticmethod
    def prepare_send_email_proposal(
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
    ) -> dict[str, Any]:
        """Generates an action card proposal for sending an email.

        Never sends silently.
        """
        return {
            "title": "Ready to send email",
            "summary": f"Send email to {to}",
            "fields": [
                ("To", to),
                ("Cc", cc or "none"),
                ("Subject", subject),
            ],
            "body": body,
            "warning": "This will transmit an email from your enterprise Outlook mailbox.",
            "editable": ["Subject", "body"],
        }
