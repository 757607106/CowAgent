"""
channel factory
"""
from common import const
from .channel import Channel


def create_channel(channel_type, *, singleton_key: str = "") -> Channel:
    """
    create a channel instance
    :param channel_type: channel type code
    :return: channel instance
    """
    ch = Channel()
    if channel_type == "terminal":
        from channel.terminal.terminal_channel import TerminalChannel
        ch = TerminalChannel()
    elif channel_type == 'web':
        from channel.web.web_channel import WebChannel
        ch = WebChannel()
    elif channel_type == "wechatmp":
        from channel.wechatmp.wechatmp_channel import WechatMPChannel
        ch = WechatMPChannel(passive_reply=True, _singleton_key=singleton_key)
    elif channel_type == "wechatmp_service":
        from channel.wechatmp.wechatmp_channel import WechatMPChannel
        ch = WechatMPChannel(passive_reply=False, _singleton_key=singleton_key)
    elif channel_type == "wechatcom_app":
        from channel.wechatcom.wechatcomapp_channel import WechatComAppChannel
        ch = WechatComAppChannel(_singleton_key=singleton_key)
    elif channel_type == const.FEISHU:
        from channel.feishu.feishu_channel import FeiShuChanel
        ch = FeiShuChanel(_singleton_key=singleton_key)
    elif channel_type == const.DINGTALK:
        from channel.dingtalk.dingtalk_channel import DingTalkChanel
        ch = DingTalkChanel(_singleton_key=singleton_key)
    elif channel_type == const.WECOM_BOT:
        from channel.wecom_bot.wecom_bot_channel import WecomBotChannel
        ch = WecomBotChannel(_singleton_key=singleton_key)
    elif channel_type == const.QQ:
        from channel.qq.qq_channel import QQChannel
        ch = QQChannel(_singleton_key=singleton_key)
    elif channel_type in (const.WEIXIN, "wx"):
        from channel.weixin.weixin_channel import WeixinChannel
        ch = WeixinChannel(_singleton_key=singleton_key)
        channel_type = const.WEIXIN
    else:
        raise RuntimeError
    ch.channel_type = channel_type
    return ch
