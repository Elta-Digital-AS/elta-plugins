---
name: use-elta-tools
description: Work with connected Elta records across domains, view permitted images or files, or create, change and remove records through authorized MCP tools.
---

Read [the common contract](../_shared/mcp-contract.md) before using tools. Live discovery and the authenticated connection decide which tools and schemas are available; the packaged catalog grants no authority.

1. Identify the requested outcome and connected workspace. Clarify ambiguous workspace, record or mutation targets. Resolve Elta's host namespace through discovery; never guess a tool name or substitute another workspace.
2. Load the required guides below for this task only. Ordinary metadata lookup needs no additional guide. Do not load unrelated domain guides or historical release notes. If the task changes, load its newly required guides before acting.
3. Obtain prerequisite IDs and current versions through authorized reads. Use returned identifiers and actual schemas. Perform only the requested action, within the shared paging/detail budget and applicable consent.
4. Report returned references and the exact outcome. An identical retry can return a historical command reply, not current state. On missing tools or authority, stop with specific connection/gate guidance; never substitute REST, a database, another token or an external service.

## Required guides by task

Every change, including uploads, requires [mutation rules](../_shared/workflows/mutations.md). Each row adds the applicable guide; for a task spanning domains, load every applicable row.

| Task | Required guide |
| --- | --- |
| Incremental sync or cursor continuation | [Sync](../_shared/workflows/sync.md) |
| Read an existing image, document, scan or generated PDF | [File delivery](../_shared/workflows/files.md) |
| Upload photos, property covers, documents or certificate scans, including mixed batches | [Uploads](../_shared/workflows/uploads.md), [file handling](../_shared/workflows/files.md), plus document/certificate guides for those target kinds |
| Remove a property cover | [Cover handling and removal quota](../_shared/workflows/uploads.md) |
| Edit finding-photo caption/order or remove a finding photo | [Finding photos](../_shared/workflows/photos.md) and [file consent](../_shared/workflows/files.md) |
| Create/change/copy/save/remove a placement template | [Templates](../_shared/workflows/templates.md) |
| Create/change/remove a person or company, or assign/change/remove a property contact role | [Contacts and roles](../_shared/workflows/contacts-and-roles.md) |
| Inspection creation, completion/removal, answers/annotations, or finding links | [Inspections](../_shared/workflows/inspections.md) |
| Set or reset remediation costs | [Costs](../_shared/workflows/costs.md) |
| Upload, rename, recategorize or remove a property document | [Documents](../_shared/workflows/documents.md) |
| Create/change/remove measuring equipment | [Equipment](../_shared/workflows/equipment.md) |
| Create/change/archive/unarchive/remove a certificate or replace its scan | [Certificates](../_shared/workflows/certificates.md) |

Property, placement and ordinary observation/evidence changes use the mutation rules and discovered schemas. Do not infer an extra tool, bulk CRUD operation or recovery permission from this routing table. The four summary skills remain metadata-only and read-only; explicitly requested files or changes use this workflow.
