# 第6章精要：项目实战2——商业级 AI 图像生成平台

> 全章主旨：从 0 构建可商业化运营的完整产品（AI 功能+用户系统+计费+部署+邮件），验证"用 AI 辅助开发 + 无缝整合现代技术栈"。

## 6.1 项目规划
- 明确商业目标、核心功能与产品边界，作为后续实现的前提。来源：6.1

## 6.2 架构设计与技术选型
- **用结构化需求让 Cursor 生成技术架构**：明确技术栈（Next.js+Supabase+Stripe+Vercel）、核心需求（AI 功能：Replicate API 集成 NanoBanana 模型实现文生图/单图编辑/多图融合；用户系统：邮箱/社交登录+图片库；计费：积分购买），要求生成详细架构方案+核心集成的前后端通信接口（含数据结构：任务启动接口、Webhook 回调接口）。来源：6.2
- **@Web / useContext7**：Cursor 用 `@Web` 开启网络搜索、`useContext7` 启用 MCP 实时文档检索（从官方源拉取与当前技术栈/版本匹配的文档），减少过时 API 或虚构接口错误。来源：6.2
- **Replicate API 设计**：任务启动接口（POST /api/generate-image）+ Webhook 回调接口（POST），本质是 Next.js API 路由。来源：6.2

## 6.3 v0.dev 生成 UI
- 用 v0.dev 快速生成平台界面（工作台、图库、设置等）。来源：6.3

## 6.4 Supabase 构建后端
- **数据建模：任务表/成果表分离**：generation_tasks（生成请求）与 user_images（最终成果）分两张表，追踪每次尝试（无论成败），利于调试与行为分析。来源：6.4
- **用户认证**：Auth 面板启用 Email，可一键开 Google/GitHub 社交登录。为所有表启用 RLS（用户只能操作 user_id 与自身 uid 匹配的记录）。来源：6.4
- **数据库视图**：user_stats_view、monthly_stats_view、cred_consumption_view、generation_type_distribution_view 简化前端数据获取。来源：6.4
- **数据库函数**：update_user_creds 安全处理积分变动（消费/充值/赠送）并自动记录交易历史。来源：6.4
- **Realtime 实时进度**：前端订阅 generation_tasks 当前用户记录变更，Webhook 更新 status 时 WebSocket 实时推送，无需刷新看到生成进度。来源：6.4

## 6.5 Replicate API 集成
- 对接 Replicate 实现文生图/编辑/融合，通过任务表管理异步生成。来源：6.5

## 6.6 用户积分与使用限制
- 积分系统（购买/消耗/限额）+ 使用限制，防止滥用、保证可持续。来源：6.6

## 6.7 Stripe 完整付费流程
- **产品/价格配置**：循环定价（月度/年度）+ 一次性定价（积分包）。**Metadata 打通付款→积分**：每个 Price 配自定义 metadata（如 key=creds, value=100），Webhook 读取后自动充值对应积分。来源：6.7
- **支付三件套**：①创建 Checkout Session（后端建/查客户→创建结账会话→返回 session_id）②前端 redirectToCheckout 跳 Stripe 托管页（敏感支付信息全由 Stripe 处理，简化 PCI 合规）③Webhook 监听 checkout.session.completed。来源：6.7
- **积分自动充值**：Webhook 处理器：①验证 Stripe-Signature 签名（真实性完整性）→②解析事件→③按 metadata 充值积分。来源：6.7

## 6.8 Resend 邮件营销
- 用 Resend 构建邮件系统（验证/通知/营销）。来源：6.8

## 6.9 Vercel 部署与生产环境
- **环境变量**：Stripe SECRET_KEY/WEBHOOK_SECRET、Resend API_KEY 放 Vercel 平台配置注入，避免在公开代码库泄露。来源：6.9
- **域名绑定+SSL**：Domains 页添加自定义域名，按 DNS 记录（A/CNAME）在注册商配置，Vercel 自动申请/续期免费 Let's Encrypt SSL（全站 HTTPS 免手动）。来源：6.9
- **性能优化**：边缘网络（push 触发部署到全球节点）；Next.js 图片组件深度集成（Supabase Storage 图片实时优化+CDN 缓存）；所有 API 路由自动部署为边缘函数（后端逻辑离用户更近、API 响应更快）。来源：6.9

## 6.10 小结
- 完整掌握"从零构建可商业化 AI 应用"全过程，理解 AI 辅助开发 + 无缝整合现代技术栈。

## 一句话总结
商业级产品工程 = 先架构后实现（结构化需求+@Web/Context7）+ 任务/成果表分离建模 + Realtime 实时进度 + Stripe 托管付费（metadata 打通积分+Webhook 验签）+ 环境变量管密钥 + Vercel 白拿边缘网络/HTTPS/图片优化。
