<p align="center">
  <strong>简体中文</strong> · <a href="README.en.md">English</a>
</p>

<h1 align="center">📝 Project Resume and Sync</h1>

<p align="center">作者：<a href="https://github.com/yunli2024">yunli</a></p>

<p align="center">
  <a href="https://github.com/yunli2024/project-resume-and-sync/releases/latest"><img src="https://img.shields.io/github/v/release/yunli2024/project-resume-and-sync?style=flat&amp;label=release&amp;color=2563eb" alt="Latest release"></a>
  <a href="https://github.com/yunli2024/project-resume-and-sync/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/yunli2024/project-resume-and-sync/tests.yml?branch=main&amp;style=flat&amp;label=tests" alt="CI status on main"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&amp;logo=python&amp;logoColor=white" alt="Python 3.10 or newer"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-0f766e?style=flat" alt="MIT license"></a>
</p>

<p align="center">
  <strong>记录项目进展和做过的决定，让 Agent 换个会话也能接着做。</strong><br>
</p>

<p align="center">
  <a href="#quick-start">开始使用</a> ·
  <a href="#everyday-use">日常使用</a> ·
  <a href="#how-it-works">工作方式</a> ·
  <a href="#faq">常见问题</a>
</p>

---

你是否会有这样的困境：和 Agent 交互的项目做了一半，换个聊天窗口，又得解释一次：做到哪了、为什么选这个方案、接下来做什么。
隔几天回来，自己已经忘了要做什么了，翻半天记录。

这个 Skill 帮你把这些事情记在项目里。下次先读一份简短摘要；想知道某个决定的来龙去脉，再顺着引用找到当时的记录和相关文件。

日常记住两个动作就够了：

| `resume` · 接上进度 | `sync` · 记下变化 |
| :--- | :--- |
| 让 Agent 在开始工作前，看看现在的状态和下一步。 | 有了实质进展或做了决定，让 Agent 把结果、理由和来源留下来。 |

这里的 sync 指更新项目记录。记录保存在本机，文件传输和云端同步由你现有的工具负责。

<a id="quick-start"></a>

## 🚀 开始使用

下面以 **Codex** 为例。需要 Python 3.10 或更新版本。

### 1. 安装 Skill

```sh
git clone https://github.com/yunli2024/project-resume-and-sync.git
cd project-resume-and-sync
python scripts/install.py
```

也可以下载 [Release 发布包](https://github.com/yunli2024/project-resume-and-sync/releases/latest)，或通过 **Code → Download ZIP** 下载源码，解压后在该目录执行最后一行。
如果你的系统使用 `python3`，把命令里的 `python` 换成 `python3`。

安装后，新开一个 Codex 会话。如果已有旧版，使用 `python scripts/install.py --upgrade` 更新。

### 2. 在你的项目里启用一次

打开**你要记录的项目**，把下面这段话发给 Agent：

```text
使用 $project-resume-and-sync 为当前项目启用持续记录。
开始工作时先 resume，有实质进展或决定后 sync，不用等我提醒。
先记下目前的目标、进展和下一步。
```

Agent 会在项目指令文件（通常是 `AGENTS.md`）里加入一小段约定，并建立本地记录。已有内容会保留，重复启用不会重复添加。

> [!TIP]
> **Skill 安装一次，每个需要记录的项目启用一次。** 已经安装后，换项目只需要重复这一步。

### 3. 继续正常做项目

下次在这个项目里新开会话，说“继续这个项目”就好。Agent 应按约定先读记录，完成实质工作后再更新。

主动调用依赖客户端加载项目指令、Agent 遵循约定。如果它漏了，直接说“用 project-resume-and-sync 恢复进度”或“同步一下项目记录”即可。

<details>
<summary><strong>安装位置、自定义路径和命令行启用</strong></summary>

新安装默认放在 `~/.agents/skills/project-resume-and-sync`。已有的 `~/.codex/skills/project-resume-and-sync` 会继续沿用；显式设置 `CODEX_HOME` 时使用其中的 `skills` 目录。安装命令会打印实际路径。

自定义安装位置：

```sh
python scripts/install.py --dest "/path/to/skills/project-resume-and-sync"
```

首次安装时，也可以直接指定要启用的项目：

```sh
python scripts/install.py --project-root "/path/to/your-project"
```

已安装后，为另一个项目启用：

```sh
python "<skill-dir>/scripts/local_ledger.py" enable --project-root "/path/to/your-project"
```

将 `<skill-dir>` 换成安装命令输出的路径。`enable` 默认使用 `AGENTS.md`；如果有非空的 `AGENTS.override.md`，则写入该文件。遇到已有的自定义调用规则，会提示 Agent 协调。

升级会备份被替换的运行文件，并保留安装目录中的其他文件。更多接入细节见[使用指南](references/local-ledger-schema.md#enable-ongoing-project-maintenance)。

</details>

<a id="everyday-use"></a>

## 💬 平时怎么用

启用后，你可以照常和 Agent 聊项目。需要指定动作时，可以这样说：

| 你说 | Agent 使用的能力 |
| --- | --- |
| “继续昨天的工作，先告诉我做到哪了。” | `resume`：读当前状态和下一步 |
| “这个方案定了，把理由也记下来。” | `sync`：更新状态，追加一条决定 |
| “之前为什么没用流式处理？” | `history` / `show`：查经过，读具体记录 |
| “准备交给队友，帮我整理交接。” | `export`：生成本地交接草稿 |
| “记录太长了，整理一下，旧细节留着。” | `compact`：归档旧快照，精简当前状态 |

普通问答和没有变化的状态不需要反复记录。值得留下的是：**做成了什么、改变了什么、为什么改、卡在哪里、下一步做什么。**

<a id="how-it-works"></a>

## 🔎 摘要背后记了什么

比如你在做一个 CSV 导入工具。换个会话后，Agent 先看到这样的摘要（简化示意）：

```text
当前目标：完成离线 CSV 导入。
已经决定：使用本地文件，暂不采用流式处理。 [决策引用]
下一步：按 docs/api.md 实现导入接口。
待确认：队友说适配器测试通过，尚未核对结果。
```

当你问“为什么没用流式处理”，Agent 可以顺着引用读取完整记录，找到当时的理由和 `docs/api.md` 等来源。
实际引用形如 `state:4#/decisions/0`，指向某个版本里的具体条目。

> 这也是这个 Skill 的核心：**平时只读当前需要的摘要，要复盘时有记录可查。**

- **控制每次读入的内容。** 默认摘要最多 6,000 个字符（不是 token），包含当前状态和最近三条事件的视图，并标明还有多少条目未展示。更早的历史按需查找。
- **保留改变主意的经过。** 当前状态写最新决定，历史保留之前的提议、变化和原因。
- **整理后仍能找回旧细节。** `compact` 保存整理前的原始快照，之后仍可搜索和读取。
- **分清已确认和待核实。** “队友说测试通过”可以带着来源记下，核实后再更新结论。
- **同时更新时发现冲突。** 多个 Agent 在同一本机协作时，过期版本的写入会被拒绝；重新读取后再协调。中途打断的更新也有恢复入口。

记录能帮你找到复现的依据；真正重新运行时，仍需要能访问对应的代码、数据和环境。

<a id="demo"></a>

## 🧪 想先看看效果？

在下载的仓库目录运行：

```sh
python examples/demo.py
```

演示会创建一个临时项目，走一遍“记录进展 → 改变决定 → 新会话接续 → 整理后找回旧理由”。不需要连接 Agent 或配置 API，运行后会打印文件位置，方便自己打开看。

<a id="faq"></a>

## ❓ 常见问题

<details>
<summary><strong>会把整个聊天记录都保存下来吗？</strong></summary>

保存的是 Agent 通过 `sync` 写下的进展、决定和来源。没有后台抓取聊天；尚未记录的内容，需要从仍可访问的会话或文件中补充。

</details>

<details>
<summary><strong>记录放在哪里？换电脑或交给队友怎么办？</strong></summary>

放在项目的 `.project-ledger/` 中，包含当前状态、事件历史和供人阅读的 `HANDOFF.md`。初始化时会为 Git 仓库添加本地忽略规则。

日常记录留在本机。交接时让 Agent 导出一份 Markdown 草稿，检查其中的私人信息后再分享；对方还需要能访问引用的文件。跨机器的记录合并目前需要人工协调。

</details>

<details>
<summary><strong>其他 Coding Agent 能用吗？</strong></summary>

Skill 由 `SKILL.md` 和标准库 Python 脚本组成。其他支持这类 Skill 的客户端，可以通过 `--dest` 指定其安装路径；项目约定也可通过 `enable --instructions CLAUDE.md` 写入对应指令文件。

当前使用说明以 Codex 为主。其他客户端的发现方式和主动调用行为尚未逐一验证，需按客户端的指令加载机制接入。

</details>

<details>
<summary><strong>我想直接用命令行</strong></summary>

在下载的仓库目录中运行，将路径替换成你要记录的项目：

```sh
python scripts/local_ledger.py resume --project-root "/path/to/your-project"
python scripts/local_ledger.py sync --project-root "/path/to/your-project" --input change.json
python scripts/local_ledger.py history --project-root "/path/to/your-project" --topic "CSV"
```

`change.json` 的最小示例见 [SKILL.md](SKILL.md)。日常一次 `sync` 会同时更新状态、事件和交接摘要。
需要查某条完整记录、导出、压缩或排查中断时，参阅[命令与存储指南](references/local-ledger-schema.md)。

</details>

<a id="why-i-built-this"></a>

## 🌱 为什么做这个

它起初用在一个持续了几个月的研究项目里。随着实验、讨论和交接越来越多，记录变长了，接续工作却越来越费劲：旧决定混在新进展中，每次新开会话都要读一大堆背景。

后来逐步收敛成现在的方式：当前状态保持简短，历史留下理由，需要时再回去查。希望它也能帮你少解释几遍项目，多花点时间把事情做完。

如果你遇到“明明记过，后来却接不上”的情况，欢迎[提一个 Issue](https://github.com/yunli2024/project-resume-and-sync/issues)。描述场景、预期和实际表现就很有帮助，示例请去掉私人信息。

[设计取舍](docs/DESIGN.md) · [验证记录](docs/VALIDATION.md) · [场景评估](docs/EVALUATION.md) · [参考项目](docs/RELATED_WORK.md) · [更新日志](CHANGELOG.md)

---

[MIT License](LICENSE) — 欢迎使用、修改和分享。
