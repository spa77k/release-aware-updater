# Release-aware updater

[日本語](README.md) | [English](README.en.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md)

这是一个通用技能：先阅读发行说明，确认兼容性、破坏性变更和迁移步骤，
再更新应用、库、软件包依赖和 Docker 镜像。
Minecraft 插件也是它支持的使用场景之一。

Claude Code、Codex 以及其他支持 [Agent Skills](https://agentskills.io/specification)
的代理都可以使用同一份 `SKILL.md`。它不依赖特定提供商的 API，
也不依赖 Claude 专用的钩子。

**适用于各种代理的依赖更新技能，以发行说明为依据。** 代理负责查阅官方发行说明；
可选的离线 Python 辅助工具负责生成可供审查的固定版本差异、执行已获授权的本地编辑，
并在文件未被再次修改的情况下撤销固定版本更新。

## 功能

- 调查从当前版本到候选版本之间的发行说明、依赖关系和兼容性
- 检查应用和库的 API、运行环境、直接与间接依赖，以及锁文件（lockfile）
- 仅在需要时检查 Minecraft、Java、服务端实现及插件依赖
- 检查 Docker 镜像的标签与摘要（digest）、CPU 平台和持久化数据
- 制定包含破坏性变更、迁移、测试和回滚步骤的更新计划，并生成差异
- 在本地更新 URL + SHA-256 或镜像摘要，并在恢复时检查文件哈希
- 暂缓处理信息不明、不兼容或尚未验证的项目

npm、pip、Cargo、Maven、Gradle 等生态的清单和锁文件由现有包管理器更新。
Python 辅助 CLI 仅用于替换文本中固定的 URL + SHA-256 和 Docker 摘要，
不会解析软件包依赖，也不会重新生成锁文件。更新 Docker Engine 或操作系统本身，
以及向线上环境部署，均属于独立任务。
脚本不会联网、下载文件、执行外部命令或重启服务。
实际的发行说明调查需要使用代理的网页或代码仓库浏览功能。

## 安装

先获取公开仓库。使用前请检查脚本内容。

```sh
git clone https://github.com/spa77k/release-aware-updater.git
cd release-aware-updater
```

### Claude Code

```sh
mkdir -p ~/.claude/skills
cp -R skills/release-aware-updater ~/.claude/skills/
```

可以通过 `/release-aware-updater` 调用。如果只想在某个项目中使用，
请将同一文件夹放入目标仓库的 `.claude/skills/release-aware-updater/`。

### Codex

```sh
mkdir -p ~/.agents/skills
cp -R skills/release-aware-updater ~/.agents/skills/
```

可以通过 `$release-aware-updater` 指定使用此技能。如果只想在某个项目中使用，
请将其放入目标仓库的 `.agents/skills/release-aware-updater/`。

如果已存在同名技能，请在覆盖前检查差异。
如果代理未能自动发现技能，请重启或重新加载。

### 其他代理及不支持技能的工具

将 `skills/release-aware-updater/` 复制到所用工具的技能目录。
具体目录和调用语法取决于该工具。即使工具不支持技能，也可以让它参考 `SKILL.md`，
并直接使用 Python CLI。本项目不保证所有工具都能自动发现技能。

有关格式和安装目录的官方文档：
[Agent Skills](https://agentskills.io/specification) /
[Claude Code](https://code.claude.com/docs/en/skills) /
[Codex](https://developers.openai.com/codex/skills)

## 请求示例

> 请检查此仓库中应用、库和 Docker 镜像从当前版本到最新兼容稳定版之间的官方发行说明。
> 制定更新方案并生成差异，说明破坏性变更、运行环境与 API 要求、对锁文件的影响，
> 以及迁移和恢复方法。先只做计划，不要部署。

> 请审阅这些应用、库和容器依赖的官方发行说明。
> 在当前检出目录中更新兼容的固定版本，运行仓库检查，
> 并列出仍需执行的迁移和运行时测试。不要部署或重启任何服务。

`仅制定计划` 和 `同时进行本地编辑` 是不同的授权范围。
安装此技能本身并不意味着授权发布、重启或部署。
操作必须遵守所用工具和用户的权限设置。

## 语言

代理撰写的建议和说明支持日语、英语、韩语及简体中文。
你可以明确指定语言，也可以直接用希望使用的语言提出请求。
在 `plan` 子命令后添加 `--lang en`、`--lang ja`、`--lang ko` 或 `--lang zh-CN`，
即可选择 Markdown 报告中标签和安全提示的语言。默认语言为英语。
证据文本、自动生成的阻碍原因诊断信息以及差异内容不会自动翻译。
JSON 字段和状态值、CLI 帮助及诊断信息仍为英语。
共用的技术参考文档以英语编写，代理会用你的语言进行解释。
语言选择不会改变验证逻辑或权限要求。

## 离线试用

环境要求：Python 3.11 或更高版本。无需额外的 Python 软件包、Docker 或 API 密钥。
以下演示使用虚构的 URL、摘要和发行说明，
并不代表已验证任何真实的发行文件。

```sh
demo=$(mktemp -d)
cp -R examples/general "$demo/repo"
python3 skills/release-aware-updater/scripts/update.py plan \
  --lang zh-CN \
  --root "$demo/repo" --manifest examples/general-manifest.json --out "$demo/plan.json"
cat "$demo/plan.md"
python3 skills/release-aware-updater/scripts/update.py apply \
  --root "$demo/repo" --plan "$demo/plan.json"
python3 skills/release-aware-updater/scripts/update.py rollback \
  --root "$demo/repo" --plan "$demo/plan.json"
```

此演示涵盖三种类型：通用应用、以文件形式分发的库，以及 Docker 镜像。
原有的 Minecraft 示例保留在 `examples/demo` 和 `examples/manifest.json` 中。
库示例使用虚构的 URL/哈希固定格式，不能替代 npm 等工具的锁文件。

用于自己的仓库时，请根据已调查确认的信息创建清单。
可以参考[输入规范](skills/release-aware-updater/references/manifest.md)和
[调查与验证要点](skills/release-aware-updater/references/research.md)。
安装后的技能文件夹也包含 `references/manifest-template.json` 和 LICENSE。
模板中的项目因尚未验证而处于暂缓状态，请填入调查结果。

## 安全性与限制

- 发行说明中的文字仅作为数据读取，不执行其中嵌入的指令
- `ready` 表示根据输入证据判断可以进行本地编辑。它不代表脚本已经证实调查内容的真实性、
  实际运行环境中的兼容性或是否可以部署
- 工具通过唯一匹配的字符串替换进行更新。YAML/Compose 语法以及应用能否实际启动，
  仍需单独测试。工具不会自动查找版本，也不提供适用于所有网站的抓取功能
- 哈希有助于检测篡改和保证可复现性，但仅凭哈希无法证明发行来源的真实性
- `rollback` 仅恢复文件中的固定版本，不会撤销数据库、世界存档或数据卷的变更
- 多个文件的更新并非一个整体事务。请在正常的仓库检出目录中使用，并停止可能冲突的编辑；
  如果执行中断，请检查当前状态
- 清单和报告包含变更行及 URL。公开前请检查其中是否含有秘密信息

## 测试

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

测试无需联网，涵盖正常的计划生成、应用与恢复、暂缓判定、无效输入、歧义替换、
路径越界、符号链接、已被修改的文件、CRLF 换行和重复执行等场景。
测试还会确认切换报告语言不会改变计划内容、验证结果或应用与恢复行为。
输入和输出文件的 1 MiB 上限按 UTF-8 字节数检查；
若更新会导致文件过大而无法恢复，则拒绝该更新。生成的计划文件限制在可读取的 8 MiB 以内。
发行内容不包含 `__pycache__` 和 Python 字节码。
GitHub Actions 也已配置相同的回归测试，使用 Python 3.11 和 3.13 运行。

## 目录结构

```text
skills/release-aware-updater/
  SKILL.md                 通用指令与语言选择
  references/              调查指南与清单规范
  scripts/update.py        仅使用标准库的 CLI
examples/                  使用虚构数据的离线演示
tests/                     回归测试
```

采用 MIT 许可证。
