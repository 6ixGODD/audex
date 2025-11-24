from __future__ import annotations

import typing as t

from pydantic import BaseModel
from pydantic import Field


# Base Authentication Parameters
class AuthParams(BaseModel):
    appkey: str = Field(
        ...,
        description="Application key",
    )
    timestamp: int = Field(
        ...,
        description="Access timestamp in milliseconds (UNIX timestamp)",
    )
    nonce: str = Field(
        ...,
        description="Random nonce, must change for each request",
    )
    sign: str = Field(
        ...,
        description="Signature for authentication",
    )


# Base Response
DataT = t.TypeVar("DataT")


class UnisoundResponse(BaseModel, t.Generic[DataT]):
    code: int = Field(
        ...,
        description="Error code, 0 indicates success",
    )
    msg: str = Field(
        ...,
        description="Response message",
    )
    sid: str = Field(
        ...,
        description="Unique session identifier",
    )
    data: DataT | None = Field(
        None,
        description="Response data body",
    )


# Create Group
class CreateGroupRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    group_info: str = Field(
        ...,
        serialization_alias="groupInfo",
        description="Voiceprint group information",
    )


class CreateGroupData(BaseModel):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    group_info: str = Field(
        ...,
        serialization_alias="groupInfo",
        description="Voiceprint group information",
    )


class CreateGroupResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: CreateGroupData | None = None


# Create Feature
class CreateFeatureRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    feature_info: str = Field(
        ...,
        serialization_alias="featureInfo",
        description="Voiceprint feature description",
    )
    audio_data: str = Field(
        ...,
        serialization_alias="audioData",
        description="Base64 encoded audio data",
    )
    audio_sample_rate: str = Field(
        ...,
        serialization_alias="audioSampleRate",
        description="Audio sample rate",
    )
    audio_format: t.Literal["pcm", "mp3", "opus", "adpcm"] = Field(
        ...,
        serialization_alias="audioFormat",
        description="Audio format",
    )


class CreateFeatureData(BaseModel):
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    feature_info: str = Field(
        ...,
        serialization_alias="featureInfo",
        description="Voiceprint feature information",
    )


class CreateFeatureResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: CreateFeatureData | None = None


# Update Feature
class UpdateFeatureRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    feature_info: str | None = Field(
        None,
        serialization_alias="featureInfo",
        description="Voiceprint feature description",
    )
    audio_data: str = Field(
        ...,
        serialization_alias="audioData",
        description="Base64 encoded audio data",
    )
    audio_sample_rate: int = Field(
        ...,
        serialization_alias="audioSampleRate",
        description="Audio sample rate",
    )
    audio_format: t.Literal["pcm", "mp3", "opus", "adpcm"] = Field(
        ...,
        serialization_alias="audioFormat",
        description="Audio format",
    )


class UpdateFeatureData(BaseModel):
    result: bool = Field(
        ...,
        description="Update result, true for success, false for failure",
    )


class UpdateFeatureResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: UpdateFeatureData | None = None


# Confirm Feature (1:1 Verification)
class ConfirmFeatureRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    audio_data: str = Field(
        ...,
        serialization_alias="audioData",
        description="Base64 encoded audio data",
    )
    audio_sample_rate: str = Field(
        ...,
        serialization_alias="audioSampleRate",
        description="Audio sample rate",
    )
    audio_format: t.Literal["pcm", "mp3", "opus", "adpcm"] = Field(
        ...,
        serialization_alias="audioFormat",
        description="Audio format",
    )


class ConfirmFeatureData(BaseModel):
    score: float = Field(
        ...,
        description="Similarity score, 0 indicates no match",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    feature_info: str = Field(
        ...,
        serialization_alias="featureInfo",
        description="Voiceprint feature information",
    )


class ConfirmFeatureResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: ConfirmFeatureData | None = None


# Identify Feature by Group ID (1:N Identification)
class IdentifyFeatureByGroupIdRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    top_n: int = Field(
        ...,
        serialization_alias="topN",
        ge=1,
        le=10,
        description="Number of top results to return",
    )
    audio_data: str = Field(
        ...,
        serialization_alias="audioData",
        description="Base64 encoded audio data",
    )
    audio_sample_rate: t.Literal[8000, 16000] = Field(
        ...,
        serialization_alias="audioSampleRate",
        description="Audio sample rate",
    )
    audio_format: t.Literal["pcm", "mp3", "opus", "adpcm"] = Field(
        ...,
        serialization_alias="audioFormat",
        description="Audio format",
    )


class IdentifyFeatureResult(BaseModel):
    score: float = Field(
        ...,
        description="Similarity score, 0 indicates no match",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    feature_info: str = Field(
        ...,
        serialization_alias="featureInfo",
        description="Voiceprint feature information",
    )


class IdentifyFeatureByGroupIdResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: list[IdentifyFeatureResult] | None = None


# Identify Feature by IDs (1:N Identification)
class FeatureListItem(BaseModel):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )


class IdentifyFeatureByIdsRequest(AuthParams):
    feature_list: list[FeatureListItem] = Field(
        ...,
        serialization_alias="featureList",
        description="List of voiceprint feature IDs",
    )
    top_n: int = Field(
        ...,
        serialization_alias="topN",
        ge=1,
        le=10,
        description="Number of top results to return",
    )
    audio_data: str = Field(
        ...,
        serialization_alias="audioData",
        description="Base64 encoded audio data",
    )
    audio_sample_rate: t.Literal[8000, 16000] = Field(
        ...,
        serialization_alias="audioSampleRate",
        description="Audio sample rate",
    )
    audio_format: t.Literal["pcm", "mp3", "opus", "adpcm"] = Field(
        ...,
        serialization_alias="audioFormat",
        description="Audio format",
    )


class IdentifyFeatureByIdsResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: list[IdentifyFeatureResult] | None = None


# Delete Feature
class DeleteFeatureRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )


class DeleteFeatureData(BaseModel):
    result: bool = Field(
        ...,
        description="Deletion result, true for success, false for failure",
    )


class DeleteFeatureResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: DeleteFeatureData | None = None


# Delete Group
class DeleteGroupRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )


class DeleteGroupData(BaseModel):
    result: bool = Field(
        ...,
        description="Deletion result, true for success, false for failure",
    )


class DeleteGroupResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: DeleteGroupData | None = None


# Query Feature List
class QueryFeatureListRequest(AuthParams):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Voiceprint group ID",
    )


class FeatureInfo(BaseModel):
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Voiceprint feature ID",
    )
    feature_info: str = Field(
        ...,
        serialization_alias="featureInfo",
        description="Voiceprint feature information",
    )


class QueryFeatureListResponse(BaseModel):
    code: int
    msg: str
    sid: str
    data: list[FeatureInfo] | None = None
