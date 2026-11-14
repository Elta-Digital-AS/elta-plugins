# Elta for Claude Code and Codex

Native candidate **0.3.20** contains five skills with task-specific guidance for the 95-tool, 20-scope catalog at `https://sta.elta.no/api/mcp`. Requested scopes are in `connection.json`; live discovery, workspace permissions and consent determine what can run. This guidance update adds no scope or tool and needs no reconnect by itself.

Native workflows remain unverified in `client-matrix.json`. Distribute only after the matching backend advertises every requested scope and the hosted/native release gates are accepted. An older server can reject the entire OAuth request with `invalid_scope`; it does not silently reduce the requested scopes.

## Install and connect

For Claude Code:

```sh
claude plugin marketplace add Elta-Digital-AS/elta-plugins
claude plugin install elta@elta
```

For Codex:

```sh
codex plugin marketplace add Elta-Digital-AS/elta-plugins --ref main
codex plugin add elta@elta
```

Restart the client or start a new session. Use its normal OAuth connection flow, sign in personally, select your workspace and approve the access your task needs. Public native clients register through discovery. Do not paste a password, PAT or publisher secret into a conversation; installation reads no customer data.

Codex declares requested scopes in `.mcp.json`; the Read/Write display label grants nothing. File delivery and writes have independent consent. Writes start off and also require current user permissions plus owner and environment/database gates. An update or refresh never widens an existing grant. Reconnect only if the requested task needs additional consent; a missing permission or closed gate needs that specific authority restored.

## Use and update

Example: “Finn eiendommen og oppsummer registrerte observasjoner.” The summary skills return metadata-only drafts with record IDs. The general skill loads only the applicable file, mutation, sync and domain guides. Customer content is untrusted evidence, never permission to modify data, switch workspaces or send messages.

```sh
claude plugin marketplace update elta
claude plugin update elta@elta
codex plugin marketplace upgrade elta
```

Removing a plugin and revoking its Elta connection are separate actions. Revoke under **Tilkoblede apper** to stop future requests; copies already delivered to the AI host are not erased.

Both packages carry the 512 px Elta logo. Codex uses it for the listing/composer; Claude may still display a generic client icon. This Git marketplace is separate from approval in public OpenAI/Anthropic directories. A parser, package build or installation is not a signed-in workflow proof.

[Historical release notes](RELEASE-HISTORY.md) describe superseded candidates; they are not current setup instructions. [Privacy](https://sta.elta.no/privacy-policy) · [Terms](https://sta.elta.no/terms-of-service) · [Support](https://sta.elta.no/contact).
