"""Tests for Natural-Language Intent and Action Detection."""
from datetime import date
import pytest

from app.services.intent import detect_intent_and_action, detect_intent_offline
from app.services.agent import run_agent
from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import principal_from_user

BASE_DATE = date(2026, 9, 19)  # Saturday


def test_leave_intent_full_extraction():
    q = "Apply leave for 2 days from tomorrow because I have a family function."
    res = detect_intent_offline(q, BASE_DATE)
    assert res["intent"] == "APPLY_LEAVE"
    assert res["status"] == "READY"
    assert res["action"] == "create_leave_request"
    assert res["start_date"] == "2026-09-20"
    assert res["duration_days"] == 2
    assert res["leave_type"] == "casual"
    assert "Family function" in res["reason"]


def test_leave_intent_natural_variations():
    variations = [
        ("I need leave tomorrow.", "2026-09-20", 1),
        ("Apply casual leave for 2 days starting Monday.", "2026-09-21", 2),
        ("I won't be available tomorrow due to a family function.", "2026-09-20", 1),
        ("Apply leave from September 22 to September 25 due to personal reasons.", "2026-09-22", 4),
    ]
    for text, expected_start, expected_days in variations:
        res = detect_intent_offline(text, BASE_DATE)
        assert res["intent"] == "APPLY_LEAVE"
        assert res["status"] == "READY"
        assert res["action"] == "create_leave_request"
        assert res["start_date"] == expected_start
        assert res["duration_days"] == expected_days


def test_leave_intent_clarification_required():
    ambiguous = [
        "I want leave.",
        "Need some leave",
        "Give me leave for a few days.",
        "I need leave next week.",
        "Can you request three days of leave for me from next week?",
    ]
    for text in ambiguous:
        res = detect_intent_offline(text, BASE_DATE)
        assert res["intent"] == "APPLY_LEAVE"
        assert res["status"] == "CLARIFICATION_REQUIRED"
        assert res["action"] == "create_leave_request"
        assert res["clarification_question"] is not None


def test_check_access_intent():
    queries = [
        "Can I access the finance documents?",
        "Who can access finance documents?",
        "Do I have permission to view board minutes?",
    ]
    for q in queries:
        res = detect_intent_offline(q, BASE_DATE)
        assert res["intent"] == "CHECK_ACCESS"
        assert res["status"] == "READY"
        assert res["action"] == "check_permissions"
        assert "access" in res["query"].lower()


def test_policy_query_intent():
    queries = [
        "What is the company leave policy?",
        "Where can I find the remote work guidelines?",
        "Tell me about the code of conduct rules.",
    ]
    for q in queries:
        res = detect_intent_offline(q, BASE_DATE)
        assert res["intent"] == "POLICY_QUERY"
        assert res["status"] == "READY"
        assert res["action"] == "search_policies"


def test_knowledge_base_intent():
    queries = [
        "What are the active projects?",
        "Who is Rahul Sharma?",
        "Give me an overview of Project Phoenix.",
    ]
    for q in queries:
        res = detect_intent_offline(q, BASE_DATE)
        assert res["intent"] == "KNOWLEDGE_BASE_QUERY"
        assert res["status"] == "READY"
        assert res["action"] == "search_knowledge"


def test_general_query_intent():
    queries = [
        "Hello",
        "Good morning",
        "Thank you",
    ]
    for q in queries:
        res = detect_intent_offline(q, BASE_DATE)
        assert res["intent"] == "GENERAL_QUERY"
        assert res["status"] == "READY"
        assert res["action"] == "none"


def test_end_to_end_agent_intent_in_timeline_and_meta():
    with SessionLocal() as db:
        user = db.query(User).filter(User.employee_code == "NT-1042").first()
        p = principal_from_user(user, "NovaTech Solutions")

        # 1. Test ready leave request -> confirmation card created
        res1 = run_agent(db, p, "Apply leave for 2 days from tomorrow because I have a family function.",
                         conversation_id="test-intent-1", history=[])
        assert res1["meta"]["intent"] == "APPLY_LEAVE"
        assert res1["meta"]["action_selected"] == "create_leave_request"
        assert res1["meta"]["intent_status"] == "READY"
        assert res1["meta"]["timeline"][0]["key"] == "intent_detection"
        assert "APPLY_LEAVE" in res1["meta"]["timeline"][0]["label"]
        assert len(res1["actions"]) == 1
        assert res1["actions"][0].tool == "create_leave_request"

        # 2. Test ambiguous leave request -> clarification question returned, NO action card created
        res2 = run_agent(db, p, "I want leave.", conversation_id="test-intent-2", history=[])
        assert res2["meta"]["intent"] == "APPLY_LEAVE"
        assert res2["meta"]["intent_status"] == "CLARIFICATION_REQUIRED"
        assert "What date should the leave start" in res2["answer"]
        assert len(res2["actions"]) == 0

        # 3. Test check access -> grounded response + RBAC preserved
        res3 = run_agent(db, p, "Can I access the finance documents?", conversation_id="test-intent-3", history=[])
        assert res3["meta"]["intent"] == "CHECK_ACCESS"
        assert res3["meta"]["action_selected"] == "check_permissions"
        assert res3["meta"]["timeline"][0]["label"] == "Intent: CHECK_ACCESS"
