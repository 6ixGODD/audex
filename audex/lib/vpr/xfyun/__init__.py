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
from httpx import HTTPStatusError
from httpx import Request
from httpx import Response
from tenacity import RetryError

from audex import utils
from audex.helper.mixin import LoggingMixin
from audex.lib.restful import RESTfulMixin
from audex.lib.vpr import VPR
from audex.lib.vpr import GroupAlreadyExistsError
from audex.lib.vpr import GroupNotFoundError
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


class XFYunAuth(LoggingMixin, Auth):
    __logtag__ = "audex.lib.vpr.xfyun.auth"

    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger.debug(f"Initialized XFYunAuth with api_key={api_key[:8]}*** (masked)")

    def auth_flow(self, request: Request) -> t.Generator[Request, Response, None]:
        self.logger.debug(f"Starting auth_flow for request: {request.method} {request.url}")

        # Docs: https://www.xfyun.cn/doc/voiceservice/isv/API.html
        # Generate RFC 1123 date
        date = eut.formatdate(timeval=None, localtime=False, usegmt=True)
        self.logger.debug(f"Generated RFC 1123 date: {date}")

        # Parse URL components
        parsed_url = urlparse.urlparse(str(request.url))
        host = parsed_url.netloc
        path = parsed_url.path
        request_line = f"{request.method} {path} HTTP/1.1"
        self.logger.debug("Parsed URL components:")
        self.logger.debug(f"  - Host: {host}")
        self.logger.debug(f"  - Path: {path}")
        self.logger.debug(f"  - Request-Line: {request_line}")

        # Create the signature origin string
        sig_origin = f"host: {host}\ndate: {date}\n{request_line}"
        self.logger.debug("Signature origin string (for HMAC):")
        self.logger.debug("\n" + sig_origin)

        # Generate HMAC-SHA256 signature
        self.logger.debug(
            f"Computing HMAC-SHA256 with api_secret={self.api_secret[:8]}*** (masked)"
        )
        sig_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            sig_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        self.logger.debug(f"HMAC-SHA256 raw digest (hex): {sig_sha.hex()}")
        self.logger.debug(f"HMAC-SHA256 raw digest length: {len(sig_sha)} bytes")

        # Base64 encode the signature
        sig = base64.b64encode(sig_sha).decode("utf-8")
        self.logger.debug(f"Base64-encoded signature: {sig}")
        self.logger.debug(f"Base64-encoded signature length: {len(sig)} chars")

        # Create the authorization origin string
        auth_origin = (
            f'api_key="{self.api_key}", '
            f'algorithm="hmac-sha256", '
            f'headers="host date request-line", '
            f'signature="{sig}"'
        )
        self.logger.debug("Authorization origin string (before base64):")
        self.logger.debug(auth_origin)
        self.logger.debug(f"Authorization origin string length: {len(auth_origin)} chars")

        # Base64 encode the authorization string
        authorization = base64.b64encode(auth_origin.encode("utf-8")).decode("utf-8")
        self.logger.debug(f"Base64-encoded authorization: {authorization}")
        self.logger.debug(f"Base64-encoded authorization length: {len(authorization)} chars")

        # Set params
        auth_params = {
            "authorization": authorization,
            "host": host,
            "date": date,
        }
        self.logger.debug("Auth parameters to append:")
        for key, value in auth_params.items():
            if key == "authorization":
                self.logger.debug(f"  - {key}: {value[:50]}... (truncated)")
            else:
                self.logger.debug(f"  - {key}: {value}")

        # Append auth params to URL
        if parsed_url.query:
            new_url = f"{request.url}&{urlparse.urlencode(auth_params)}"
            self.logger.debug("Appending auth params to existing query string")
        else:
            new_url = f"{request.url}?{urlparse.urlencode(auth_params)}"
            self.logger.debug("Adding auth params as new query string")

        self.logger.debug(f"Final authenticated URL (truncated): {new_url[:100]}...")

        # Update request URL
        request.url = URL(new_url)
        self.logger.debug("Successfully updated request URL with auth parameters")

        yield request

    async def async_auth_flow(self, request: Request) -> typing.AsyncGenerator[Request, Response]:
        self.logger.debug(f"Starting async_auth_flow for request: {request.method} {request.url}")
        # Reuse the synchronous auth_flow logic
        auth_gen = self.auth_flow(request)
        try:
            while True:
                req = next(auth_gen)
                self.logger.debug("Yielding authenticated request in async_auth_flow")
                yield req
        except StopIteration:
            self.logger.debug("Completed async_auth_flow")
            pass


class XFYunVPR(RESTfulMixin, VPR):
    __logtag__ = "audex.lib.vpr.xfyun"

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
        self.auth = XFYunAuth(api_key=api_key, api_secret=api_secret)

        RESTfulMixin.__init__(
            self,
            base_url=base_url,
            proxy=proxy,
            auth=self.auth,
            timeout=timeout,
            http_client=http_client,
            default_headers=default_headers,
            default_params=default_params,
        )
        VPR.__init__(self, group_id=group_id)
        self.logger.info("XFYunVPR client initialized successfully")

    async def create_group(self, name: str, gid: str | None = None) -> str:
        self.logger.info(f"Creating group with name='{name}', gid={gid or 'auto-generated'}")

        if self.group_id:
            error_msg = f"Group already exists (group_id={self.group_id}), cannot create a new one."
            self.logger.error(error_msg)
            raise GroupAlreadyExistsError(error_msg)

        group_id = gid or utils.gen_id()
        self.logger.debug(f"Using group_id: {group_id}")

        request = CreateGroupRequest(
            header=RequestHeader(app_id=self.app_id),
            parameter=CreateGroupParams(
                s782b4996=S782b4996CreateGroupParams(groupId=group_id, groupName=name)
            ),
        ).model_dump(exclude_none=True)

        self.logger.debug("Request payload (JSON):")
        self.logger.debug(json.dumps(request, indent=2, ensure_ascii=False))

        self.logger.debug(f"Sending create_group request to {self.endpoint}")

        try:
            response = await self.request(
                endpoint=self.endpoint,
                method="POST",
                json=request,
                cast_to=CreateGroupResponse,
                strict=False,
            )
        except HTTPStatusError as e:
            error_msg = f"HTTP error during create_group request: {e}"
            self.logger.bind(request=e.request.content, response=e.response.text).error(error_msg)
            raise VPRError(error_msg) from e
        except RetryError as e:
            error_msg = f"Retry error during verify request: {e}"
            self.logger.error(error_msg)
            raise VPRError(error_msg) from e

        self.logger.debug(
            f"Received response with code={response.header.code}, message='{response.header.message}'"
        )

        if response.header.code != 0:
            error_msg = (
                f"Failed to create group: {response.header.message} (code={response.header.code})"
            )
            self.logger.error(error_msg)
            raise VPRError(error_msg)

        text = response.payload.create_group_res.text
        self.logger.debug(f"Response payload text (base64): {text[:100]}... (truncated)")

        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        self.logger.debug(f"Decoded payload (JSON): {obj_str}")

        obj_json = json.loads(obj_str)
        obj = CreateGroupResult.model_validate(obj_json)
        self.logger.debug(f"Parsed CreateGroupResult: group_id={obj.group_id}")

        if group_id != obj.group_id:
            error_msg = f"Group ID mismatch after creation: expected={group_id}, got={obj.group_id}"
            self.logger.error(error_msg)
            raise VPRError(error_msg)

        self.group_id = obj.group_id
        self.logger.info(f"Group created successfully: group_id={self.group_id}, name='{name}'")
        return self.group_id

    async def enroll(self, data: bytes, sr: int, uid: str | None = None) -> str:
        self.logger.info(
            f"Enrolling feature with sr={sr}, uid={uid or 'auto-generated'}, data_size={len(data)} bytes"
        )

        if not self.group_id:
            error_msg = "Group ID is not set. Cannot enroll feature. Please create a group first."
            self.logger.error(error_msg)
            raise GroupNotFoundError(error_msg)

        uid = uid or utils.gen_id()
        self.logger.debug(f"Using feature_id (uid): {uid}")
        self.logger.debug(f"Target group_id: {self.group_id}")

        audio_b64 = base64.b64encode(data).decode("utf-8")
        self.logger.debug(f"Encoded audio data to base64: length={len(audio_b64)} chars")

        request_payload = CreateFeatureRequest(
            header=RequestHeader(app_id=self.app_id),
            parameter=CreateFeatureParams(
                s782b4996=S782b4996CreateFeatureParams(groupId=self.group_id, featureId=uid)
            ),
            payload=AudioPayload(resource=AudioResource(audio=audio_b64, sample_rate=sr)),
        ).model_dump(exclude_none=True)

        self.logger.debug(f"Sending enroll request to {self.endpoint}")

        try:
            response = await self.request(
                endpoint=self.endpoint,
                method="POST",
                json=request_payload,
                cast_to=CreateFeatureResponse,
            )
        except HTTPStatusError as e:
            error_msg = f"HTTP error during enroll request: {e}"
            self.logger.bind(request=e.request.content, response=e.response.text).error(error_msg)
            raise VPRError(error_msg) from e
        except RetryError as e:
            error_msg = f"Retry error during verify request: {e}"
            self.logger.error(error_msg)
            raise VPRError(error_msg) from e

        self.logger.debug(
            f"Received response with code={response.header.code}, message='{response.header.message}'"
        )

        if response.header.code != 0:
            error_msg = (
                f"Failed to enroll feature: {response.header.message} (code={response.header.code})"
            )
            self.logger.error(error_msg)
            raise VPRError(error_msg)

        text = response.payload.create_feature_res.text
        self.logger.debug(f"Response payload text (base64): {text[:100]}... (truncated)")

        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        self.logger.debug(f"Decoded payload (JSON): {obj_str}")

        obj_json = json.loads(obj_str)
        obj = CreateFeatureResult.model_validate(obj_json)
        self.logger.debug(f"Parsed CreateFeatureResult: feature_id={obj.feature_id}")

        if uid != obj.feature_id:
            error_msg = (
                f"Feature ID mismatch after registration: expected={uid}, got={obj.feature_id}"
            )
            self.logger.error(error_msg)
            raise VPRError(error_msg)

        self.logger.info(
            f"Feature enrolled successfully: feature_id={obj.feature_id}, group_id={self.group_id}"
        )
        return obj.feature_id

    async def update(self, uid: str, data: bytes, sr: int) -> None:
        self.logger.info(f"Updating feature: uid={uid}, sr={sr}, data_size={len(data)} bytes")

        if not self.group_id:
            error_msg = "Group ID is not set. Cannot update feature. Please create a group first."
            self.logger.error(error_msg)
            raise GroupNotFoundError(error_msg)

        self.logger.debug(f"Target group_id: {self.group_id}")

        audio_b64 = base64.b64encode(data).decode("utf-8")
        self.logger.debug(f"Encoded audio data to base64: length={len(audio_b64)} chars")

        request_payload = UpdateFeatureRequest(
            header=RequestHeader(app_id=self.app_id),
            parameter=UpdateFeatureParams(
                s782b4996=S782b4996UpdateFeatureParams(groupId=self.group_id, featureId=uid)
            ),
            payload=AudioPayload(resource=AudioResource(audio=audio_b64, sample_rate=sr)),
        ).model_dump(exclude_none=True)

        self.logger.debug(f"Sending update request to {self.endpoint}")

        try:
            response = await self.request(
                endpoint=self.endpoint,
                method="POST",
                json=request_payload,
                cast_to=UpdateFeatureResponse,
            )
        except HTTPStatusError as e:
            error_msg = f"HTTP error during update request: {e}"
            self.logger.bind(request=e.request.content, response=e.response.text).error(error_msg)
            raise VPRError(error_msg) from e
        except RetryError as e:
            error_msg = f"Retry error during verify request: {e}"
            self.logger.error(error_msg)
            raise VPRError(error_msg) from e

        self.logger.debug(
            f"Received response with code={response.header.code}, message='{response.header.message}'"
        )

        if response.header.code != 0:
            error_msg = (
                f"Failed to update feature: {response.header.message} (code={response.header.code})"
            )
            self.logger.error(error_msg)
            raise VPRError(error_msg)

        text = response.payload.update_feature_res.text
        self.logger.debug(f"Response payload text (base64): {text[:100]}... (truncated)")

        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        self.logger.debug(f"Decoded payload (JSON): {obj_str}")

        obj_json = json.loads(obj_str)
        obj = UpdateFeatureResult.model_validate(obj_json)
        self.logger.debug(f"Parsed UpdateFeatureResult: msg={obj.msg}")
        self.logger.info(
            f"Feature updated successfully: feature_id={uid}, group_id={self.group_id}"
        )

    async def verify(self, uid: str, data: bytes, sr: int) -> float:
        self.logger.info(f"Verifying feature: uid={uid}, sr={sr}, data_size={len(data)} bytes")

        if not self.group_id:
            error_msg = "Group ID is not set. Cannot verify feature. Please create a group first."
            self.logger.error(error_msg)
            raise GroupNotFoundError(error_msg)

        self.logger.debug(f"Target group_id: {self.group_id}")
        self.logger.debug(f"Target dst_feature_id: {uid}")

        audio_b64 = base64.b64encode(data).decode("utf-8")
        self.logger.debug(f"Encoded audio data to base64: length={len(audio_b64)} chars")

        request_payload = SearchScoreFeaRequest(
            header=RequestHeader(app_id=self.app_id),
            parameter=SearchScoreFeaParams(
                s782b4996=S782b4996SearchScoreFeaParams(groupId=self.group_id, dstFeatureId=uid)
            ),
            payload=AudioPayload(resource=AudioResource(audio=audio_b64, sample_rate=sr)),
        ).model_dump(exclude_none=True)

        self.logger.debug(f"Sending verify request to {self.endpoint}")

        try:
            response = await self.request(
                endpoint=self.endpoint,
                method="POST",
                json=request_payload,
                cast_to=SearchScoreFeaResponse,
            )
        except HTTPStatusError as e:
            error_msg = f"HTTP error during verify request: {e}"
            self.logger.bind(request=e.request.content, response=e.response.text).error(error_msg)
            raise VPRError(error_msg) from e
        except RetryError as e:
            error_msg = f"Retry error during verify request: {e}"
            self.logger.error(error_msg)
            raise VPRError(error_msg) from e

        self.logger.debug(
            f"Received response with code={response.header.code}, message='{response.header.message}'"
        )

        if response.header.code != 0:
            error_msg = (
                f"Failed to verify feature: {response.header.message} (code={response.header.code})"
            )
            self.logger.error(error_msg)
            raise VPRError(error_msg)

        text = response.payload.search_score_fea_res.text
        self.logger.debug(f"Response payload text (base64): {text[:100]}... (truncated)")

        # Base-64 decode the model from text
        obj_str = base64.b64decode(text).decode("utf-8")
        self.logger.debug(f"Decoded payload (JSON): {obj_str}")

        obj_json = json.loads(obj_str)
        obj = SearchScoreFeaResult.model_validate(obj_json)
        self.logger.bind(feature_id=uid, score=obj.score).debug(
            f"Parsed SearchScoreFeaResult: feature_id={obj.feature_id}, score={obj.score}"
        )

        if uid != obj.feature_id:
            error_msg = (
                f"Feature ID mismatch after verification: expected={uid}, got={obj.feature_id}"
            )
            self.logger.bind(expected=uid, got=obj.feature_id).error(error_msg)
            raise VPRError(error_msg)

        self.logger.bind(feature_id=uid, score=obj.score).info(
            f"Feature verified successfully: feature_id={uid}, score={obj.score}"
        )
        return obj.score
