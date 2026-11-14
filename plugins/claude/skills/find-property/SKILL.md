---
name: find-property
description: Find an Elta property by address or name, clarify multiple matches, or read its recorded identification facts.
---

Read [the read contract](../_shared/read-contract.md) before using any tool; follow its connection, evidence, scope and pagination rules.

1. Ask for an address/name when none was supplied. For an explicit property ID use `get_property`; otherwise use `list_properties` with a focused `search` and bounded paging.
2. If several plausible matches remain, show only the identifying facts needed to choose, including IDs, and ask the user to select one. Do not select a property just because it was the first result.
3. Confirm the selected property's returned address, ID and recorded property type/year. Label missing fields as unrecorded. An unavailable ID is not proof that no such property exists.
4. Stop with the confirmed identification or the clarification question. Offer observation reading only when it helps the user's request.
