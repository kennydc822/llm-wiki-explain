# LLM Wiki Explain

Explain unfamiliar programming terms in a separate task, reuse what your personal LLM wiki already knows, and archive a sourced explanation only when the wiki has a real knowledge gap.

It is designed for questions such as:

```text
$llm-wiki-explain Explain dependency injection in another task.
wiki explain composition root
查下 Programming Vault 有冇 service locator，冇就寫低
解釋 async/await，唔好加重呢個 context
```

The skill supports local Obsidian or indexed Markdown wikis and connected Notion wikis. It defaults to Traditional Chinese explanations while preserving English technical terms, unless you ask for another language or depth.

## What it does

1. Keeps the original task lightweight by dispatching the explanation to a separate task or fresh worker.
2. Searches your configured wiki before researching elsewhere.
3. Reuses and links relevant existing notes.
4. Classifies the wiki coverage as `existing`, `partial`, or `missing`.
5. Researches authoritative sources only when durable knowledge is incomplete.
6. Merges the result into the canonical note, or creates one when needed, then validates the write.

An adequate existing page remains read-only. The skill does not create duplicate notes just to record that a question was asked.

## Install

Ask Codex to install the skill from this repository:

```text
Install the skill from https://github.com/kennydc822/llm-wiki-explain
```

Or clone it manually:

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/kennydc822/llm-wiki-explain.git \
  ~/.codex/skills/llm-wiki-explain
```

Start a new task or reload Codex after installation so the skill is discovered. See [OpenAI Docs — Build skills](https://learn.chatgpt.com/docs/build-skills) for the standalone skill format and supported Codex surfaces.

## Use it explicitly or naturally

The most predictable invocation is:

```text
$llm-wiki-explain Explain <term> in another task.
```

It can also trigger from natural-language requests containing either:

- a wiki cue, such as `wiki`, `LLM wiki`, `Programming Vault`, `Obsidian`, `Notion`, or `存入 wiki`; or
- a context-isolation cue, such as `another task`, `另開 task`, `唔好加重 context`, or `without bloating this context`.

An ordinary request such as “explain dependency injection” should not invoke the skill implicitly. Add a wiki or isolation cue when you want this workflow.

## First-use setup

If no valid wiki configuration exists, the skill runs onboarding in a separate setup task when possible. It offers three choices:

1. Use an existing Obsidian or indexed Markdown wiki.
2. Use a connected Notion wiki.
3. Cancel without changing anything.

For Obsidian, discovery is limited to conventional local roots or parent folders you provide. The skill shows at most three candidates and always asks you to confirm the write target. An indexed wiki must contain `index.md`; the skill will not silently initialize or restructure a plain vault.

For Notion, the Notion connector must support search, read, create, and update operations. The skill asks you to confirm one target database or parent page before saving it.

The selected backend and target are stored outside the installed skill at:

```text
~/.codex/llm-wiki-explain/config.json
```

The config contains no credentials, API keys, or copied wiki content. If a configured vault moves or becomes inaccessible, the repair flow shows the stale location, runs bounded discovery again, and asks before replacing it.

## Requirements and isolation behavior

- A Codex environment that supports standalone skills.
- Python 3 for the bundled Obsidian helpers.
- An existing indexed Markdown/Obsidian wiki, or a connected Notion wiki.
- User-visible task creation for the strongest context isolation.

When user-visible task creation is unavailable, the skill may use one fresh background worker with wiki access. If neither isolation method exists, it stops instead of placing the full explanation into the calling task.

## Safety and privacy

- Wiki search, source research, explanation drafting, and wiki edits happen outside the calling task.
- Only the minimum context needed to disambiguate the term is passed to the isolated task.
- Unrelated private wiki content and secrets must not appear in the explanation.
- The skill never guesses a write target, silently switches backends, or stores connector tokens.
- External sources are paraphrased and linked; full articles are not copied into the wiki.
- Existing vault instructions, indexes, frontmatter, naming rules, and archive conventions take precedence.
- A successful write is re-read and validated before it is reported as complete.

## Repository layout

```text
SKILL.md                    Main workflow and trigger description
agents/openai.yaml          UI metadata and implicit-invocation policy
references/setup.md         First-use and moved-wiki repair flow
references/obsidian.md      Obsidian retrieval, archive, and validation rules
references/notion.md        Notion capability, retrieval, and write rules
scripts/configure.py        Per-user configuration and bounded discovery
scripts/search_wiki.py      Read-only ranked Markdown search
scripts/validate_wiki.py    Programming Vault write validation
```

The helper scripts expose their options through `--help`. For example:

```bash
python3 scripts/configure.py show
python3 scripts/configure.py discover
python3 scripts/search_wiki.py --vault "/path/to/vault" --query "composition root"
```

`search_wiki.py` only discovers candidates. The isolated task still reads the actual notes, follows relevant links and sources, and decides whether they answer the question.
