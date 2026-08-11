# Research Index bootstrap registry

This directory is the canonical bootstrap registry for the future `theobserverofmultiverses.info` research layer. It aggregates the five distributed `metadata/website_metadata.yaml` contracts without rewriting historical citation records, DOI objects, tagged releases, manuscripts, or checksums.

## Authority order

1. Frozen/tagged research artifacts and immutable archival records remain authoritative for historical publication objects.
2. Each repository's `metadata/website_metadata.yaml` is authoritative for the normalized website adapter.
3. `research_index.json` is the cross-repository index used to build `/research/`.
4. WordPress is a presentation/editorial layer and must not silently override version, DOI scope, review status, license scope, claim boundaries, or source provenance.

## Bootstrap host

The current host is `Observer1117/geometry-of-observation` only because the connected GitHub integration cannot create a new repository. This does not make Geometry of Observation the scientific parent of the other outputs. When a dedicated website repository exists, move this registry with work IDs, canonical paths, and semantic meanings unchanged.

## Semantic model

The mixed Research Index is a Schema.org `CollectionPage` whose `mainEntity` is an ordered `ItemList`. Papers use `ScholarlyArticle`; the Geometry of Observation corpus uses `Dataset` as its primary corpus entity; substantive reproducibility code may receive a `SoftwareSourceCode` entity. `DataCatalog` is intentionally not the primary type for `/research/`, because the page is a mixed collection rather than a catalog solely of datasets.

## WordPress model

Use one public custom post type, `research_output`, archived at `/research/` and exposed at REST base `research`. Scientific fields are registered post meta. The post type must support `custom-fields` and use `show_in_rest`. The native WordPress post-author account is a CMS account, not the scholarly-author authority; JSON-LD `author` resolves to the global `Person` entity for Stassis Stashkevichyus.

## Files

- `research_index.json` — ordered cross-repository index.
- `wordpress_data_model.json` — custom-post-type and machine-meta contract.
- `jsonld_mapping.json` — mapping to Schema.org entities.
- `research_index.jsonld` — concrete JSON-LD graph for `/research/`.
- `../scripts/validate_registry.py` — zero-dependency validator.

## Vocabulary references

- https://schema.org/Person
- https://schema.org/ScholarlyArticle
- https://schema.org/Dataset
- https://schema.org/SoftwareSourceCode
- https://schema.org/ItemList
- https://schema.org/CollectionPage
- https://developer.wordpress.org/reference/functions/register_post_type/
- https://developer.wordpress.org/reference/functions/register_post_meta/
