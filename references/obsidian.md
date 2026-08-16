# Obsidian backend

Use this backend for the default Programming Vault or another local Obsidian vault.

## Configured target

- Read the validated vault path and optional saved-project label from the per-user config described in [setup.md](setup.md).
- An explicit path in the current request overrides the configured path for that run.

Resolve the path before reading or writing and keep every operation inside it. Do not traverse symlinks that escape the vault. If the path is missing or invalid, return to the repair flow instead of guessing another target.

## Bootstrap

1. Read `CLAUDE.md`, `AGENTS.md`, or another vault instruction file completely when present. It is the authority for schema, language, indexing, source handling, and logging.
2. Read `index.md` completely when present.
3. Read the relevant domain index and recent query log when the local schema defines them.
4. Obey any more specific instruction file that governs the page being edited.

If the vault is absent or instructions conflict, stop and report the exact problem rather than inventing a replacement structure. If no archive instructions exist, allow read-only retrieval but ask the user to define or initialize archive rules before writing.

## Retrieval

1. Use `index.md` to choose the likely domain when it exists.
2. Use domain indexes and wikilinks to identify canonical candidate pages when the vault defines them.
3. Resolve the skill directory from the loaded `SKILL.md`; do not assume the vault is the current directory. Run the bundled search helper for a ranked second pass:

   ```bash
   python3 "/absolute/path/to/llm-wiki-explain/scripts/search_wiki.py" \
     --vault "/absolute/path/to/vault" \
     --query "term or phrase" \
     --limit 8
   ```

4. Open strong candidates and follow only relevant `related` links and `sources`.
5. Use broader text search only when indexes are absent or the indexed candidates expose a gap.

The helper never decides whether a page is correct. Confirm meaning from page content and sources, especially for homonyms.

## Archive

If an existing canonical page already contains adequate durable knowledge, keep the vault read-only. Otherwise follow the vault's current archive checklist. In a Programming Vault-compatible schema this normally means:

- merge with the canonical page when one exists;
- otherwise create a kebab-case page under the correct `wiki/` domain;
- preserve `created` and update `updated` on edits;
- add sources for non-stub knowledge;
- maintain related links and the relevant domain index;
- update hub counts when the vault schema requires it;
- append a concise query record to `log.md`.

Use a URL or an immutable local source note as provenance according to `CLAUDE.md`. Paraphrase copyrighted sources; do not paste full articles into the vault. Never modify curated `_sources/` material except through the vault's explicit ingestion procedure.

## Validate

For the Programming Vault schema, run validation with the script path resolved from the loaded skill:

```bash
python3 "/absolute/path/to/llm-wiki-explain/scripts/validate_wiki.py" \
  --vault "/absolute/path/to/vault" \
  --page "wiki/programming/example.md"
```

Repeat `--page` for multiple changed pages. Errors block completion. Warnings require review and should be mentioned if intentionally left unresolved. For another schema, use its local checks instead of forcing this validator.

Finally, re-open the edited page, its domain-index entry, and the new log entry. A successful file write alone is not sufficient verification.
