---
name: zoom-out
description: Ask the agent to zoom out a level and map the relevant modules and callers using the project's domain language.
disable-model-invocation: true
metadata:
  author: Matt Pocock
  source: https://github.com/mattpocock/skills/blob/801a01cc7d265e06dd9dbcef5a4c471add05a0b3/skills/engineering/zoom-out/SKILL.md
  comparison-baseline: 801a01cc7d265e06dd9dbcef5a4c471add05a0b3
  license: MIT
  local-differences: Provenance metadata and per-skill LICENSE added. Upstream removed this skill in e112a6b; the baseline is the last revision before removal.
---

I don't know this area of code well. Go up a layer of abstraction. Give me a map of all the relevant modules and callers, using the project's domain glossary vocabulary.
