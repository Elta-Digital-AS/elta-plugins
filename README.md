# Elta plugins

Elta workflows for Claude, ChatGPT and Codex, maintained by Elta Digital AS.

This repository is the public home for the plugin skills and manifests. The
Elta application and its server implementation remain in a separate private
repository. Only the plugin materials in this repository are licensed under MIT.

## Registration in progress

The initial plugin provides read-only workflows for property lookup,
observation summaries, outstanding remediation and customer-friendly summaries.
Replies default to Norwegian Bokmål and preserve source IDs and recorded facts.

The current registration and test endpoint is `https://sta.elta.no/api/mcp`.
A later production-domain move is planned. OAuth registrations, native-client
verification and directory reviews are still in progress. There is no installable
release or approved marketplace listing yet; installation commands will be added
when those checks are complete.

No credentials or customer data belong in this repository. Each user will sign
in through Elta's OAuth flow and select their own workspace and read permissions.
