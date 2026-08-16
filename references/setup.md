# First-use and repair setup

Read this reference only when the per-user config is missing, invalid, or explicitly being changed.

## Config contract

The default config is `~/.codex/llm-wiki-explain/config.json`. An explicit `--config` path or `LLM_WIKI_EXPLAIN_CONFIG` environment value overrides it. Keep configuration outside the installed skill so updates do not overwrite it.

The config stores only:

- schema version;
- backend (`obsidian` or `notion`);
- Obsidian vault path, project label, and detected schema; or
- Notion target page/database identifier;
- update timestamp.

Never store connector credentials, API keys, or copied wiki content.

Resolve the skill directory from the loaded `SKILL.md`, then inspect config with:

```bash
python3 "/absolute/path/to/llm-wiki-explain/scripts/configure.py" show
```

## Missing or invalid config

Keep onboarding in a separate user-visible setup task when possible. Pass the original explanation request into that task so it can continue immediately after setup.

Offer three choices:

1. use an existing Obsidian or indexed Markdown wiki;
2. use a connected Notion wiki;
3. cancel without changing anything.

If task creation is unavailable, ask one concise setup question in the calling task. Do not explain the requested term until setup succeeds.

## Obsidian discovery

Search only bounded, conventional roots. Do not scan the entire home directory or external volumes. Run:

```bash
python3 "/absolute/path/to/llm-wiki-explain/scripts/configure.py" discover
```

Use `--root "/path"` one or more times when the user gives likely parent folders. Present at most three candidates with their path and markers. Always ask the user to confirm one; never select a write target solely from ranking.

After confirmation, save and validate it:

```bash
python3 "/absolute/path/to/llm-wiki-explain/scripts/configure.py" \
  set-obsidian --vault "/confirmed/vault/path" --project-label "optional label"

python3 "/absolute/path/to/llm-wiki-explain/scripts/configure.py" validate
```

An indexed wiki must contain `index.md`. A plain Obsidian vault without an index is not automatically an LLM wiki. Only pass `--allow-unindexed` after the user explicitly confirms that vault and accepts read-only discovery until archive rules are defined.

Do not create `index.md`, wiki folders, or schema files during setup unless the user separately asks to initialize a wiki and approves the proposed structure.

## Notion setup

Confirm a Notion connector is installed and connected before saving Notion as the backend. Ask for or discover a single target database/page, then ask the user to confirm it. If several targets are plausible, do not guess.

Save and validate the confirmed target:

```bash
python3 "/absolute/path/to/llm-wiki-explain/scripts/configure.py" \
  set-notion --target "confirmed database or page identifier"

python3 "/absolute/path/to/llm-wiki-explain/scripts/configure.py" validate
```

The config records only the target identifier; authentication remains in the connector.

## Repair and completion

If a configured vault moved or became inaccessible, show the stale target, rerun bounded discovery, and ask before replacing it. Never silently switch backend or target.

After validation succeeds, continue the original explanation inside the same isolated setup task. State that setup was saved, but do not echo the full config into the calling task.
