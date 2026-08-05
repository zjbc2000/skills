---
name: "ai-product-engineering"
description: "用AI把想法做成商业级产品的工程实战方法论。当你需要从0搭建可商业化运营的全栈应用（含AI功能、付费、部署、邮件）、集成第三方服务、或把原型打磨成生产级产品时使用。触发词：商业级、Stripe、积分付费、Vercel部署、生产环境、第三方API集成、图像生成平台。"
---

# 商业级 AI 产品工程

## 何时使用
- 你要从 0 构建一个可商业化运营的全栈应用（AI 功能+用户系统+付费+部署）。
- 你要集成第三方服务（图像生成 API、支付、邮件、数据库、部署平台）。
- 你要把原型打磨成生产级产品，处理异步任务、安全、性能、运维。

## 核心规则

1. **先规划后实现，用结构化需求喂 AI**：规划完成后再用 Cursor 打开项目代码，给结构化需求生成技术架构（技术栈+核心需求+要求生成详细架构与前后端通信接口含数据结构），AI 才会输出可落地架构而非泛泛建议。来源：第6章

2. **异步任务用"任务表与成果表分离"的数据建模**：把"生成请求"（generation_tasks）与"最终成果"（user_images）分成两张表，能追踪每次尝试（无论成败），对调试与用户行为分析至关重要。来源：第6章

3. **长任务进度用 Supabase Realtime 推前端**：前端订阅 generation_tasks 当前用户的记录变更，后端 Webhook 更新 status 字段时通过 WebSocket 实时推送，用户无需刷新即可看到生成进度。来源：第6章

4. **付费流程交给 Stripe 托管，服务端不碰卡信息**：三件套——①创建 Checkout Session（后端建/查客户→创建结账会话→返回 session_id）；②前端 redirectToCheckout 跳 Stripe 托管页（PCI 合规大幅简化）；③Webhook 监听 checkout.session.completed 处理结果。来源：第6章

5. **用 Stripe 产品元数据打通"付款→积分"**：为每个 Price 配自定义 metadata（如 key=creds, value=100），支付成功 Webhook 读取该元数据自动为对应用户充值积分，无需硬编码映射。来源：第6章

6. **Webhook 处理器第一件事是验签**：用 Stripe 仪表盘的 Webhook 签名密钥验证请求头 Stripe-Signature，确保请求真实完整，再解析事件数据——绝不能信任未验签的支付回调。来源：第6章

7. **敏感配置一律进环境变量**：Stripe SECRET_KEY/WEBHOOK_SECRET、Resend API_KEY 等放在 Vercel 平台配置注入，构建/运行时安全使用，避免在公开代码库泄露。来源：第6章

8. **部署后白拿性能优化**：Vercel 自动把 Next.js API 路由部署为边缘函数（离用户近、响应快），域名绑定后自动申请/续期免费 Let's Encrypt SSL（全站 HTTPS 免手动）；用 Next.js 图片组件展示 Supabase Storage 图片，Vercel 自动实时优化+CDN 缓存。来源：第6章

## 检查清单
- [ ] 实现前是否先生成/确认了技术架构与接口设计（用结构化需求喂 AI）？
- [ ] 异步任务是否用了"任务表/成果表"分离建模，而非单表堆砌？
- [ ] 长耗时任务进度是否通过 Realtime/WebSocket 实时反馈给前端？
- [ ] 付费是否走 Stripe 托管结账 + Webhook，且服务端未触碰卡信息？
- [ ] 积分/权限是否通过 Stripe metadata 打通、Webhook 是否先验签？
- [ ] 密钥是否全部走环境变量、未进代码库？
- [ ] 部署后是否验证了边缘函数、HTTPS/SSL、图片 CDN 优化生效？
