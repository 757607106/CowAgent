from bridge.file_reply import create_file_reply
from bridge.reply import ReplyType


def test_create_file_reply_preserves_text_for_image() -> None:
    reply = create_file_reply(
        {"file_type": "image", "path": "/tmp/out.png", "file_name": "out.png"},
        "done",
    )

    assert reply.type == ReplyType.IMAGE_URL
    assert reply.content == "file:///tmp/out.png"
    assert reply.text_content == "done"
    assert not hasattr(reply, "file_name")


def test_create_file_reply_uses_file_type_for_unknown_files() -> None:
    reply = create_file_reply({"file_type": "archive", "path": "/tmp/out.zip"}, "")

    assert reply.type == ReplyType.FILE
    assert reply.content == "file:///tmp/out.zip"
    assert reply.file_name == "out.zip"
