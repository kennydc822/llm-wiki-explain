# Notion backend

Use this backend only when the user explicitly selects Notion or has configured it as their LLM wiki.

## Capability gate

Confirm that a Notion plugin or connector is installed, connected, and exposes search, read, create, and update operations. If it is unavailable, stop and tell the user that the Notion connection is required. Do not claim a write and do not silently switch to Obsidian.

## Target selection

Use an explicit database or parent-page URL when provided, then the validated per-user config described in [setup.md](setup.md). Otherwise discover a single database clearly named for the user's LLM wiki. If multiple plausible targets exist, pause in the isolated task and ask the user to choose; never guess a production database.

Prefer these properties when the database supports them:

- `Name` or `Title`: canonical concept name;
- `Aliases`: alternate terms;
- `Domains`: one or more subject areas;
- `Status`: `stub`, `growing`, or `stable`;
- `Sources`: source URLs or relations;
- `Related`: relations to other concepts;
- `Created` and `Updated`: dates;
- `Slug`: stable kebab-case identifier when present.

Adapt to an existing database schema rather than creating duplicate properties.

## Retrieval

1. Search exact title, slug, and aliases.
2. Search the term plus its local programming context.
3. Read the best candidates and their relevant relations.
4. Classify the answer as `existing`, `partial`, or `missing`.
5. Treat search snippets as discovery only; use full page content and sources for synthesis.

## Archive

Merge into the canonical page when possible. Otherwise create one page in the selected database or under the selected parent. Preserve unrelated blocks and existing properties. Add concise provenance links, related concepts, and an updated date. Do not copy entire external articles.

If the workspace has a query-log database or page, append a compact entry. Do not invent one when the existing wiki has no logging convention.

## Verify

Re-read the page after every create or update. Confirm:

- the canonical title and properties;
- the explanation blocks and source links;
- the page URL;
- any relation or query-log update.

Return the verified Notion page URL in the isolated task. If re-read fails, report the write as unverified.
