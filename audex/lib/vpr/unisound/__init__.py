from __future__ import annotations

import base64
import hashlib
import typing as t
import uuid

from httpx import URL
from httpx import AsyncClient

from audex import utils
from audex.lib.restful import RESTfulMixin
from audex.lib.vpr import VPR
from audex.lib.vpr import VPRError
from audex.lib.vpr.unisound.types import ConfirmFeatureRequest
from audex.lib.vpr.unisound.types import ConfirmFeatureResponse
from audex.lib.vpr.unisound.types import CreateFeatureRequest
from audex.lib.vpr.unisound.types import CreateFeatureResponse
from audex.lib.vpr.unisound.types import CreateGroupRequest
from audex.lib.vpr.unisound.types import CreateGroupResponse
from audex.lib.vpr.unisound.types import UpdateFeatureRequest
from audex.lib.vpr.unisound.types import UpdateFeatureResponse


class UnisoundVPR(RESTfulMixin, VPR):
    __logtag__ = "audex.lib.vpr.unisound"

    def __init__(
        self,
        *,
        appkey: str,
        secret: str,
        group_id: str | None = None,
        base_url: str = "https://ai-vpr.hivoice.cn",
        proxy: str | URL | None = None,
        timeout: float = 10.0,
        http_client: AsyncClient | None = None,
        default_headers: dict[str, str] | None = None,
        default_params: dict[str, t.Any] | None = None,
    ):
        self.appkey = appkey
        self.secret = secret
        self.group_id = group_id
        super().__init__(
            base_url=base_url,
            proxy=proxy,
            timeout=timeout,
            http_client=http_client,
            default_headers=default_headers,
            default_params=default_params,
        )

    def _generate_sign(self, timestamp: int, nonce: str) -> str:
        """Generate signature for authentication."""
        sign_str = f"{self.appkey}{timestamp}{self.secret}{nonce}"
        return hashlib.sha256(sign_str.encode("utf-8")).hexdigest().upper()

    def _build_auth_params(self) -> dict[str, t.Any]:
        """Build authentication parameters."""
        timestamp = int(utils.utcnow().timestamp() * 1000)
        nonce = uuid.uuid4().hex
        sign = self._generate_sign(timestamp, nonce)
        return {
            "appkey": self.appkey,
            "timestamp": timestamp,
            "nonce": nonce,
            "sign": sign,
        }

    async def create_group(self, name: str, gid: str | None = None) -> str:
        if self.group_id:
            raise VPRError("Group already exists, cannot create a new one.")
        group_id = gid or utils.gen_id()
        auth_params = self._build_auth_params()

        response = await self.request(
            endpoint="/vpr/v1/createGroup",
            method="POST",
            json=CreateGroupRequest(
                **auth_params,
                group_id=group_id,
                group_info=name,
            ).model_dump(by_alias=True),
            cast_to=CreateGroupResponse,
        )

        if response.code != 0:
            raise VPRError(f"Failed to create group: [{response.code}] {response.msg}")

        if not response.data or response.data.group_id != group_id:
            raise VPRError("Group ID mismatch after creation.")

        self.group_id = group_id
        return self.group_id

    async def enroll(self, data: bytes, sr: str, uid: str | None = None) -> str:
        if not self.group_id:
            raise VPRError("Group ID is not set. Cannot enroll feature.")

        uid = uid or utils.gen_id()
        auth_params = self._build_auth_params()

        audio_data = base64.b64encode(data).decode("utf-8")

        response = await self.request(
            endpoint="/vpr/v1/createFeature",
            method="POST",
            json=CreateFeatureRequest(
                **auth_params,
                group_id=self.group_id,
                feature_id=uid,
                feature_info=f"Feature {uid}",
                audio_data=audio_data,
                audio_sample_rate=sr,
                audio_format="pcm",
            ).model_dump(by_alias=True),
            cast_to=CreateFeatureResponse,
        )

        if response.code != 0:
            raise VPRError(f"Failed to enroll feature: [{response.code}] {response.msg}")

        if not response.data or response.data.featureId != uid:
            raise VPRError("Feature ID mismatch after registration.")

        return uid

    async def update(self, uid: str, data: bytes, sr: int) -> None:
        if not self.group_id:
            raise VPRError("Group ID is not set. Cannot update feature.")

        auth_params = self._build_auth_params()

        audio_data = base64.b64encode(data).decode("utf-8")

        response = await self.request(
            endpoint="/vpr/v1/updateFeatureById",
            method="POST",
            json=UpdateFeatureRequest(
                **auth_params,
                group_id=self.group_id,
                feature_id=uid,
                feature_info=f"Updated feature {uid}",
                audio_data=audio_data,
                audio_sample_rate=sr,
                audio_format="pcm",
            ).model_dump(by_alias=True),
            cast_to=UpdateFeatureResponse,
        )

        if response.code != 0:
            raise VPRError(f"Failed to update feature: [{response.code}] {response.msg}")

        if not response.data or not response.data.result:
            raise VPRError("Feature update failed.")

    async def verify(self, uid: str, data: bytes, sr: str) -> float:
        if not self.group_id:
            raise VPRError("Group ID is not set. Cannot verify feature.")

        auth_params = self._build_auth_params()

        audio_data = base64.b64encode(data).decode("utf-8")

        response = await self.request(
            endpoint="/vpr/v1/confirmFeature",
            method="POST",
            json=ConfirmFeatureRequest(
                **auth_params,
                group_id=self.group_id,
                feature_id=uid,
                audio_data=audio_data,
                audio_sample_rate=sr,
                audio_format="pcm",
            ).model_dump(by_alias=True),
            cast_to=ConfirmFeatureResponse,
        )

        if response.code != 0:
            raise VPRError(f"Failed to verify feature: [{response.code}] {response.msg}")

        if not response.data:
            raise VPRError("No verification data returned.")

        return response.data.score  # type: ignore
