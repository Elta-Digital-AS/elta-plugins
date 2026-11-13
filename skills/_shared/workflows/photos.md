# Finding photo edits

Read [the common contract](../mcp-contract.md) before using tools.
For changes, also read [mutation rules](mutations.md).
These finding-photo edit tools are offered only with file consent in addition to write consent and their required scopes. Read [file consent rules](files.md); this also applies to caption, order and removal changes that do not deliver file bytes.

When discovered and authorized, use `update_observation_photo_caption`, `reorder_observation_photos` and `remove_observation_photo` for finding photos only. Read the current observation version and photo metadata first. Null clears a caption. Reordering requires the complete unique set of 1–100 active finding-photo IDs, never a partial list. Removal identifies one specific photo; resolve ambiguous references such as “the last one” from authoritative context and current records. Position and filename are not upload chronology. Remediation photos cannot be removed through these tools. Keep the same ID, version and key for an identical retry and report deletion only from its successful result.
