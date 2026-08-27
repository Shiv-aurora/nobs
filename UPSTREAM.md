# Upstream foundation

NoPing uses Mattermost Team Edition as its collaboration kernel and follows the official Mattermost Plugin Starter Template structure.

- Repository: `mattermost/mattermost-plugin-starter-template`
- Pinned commit: `3296cf6fad808c2372c254cf7b64bcc8a2144e67`
- Commit date: 2026-08-13
- License: Apache-2.0
- Mattermost core is deployed as an official container image and is not vendored into this repository.

The plugin scaffold in `plugin/` preserves the official manifest, Go server, React webapp, and packaging boundaries, then replaces the template behavior with NoPing's original product and agent architecture. See `docs/OSS_DISCLOSURE.md` and `docs/CONTRIBUTION_MAP.md`.
