# avegancafe

Kyle's personal Claude Code plugin — a home for one-off skills that don't
warrant a plugin of their own.

It lives in its own repo, [`avegancafe/claude-plugin-avegancafe`](https://github.com/avegancafe/claude-plugin-avegancafe),
and is listed in [`avegancafe-marketplace`](https://github.com/avegancafe/avegancafe-marketplace)
(it was vendored there under `plugins/avegancafe/` until 3.7.0; its history came with it).

## Install

```bash
/plugin marketplace add avegancafe/avegancafe-marketplace
/plugin install avegancafe@avegancafe-marketplace
```

## Skills

| Skill | Purpose |
|-------|---------|
| `work-notes-vault` | Kyle's private Obsidian work vault, [`avegancafe/notes--work`](https://github.com/avegancafe/notes--work) (expected at `~/workspace/notes--work/`): locating/refreshing it, its layout, and its weekly-synced **Granola meeting archive** (`granola/notes/`, `.md` + raw `.json`) — schema, `rg`/`jq` mining recipes, freshness limits, and what not to touch. Lets Claude "mine my Granola meetings for X" from any working directory; the vault's own `.claude/CLAUDE.md` stays the authority on its conventions. No meeting content lives here — only the archive's structure. |
| `hifi-h2` | Tags store-bought FLACs from MusicBrainz (full tags, 500×500 baseline cover, `NN - Title` names), audits the Rockbox HIFI H2 library for tracks that would land under `<Untagged>` (missing album artist, ID3v1-only, truncated titles), and covers mounting, copying and the Rockbox database rebuild. |
| `phone-push` | Sends a push notification to Kyle's phone, now or at a scheduled time, through a one-time or recurring cloud routine (`RemoteTrigger`) that calls `PushNotification`; can check Gmail/HEY first and push a one-line result. Covers the create body, UTC timing, connectors, prompt templates and run debugging. |
| `flipper-usb` | Drives Kyle's Flipper Zero over USB: a hard-timeout CLI helper (`flipper_cli.py`: commands, SD text files, button presses, live logs), ufbt builds matched to the firmware API, finding `MissingImports`, the one-process-per-serial-port rules, and a probe-app recipe for GPIO boards (with ESP32 Marauder v1.17 findings). |
`side-quest` moved to a work plugin outside the marketplace in 2.0.0 (skill + `Stop` hook).
The `session-title` mod (`/session-title`, `/autoname`) moved to its own public plugin,
[`session-management`](https://github.com/avegancafe/session-management), in 3.0.0.

## Releasing

Bump `version` in [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) and merge to `main`.
[`release.yml`](.github/workflows/release.yml) then sends a `plugin-released` event to
`avegancafe-marketplace`, whose sync workflow updates this plugin's entry there.

It needs the `MARKETPLACE_DISPATCH_TOKEN` repo secret: a fine-grained PAT scoped to
`avegancafe/avegancafe-marketplace` only, with Contents read & write.

```bash
gh secret set MARKETPLACE_DISPATCH_TOKEN -R avegancafe/claude-plugin-avegancafe
```

Without it the release run fails and the marketplace entry stops tracking new versions.
