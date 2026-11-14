---
name: summarize-observations
description: Summarize recorded Elta observations for a selected property, including grades, status and relevant remediation evidence.
---

Read [the read contract](../_shared/read-contract.md) before using any tool; follow its connection, evidence, scope and pagination rules.

1. Resolve and confirm one property using the `find-property` workflow or an unambiguous returned ID before listing findings.
2. Read `list_property_observations` with the requested filters and bounded paging. Preserve `meta.hasMore`; state any partial scan.
3. Read `get_property_observation` only where the requested summary needs details. Resolve placement labels through `list_property_placements` when needed, within the same page bound.
4. Summarize the recorded issue, TG grade and status, then the documented remediation/evidence when present. Distinguish a recorded completion from independent verification. Give property and observation references and relevant data gaps; draw no new compliance conclusion.
