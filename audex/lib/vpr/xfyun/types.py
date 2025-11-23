from __future__ import annotations

import typing as t

from pydantic import BaseModel
from pydantic import Field


class RequestHeader(BaseModel):
    app_id: str = Field(
        ...,
        serialization_alias="app_id",
        description="Application ID obtained from XFYun platform",
    )
    status: t.Literal[3] = Field(
        default=3,
        description="Request status, value must be 3 (one-time transmission)",
    )


class XFYunResponseHeader(BaseModel):
    code: int = Field(
        ...,
        description="Response code, 0 indicates success",
    )
    message: str = Field(
        ...,
        description="Response message description",
    )
    sid: str = Field(
        ...,
        description="Unique session identifier for this request",
    )


class ResFormat(BaseModel):
    encoding: t.Literal["utf-8"] = Field(
        default="utf-8",
        description="Encoding format, fixed to utf-8",
    )
    compress: t.Literal["raw"] = Field(
        default="raw",
        description="Compression format, fixed to raw",
    )
    format: t.Literal["json"] = Field(
        default="json",
        description="Text format, fixed to json",
    )


class AudioResource(BaseModel):
    encoding: t.Literal["lame"] = Field(
        default="lame",
        description="Audio encoding format, fixed to lame (MP3)",
    )
    sample_rate: t.Literal[8000, 16000] = Field(
        default=16000,
        description="Audio sample rate in Hz, must be 16000",
    )
    channels: t.Literal[1] = Field(
        default=1,
        description="Audio channel count, fixed to 1 (mono)",
    )
    bit_depth: t.Literal[16] = Field(
        default=16,
        description="Audio bit depth, fixed to 16",
    )
    status: t.Literal[3] = Field(
        default=3,
        description="Audio data status, value must be 3 (one-time transmission)",
    )
    audio: str = Field(
        ...,
        description="Base64 encoded audio data, max size 4M after encoding",
    )


class AudioPayload(BaseModel):
    resource: AudioResource = Field(
        ...,
        description="Audio resource parameters",
    )


PayloadT = t.TypeVar("PayloadT", bound=BaseModel)


class XFYunResponse(BaseModel, t.Generic[PayloadT]):
    header: XFYunResponseHeader = Field(
        ...,
        description="Response header with platform parameters",
    )
    payload: PayloadT = Field(
        ...,
        description="Response payload data",
    )


class TextResult(BaseModel):
    text: str = Field(
        ...,
        description="Base64 encoded response data",
    )


# Create Group -----------------------------------------------------------------
class S782b4996CreateGroupParams(BaseModel):
    func: t.Literal["createGroup"] = Field(
        default="createGroup",
        description="Function identifier for creating voiceprint group",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Unique identifier for the group, supports letters, numbers and underscores, max length 32",
    )
    group_name: str | None = Field(
        default=None,
        serialization_alias="groupName",
        description="Name of the group, optional, length range 0-256",
    )
    group_info: str | None = Field(
        default=None,
        serialization_alias="groupInfo",
        description="Description information for the group, optional, length range 0-256",
    )
    create_group_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="createGroupRes",
        description="Expected response format configuration",
    )


class CreateGroupParams(BaseModel):
    s782b4996: S782b4996CreateGroupParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class CreateGroupRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: CreateGroupParams = Field(
        ...,
        description="Service feature parameters",
    )


class CreateGroupResult(BaseModel):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Created group unique identifier",
    )
    group_name: str | None = Field(
        default=None,
        serialization_alias="groupName",
        description="Created group name",
    )
    group_info: str | None = Field(
        default=None,
        serialization_alias="groupInfo",
        description="Created group description",
    )


class CreateGroupPayload(BaseModel):
    create_group_res: TextResult = Field(
        ...,
        serialization_alias="createGroupRes",
        description="Base64 encoded group creation result",
    )


class CreateGroupResponse(XFYunResponse[CreateGroupPayload]): ...


# Create Feature ---------------------------------------------------------------
class S782b4996CreateFeatureParams(BaseModel):
    func: t.Literal["createFeature"] = Field(
        default="createFeature",
        description="Function identifier for creating voiceprint feature",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID where the feature will be stored, max length 32",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Unique identifier for the feature, length range 0-32",
    )
    feature_info: str | None = Field(
        default=None,
        serialization_alias="featureInfo",
        description="Feature description, recommended to include timestamp, length range 0-256",
    )
    create_feature_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="createFeatureRes",
        description="Expected response format configuration",
    )


class CreateFeatureParams(BaseModel):
    s782b4996: S782b4996CreateFeatureParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class CreateFeatureRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: CreateFeatureParams = Field(
        ...,
        description="Service feature parameters",
    )
    payload: AudioPayload = Field(
        ...,
        description="Audio data payload",
    )


class CreateFeatureResult(BaseModel):
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Created feature unique identifier",
    )


class CreateFeaturePayload(BaseModel):
    create_feature_res: TextResult = Field(
        ...,
        serialization_alias="createFeatureRes",
        description="Base64 encoded feature creation result",
    )


class CreateFeatureResponse(XFYunResponse[CreateFeaturePayload]): ...


# Update Feature ---------------------------------------------------------------
class S782b4996UpdateFeatureParams(BaseModel):
    func: t.Literal["updateFeature"] = Field(
        default="updateFeature",
        description="Function identifier for updating voiceprint feature",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Group ID where the feature is stored, max length 32",
    )
    feature_id: str | None = Field(
        default=None,
        serialization_alias="featureId",
        description="Feature ID to update, length range 0-32",
    )
    feature_info: str | None = Field(
        default=None,
        serialization_alias="featureInfo",
        description="Updated feature description, recommended to include timestamp, length range 0-256",
    )
    cover: bool = Field(
        default=True,
        description="Update mode: True to overwrite existing feature, False to merge with existing feature",
    )
    update_feature_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="updateFeatureRes",
        description="Expected response format configuration",
    )


class UpdateFeatureParams(BaseModel):
    s782b4996: S782b4996UpdateFeatureParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class UpdateFeatureRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: UpdateFeatureParams = Field(
        ...,
        description="Service feature parameters",
    )
    payload: AudioPayload = Field(
        ...,
        description="Audio data payload",
    )


class UpdateFeatureResult(BaseModel):
    msg: str = Field(
        ...,
        description="Update result message, 'success' indicates successful update",
    )


class UpdateFeaturePayload(BaseModel):
    update_feature_res: TextResult = Field(
        ...,
        serialization_alias="updateFeatureRes",
        description="Base64 encoded feature update result",
    )


class UpdateFeatureResponse(XFYunResponse[UpdateFeaturePayload]): ...


# Query Feature List -----------------------------------------------------------
class S782b4996QueryFeatureListParams(BaseModel):
    func: t.Literal["queryFeatureList"] = Field(
        default="queryFeatureList",
        description="Function identifier for querying feature list",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID to query features from, max length 32",
    )
    query_feature_list_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="queryFeatureListRes",
        description="Expected response format configuration",
    )


class QueryFeatureListParams(BaseModel):
    s782b4996: S782b4996QueryFeatureListParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class QueryFeatureListRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: QueryFeatureListParams = Field(
        ...,
        description="Service feature parameters",
    )


class FeatureInfo(BaseModel):
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Unique feature identifier",
    )
    feature_info: str | None = Field(
        None,
        serialization_alias="featureInfo",
        description="Feature description, recommended to include timestamp for easy identification",
    )


class QueryFeatureListResult(BaseModel):
    __root__: list[FeatureInfo]


class QueryFeatureListPayload(BaseModel):
    query_feature_list_res: TextResult = Field(
        ...,
        serialization_alias="queryFeatureListRes",
        description="Base64 encoded feature list",
    )


class QueryFeatureListResponse(XFYunResponse[QueryFeatureListPayload]): ...


# Search Score Feature (1:1 Verification) --------------------------------------
class S782b4996SearchScoreFeaParams(BaseModel):
    func: t.Literal["searchScoreFea"] = Field(
        default="searchScoreFea",
        description="Function identifier for 1:1 feature verification",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID where the target feature is stored, max length 32",
    )
    dst_feature_id: str = Field(
        ...,
        serialization_alias="dstFeatureId",
        max_length=32,
        description="Target feature ID to compare against, length range 0-32",
    )
    search_score_fea_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="searchScoreFeaRes",
        description="Expected response format configuration",
    )


class SearchScoreFeaParams(BaseModel):
    s782b4996: S782b4996SearchScoreFeaParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class SearchScoreFeaRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: SearchScoreFeaParams = Field(
        ...,
        description="Service feature parameters",
    )
    payload: AudioPayload = Field(
        ...,
        description="Audio data payload for comparison",
    )


class SearchScoreFeaResult(BaseModel):
    score: float = Field(
        ...,
        description="Similarity score, normal range 0-1 (precise to 2 decimal places), full range -1 to 1. Score 0.6-1 recommended for verification pass",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Target feature unique identifier",
    )
    feature_info: str | None = Field(
        None,
        serialization_alias="featureInfo",
        description="Target feature description",
    )


class SearchScoreFeaPayload(BaseModel):
    search_score_fea_res: TextResult = Field(
        ...,
        serialization_alias="searchScoreFeaRes",
        description="Base64 encoded comparison result",
    )


class SearchScoreFeaResponse(XFYunResponse[SearchScoreFeaPayload]): ...


# Search Feature (1:N Identification) ------------------------------------------
class S782b4996SearchFeaParams(BaseModel):
    func: t.Literal["searchFea"] = Field(
        default="searchFea",
        description="Function identifier for 1:N feature identification",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID to search features in, max length 32",
    )
    top_k: int = Field(
        ...,
        serialization_alias="topK",
        description="Number of top matching features to return, max 10 (requires sufficient features in the group)",
    )
    search_fea_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="searchFeaRes",
        description="Expected response format configuration",
    )


class SearchFeaParams(BaseModel):
    s782b4996: S782b4996SearchFeaParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class SearchFeaRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: SearchFeaParams = Field(
        ...,
        description="Service feature parameters",
    )
    payload: AudioPayload = Field(
        ...,
        description="Audio data payload for identification",
    )


class ScoreItem(BaseModel):
    score: float = Field(
        ...,
        description="Similarity score, normal range 0-1 (precise to 2 decimal places), full range -1 to 1",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Matched feature unique identifier",
    )
    feature_info: str | None = Field(
        None,
        serialization_alias="featureInfo",
        description="Matched feature description",
    )


class SearchFeaResult(BaseModel):
    score_list: list[ScoreItem] = Field(
        ...,
        serialization_alias="scoreList",
        description="List of top K matching features ordered by similarity score (descending)",
    )


class SearchFeaPayload(BaseModel):
    search_fea_res: TextResult = Field(
        ...,
        serialization_alias="searchFeaRes",
        description="Base64 encoded search results",
    )


class SearchFeaResponse(XFYunResponse[SearchFeaPayload]): ...


# Delete Feature ---------------------------------------------------------------
class S782b4996DeleteFeatureParams(BaseModel):
    func: t.Literal["deleteFeature"] = Field(
        default="deleteFeature",
        description="Function identifier for deleting voiceprint feature",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID where the feature is stored, max length 32",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Feature ID to delete, length range 1-32",
    )
    delete_feature_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="deleteFeatureRes",
        description="Expected response format configuration",
    )


class DeleteFeatureParams(BaseModel):
    s782b4996: S782b4996DeleteFeatureParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class DeleteFeatureRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: DeleteFeatureParams = Field(
        ...,
        description="Service feature parameters",
    )


class DeleteFeatureResult(BaseModel):
    msg: str = Field(
        ...,
        description="Deletion result message, 'success' indicates successful deletion",
    )


class DeleteFeaturePayload(BaseModel):
    delete_feature_res: TextResult = Field(
        ...,
        serialization_alias="deleteFeatureRes",
        description="Base64 encoded deletion result",
    )


class DeleteFeatureResponse(XFYunResponse[DeleteFeaturePayload]): ...


# Delete Group -----------------------------------------------------------------
class S782b4996DeleteGroupParams(BaseModel):
    func: t.Literal["deleteGroup"] = Field(
        default="deleteGroup",
        description="Function identifier for deleting voiceprint group",
    )
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID to delete, max length 32",
    )
    delete_group_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="deleteGroupRes",
        description="Expected response format configuration",
    )


class DeleteGroupParams(BaseModel):
    s782b4996: S782b4996DeleteGroupParams = Field(
        ...,
        description="Service-specific parameters for voiceprint recognition",
    )


class DeleteGroupRequest(BaseModel):
    header: RequestHeader = Field(
        ...,
        description="Request header with platform parameters",
    )
    parameter: DeleteGroupParams = Field(
        ...,
        description="Service feature parameters",
    )


class DeleteGroupResult(BaseModel):
    msg: str = Field(
        ...,
        description="Deletion result message, 'success' indicates successful deletion of voiceprint group",
    )


class DeleteGroupPayload(BaseModel):
    delete_group_res: TextResult = Field(
        ...,
        serialization_alias="deleteGroupRes",
        description="Base64 encoded deletion result",
    )


class DeleteGroupResponse(XFYunResponse[DeleteGroupPayload]): ...
