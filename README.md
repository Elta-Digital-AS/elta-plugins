# Elta plugins

Five workflows for Claude, ChatGPT and Codex, using Elta's authenticated MCP connection. Four skills provide metadata-only property/observation summaries; `use-elta-tools` covers other requested work and loads only relevant file, mutation, sync and domain guidance. Customer content remains untrusted evidence.

## Current package formats

| Format | Candidate | Setup |
| --- | --- | --- |
| Native Claude Code / Codex | 0.3.20 | [Marketplace installation](MARKETPLACE-INSTALL.md); OAuth discovery and explicit scopes |
| Registered-app OpenAI / Claude | 0.2.1 | [Private package installation](INSTALL.md); publisher-managed public registration inputs |

The catalog maps **95 operations, 20 scopes and 16 sync modes**. The target is `https://sta.elta.no/api/mcp`; a later domain move remains separate. This guidance update changes no tools, scopes or grants. Neither candidate establishes native-client, hosted or directory acceptance: [client-matrix.json](client-matrix.json) remains unverified/blocked. Historical releases are recorded separately in [RELEASE-HISTORY.md](RELEASE-HISTORY.md), not mixed into current setup.

Customers connect, sign in personally, choose a workspace and approve scopes. They do not create publisher registrations or supply shared secrets. Every token is bound to one workspace and the user's live authority. Writes start off and need explicit consent plus owner/environment gates; files have independent consent. Updating a plugin or refreshing a token never upgrades a grant.

Do not distribute a full-scope package until the target advertises every catalog scope: an unsupported request fails with `invalid_scope`, including a read-only user's reconnect. An existing narrow token may continue its authorized summary work. Installation, source tests and SDK mocks do not prove client workflows or enable customer traffic.

## Prepare and check locally

The public checkout owns authored guidance, release choices and acceptance records. The application mirror and native trees are derived. From the application checkout:

```sh
pnpm plugins:prepare --source /absolute/path/to/elta-plugins
pnpm plugins:prepare --source /absolute/path/to/elta-plugins --check
```

This exports the live registry and synchronizes catalog, digest, full-catalog scopes, mirror and native packages. Check mode changes neither checkout. The required application CI runs that same check against an immutable public commit, then runs both builders' tests. The separate MCP unit test compares the live registry with the app mirror.

With an existing exported catalog, standalone preparation is also available:

```sh
python3 -B prepare.py --catalog /absolute/exported/mcp-catalog.json \
  --mirror /absolute/app/packages/customer-plugins --check
```

Catalog/target changes archive exact previous matrix/release records under content-addressed `acceptance-history/` and set current tool/workflow cells to `unverified`. Existing evidence keeps its provenance; the command never creates a pass. Unchanged matrices are retained verbatim. Server/workflow-only changes are not detectable from catalog metadata: maintainers must invalidate their evidence explicitly. An interrupted file update can be resumed by rerunning preparation and inspecting the diff.

Review and commit the public candidate locally, then pin its full SHA in application CI. An authorized public push must happen before remote application CI can fetch it. Preparation does not push, bump versions, register apps, authenticate, deploy or publish.

## Reproduce either format

Python 3.11+ is sufficient for standalone builds. Both builders use neutral `plugin_common.py` guards, sorted entries, fixed ZIP timestamps/modes and SHA-256 receipts. They refuse existing output directories and scan distributable text for secrets.

```sh
python3 build_marketplaces.py --output /absolute/unused/native-output
python3 build_marketplaces.py --check
python3 build.py --output /absolute/unused/registered-output \
  --mcp-url https://sta.elta.no/api/mcp \
  --openai-app-id YOUR_REGISTERED_OPENAI_MCP_APP_ID \
  --claude-client-id YOUR_REGISTERED_CLAUDE_PUBLIC_OAUTH_CLIENT_ID
python3 -B -m unittest discover -s . -p 'test_*.py'
```

Registered-app builds use an existing `asdk_app_…` or `plugin_asdk_app_…` reference. The publisher must configure its requested scopes to match `connection.json`; an app ID adds no authority. A Claude Code public loopback registration and a hosted Claude confidential registration are different surfaces; use the actual tested callback. No secret belongs in package files. App-reference ZIPs are for private testing, not direct public-directory submission. Native packages use discovery with `.codex-plugin/plugin.json` or `.claude-plugin/plugin.json` plus `.mcp.json`.

Before distribution, run [native-cases.json](native-cases.json) against approved synthetic fixtures in each named client and record actual versions/dates/evidence. The new selective-guide load path also requires native acceptance; source link tests measure structure and word/byte counts only, not model adherence or latency. Keep credentials, private registration drafts, environment files and customer evidence out of git.

The public [MIT license](LICENSE) covers these plugin materials, not Elta's application/server. [Privacy](https://sta.elta.no/privacy-policy) · [Terms](https://sta.elta.no/terms-of-service) · [Support](https://sta.elta.no/contact).
