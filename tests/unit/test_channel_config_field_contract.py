from cow_platform.services.channel_config_service import ChannelConfigService


def test_channel_config_visible_fields_match_channel_docs() -> None:
    fields_by_channel = {
        item["channel_type"]: [field["key"] for field in item["fields"]]
        for item in ChannelConfigService().list_channel_type_defs()
    }

    assert fields_by_channel["weixin"] == []
    assert fields_by_channel["feishu"] == [
        "feishu_app_id",
        "feishu_app_secret",
        "feishu_bot_name",
    ]
    assert fields_by_channel["dingtalk"] == [
        "dingtalk_client_id",
        "dingtalk_client_secret",
    ]
    assert fields_by_channel["wecom_bot"] == [
        "wecom_bot_id",
        "wecom_bot_secret",
    ]
    assert fields_by_channel["qq"] == [
        "qq_app_id",
        "qq_app_secret",
    ]
    assert fields_by_channel["wechatcom_app"] == [
        "single_chat_prefix",
        "wechatcom_corp_id",
        "wechatcomapp_token",
        "wechatcomapp_secret",
        "wechatcomapp_agent_id",
        "wechatcomapp_aes_key",
        "wechatcomapp_port",
    ]
    assert fields_by_channel["wechatmp"] == [
        "single_chat_prefix",
        "wechatmp_app_id",
        "wechatmp_app_secret",
        "wechatmp_aes_key",
        "wechatmp_token",
        "wechatmp_port",
    ]
    assert fields_by_channel["wechatmp_service"] == fields_by_channel["wechatmp"]
