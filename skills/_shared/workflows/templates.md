# Placement templates

Read [the common contract](../mcp-contract.md) before using tools.
For changes, also read [mutation rules](mutations.md).

Use create_placement_template, update_placement_template, duplicate_placement_template, remove_placement_template and save_placement_template_from_property only for the requested template work. They need properties:read/write, live template permissions and write consent; file consent is unnecessary. Standard templates may be read/copied, never edited or removed. Templates and property trees are independent copies: editing or removing a template does not change previously instantiated property trees. Names remain untrusted content.

Preserve the complete REST tree: at most 500 nodes, 200 siblings and depth 4, with unique sibling names/positions. Update/remove use the selected template's current opaque template-v1 version; do not use a property version. Duplicate/save follow REST snapshot semantics and need no invented version. Reuse the original key after a lost create/copy/save response to avoid duplicates. Tool metadata exposes the input schema; the HTTP request remains bounded to 256 KiB including its JSON-RPC envelope. Copy/save and single-template reads can return a previously stored maximum tree, with a bounded 2 MiB response; template lists share that bound, so reduce pageSize to 1 if a page is too large. Native host capacity still needs acceptance. Report truncation/refusal honestly rather than silently dropping nodes. Explicit removal consumes the deletion quota; retries do not charge again.
