"""A7 characterization tests for _read_flow_or_public (OSS mode, no authorization plugin)."""

from uuid import uuid4

import pytest
from langflow.api.v1.flows_helpers import _read_flow_or_public
from langflow.services.database.models.flow.model import AccessTypeEnum, Flow
from langflow.services.database.models.user.model import User


async def _make_user(session, name):
    user = User(username=name, password="x", is_active=True)  # noqa: S106
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_flow(session, *, owner_id, access_type):
    flow = Flow(name=f"flow-{uuid4()}", data={}, user_id=owner_id, access_type=access_type)
    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    return flow


@pytest.fixture
async def users(async_session):
    return await _make_user(async_session, "owner"), await _make_user(async_session, "stranger")


async def test_read_flow_or_public_when_user_owns_private_flow_returns_flow(async_session, users):
    owner, _ = users
    flow = await _make_flow(async_session, owner_id=owner.id, access_type=AccessTypeEnum.PRIVATE)

    result = await _read_flow_or_public(async_session, flow.id, owner.id)

    assert result is not None
    assert result.id == flow.id


async def test_read_flow_or_public_when_other_users_flow_is_public_returns_flow(async_session, users):
    owner, stranger = users
    flow = await _make_flow(async_session, owner_id=owner.id, access_type=AccessTypeEnum.PUBLIC)

    result = await _read_flow_or_public(async_session, flow.id, stranger.id)

    assert result is not None
    assert result.id == flow.id


async def test_read_flow_or_public_when_public_flow_has_no_owner_returns_flow(async_session, users):
    _, stranger = users
    flow = await _make_flow(async_session, owner_id=None, access_type=AccessTypeEnum.PUBLIC)

    result = await _read_flow_or_public(async_session, flow.id, stranger.id)

    assert result is not None
    assert result.id == flow.id


async def test_read_flow_or_public_when_private_flow_has_no_owner_returns_none(async_session, users):
    _, stranger = users
    flow = await _make_flow(async_session, owner_id=None, access_type=AccessTypeEnum.PRIVATE)

    assert await _read_flow_or_public(async_session, flow.id, stranger.id) is None


async def test_read_flow_or_public_when_other_users_flow_is_private_returns_none(async_session, users):
    owner, stranger = users
    flow = await _make_flow(async_session, owner_id=owner.id, access_type=AccessTypeEnum.PRIVATE)

    assert await _read_flow_or_public(async_session, flow.id, stranger.id) is None


async def test_read_flow_or_public_when_flow_id_does_not_exist_returns_none(async_session, users):
    owner, _ = users

    assert await _read_flow_or_public(async_session, uuid4(), owner.id) is None
