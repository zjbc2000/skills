# 飞书事件结构（事件层）

lark-oapi（`lark_oapi` Python SDK）长连接消息事件 `im.message.receive_v1` 的反序列化模型。

## 模型树

```
P2ImMessageReceiveV1Data          # 事件体 = data.event
├── sender    : EventSender       # ★ 发送者在这里（事件层，不在 message 里）
│   ├── sender_id   : UserId      # open_id / union_id / user_id
│   ├── sender_type : str         # "user" / "app"（bot 自己发的消息）
│   └── tenant_key  : str
└── message   : EventMessage      # 消息内容（无 sender 字段！）
    ├── message_id  : str
    ├── chat_id     : str
    ├── chat_type   : str
    ├── message_type: str         # "text" / "file" / ...
    ├── content     : str         # JSON 字符串，需 json.loads
    └── create_time : int
```

## 内容字段（content 的 JSON）

- 文本：`{"text": "..."}`
- 文件：`{"file_key": "...", "file_name": "..."}`

## 关键坑

- **`EventMessage` 没有 `sender` 字段**——从 `data.event.message.sender` 找发送者必然得到 None，@ 静默不渲染（无报错）。
- **`Sender` 类（字段 `id`）是另一套模型**（`im:chat` 成员等 API 返回），与事件里的 `EventSender`（字段 `sender_id`）不同，别混用。
- `content` 是 JSON 字符串，解析失败要容错（返回空 dict，不崩）。

## 注册与启动骨架

```python
import lark_oapi
from lark_oapi.api.im.v1 import GetMessageResourceRequest, CreateMessageRequest, CreateMessageRequestBody

client = lark_oapi.Client.builder().app_id(app_id).app_secret(app_secret).build()

def on_message(data):
    sender = getattr(data.event, "sender", None)          # EventSender
    open_id = _extract_sender_open_id(sender)             # sender.sender_id.open_id
    msg = data.event.message                              # EventMessage
    parsed = parse_message({
        "message_id": msg.message_id,
        "chat_id": msg.chat_id,
        "msg_type": getattr(msg, "message_type", ""),
        "content": msg.content,
        "sender": {"sender_id": {"open_id": open_id}},
    })
    handler(parsed)

dispatcher = (
    lark_oapi.EventDispatcherHandler.builder("", "")
    .register_p2_im_message_receive_v1(on_message)
    .build()
)
ws = lark_oapi.ws.Client(app_id, app_secret, event_handler=dispatcher)
ws.start()  # 阻塞；长连接，无需端口映射 / 公网回调
```

## 发送消息

```python
body = (CreateMessageRequestBody.builder()
        .receive_id(chat_id).msg_type("text")
        .content(json.dumps({"text": text}, ensure_ascii=False)).build())
req = (CreateMessageRequest.builder()
       .receive_id_type("chat_id").request_body(body).build())
resp = client.im.v1.message.create(req)
if not resp.success():
    raise RuntimeError(f"发送失败: {resp.code} {resp.msg}")
```

## 下载消息文件（筛选场景）

```python
from lark_oapi.api.im.v1 import GetMessageResourceRequest
req = (GetMessageResourceRequest.builder()
       .message_id(message_id).file_key(file_key).type("file").build())
resp = client.im.v1.message_resource.get(req)   # resp.file 即二进制 IO 流
```

## 事件层提取纯函数（可测）

```python
def _extract_sender_open_id(sender) -> str:
    """EventSender.sender_id.open_id；None 安全降级。"""
    if sender is None:
        return ""
    sender_id = getattr(sender, "sender_id", None)
    if sender_id is None:
        return ""
    return getattr(sender_id, "open_id", "") or ""
```
