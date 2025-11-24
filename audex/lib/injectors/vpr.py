from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from audex.config import Config
    from audex.lib.vpr import VPR


def make_vpr(config: Config) -> VPR:
    if config.provider.vpr.provider == "xfyun":
        from audex.lib.vpr.xfyun import XFYunVPR

        return XFYunVPR(
            app_id=config.provider.vpr.xfyun.credential.app_id,
            api_key=config.provider.vpr.xfyun.credential.api_key,
            api_secret=config.provider.vpr.xfyun.credential.api_secret,
            group_id=config.provider.vpr.xfyun.group_id,
            proxy=config.provider.vpr.xfyun.http.proxy,
            timeout=config.provider.vpr.xfyun.http.timeout,
            default_headers=config.provider.vpr.xfyun.http.default_headers,
            default_params=config.provider.vpr.xfyun.http.default_params,
        )

    if config.provider.vpr.provider == "unisound":
        from audex.lib.vpr.unisound import UnisoundVPR

        return UnisoundVPR(
            appkey=config.provider.vpr.unisound.credential.appkey,
            secret=config.provider.vpr.unisound.credential.secret,
            group_id=config.provider.vpr.unisound.group_id,
            proxy=config.provider.vpr.unisound.http.proxy,
            timeout=config.provider.vpr.unisound.http.timeout,
            default_headers=config.provider.vpr.unisound.http.default_headers,
            default_params=config.provider.vpr.unisound.http.default_params,
        )

    return NotImplemented
