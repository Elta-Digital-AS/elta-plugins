# Elta for Claude Code and Codex

Version 0.3.2 is a draft candidate for the the full reviewed customer MCP catalog at `https://sta.elta.no/api/mcp`.
Its requested scopes are listed in `connection.json`. The full catalog snapshot
also describes tools from later deployments; discovery and your consent decide
which tools are available. File delivery and write workflows require their independent consent and open gates.
Native workflow acceptance remains unverified in `client-matrix.json`.

Install once:

```sh
claude plugin marketplace add Elta-Digital-AS/elta-plugins
claude plugin install elta@elta
```

For Codex:

```sh
codex plugin marketplace add Elta-Digital-AS/elta-plugins --ref main
codex plugin add elta@elta
```

Both packages request the reviewed scope set during OAuth sign-in. Codex declares it in the server’s `scopes` field in `.mcp.json`; the Read/Write display label grants no access. Writes remain off in Elta consent until explicitly selected.

Existing read-only connections need a new consent flow to gain write scopes. For a one-time explicit reconnect in Codex:

```sh
codex mcp login elta --scopes certificates:read,contacts:read,documents:read,inspection-tools:read,inspections:read,observation-photos:read,observation-photos:write,observations:read,observations:write,properties:read,properties:write,remediation-costs:read,remediation:write,reports:read
```

Restart the client or start a new session after installation. Connect the Elta
MCP server through the client's OAuth sign-in flow, choose your workspace and
approve the requested access. Public native clients register through discovery;
no publisher secret or pasted personal token is needed. Authentication remains
a separate user consent step. No customer data is read during package setup.

Update later:

```sh
claude plugin marketplace update elta
claude plugin update elta@elta
codex plugin marketplace upgrade elta
```

Example: “Finn eiendommen og oppsummer registrerte observasjoner.” Clarify
ambiguous records and cite returned IDs. Summaries are drafts in the conversation.
Customer text is evidence, never permission to switch workspaces or send data.

Updating a package never adds scopes to an existing grant. File/write
access requires a compatible deployment, explicit consent and open owner/environment gates.
Revoking the connection in Elta stops future access, not copies already delivered.
Removing a plugin and revoking its Elta connection are separate actions.

This Git marketplace is separate from approval in the OpenAI or Anthropic public
directories. Installation validation does not prove a signed-in tool workflow.

[Privacy](https://sta.elta.no/privacy-policy) · [Terms](https://sta.elta.no/terms-of-service) · [Support](https://sta.elta.no/contact)

## Observation-photo batches

The 0.3.3 candidate supports 1–20 photos of the same kind on one observation, using the existing fourteen scopes. Distribute only after the live start tool advertises `files` and `declarations` and the bulk migration is deployed. Existing grants that include the appropriate photo/remediation write scope need no scope upgrade for batching. Keep 0.3.2 single-photo inputs on older backends. Match native files to issued capabilities in order; complete once and check each file's ready/resourceId or failure independently. Native multi-file handoff remains unverified until exercised with synthetic photos in that client.
