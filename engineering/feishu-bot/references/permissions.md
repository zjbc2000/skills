# 飞书权限 scopes 清单

飞书开放平台企业自建应用需在「权限管理」开通 scope 后，对应 API 才能用。报错 `99991672 Access denied` 时按响应里的提示链接补权限。

## 消息 / 群

| Scope | 用途 |
|---|---|
| `im:message` | 发送消息（**bot 回复必开**） |
| `im:message:send_as_bot` | 以 bot 身份发消息（部分版本用 `im:message` 即可） |
| `im:message:readonly` | 读取**历史消息**（排查 @、拿 sender.open_id、验证消息结构） |
| `im:message.group_msg:send_as_bot` | 群发消息（按需） |
| `im:chat.members:read` | 查群成员（**默认没有**；拿不到群成员 open_id，别依赖它做 @ 目标验证） |
| `im:chat:read` | 查群详情（默认没有） |

## 文件 / 文档

| Scope | 用途 |
|---|---|
| `im:resource` | 下载消息里的文件（筛选简历 PDF/zip 必开） |
| `docx:document` / `wiki:wiki` | 云文档 / 知识库（文档类 MCP 场景） |
| `bitable:app` | 多维表格 |

## 通讯录 / 用户

| Scope | 用途 |
|---|---|
| `contact:contact.base:readonly` | 查用户基础信息 |
| `contact:user.base:readonly` | 用户基础信息 |
| `contact:user.id:readonly` | 用户 ID |

## 事件订阅（长连接）

- 事件订阅必须切到 **「使用长连接接收事件」**（开放平台 → 事件与回调 → 订阅方式），否则 ws 收不到推送
- 长连接**无需**配置公网回调地址 / 端口映射

## 经验

- **最小权限集**（简历筛选 bot）：`im:message`（发）+ `im:resource`（下载文件）+ `im:message:readonly`（可选，排查用）
- 拿到 `Access denied` 的报错里会带权限申请链接（`open.feishu.cn/app/.../auth?q=...`），点开一键申请
- 权限变更在飞书开放平台可能需**发布版本**后才对正式环境生效（开发态自测不需要）
