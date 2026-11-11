# Elta plugins

## Install from the Elta marketplace

The native **0.3.2 candidate** is packaged under `plugins/claude`
and `plugins/codex`, with marketplace catalogs for both clients. See
[installation, OAuth and update commands](MARKETPLACE-INSTALL.md).

This candidate uses native OAuth discovery and the scopes in `marketplace-release.json`. It needs no private OpenAI app mapping or publisher secret. File
delivery and writes require explicit consent and open gates; native workflow
verification remains separate from package installation. The full
catalog source and its unfulfilled native acceptance record below are retained.

Maintainers reproduce the native release with
`python3 build_marketplaces.py --output /absolute/unused/directory` and verify
checked-in packages with `python3 build_marketplaces.py --check`.

The Story 9.58 candidate adds observation photo uploads and requests fourteen scopes. Keep this PR in draft until the backend advertises every requested scope and native attachment acceptance is recorded. The released marketplace remains unchanged until this source is merged and released.

## Full-catalog package source

Elta workflows for Claude, ChatGPT and Codex. The packages support the released customer MCP catalog: authorized metadata reads, image/file tools and the existing property/placement/observation write tools. The public [MIT license](LICENSE) covers these plugin materials, not the separate Elta application or server implementation.

## Status and access

Version 0.2.0 is pre-release source. Native acceptance remains **blocked by deployment prerequisites** in [client-matrix.json](client-matrix.json); no marketplace approval or hosted deployment is claimed. The current test endpoint is `https://sta.elta.no/api/mcp`; a later production-domain move is planned.

[mcp-catalog.json](mcp-catalog.json) is an exported snapshot of Elta's released tool names, scopes and read/file/write flags. The policy pins its canonical SHA-256 digest. A snapshot documents support; it grants no authority. Live tool discovery, the user's selected workspace, role, consent and backend gates determine what can run. New backend tools need a reviewed catalog update and the same acceptance checks, not an unrestricted wildcard.

Customers choose Connect, sign in personally, choose their workspace and review Elta consent. They never supply the publisher's client secret. Writes are off by default and need explicit consent, owner approval and environment gates. Files have independent consent. Existing narrow grants remain narrow after an update or refresh; a broader task may require an explicit reconnect. No shared workspace credential is bundled.

Do not distribute or reconnect this full-scope Claude package until the target protected-resource metadata advertises every scope in `mcp-catalog.json`. Elta rejects unsupported requested scopes with `invalid_scope`; it does not silently downgrade the request. On a lagging deployment, even a read-only reconnect can fail. Existing narrow tokens can continue their permitted summary workflows until revoked or expired; keep the previous compatible package until deployment and native acceptance are complete.

## Build

Python 3.11+ is sufficient. Publisher-managed public client IDs are maintainer inputs, not customer credentials. Register each platform's exact callback and verify the public-client flow before using real identifiers.

```sh
python3 build.py \
  --output /absolute/unused/output-directory \
  --mcp-url https://sta.elta.no/api/mcp \
  --openai-app-id YOUR_REGISTERED_OPENAI_MCP_APP_ID \
  --claude-client-id YOUR_REGISTERED_CLAUDE_PUBLIC_OAUTH_CLIENT_ID
```

The OpenAI input is an existing `asdk_app_…` registration or its `plugin_asdk_app_…` URL identifier. The package emits `plugin.json` and `.app.json`. The publisher must configure that registered app's host-side OAuth request to match every scope in `connection.json`, then verify native discovery. An app ID does not upgrade an existing two-scope connection. App-reference ZIPs are for private testing and cannot be uploaded directly to the public submission portal.

The legacy `build.py` app-reference format remains available for registered-app testing. The native `build_marketplaces.py` format uses Codex’s `.codex-plugin/plugin.json` and `.mcp.json` format with explicit `scopes` and OAuth discovery. Codex 0.167.0 rejects the documented per-server `extensions.com.openai.auth` field in the generic Agent Plugins MCP format, so that format cannot carry the scope fix for this client version. Marketplace submission remains separate.

The Claude package emits `.claude-plugin/plugin.json` and `.mcp.json`, pinning the catalog scope request. Its client ID must be a public OAuth registration appropriate to the tested host callback; a hosted Claude confidential registration cannot be substituted for a Claude Code public loopback client. Secrets belong only in the host's secure connection setup when that host requires them.

Both folders/ZIPs include the same five skills, shared contracts, catalog, connection record, compatibility matrix and MIT license. Builds have sorted entries, fixed ZIP timestamps/modes and SHA-256 receipts, and refuse existing output paths. The four property/observation summary skills stay read-only; `use-elta-tools` handles other domains, files and requested mutations within granted authority. See [INSTALL.md](INSTALL.md).

## Validation

```sh
python3 -m unittest discover -s . -p 'test_*.py'
claude plugin validate /absolute/output/claude
```

The tests use deliberately non-working identifiers and exercise manifest/connection separation, full catalog scope coverage, deterministic ZIPs, source/path/secret guards, license inclusion and truthful native-evidence metadata. They do not log in, run customer tools or prove native host behavior. A parser or schema result is structural evidence only.

Before distribution, run [native-cases.json](native-cases.json) using approved synthetic fixtures in each named surface. Record the version/date and evidence plus the full authorized tool matrix. Missing hosted tools, closed write gates and unsupported previews are explicit blockers. Never describe a mocked SDK test as native ChatGPT/Claude acceptance.

The application-side MCP tests compare the application mirror of this snapshot with the real released registry. Application CI separately checks out a pinned public source commit and compares all distributable files with that mirror. Publish the matching public commit before running application CI; a coordinated source change cannot pass against an older pin. The public repository needs no access to private application files.

Application maintainers export the registry with `pnpm --filter @elta/customer-mcp --silent catalog:export`, copy the resulting JSON to this repository's `mcp-catalog.json`, and update the matrix alongside it. Recompute the policy's `catalogSha256` with the command below. Pin the reviewed public source commit in application CI after publishing it.

```sh
python3 -c 'import json; from build import catalog_digest; print(catalog_digest(json.load(open("mcp-catalog.json"))))'
```

Directory submission, live registration changes, customer rollout and backend deployment remain separate actions. Do not commit credentials, tokens, private registration records, environment files or customer evidence.

## Platform references

- [OpenAI packaging and provided OAuth clients](https://developers.openai.com/plugins/build/plugins)
- [OpenAI authentication](https://developers.openai.com/plugins/build/auth)
- [OpenAI public submission](https://developers.openai.com/plugins/deploy/submission)
- [Claude MCP OAuth and scope pinning](https://code.claude.com/docs/en/mcp)
- [Claude plugin structure](https://code.claude.com/docs/en/plugins-reference)

[Privacy policy](https://sta.elta.no/privacy-policy) · [Terms](https://sta.elta.no/terms-of-service) · [Support](https://sta.elta.no/contact)
