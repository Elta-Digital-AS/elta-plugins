# Elta plugins

## Install from the Elta marketplace

The native **0.3.19 candidate** is packaged under `plugins/claude`
and `plugins/codex`, with marketplace catalogs for both clients. See
[installation, OAuth and update commands](MARKETPLACE-INSTALL.md).

This candidate uses native OAuth discovery and the scopes in `marketplace-release.json`. It needs no private OpenAI app mapping or publisher secret. File
delivery and writes require explicit consent and open gates; native workflow
verification remains separate from package installation. The full
catalog source and its unfulfilled native acceptance record below are retained.

Maintainers reproduce the native release with
`python3 build_marketplaces.py --output /absolute/unused/directory` and verify
checked-in packages with `python3 build_marketplaces.py --check`.

The Story 9.59 candidate adds 1–20 photos per observation upload batch with the same fourteen scopes. Distribute only after the backend start tool advertises `files` and `declarations` and the bulk migration is deployed. Native multi-file workflows require their own acceptance; single-photo acceptance does not prove bulk handoff.

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

Application maintainers use one local command from the application checkout:

```sh
pnpm plugins:prepare --source /absolute/path/to/elta-plugins
pnpm plugins:prepare --source /absolute/path/to/elta-plugins --check
```

The command exports the live catalog and updates its digest, full-catalog scope
request, application mirror and both checked-in native trees. It validates the
candidate before writing. Check mode reports drift without writing either checkout;
the required application CI runs the same check against an immutable public commit.
No login, push, version bump, registration or publication is performed.

The public checkout owns authored skills, installation text, release choices and
acceptance records. The application mirror is derived; edit authored material here
and prepare it again. The registered-app builder and native builder share
`plugin_common.py`, while their manifest formats and compression settings remain
separate. Both continue to accept only unused output directories.

When catalog metadata or the target changes, preparation preserves the exact prior
matrix and release record under `acceptance-history/`, named by their content digests. It retains the old
catalog digest, connection, dates and evidence there, and resets current tool and
workflow cells to `unverified`. An unchanged catalog preserves the current matrix
verbatim. New evidence is recorded manually after real-client checks; preparation
never generates a pass. A catalog cannot detect a server behavior or workflow-only
change: maintainers must invalidate affected evidence explicitly in those cases.

For standalone work with an already exported catalog:

```sh
python3 -B prepare.py --catalog /absolute/exported/mcp-catalog.json \
  --mirror /absolute/app/packages/customer-plugins --check
```

Review and commit the public candidate, then pin its full commit in application CI.
Publish that public commit before remote application CI can fetch it. Local
preparation and local commits do not publish anything.

Directory submission, live registration changes, customer rollout and backend deployment remain separate actions. Do not commit credentials, tokens, private registration records, environment files or customer evidence.

## Platform references

- [OpenAI packaging and provided OAuth clients](https://developers.openai.com/plugins/build/plugins)
- [OpenAI authentication](https://developers.openai.com/plugins/build/auth)
- [OpenAI public submission](https://developers.openai.com/plugins/deploy/submission)
- [Claude MCP OAuth and scope pinning](https://code.claude.com/docs/en/mcp)
- [Claude plugin structure](https://code.claude.com/docs/en/plugins-reference)

[Privacy policy](https://sta.elta.no/privacy-policy) · [Terms](https://sta.elta.no/terms-of-service) · [Support](https://sta.elta.no/contact)

Core sync candidate0.3.17 requires the matching backend for the six core collection modes. No new OAuth scopes or reconnect are required for existing read grants. Exact cursor, tombstone and workflow-limit guidance is in the shared MCP contract. Native/hosted acceptance remains unverified; remaining collection sync modes are not claimed.

Remaining collection sync candidate0.3.18 completes all16REST sync modes on the matching backend. No new scopes or reconnect are required for existing metadata grants. Property-role offset and sync envelopes differ; follow the shared contract. Hosted/native continuation, tombstone and authority acceptance remains unverified.

Final parity candidate0.3.19 maps95REST operations,20scopes,16sync modes and existing bulk variants. Offset-only tools retain their own full REST bounds. Required source CI reproduces both native package trees and checks the exact public mirror. Actual hosted and client acceptance remains unverified; do not distribute before matching backend and release acceptance.
