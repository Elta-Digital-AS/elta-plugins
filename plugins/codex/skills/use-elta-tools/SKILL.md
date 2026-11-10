---
name: use-elta-tools
description: Work with connected Elta records across domains, view permitted images or files, or create, change and remove records through authorized MCP tools.
---

Read `../_shared/mcp-contract.md` before using tools. Consult `../../mcp-catalog.json` for the packaged tool/scope metadata; the live discovered tool schemas and connection grant decide what can actually run.

1. Identify the user's requested outcome and the intended connected workspace. Clarify ambiguous workspace, record or mutation targets before acting. Resolve the host's Elta tool namespace from discovery, not a guessed tool name.
2. Choose the supported tool for the domain: properties/placements, observations/remediation, contacts/property roles, inspections, documents/reports, equipment/certificates, or reference/history data. Obtain prerequisite record IDs and current versions using authorized reads. Use returned identifiers and the discovered schemas.
3. For a read, page within the shared bound and cite record IDs. For an image/file, check the user's requested purpose and file consent; explain expiry/preview limitations. For a change, follow the shared mutation rules and the host's configured approval mechanism.
4. After a successful change, report exactly what changed with returned references. An identical retry may return the original command reply, not the current record. Preserve the same key/input after an uncertain result; read current state before deciding after a version conflict.
5. On missing tools or denied authority, stop with the specific connection/gate guidance. An available tool is not permission to use it for an unrelated action. Never substitute another workspace, token, REST endpoint, database or external service.
