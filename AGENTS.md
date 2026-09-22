# Shared agent skills

Curated from upstream sources, including [Matt Pocock's skills](https://github.com/mattpocock/skills) and [HumanLayer's skills](https://github.com/humanlayer/skills).

Each skill's `SKILL.md` frontmatter records its provenance. Each folder includes its upstream `LICENSE`; preserve any additional per-skill credits, such as [pr/CREDITS.md](pr/CREDITS.md).

## Maintenance

- When adding or updating a skill, maintain its frontmatter `metadata`: `author`, `source` (pinned upstream file URL), `comparison-baseline` (exact upstream commit), `license`, and `local-differences`.
- Compare all skill files against the baseline and summarize differences in the metadata. A comparison baseline is not necessarily the original import revision.
- Preserve existing attribution metadata, per-skill credits, and the applicable license and copyright notice in each skill folder's `LICENSE`.
- Include the upstream source URL and commit in import/update commit messages.
- Keep skill names and cross-skill references stable; use metadata for attribution rather than renaming skills.
