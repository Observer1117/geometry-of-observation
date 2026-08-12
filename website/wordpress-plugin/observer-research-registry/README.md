# Observer Research Registry — P1.6

This WordPress plugin is the executable research-registry core for the future `theobserverofmultiverses.info` site.

## Authority boundary

```text
pinned GitHub registry
        ↓
validated, journaled synchronization
        ↓
research_output machine layer + WordPress editorial layer
        ↓
/research/, work pages, badges, evidence links, read-only REST, JSON-LD
```

GitHub determines scientific identity, versions, DOI scope, release and review status, license scope, claim boundaries, source provenance, and companion relations. WordPress determines public explanation, excerpt, media, layout, post author, and visibility. `post_status=publish` is only a CMS visibility state.

## Safety properties

- no network fetches or webhook imports;
- bundled JSON pinned to source commit `bab4480e50f8abe32087da765a145575a4519f8a` and checked by SHA-256;
- full registry and collision preflight before writes;
- connection-owned MySQL/MariaDB advisory lock with fenced compare-and-swap journal/state transitions;
- durable create intents, row markers, snapshots, conservative rollback, and explicit recovery;
- identity by `observer_work_id`, never title or slug;
- canonical-slug collision abort instead of silent `-2` renaming;
- new records are drafts;
- repeat synchronization of unchanged input produces no post mutations or revisions;
- scientific meta is protected and REST read-only;
- disappearing registry works are reported as orphans and never deleted;
- uninstall preserves research records.

On non-MySQL development backends the plugin uses an add-only option mutex for clean-run compatibility and deliberately refuses automatic stale-lock takeover after a crashed request. That fallback fails closed and requires operator review; production recovery guarantees assume the standard WordPress MySQL/MariaDB backend.

## Installed behavior

The plugin registers public CPT `research_output`, archive `/research/`, and REST base `/wp-json/wp/v2/research`. Theme overrides are supported at:

- `observer-research-registry/archive-research_output.php`
- `observer-research-registry/single-research_output.php`

Runtime presentation is derived from the bundled registry. Fields deliberately omitted from the P1.5 machine-meta contract—priority, short title, result class, gates, site path, and badges—are not invented as writable WordPress metadata.

## Synchronization

In wp-admin use **Tools → Research Registry**, or use WP-CLI:

```bash
wp observer registry validate
wp observer registry status
wp observer registry sync
wp observer registry recover
```

Activation only registers the model, grants `manage_observer_registry` to administrators, and flushes rewrite rules. It does not import records automatically.

## Validation

From the repository root:

```bash
python3 website/scripts/validate_registry.py
python3 website/scripts/validate_wordpress_plugin.py
find website/wordpress-plugin/observer-research-registry -type f -name '*.php' -print0 | xargs -0 -n1 php -l
php website/wordpress-plugin/observer-research-registry/tests/run.php
```

The mandatory gate is dependency-free. A clean WordPress Playground smoke run has also verified activation, a five-draft first sync, an unchanged second sync, and blocked direct/REST machine-meta writes. A target-hosting integration matrix remains deferred until the WordPress tier, staging instance, theme, cache, and SEO plugins are selected.

## WordPress API references

- <https://developer.wordpress.org/reference/functions/register_post_type/>
- <https://developer.wordpress.org/reference/functions/register_meta/>
- <https://developer.wordpress.org/reference/functions/register_rest_field/>
- <https://developer.wordpress.org/rest-api/extending-the-rest-api/modifying-responses/>

## License

Plugin code is GPL-2.0-or-later. Registry entries retain the per-object license scopes recorded in `data/research_index.json`.
