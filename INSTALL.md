# Elta read-only plugin: private installation

This package provides four workflows: find a property, summarize observations, review outstanding remediation, and draft a customer-friendly summary. Replies default to Norwegian Bokmål. It uses only the five property/placement/observation reads and `properties:read observations:read`; it provides no file access, writes, report generation or email delivery. The packaged `connection.json` names the exact server and requested scopes.

An installed skill is a workflow, not an authorization boundary. Connect through the host's OAuth sign-in, select the intended Elta workspace, and review its consent. Keep write/file choices off. Elta enforces your current permissions on every call. The AI host receives authorized read data under its own terms; this package makes no processing-location promise.

## Customer connection and publisher setup

Customers choose **Connect**, sign in to their own Elta account, select their workspace, and approve the two read scopes. Each connection receives separate workspace-bound access and refresh tokens. The publisher's client ID or secret identifies the integration and grants no customer-data access by itself.

Elta manages a shared platform app registration. The workspace owning that registration manages the integration; each customer separately selects the workspace whose data they authorize. For a public Claude directory listing, require user sign-in and use Anthropic-held client credentials; for the current OpenAI connection, use a registered public OAuth client with PKCE. Customers installing those listings do not create developer apps or enter the publisher's client secret. A custom connector's “use your own client” form is publisher/test setup, not the marketplace customer's connection flow. Claude Code loopback registration is a separate native-client setup.

## ChatGPT and Codex

The OpenAI package references an existing registered custom MCP app through `.app.json`. Its public app ID is not an OAuth client ID or a credential. Before generating the package, configure that app with the exact `connection.json` resource and the two read scopes. Hosted ChatGPT callbacks require a registered Elta developer app with the exact callback shown by ChatGPT; Elta's automatic registration accepts loopback callbacks only. Use public-client OAuth (`none`) where the host supports it; enter any required confidential client secret only in host connection setup.

For private desktop testing, add the generated OpenAI folder to your own local marketplace following OpenAI's [packaging guide](https://developers.openai.com/plugins/build/plugins). Point its local `source.path` to the plugin folder. Install it from that marketplace, enable it, connect Elta, and start a new conversation. Codex CLI also supports marketplace installation; use `codex plugin --help` for the installed version. Hosted private plugin upload/setup availability depends on your workspace and surface; a ZIP existing locally is not proof of a successful hosted installation. An app-reference ZIP is for private distribution, not the public submission portal.

Ask for one of the bundled workflows, using the host's plugin/skill picker when needed. If the app mapping is unavailable or sign-in cannot finish, stop and have the owner verify the app ID, callback registration and scopes. Never replace OAuth with a pasted personal token.

## Claude

Install the Claude folder privately using the custom plugin upload option, or use `claude --plugin-dir /absolute/path/to/claude` for a temporary Claude Code session. `claude plugin validate /absolute/path/to/claude` validates its manifest. The packaged server is named `elta`; authenticate it through the host's MCP/connector setup before asking a workflow to read data.

The package pins `oauth.scopes` to the two reads and uses a registered public `oauth.clientId`. Claude Code uses a loopback callback; configure a fixed callback port in host settings if the client registration requires it. Claude chat/Cowork remote connectors connect from Anthropic's cloud and require a publicly reachable HTTPS endpoint and their actual registered callback. For private publisher testing, the connector setup may require selecting “Use your own OAuth client”; that is not a step for customers installing the public directory listing. A Claude Code parser result does not establish chat/Cowork interoperability; consult the dated compatibility record supplied with your distribution.

## Try the workflows

- “Finn eiendommen i Syntetisk vei 954.” If several properties match, select one by the returned reference.
- “Oppsummer registrerte observasjoner for denne eiendommen, med TG og status.”
- “Hvilke observasjoner er fortsatt åpne eller under utbedring?”
- “Lag et kundevennlig utkast her i samtalen basert på disse funnene.”

Results identify source IDs. A scan stops at 10 pages/250 rows or 50 detail calls and clearly labels partial results. Narrow the request or explicitly continue for more. An empty authorized result differs from a missing/inaccessible record; ask the workspace owner to check access when forbidden. Expired/revoked sign-in requires reconnecting after authority is restored. Changing workspace requires explicit reconnection, not an inferred account switch. After the independent-workspace OAuth migration is deployed, the same user and app can retain one connection per workspace: reconnecting replaces only that workspace's previous connection. Each connection retains separate consent and revocation. Hosted rollout and native-client support for retaining multiple connections must be verified separately.

## Update, disconnect and remove

Replace a private package with the newly generated version and refresh/restart the host as required by its installation mechanism. Recheck the connection target/scopes after updating. Remove or disable the plugin through the host's plugin settings. Separately revoke its Elta connection under **Tilkoblede apper** when access must stop. Revocation stops future access; it does not erase data already received by the AI host. Do not send a customer's summary externally from these workflows; the draft stays in the conversation for review.

Public directory submission, workspace-wide publishing, production deployment and access-switch changes are separate operator actions. This package grants none of them automatically.

## License

The shared skills, manifests and build tooling in this repository are licensed under MIT. Generated packages include the license. This does not license the separate Elta service or its server implementation.
