"""A7 red test: multi-flow ZIP export must keep every flow when names collide after sanitizing."""

import io
import zipfile
from uuid import uuid4

from langflow.api.v1.flows_helpers import _build_flows_download_response
from langflow.services.database.models.flow.model import Flow


async def test_download_zip_when_two_flow_names_sanitize_to_same_filename_keeps_both_flows(async_session, tmp_path):
    flows = [
        Flow(id=uuid4(), name="Q1/Q2", data={"nodes": [], "edges": []}),
        Flow(id=uuid4(), name="Q1_Q2", data={"nodes": [], "edges": []}),
    ]

    response = await _build_flows_download_response(async_session, flows, caller_id=uuid4())
    body = b"".join([chunk async for chunk in response.body_iterator])

    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        names = zf.namelist()
        zf.extractall(tmp_path)

    assert len(set(names)) == 2, f"ZIP entries collide: {names}"
    assert len(list(tmp_path.iterdir())) == 2
