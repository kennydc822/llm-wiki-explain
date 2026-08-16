---
name: llm-wiki-explain
description: Explain an unfamiliar technical or programming term outside the calling task, reuse matching knowledge from the user's LLM wiki, and archive a sourced explanation when the wiki is incomplete. Run a safe first-use setup when the wiki is not configured or has moved. Use for $llm-wiki-explain and requests such as “wiki explain X”, “LLM wiki 解釋 X”, “查 wiki／Programming Vault 再解釋”, “先睇 wiki 有冇，冇就寫低”, “另開 task 解釋 X”, “唔好加重呢個 context”, “將解釋存入 wiki”, “explain X in another task”, “look up X in my wiki”, “explain without bloating this context”, or “save/archive this explanation to my wiki”. Do not trigger for ordinary explain/summarize requests that mention neither a separate task/context isolation nor the user's wiki. Supports Obsidian and connected Notion.
---

# LLM Wiki Explain

Keep the calling task lightweight while turning one unclear term into reusable wiki knowledge. Treat invocation by the skill name, a separate-task/context-isolation phrase, or a wiki lookup-and-save phrase as authorization to dispatch the work and update the selected wiki after following its local rules.

Do not activate merely because the user says `explain`, `解釋`, or `我唔明`. Require either a wiki cue (`wiki`, `LLM wiki`, `Programming Vault`, `Obsidian`, `Notion`, `存入 wiki`) or an isolation cue (`another/separate/new task`, `另開 task`, `唔好加重 context`, `without bloating context`).

## Resolve configuration

Resolve bundled scripts relative to the directory containing this `SKILL.md`.

1. Honor an explicit backend or wiki target in the request.
2. Otherwise run `scripts/configure.py show` before dispatch. This reads only the small per-user config; it does not search the wiki.
3. If the config is valid, use its backend, target, and optional project label.
4. If the config is missing or invalid, read [references/setup.md](references/setup.md) completely and run the first-use or repair flow in a separate setup task. Keep setup out of the calling task when task creation is available.
5. If a valid config already exists, treat a different explicit target as a one-run override unless the user says to remember it. If no config exists, validate and remember an explicit target as the first-use choice.

Never bake a machine-specific vault path into this skill. Store per-user configuration outside the skill directory. Never store connector tokens or other secrets in the config.

## Separate the work

Perform only dispatch in the calling task. Do not search the wiki, browse sources, draft the explanation, or edit wiki files there.

1. Extract a compact request containing:
   - the term or concept;
   - one or two sentences of local context needed to disambiguate it;
   - requested depth, language, or backend when specified.
2. Add the resolved backend and wiki target. Do not guess either when setup is incomplete.
3. Create a separate user-visible task when the environment supports task creation. In Codex desktop, use the configured saved project in its local environment when available because the live wiki is the intended output, not an isolated worktree.
4. If user-visible task creation is unavailable, use one fresh background worker that can access and update the wiki. Keep its returned content out of the calling answer except for a compact status and note location.
5. If neither isolation method exists, stop and explain that the workflow cannot preserve context isolation. Do not fall back to explaining inline.

Pass this worker contract with the compact request:

```text
You are already the isolated LLM Wiki Explain worker. Skip the dispatch section
and run the knowledge workflow entirely in this task.
Backend: <configured obsidian|notion>
Wiki: <validated vault path or Notion target>
Term: <term>
Context: <minimal disambiguating context>
Preferences: <language/depth or defaults>

Search the wiki first and synthesize any existing relevant notes. If durable
knowledge is incomplete, fill the gap from authoritative sources, archive it under
the wiki's own rules, and validate the write. Give the full explanation plus the
canonical note link in this task. Keep an adequate canonical page read-only.
Do not send the full explanation back to the calling task.
```

After dispatch, return only a short receipt and the new task link or identifier. If using a background worker, return only completion status and the saved page path or URL.

## Run inside the isolated task

### Choose the backend

- For Obsidian, read [references/obsidian.md](references/obsidian.md) completely and follow it.
- For Notion, read [references/notion.md](references/notion.md) completely and follow it.
- Never dual-write unless the user explicitly requests it.

### Retrieve before explaining

Follow the wiki's own instructions and indexes before broad search. Classify the result:

- `existing`: one or more pages already answer the question;
- `partial`: durable conceptual knowledge is materially incomplete or incorrect;
- `missing`: no reliable answer exists.

For Obsidian, resolve bundled scripts relative to the directory containing this `SKILL.md`; do not assume the vault is the current directory. Run `scripts/search_wiki.py` only after reading the vault's main index. Treat its ranked output as candidate discovery, not truth. Open the best candidates, follow relevant links and cited sources, and surface conflicts.

Missing a request-specific example does not by itself make an otherwise adequate canonical page `partial`. Generate a transient example in the explanation unless it adds reusable knowledge.

### Build a grounded explanation

Combine rather than copy existing material. Explain the term in the user's requested language, defaulting to Traditional Chinese with technical tokens preserved in English. Include:

1. a one-sentence definition;
2. why it matters in the supplied context;
3. a small concrete example;
4. common confusion or boundary conditions;
5. links to related wiki concepts when available, plus sources.

When the wiki is partial or missing, research authoritative primary sources. Distinguish sourced facts from inference. Do not invent an answer when sources are unavailable; report the gap and create a stub only if the wiki's policy permits it.

### Archive safely

Prefer, in order:

1. merging into an existing canonical page;
2. adding a focused section to a closely related page;
3. creating a new canonical page.

If an adequate canonical page already exists and there is no reusable knowledge to add, do not edit it and do not add a duplicate log entry merely to complete the workflow. Otherwise, preserve unrelated user content, use `apply_patch` for local Markdown edits, and never rewrite or delete curated source material. Follow all frontmatter, naming, index, link, date, and query-log rules defined by the wiki itself.

For an Obsidian wiki using the bundled Programming Vault schema, run `scripts/validate_wiki.py` against every page changed. For other Obsidian schemas, validate against their local instructions and re-read every changed page and index entry. For Notion, re-read the saved page and database properties after writing.

### Finish in the isolated task

Return the full explanation there, state whether knowledge was `existing`, `partial`, or `missing`, identify what was reused or added, and link the canonical wiki page. Mention validation failures or unresolved source conflicts plainly.

## Safety boundaries

- Do not expose secrets or unrelated private wiki content in the explanation.
- Do not initialize, restructure, or choose a wiki without explicit confirmation in the setup task.
- Do not overwrite a canonical page merely because a generated title matches it.
- Do not claim a Notion write occurred without a connected Notion capability and a successful re-read.
- Do not allow a failed archive step to masquerade as success.
- Keep the calling task free of the explanation even if the user later follows up there; direct them to the isolated task unless they explicitly cancel isolation.
