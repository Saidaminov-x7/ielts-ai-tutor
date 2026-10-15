# Railway Obsidian server

This runs the Obsidian desktop application in a Railway container and serves its
browser UI through GitHub OAuth. The Obsidian app has no public domain; only the
OAuth2 Proxy service is public. A persistent Railway Volume stores `/config`,
including the cloned private vault and Obsidian settings.

## Architecture

```text
Browser --HTTPS--> public oauth2-proxy --private HTTP--> obsidian-app:3000
                                                        |
                                                        +-- /config/vault
                                                            private GitHub repo
```

OAuth2 Proxy allows only the GitHub login in `OAUTH2_PROXY_GITHUB_USERS`.
LinuxServer's Obsidian container is locked down with `HARDEN_DESKTOP=true`,
which disables its terminal, sudo, and other open tools. Do not create a Railway
domain for `obsidian-app` or expose its ports publicly.

## Build and app service

Create the `obsidian-app` Railway service from this repository and branch, with
Root Directory `obsidian-server` and Dockerfile builder. Mount a persistent
Railway Volume at `/config`. Keep this service private and do not generate a
public domain. Set these Railway variables:

```text
GITHUB_TOKEN=<fine-grained token limited to the private vault>
GITHUB_REPO=Saidaminov-x7/ielts-tutor-notes-vault
GITHUB_BRANCH=main
HARDEN_DESKTOP=true
SELKIES_ENABLE_SHARING=false|locked
SELKIES_ENABLE_COLLAB=false|locked
SELKIES_FILE_TRANSFERS=none
```

This is a separate Railway project, so Railway cannot reference the
`ielts-webhook` service variable across projects. Set a fine-grained PAT directly
on `obsidian-app`, restricted to this private vault with Contents read/write.
Do not paste it into a command, image, URL, repository, vault, or chat. The
startup initializer uses an in-memory Git credential helper; the token is not
written to the remote URL or Git config. Clone/pull error output is suppressed
so Git cannot disclose credential-related details to Railway logs.

`init-vault` clones the selected branch into `/config/vault` on first start.
For an existing checkout it verifies the origin and fast-forward pulls changes.
It refuses to overwrite a non-empty, non-Git directory or a checkout with a
different origin.

## Railway idle sleep

Both `obsidian-app` and `obsidian-auth` use Railway's `sleepApplication` mode,
matching the `ielts-webhook` service. Railway does not expose a one-minute idle
threshold: Serverless sleeps after roughly five minutes without outbound
traffic, and sampling can make the observed delay about 5–10 minutes. Incoming
traffic wakes the service. The open remote-desktop/WebSocket session may keep
the app active, so close the Obsidian browser tab when you want it to sleep.
Railway applies the setting on deployment. See
[Railway Serverless](https://docs.railway.com/deployments/serverless) and
[WebSocket limits](https://docs.railway.com/networking/public-networking/specs-and-limits).

## Public OAuth2 Proxy service

Create a second service from the public image
`quay.io/oauth2-proxy/oauth2-proxy:v7.15.5` named `obsidian-auth`. Set its
start command to:

```text
oauth2-proxy --http-address=0.0.0.0:4180 --provider=github --email-domain=* --github-user=<your-github-login> --upstream=http://obsidian-app.railway.internal:3000/ --reverse-proxy=true --proxy-websockets=true --skip-provider-button=true --cookie-secure=true --cookie-httponly=true --cookie-samesite=lax --cookie-refresh=1h --cookie-expire=8h --pass-access-token=false --request-logging=false
```

Set the following variables on `obsidian-auth` (all secrets belong in Railway
Variables, never in this repository):

```text
OAUTH2_PROXY_CLIENT_ID=<GitHub OAuth App client ID>
OAUTH2_PROXY_CLIENT_SECRET=<GitHub OAuth App client secret>
OAUTH2_PROXY_COOKIE_SECRET=<random base64-encoded 32-byte value>
OAUTH2_PROXY_REDIRECT_URL=https://<generated-domain>/oauth2/callback
```

Generate one Railway public domain for `obsidian-auth`, target port `4180`, then
use that exact HTTPS callback URL in the GitHub OAuth App. Do not make the
Obsidian service public. Use a dedicated GitHub OAuth App and allowlist only the
account that owns the vault.

## Open the vault and enable Git sync

After the services are deployed and OAuth works, open the `obsidian-auth`
domain, authenticate with the allowlisted GitHub account, and choose
`/config/vault` if Obsidian asks which vault to open. In Obsidian, install and
enable the community plugin **Obsidian Git**. The Git executable and a
credential helper are already available in the container. In the plugin
settings enable auto-pull on startup and set auto-pull and auto-push intervals
(for example, 5 minutes); keep pull-before-push enabled. This makes bot-created
notes appear in the server vault and sends edits back to the private GitHub
repository.

Seal the PAT as a Railway variable after setting it. Do not copy it into this
repo or a shell command.

## Security and operating notes

- The vault repository must remain private.
- The app service is private; only `obsidian-auth` receives a public domain.
- The OAuth callback is HTTPS and only the selected GitHub account is allowed.
- The OAuth client secret, cookie secret, and GitHub PAT must never be put in
  source files, Docker build arguments, Git URLs, Obsidian notes, logs, or chat.
- `/config` is persistent. Back it up through the private Git repository; the
  repository does not include runtime-only Obsidian settings unless committed.
- Git edits from Obsidian and bot API writes can race. The bot uses GitHub
  Contents API conflict handling; the plugin should pull before pushing. Resolve
  any non-fast-forward conflict in Obsidian before restarting the service.
