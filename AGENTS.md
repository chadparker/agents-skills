# Shared agent skills

Curated from upstream sources, including [Matt Pocock's skills](https://github.com/mattpocock/skills), [HumanLayer's skills](https://github.com/humanlayer/skills), and [Armin Ronacher's agent-stuff](https://github.com/mitsuhiko/agent-stuff), plus local skills written for this repo.

Each skill's `SKILL.md` frontmatter records its provenance. Each folder includes a `LICENSE` and an `agents/openai.yaml`; preserve any additional per-skill credits, such as [pr/CREDITS.md](pr/CREDITS.md).

## Maintenance

- Keep skill names and cross-skill references stable; use metadata for attribution rather than renaming skills.
- Keep `agents/openai.yaml` consistent with the skill: set `policy.allow_implicit_invocation: false` when `SKILL.md` has `disable-model-invocation: true`.

### Imported skills

- When adding or updating a skill, maintain its frontmatter `metadata`: `author`, `source` (pinned upstream file URL), `comparison-baseline` (exact upstream commit), `license`, and `local-differences`.
- Compare all skill files against the baseline and summarize differences in the metadata. A comparison baseline is not necessarily the original import revision.
- Preserve existing attribution metadata, per-skill credits, and the applicable license and copyright notice in each skill folder's `LICENSE`.
- Include the upstream source URL and commit in import/update commit messages.

### Local skills

- Skills written here use `metadata`: `author` (the git author name), `source: local`, and `license: MIT`. Omit `comparison-baseline` and `local-differences`.
- Add an MIT `LICENSE` with the author's copyright.
- If a local skill adapts substantial upstream content, treat it as imported instead.
