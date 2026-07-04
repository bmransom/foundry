---
title: Glossary — the ubiquitous language
description: The vocabulary contract for specs, code, APIs, and concepts.
type: reference
---

<!-- foundry-seed: glossary v2 -->

# Glossary — the ubiquitous language

The vocabulary contract for this repo's specs, code, APIs, and concepts. When code and
this file disagree, this file wins; the code is debt to be migrated. A new term
names its prior art — the industry or stack standard it follows — or records why
none fits.

**Vocabulary polarity:** `<state whether this repo excludes outside domain
vocabulary (a neutral engine) or embraces it (a product), and what enforces the rule>`.

## Entity model

The repo's core entities and how they nest — the spine every new public type,
field, and record must fit. Sketch it as an indented tree, one line per entity,
when the first design names them.

## Bounded contexts

The sub-domains this repo spans, when it spans more than one — each has its own model
and its own use of the vocabulary, so the same word can mean different things across a
boundary. State **N/A** for a single-context repo. When there are several, name which
context owns each canonical term below (a `Context` column, or a subheading per context)
so a reader knows which language applies where. Prior art: DDD bounded contexts; the code
side of the same boundary is `modular-structure`.

## Canonical terms

Keep the rows **alphabetical by term** (with several contexts, group by context then
alphabetical) so a term is findable by scanning.

| Term | Definition | Wire / id | Replaces (now debt) |
|---|---|---|---|
