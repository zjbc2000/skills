# 微信读书导出（强制全文）

拆书 skill 的微信读书路径 = **强制全文导出**，拿不到全文就停下提示换源，不降级到划线骨架。

## 机制
- 导出器（`lbq110/weread-exporter` 的 `export_precise.py`）用 **Playwright 启动有头（headless=False）Chromium 真窗口**。
- **扫码登录**：打开 weread.qq.com/web/shelf，未登录则停在登录页等用户扫码（每 5 秒轮询 URL，最长 10 分钟）。会话持久化在 `cache/browser_profile/`，**扫码只需一次**。
- 翻页方式：原生点击目录首项跳全书开头 → `ArrowRight` 逐页翻 → 目录比对判断末尾 → 自动停止；中途卡住自动重开续传。

## 使用规则（SKILL.md 执行）
1. 首次使用**必须提示用户**"会有浏览器窗口弹出，请扫码登录微信读书"。
2. 前置：`pip install playwright && playwright install chromium`。
3. 导出是长任务（整本书 30 分钟至数小时），需耐心等待；`export_book` 超时 4 小时。
4. 失败场景（出版社限制"去 App 阅读"、无权限、无 Chromium）→ 停下提示换源：提供 PDF/Markdown 或换正版电子书。**绝不降级到官方 API 划线骨架**（官方 API 无正文，仅可用于把书名解析成 reader 链接）。

## 坑
- 导出器约 1-2 秒/页；Cookie 会过期需重新扫码；账号可能被风控，仅供个人自用。
- Canvas Hook 导出有断行拼接痕迹，蒸馏前需清理。
- 纯图廊章节图片密集时图注与图配对偶差一位。
