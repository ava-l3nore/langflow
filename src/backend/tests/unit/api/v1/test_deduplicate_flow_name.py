"""A7 characterization tests for _deduplicate_flow_name."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from langflow.api.v1.flows_helpers import _deduplicate_flow_name
from langflow.services.database.models.flow.model import Flow
from langflow.services.database.models.user.model import User


async def _make_user(session, name):
    user = User(username=name, password="x", is_active=True)  # noqa: S106
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _add_flows(session, user_id, *names):
    for name in names:
        session.add(Flow(name=name, data={}, user_id=user_id))
    await session.commit()


@pytest.fixture
async def owner(async_session):
    return await _make_user(async_session, f"owner-{uuid4()}")


async def test_deduplicate_flow_name_when_name_unused_returns_name_unchanged(async_session, owner):
    assert await _deduplicate_flow_name(async_session, "My Flow", owner.id) == "My Flow"


async def test_deduplicate_flow_name_when_name_used_once_appends_one(async_session, owner):
    await _add_flows(async_session, owner.id, "My Flow")

    assert await _deduplicate_flow_name(async_session, "My Flow", owner.id) == "My Flow (1)"


async def test_deduplicate_flow_name_when_copies_have_gaps_uses_highest_plus_one(async_session, owner):
    await _add_flows(async_session, owner.id, "My Flow", "My Flow (1)", "My Flow (3)")

    assert await _deduplicate_flow_name(async_session, "My Flow", owner.id) == "My Flow (4)"


async def test_deduplicate_flow_name_when_suffix_is_not_a_number_ignores_it(async_session, owner):
    await _add_flows(async_session, owner.id, "My Flow", "My Flow (draft)")

    assert await _deduplicate_flow_name(async_session, "My Flow", owner.id) == "My Flow (1)"


async def test_deduplicate_flow_name_when_other_user_has_same_name_returns_name_unchanged(async_session, owner):
    other = await _make_user(async_session, f"other-{uuid4()}")
    await _add_flows(async_session, other.id, "My Flow")

    assert await _deduplicate_flow_name(async_session, "My Flow", owner.id) == "My Flow"


async def test_deduplicate_flow_name_when_conflict_and_fail_on_conflict_raises409(async_session, owner):
    await _add_flows(async_session, owner.id, "My Flow")

    with pytest.raises(HTTPException) as exc_info:
        await _deduplicate_flow_name(async_session, "My Flow", owner.id, fail_on_conflict=True)

    assert exc_info.value.status_code == 409
