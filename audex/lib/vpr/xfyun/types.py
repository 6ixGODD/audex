from __future__ import annotations

import typing as t

from pydantic import BaseModel
from pydantic import Field


class RequestHeader(BaseModel):
    app_id: str = Field(
        ...,
        serialization_alias="app_id",
        description="Application ID from XFYun platform",
    )
    status: t.Literal[3] = 3


class XFYunResponseHeader(BaseModel):
    code: int
    message: str
    sid: str


class ResFormat(BaseModel):
    encoding: t.Literal["utf-8"] = "utf-8"
    compress: t.Literal["raw"] = "raw"
    format: t.Literal["json"] = "json"


class AudioResource(BaseModel):
    encoding: t.Literal["lame"] = "lame"
    sample_rate: t.Literal[8000, 16000] = 16000
    channels: t.Literal[1] = 1
    bit_depth: t.Literal[16] = 16
    status: t.Literal[3] = 3
    audio: str = Field(..., description="Base64 encoded audio data")


class AudioPayload(BaseModel):
    resource: AudioResource


PayloadT = t.TypeVar("PayloadT", bound=BaseModel)


class XFYunResponse(BaseModel, t.Generic[PayloadT]):
    header: XFYunResponseHeader
    payload: PayloadT


class TextResult(BaseModel):
    text: str = Field(..., description="Base64 encoded response data")


# Create Group -----------------------------------------------------------------
class S782b4996CreateGroupParams(BaseModel):
    func: t.Literal["createGroup"] = "createGroup"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Unique identifier for the group, supports letters, numbers and underscores",
    )
    group_name: str | None = Field(
        default=None,
        serialization_alias="groupName",
        description="Name of the group, optional",
    )
    group_info: str | None = Field(
        default=None,
        serialization_alias="groupInfo",
        description="Description information for the group, optional",
    )
    create_group_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="createGroupRes",
        description="Expected response format",
    )


class CreateGroupParams(BaseModel):
    s782b4996: S782b4996CreateGroupParams


class CreateGroupRequest(BaseModel):
    header: RequestHeader
    parameter: CreateGroupParams


class CreateGroupResult(BaseModel):
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Created group ID",
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
    func: t.Literal["createFeature"] = "createFeature"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID where the feature will be stored",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Unique identifier for the feature",
    )
    feature_info: str | None = Field(
        default=None,
        serialization_alias="featureInfo",
        description="Feature description, recommended to include timestamp",
    )
    create_feature_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="createFeatureRes",
        description="Expected response format",
    )


class CreateFeatureParams(BaseModel):
    s782b4996: S782b4996CreateFeatureParams


class CreateFeatureRequest(BaseModel):
    header: RequestHeader
    parameter: CreateFeatureParams
    payload: AudioPayload


class CreateFeatureResult(BaseModel):
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Created feature ID",
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
    func: t.Literal["updateFeature"] = "updateFeature"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Group ID where the feature is stored",
    )
    feature_id: str | None = Field(
        default=None,
        serialization_alias="featureId",
        description="Feature ID to update",
    )
    feature_info: str | None = Field(
        default=None,
        serialization_alias="featureInfo",
        description="Updated feature description",
    )
    cover: bool = Field(
        default=True,
        description="Update mode: True to overwrite, False to merge with existing feature",
    )
    update_feature_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="updateFeatureRes",
        description="Expected response format",
    )


class UpdateFeatureParams(BaseModel):
    s782b4996: S782b4996UpdateFeatureParams


class UpdateFeatureRequest(BaseModel):
    header: RequestHeader
    parameter: UpdateFeatureParams
    payload: AudioPayload


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
    func: t.Literal["queryFeatureList"] = "queryFeatureList"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID to query features from",
    )
    query_feature_list_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="queryFeatureListRes",
        description="Expected response format",
    )


class QueryFeatureListParams(BaseModel):
    s782b4996: S782b4996QueryFeatureListParams


class QueryFeatureListRequest(BaseModel):
    header: RequestHeader
    parameter: QueryFeatureListParams


class FeatureInfo(BaseModel):
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Unique feature identifier",
    )
    feature_info: str | None = Field(
        None,
        serialization_alias="featureInfo",
        description="Feature description",
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


# Search Score Feature ---------------------------------------------------------
class S782b4996SearchScoreFeaParams(BaseModel):
    func: t.Literal["searchScoreFea"] = "searchScoreFea"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID where the target feature is stored",
    )
    dst_feature_id: str = Field(
        ...,
        serialization_alias="dstFeatureId",
        max_length=32,
        description="Target feature ID to compare against",
    )
    search_score_fea_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="searchScoreFeaRes",
        description="Expected response format",
    )


class SearchScoreFeaParams(BaseModel):
    s782b4996: S782b4996SearchScoreFeaParams


class SearchScoreFeaRequest(BaseModel):
    header: RequestHeader
    parameter: SearchScoreFeaParams
    payload: AudioPayload


class SearchScoreFeaResult(BaseModel):
    score: float = Field(
        ...,
        description="Similarity score between -1 and 1, normal range 0-1",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Target feature ID",
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


# Search Feature ---------------------------------------------------------------
class S782b4996SearchFeaParams(BaseModel):
    func: t.Literal["searchFea"] = "searchFea"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID to search features in",
    )
    top_k: int = Field(
        ...,
        serialization_alias="topK",
        description="Number of top matching features to return, max 10",
    )
    search_fea_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="searchFeaRes",
        description="Expected response format",
    )


class SearchFeaParams(BaseModel):
    s782b4996: S782b4996SearchFeaParams


class SearchFeaRequest(BaseModel):
    header: RequestHeader
    parameter: SearchFeaParams
    payload: AudioPayload


class ScoreItem(BaseModel):
    score: float = Field(
        ...,
        description="Similarity score between -1 and 1, normal range 0-1",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Matched feature ID",
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
        description="List of top K matching features ordered by similarity",
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
    func: t.Literal["deleteFeature"] = "deleteFeature"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID where the feature is stored",
    )
    feature_id: str = Field(
        ...,
        serialization_alias="featureId",
        description="Feature ID to delete",
    )
    delete_feature_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="deleteFeatureRes",
        description="Expected response format",
    )


class DeleteFeatureParams(BaseModel):
    s782b4996: S782b4996DeleteFeatureParams


class DeleteFeatureRequest(BaseModel):
    header: RequestHeader
    parameter: DeleteFeatureParams


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
    func: t.Literal["deleteGroup"] = "deleteGroup"
    group_id: str = Field(
        ...,
        serialization_alias="groupId",
        description="Group ID to delete",
    )
    delete_group_res: ResFormat = Field(
        default_factory=ResFormat,
        serialization_alias="deleteGroupRes",
        description="Expected response format",
    )


class DeleteGroupParams(BaseModel):
    s782b4996: S782b4996DeleteGroupParams


class DeleteGroupRequest(BaseModel):
    header: RequestHeader
    parameter: DeleteGroupParams


class DeleteGroupResult(BaseModel):
    msg: str = Field(
        ...,
        description="Deletion result message, 'success' indicates successful deletion",
    )


class DeleteGroupPayload(BaseModel):
    delete_group_res: TextResult = Field(
        ...,
        serialization_alias="deleteGroupRes",
        description="Base64 encoded deletion result",
    )


class DeleteGroupResponse(XFYunResponse[DeleteGroupPayload]): ...
