from __future__ import annotations

import base64
import email.utils as eut
import hashlib
import hmac
import json
import typing
import typing as t
import urllib.parse as urlparse

from httpx import URL
from httpx import AsyncClient
from httpx import Auth
from httpx import Request
from httpx import Response

from audex import utils
from audex.lib.restful import RESTfulMixin
from audex.lib.vpr import VPR
from audex.lib.vpr import VPRError
from audex.lib.vpr.xfyun.types import AudioPayload
from audex.lib.vpr.xfyun.types import AudioResource
from audex.lib.vpr.xfyun.types import CreateFeatureParams
from audex.lib.vpr.xfyun.types import CreateFeatureRequest
from audex.lib.vpr.xfyun.types import CreateFeatureResponse
from audex.lib.vpr.xfyun.types import CreateFeatureResult
from audex.lib.vpr.xfyun.types import CreateGroupParams
from audex.lib.vpr.xfyun.types import CreateGroupRequest
from audex.lib.vpr.xfyun.types import CreateGroupResponse
from audex.lib.vpr.xfyun.types import CreateGroupResult
from audex.lib.vpr.xfyun.types import RequestHeader
from audex.lib.vpr.xfyun.types import S782b4996CreateFeatureParams
from audex.lib.vpr.xfyun.types import S782b4996CreateGroupParams
from audex.lib.vpr.xfyun.types import S782b4996SearchScoreFeaParams
from audex.lib.vpr.xfyun.types import S782b4996UpdateFeatureParams
from audex.lib.vpr.xfyun.types import SearchScoreFeaParams
from audex.lib.vpr.xfyun.types import SearchScoreFeaRequest
from audex.lib.vpr.xfyun.types import SearchScoreFeaResponse
from audex.lib.vpr.xfyun.types import SearchScoreFeaResult
from audex.lib.vpr.xfyun.types import UpdateFeatureParams
from audex.lib.vpr.xfyun.types import UpdateFeatureRequest
from audex.lib.vpr.xfyun.types import UpdateFeatureResponse
from audex.lib.vpr.xfyun.types import UpdateFeatureResult


class XFYunAuth(Auth):
    def __init__(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def auth_flow(self, request: Request) -> t.Generator[Request, Response, None]:
        # Docs: https://www.xfyun.cn/doc/voiceservice/isv/API.html
        # Generate RFC 1123 date
        date = eut.formatdate(timeval=None, localtime=False, usegmt=True)

        # Parse URL components
        parsed_url = urlparse.urlparse(str(request.url))
        host = parsed_url.netloc
        request_line = f"{request.method} {parsed_url.path} HTTP/1.1"

        # Create the signature origin string
        sig_origin = f"host: {host}\ndate: {date}\n{request_line}"

        # Generate HMAC-SHA256 signature
        sig = hmac.new(
            self.api_secret.encode("utf-8"),
            sig_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        # Create the authorization origin string
        auth_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{sig}"'
        )

        # Base64 encode the signature
        authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")

        # Set params
        auth_params = {
            "authorization": authorization,
            "host": host,
            "date": date,
        }

        # Append auth params to URL
        if parsed_url.query:
            new_url = f"{request.url}&{urlparse.urlencode(auth_params)}"
        else:
            new_url = f"{request.url}?{urlparse.urlencode(auth_params)}"

        # Update request URL
        request.url = URL(new_url)

        yield request

    async def async_auth_flow(self, request: Request) -> typing.AsyncGenerator[Request, Response]:
        # Reuse the synchronous auth_flow logic
        auth_gen = self.auth_flow(request)
        try:
            while True:
                req = next(auth_gen)
                yield req
        except StopIteration:
            pass


class XFYunVPR(RESTfulMixin, VPR):
    __logtag__ = "vpr.xfyun"

    def __init__(
        self,
        *,
        endpoint: str = "/v1/private/s782b4996",
        app_id: str,
        api_key: str,
        api_secret: str,
        group_id: str | None = None,
        base_url: str = "https://api.xf-yun.com",
        proxy: str | URL | None = None,
        timeout: float = 10.0,
        http_client: AsyncClient | None = None,
        default_headers: dict[str, str] | None = None,
        default_params: dict[str, t.Any] | None = None,
    ):
        self.endpoint = endpoint
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.group_id = group_id
        self.auth = XFYunAuth(api_key=api_key, api_secret=api_secret)
        super().__init__(
            base_url=base_url,
            proxy=proxy,
            auth=self.auth,
            timeout=timeout,
            http_client=http_client,
            default_headers=default_headers,
            default_params=default_params,
        )

    async def create_group(self, name: str, gid: str | None = None) -> str:
        if self.group_id:
            raise VPRError("Group already exists, cannot create a new one.")
        group_id = gid or utils.gen_id()
        response = await self.request(
            endpoint=self.endpoint,
            method="POST",
            json=CreateGroupRequest(
                header=RequestHeader(app_id=self.app_id),
                parameter=CreateGroupParams(
                    s782b4996=S782b4996CreateGroupParams(group_id=group_id, group_name=name)
                ),
            ).model_dump(exclude_none=True),
            cast_to=CreateGroupResponse,
        )
        if response.header.code != 0:
            raise VPRError(f"Failed to create group: {response.header.message}")
        text = response.payload.create_group_res.text
        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        obj_json = json.loads(obj_str)
        obj = CreateGroupResult.model_validate(obj_json)
        if not group_id == obj.group_id:
            raise VPRError("Group ID mismatch after creation.")
        self.group_id = obj.group_id
        return self.group_id

    async def register(
        self, data: bytes, sr: t.Literal[8000, 16000], uid: str | None = None
    ) -> str:
        if not self.group_id:
            raise VPRError("Group ID is not set. Cannot register feature.")
        uid = uid or utils.gen_id()
        response = await self.request(
            endpoint=self.endpoint,
            method="POST",
            json=CreateFeatureRequest(
                header=RequestHeader(app_id=self.app_id),
                parameter=CreateFeatureParams(
                    s782b4996=S782b4996CreateFeatureParams(group_id=self.group_id, feature_id=uid)
                ),
                payload=AudioPayload(
                    resource=AudioResource(
                        audio=base64.b64encode(data).decode("utf-8"),
                        sample_rate=sr,
                    )
                ),
            ).model_dump(exclude_none=True),
            cast_to=CreateFeatureResponse,
        )
        if response.header.code != 0:
            raise VPRError(f"Failed to register feature: {response.header.message}")
        text = response.payload.create_feature_res.text
        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        obj_json = json.loads(obj_str)
        obj = CreateFeatureResult.model_validate(obj_json)
        if not uid == obj.feature_id:
            raise VPRError("Feature ID mismatch after registration.")
        return obj.feature_id

    async def update(self, uid: str, data: bytes, sr: t.Literal[8000, 16000]) -> None:
        if not self.group_id:
            raise VPRError("Group ID is not set. Cannot register feature.")
        response = await self.request(
            endpoint=self.endpoint,
            method="POST",
            json=UpdateFeatureRequest(
                header=RequestHeader(app_id=self.app_id),
                parameter=UpdateFeatureParams(
                    s782b4996=S782b4996UpdateFeatureParams(group_id=self.group_id, feature_id=uid)
                ),
                payload=AudioPayload(
                    resource=AudioResource(
                        audio=base64.b64encode(data).decode("utf-8"),
                        sample_rate=sr,
                    )
                ),
            ).model_dump(exclude_none=True),
            cast_to=UpdateFeatureResponse,
        )
        if response.header.code != 0:
            raise VPRError(f"Failed to update feature: {response.header.message}")
        text = response.payload.update_feature_res.text
        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        obj_json = json.loads(obj_str)
        obj = UpdateFeatureResult.model_validate(obj_json)
        if not uid == obj.feature_id:
            raise VPRError("Feature ID mismatch after update.")

    async def verify(self, uid: str, data: bytes, sr: t.Literal[8000, 16000]) -> float:
        if not self.group_id:
            raise VPRError("Group ID is not set. Cannot verify feature.")
        response = await self.request(
            endpoint=self.endpoint,
            method="POST",
            json=SearchScoreFeaRequest(
                header=RequestHeader(app_id=self.app_id),
                parameter=SearchScoreFeaParams(
                    s782b4996=S782b4996SearchScoreFeaParams(
                        group_id=self.group_id, dst_feature_id=uid
                    )
                ),
                payload=AudioPayload(
                    resource=AudioResource(
                        audio=base64.b64encode(data).decode("utf-8"),
                        sample_rate=sr,
                    )
                ),
            ).model_dump(exclude_none=True),
            cast_to=SearchScoreFeaResponse,
        )
        if response.header.code != 0:
            raise VPRError(f"Failed to verify feature: {response.header.message}")
        text = response.payload.search_score_fea_res.text
        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        obj_json = json.loads(obj_str)
        obj = SearchScoreFeaResult.model_validate(obj_json)
        if not uid == obj.feature_id:
            raise VPRError("Feature ID mismatch after verification.")
        return obj.score
