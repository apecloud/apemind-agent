# ApeMind Agent fork change list

> Status: tracking document. Keep the pull request for this file open as the
> living record for ApeMind Agent fork changes. Do not merge it into `main`
> unless the team explicitly decides to turn this record into repository docs.

This file records the changes we have made on top of upstream Goose for the
ApeMind Agent proof of concept. The goal is to keep the fork easy to rebase
against upstream: prefer UI hiding, copy replacement, configuration defaults,
and packaging changes over deleting upstream code paths or changing core logic.

## Upstream-friendly rule

- Prefer hiding features in the Desktop UI instead of removing backend,
  protocol, or runtime code.
- Preserve upstream internal names when they are part of compatibility:
  `goose://`, `.goosehints`, recipe file format, and Goose Rust crate names stay
  as-is unless there is a separate migration plan.
- Keep branding and distribution changes isolated in Desktop assets, i18n,
  release workflows, install scripts, and repo metadata.
- Treat functional/core runtime changes as exceptions that need explicit
  review because they raise future upstream merge cost.

## Current merged changes

| Area | User-visible behavior | Main code locations | Source |
| --- | --- | --- | --- |
| Chinese GitHub templates | Issue and pull request templates are Chinese-first for this fork. | `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/pull_request_template.md` | PR #2 |
| Release dry-run safety | Early release dry runs skip desktop signing jobs that need unavailable signing secrets. | `.github/workflows/release.yml` | PR #4 |
| Docker and CLI download repo | Docker images and CLI download scripts point at the ApeCloud fork instead of upstream Goose. | `.github/workflows/publish-docker.yml`, `download_cli.sh`, `download_cli.ps1` | PR #6 |
| Desktop branding | Product is branded as ApeMind Agent in desktop copy, icons, menus, onboarding, prompts, and visible metadata. | `ui/desktop/package.json`, `ui/desktop/forge.config.ts`, `ui/desktop/src/images/*`, `ui/desktop/src/i18n/messages/*.json`, `ui/desktop/src/main.ts`, `ui/desktop/src/components/*`, `crates/goose/src/prompts/*` | PR #7 |
| Linux package lookup | Linux desktop package generation keeps the executable lookup stable after branding changed the product name. | `ui/desktop/forge.config.ts` | PR #8 |
| Repository rename | Links and updater metadata point at `apecloud/apemind-agent`. | `download_cli.sh`, `download_cli.ps1`, `Dockerfile`, `ui/desktop/forge.config.ts`, `ui/desktop/src/utils/githubUpdater.ts`, `ui/desktop/src/components/settings/app/AppSettingsSection.tsx`, `ui/desktop/src/components/ui/Diagnostics.tsx` | PR #9 |
| Unsigned desktop PoC builds | macOS and Windows desktop packages are built for quick PoC testing without code-signing secrets. | `.github/workflows/release.yml` | PR #10 |
| Branded artifact paths | Release workflows can find and upload Desktop artifacts under `ApeMind Agent` bundle paths. | `.github/workflows/bundle-desktop.yml`, `.github/workflows/bundle-desktop-intel.yml`, `.github/workflows/bundle-desktop-windows.yml`, `.github/workflows/release.yml`, `.github/workflows/release-branches.yml`, `.github/workflows/pr-comment-bundle*.yml` | PR #11 |
| Upstream links and watermark | Desktop no longer sends users from the main chat and extensions pages to Goose docs through prominent links; chat watermark shows ApeMind Agent. | `ui/desktop/src/components/BaseChat.tsx`, `ui/desktop/src/components/extensions/ExtensionsView.tsx`, `ui/desktop/src/components/settings/extensions/ExtensionsSection.tsx` | PR #12 |
| Apps hidden, recipes renamed | Apps are hidden from navigation while underlying MCP app/resource code remains. User-facing "Recipe/配方" copy is now "Workflow/工作流"; the underlying `recipe` protocol and file format remain unchanged. Local Inference and Mesh settings tabs are also hidden from the settings UI and deep links fall back to Models. | `ui/desktop/src/hooks/useNavigationItems.ts`, `ui/desktop/src/components/Layout/NavigationContext.tsx`, `ui/desktop/src/components/settings/app/NavigationCustomizationSettings.tsx`, `ui/desktop/src/App.tsx`, `ui/desktop/src/components/recipes/*`, `ui/desktop/src/components/settings/SettingsView.tsx`, `ui/desktop/src/i18n/messages/*.json`, `ui/desktop/src/recipe/*` | PR #13 |
| Sessions, project hints, and prompt injection controls hidden | The Settings UI hides the Sessions tab, Project Hints (`.goosehints`), and Prompt Injection Detection controls. Underlying session sharing, gateway, project-hints, and security-toggle code remains for upstream compatibility. `.goosehints` help text now says it improves communication with ApeMind. | `ui/desktop/src/components/settings/SettingsView.tsx`, `ui/desktop/src/components/settings/chat/ChatSettingsSection.tsx`, `ui/desktop/src/components/settings/chat/GoosehintsModal.tsx`, `ui/desktop/src/components/settings/chat/GoosehintsSection.tsx`, `ui/desktop/src/i18n/messages/*.json` | PR #14 |

## Build and release validation

- Tag `v1.35.0-apecloud.5` completed the first end-to-end PoC release dry run.
- GitHub Release produced 29 assets, including macOS, Windows, Linux desktop
  packages and CLI binaries.
- Docker image published successfully:
  `ghcr.io/apecloud/apemind-agent:v1.35.0-apecloud.5`.
- macOS arm64 Desktop package was downloaded and launched locally; `goosed`
  started inside the packaged app.
- Windows standard/CUDA Desktop packages built successfully in GitHub Actions.
- PR #14 was also packaged locally on the 3F Mac after merge and the packaged
  app was opened successfully for UI smoke testing.

## In progress / pending record items

- Remaining Goose/upstream outbound links still need product decisions:
  provider quickstart docs, diagnostics troubleshooting, GitHub issue/feature
  links, recipe help, `.goosehints` help, and the iOS App Store link.
- Windows artifact names still include `Goose-win32-*`; the app itself is
  branded, but the artifact names should be fixed in a later packaging PR.
- CLI binary name is still `goose`; a future `apemind` command or compatibility
  symlink needs a separate decision.
- Code signing, NPM publishing, Homebrew tap, and formal external distribution
  are deferred until after PoC validation.

## Reference issues

- Issue #1: ApeCloud local Agent Goose fork PoC.
- Issue #3: Fork CI/CD dry-run plan.
- Issue #5: ApeCloud-branded distribution change list.
