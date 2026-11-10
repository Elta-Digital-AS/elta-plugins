# Elta plugins

Read-only Elta workflows for ChatGPT, Codex and Claude, maintained by Elta Digital AS.

This public repository contains four shared skills and a dependency-free Python builder that emits each platform's manifests and connection configuration. The Elta application and server implementation remain in their separate private repository. Only the plugin materials here are licensed under [MIT](LICENSE).

## Status

This is pre-release source for private testing, not an approved marketplace listing. Native installation and end-to-end workflow acceptance remain unverified in [client-matrix.json](client-matrix.json). The current connection endpoint is `https://sta.elta.no/api/mcp`; a later move to the production domain is planned.

The workflows find a property, summarize observations, review outstanding remediation and draft a customer-friendly summary. Replies default to Norwegian Bokmål and preserve recorded facts and source IDs. They request only `properties:read observations:read` and use five read tools. No writes, file downloads, report generation or message sending are included.

## Customer connection

Customers choose Connect in the supported host, sign in to Elta, select an eligible workspace and approve the read scopes. Each connection is bound to one workspace and the user's current permissions. Marketplace customers do not supply the publisher's OAuth client ID or secret. Registration identifiers below are build inputs for maintainers, not a customer setup step. See [INSTALL.md](INSTALL.md) for private installation and disconnection guidance.

## Build for private testing

Use Python 3.11 or later. A maintainer must first verify the host registration, exact callback, endpoint and read scopes. No credentials are bundled.

```sh
python3 build.py \
  --output /absolute/unused/output-directory \
  --mcp-url https://sta.elta.no/api/mcp \
  --openai-app-id YOUR_REGISTERED_OPENAI_MCP_APP_ID \
  --claude-client-id YOUR_REGISTERED_ELTA_PUBLIC_OAUTH_CLIENT_ID
```

The OpenAI input is an existing `asdk_app_…` registration or its `plugin_asdk_app_…` URL identifier, not an Elta OAuth client ID. The Claude input is a public `elta_app_…` OAuth client registered for the tested host callback. A hosted Claude confidential registration cannot be substituted for a Claude Code public loopback registration.

The builder emits `openai/`, `claude/`, two versioned ZIPs and `artifacts.json` with SHA-256 hashes. The OpenAI manifest uses a registered app mapping; that format is for private testing and is not eligible for direct public ZIP submission. Claude receives its own manifest and remote MCP configuration. Both packages contain identical skill bytes, the read contract, compatibility record and MIT license. Outputs are deterministic and existing output directories are refused.

## Validate

```sh
python3 -m unittest discover -s . -p 'test_*.py'
claude plugin validate /absolute/output/claude
```

Offline tests deliberately use synthetic, non-working registration IDs. They check deterministic builds, manifest separation, identical skills, bounded read policy, license inclusion, malformed targets, accidental secrets, source escape and overwrite refusal. A parser or schema check does not prove native OAuth or workflow behavior. Run the synthetic scenarios in [native-cases.json](native-cases.json) on each target client before accepting a release.

Directory submission, customer-wide distribution and hosted deployment remain separate actions. Do not commit passwords, tokens, client secrets, local environment files or customer data.
