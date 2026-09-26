# skills

个人 agent skill 集合。一个 skill = 一个含 `SKILL.md` 的文件夹：frontmatter 里的 `name` 与 `description` 声明它是什么、何时用，正文是给 agent 执行的指令。

## Skill 总览

| Skill | 一句话 | 路径 |
|---|---|---|
| evals-builder | 给 LLM 功能搭一套可回测、可校准、能进 CI 门禁的评估体系 | [engineering/evals-builder](engineering/evals-builder/) |
| eval_optimize_loop | 评测优化循环：定义标准 → 跑基线 → 对比归因 → 接受/拒绝，含编排器与 3 个专家 skill | [engineering/eval_optimize_loop](engineering/eval_optimize_loop/) |
| feishu-bot | 飞书（Lark）长连接双向 bot 的开发与排障，含事件层踩坑经验 | [engineering/feishu-bot](engineering/feishu-bot/) |
| domain-drill | 领域钻探学习法：调研后逐轮讲共识与分歧，再逐题拷问用户 | [study/domain-drill](study/domain-drill/) |
| feynman | 费曼讲台：用户口喷讲解，agent 只做好奇的学生 | [study/feynman](study/feynman/) |

> `domain-drill` 与 `feynman` 是学习对话类 skill，设计为用户手动调用（`disable-model-invocation: true`），agent 不会自动触发。

## 快速开始

以 Claude Code 为例，其他支持 Agent Skills 的工具同理：

```bash
git clone https://github.com/zjbc2000/skills.git
mkdir -p ~/.claude/skills
ln -s "$(pwd)/skills/engineering/evals-builder" ~/.claude/skills/evals-builder
```

重启会话，用自然语言或触发词唤起。比如对 agent 说「帮我搭一个评估体系」，命中 evals-builder 的 description，它就会加载并按指令执行。

注意：

- 链接（或复制）整个 skill 文件夹即可，不要只复制 `SKILL.md`——深材料和脚本都在文件夹里。
- `eval_optimize_loop/` 下是 4 个独立 skill（编排器 + 3 个专家）。通常只需链接 `optimization-orchestrator/`，它会按状态路由到专家。
- 每个 skill 的详细用法都在它自己的文件夹里，按需阅读。

## 供 Agent 阅读（For agents）

- 先判断任务是否命中上表某个 skill 的 description：命中才读该 skill 的 `SKILL.md`，并按其内部指引加载 `references/` 与 `scripts/`；不必读取整个仓库。
- `disable-model-invocation: true` 的 skill 只在用户显式点名时使用。
