=== Observer Research Registry ===
Contributors: observer1117
Tags: research, preprint, metadata, schema, reproducibility
Requires at least: 6.4
Requires PHP: 7.4
Stable tag: 0.1.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Registry-driven research pages with read-only scientific metadata, explicit review badges, pinned evidence links, companion works, and JSON-LD.

== Description ==

Observer Research Registry is the executable P1.6 core for the future research layer of theobserverofmultiverses.info.

GitHub registry contracts remain authoritative. WordPress owns only presentation: explanatory content, excerpts, media, layout, and visibility. A WordPress `publish` status never means peer review.

The plugin performs no remote requests. Its bundled registry is pinned by a manifest and SHA-256 hashes. Synchronization is explicit, capability-protected, nonce-protected in wp-admin, single-writer locked, journaled, and idempotent.

== Installation ==

1. Upload and activate the plugin.
2. Open Tools > Research Registry.
3. Review the preflight plan.
4. Synchronize the pinned registry.
5. Edit the five generated drafts and publish them individually when their public presentation is ready.

WP-CLI commands:

`wp observer registry validate`
`wp observer registry status`
`wp observer registry sync`
`wp observer registry recover`

== Data ownership ==

Synchronization may create a draft or update the canonical slug and read-only machine layer. It does not overwrite post content, excerpt, thumbnail, author, status, layout, or media.

Deactivation and uninstall preserve all research posts and metadata. Uninstall removes only operational options and the dedicated administrator capability.

== Changelog ==

= 0.1.0 =
* Initial P1.6 executable registry core.

