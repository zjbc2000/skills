# skill vs plugin 判别树

判断一本书的产出该走 skill 形态还是 plugin 形态：

```
Q1 干货是程序性知识（方法论/清单/领域规则）吗？
├─ 否（靠外部工具/数据）→ 需要 MCP server → plugin 形态
└─ 是 → Q2

Q2 需要 hooks（事件自动执行）/ 子代理 / 多命令分发吗？
├─ 是 → plugin 形态
└─ 否 → Q3

Q3 要分发（团队/社区/版本化）吗？
├─ 是 → plugin 形态（+ marketplace.json）
└─ 否 → skill 形态（裸 skill）
```

## 要点

- **skill 优先，plugin 是升级路径**。纯方法论书（Clean Code 这类）默认 skill 形态。
- 判别树结果在检查点1 时展示给用户，用户可改判。
- plugin 形态时：`SKILL.md` 移入 `skills/`，新增 `.claude-plugin/plugin.json`（必需）+ 可选 `marketplace.json`/`agents/`/`hooks/`/`.mcp.json`，用 `validate_plugin.py` 校验。
