# Laptop-independent development

Requested repository: https://github.com/shreyans-chowdry/mud . Target real-data network: Base.

A GitHub login or repository push does not move this local chat into cloud execution. GitHub Actions can run the supplied verification jobs on remote runners while the laptop is off. Continued AI coding requires a started Codex Cloud task in a published environment, or another explicitly connected remote executor. A local heartbeat cannot do that.

The current official UI procedure is:
1. In Codex on the web or desktop, choose **Work in > Cloud**.
2. Open **Select environment > Create environment** and connect GitHub if prompted.
3. Select shreyans-chowdry/mud, configure Node 22 and Python 3.11+, and use `bash infrastructure/scripts/cloud-setup.sh` as the dependency/setup command.
4. Allow the package registry hosts needed by npm and Python. Provide test services only when running integration tests; do not give the coding environment production signing keys or customer databases.
5. Test and publish the environment, then start the cloud task with the continuation prompt below. Confirm that the task's environment is Cloud before closing the laptop.

Cloud coding is separate from always-on application hosting. A completed cloud coding task is not a publicly deployed website, and neither guarantees revenue. Account capacity limits still apply.

## Continuation prompt

Continue the MUD Base protocol in this repository. Read docs/CONTINUATION.md, docs/VERIFICATION.md, docs/LIVE_SETUP.md and docs/API_KEYS.md first. Preserve user edits. Public builds must use genuine verified chain state or show unavailable, never fall back to test fixtures. Keep samples under tests/fixtures and require explicit local opt-in. Fix meaningful failures found by tests or review, run appropriate checks, and provide reviewable commits/PRs. Do not deploy to mainnet, broadcast financial transactions, access production signing keys, fabricate prices, create fake products or promise profits. Record exact checks, remaining release blockers and deployment requirements. Keep server credentials out of browser variables, logs and commits.

Official reference: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments), checked October 22, 2026. The guide describes cloud tasks that continue while the computer is asleep; this file is setup/handoff material, not evidence that a cloud task has started.
