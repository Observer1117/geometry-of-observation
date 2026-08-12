<?php

declare(strict_types=1);

$GLOBALS['observer_test_actions'] = array();
$GLOBALS['observer_test_filters'] = array();
$GLOBALS['observer_test_post_type'] = null;
$GLOBALS['observer_test_meta'] = array();
$GLOBALS['observer_test_meta_by_mid'] = array();
$GLOBALS['observer_test_activation'] = null;
$GLOBALS['observer_test_deactivation'] = null;

define( 'ABSPATH', __DIR__ . '/' );

function plugin_dir_path(string $file): string {
	return dirname( $file ) . '/';
}

function plugin_dir_url(string $file): string {
	return 'https://example.test/wp-content/plugins/' . basename( dirname( $file ) ) . '/';
}

function register_activation_hook(string $file, $callback): void {
	$GLOBALS['observer_test_activation'] = $callback;
}

function register_deactivation_hook(string $file, $callback): void {
	$GLOBALS['observer_test_deactivation'] = $callback;
}

function add_action(string $hook, $callback, int $priority = 10, int $accepted_args = 1): void {
	$GLOBALS['observer_test_actions'][] = array( $hook, $callback, $priority, $accepted_args );
}

function add_filter(string $hook, $callback, int $priority = 10, int $accepted_args = 1): void {
	$GLOBALS['observer_test_filters'][] = array( $hook, $callback, $priority, $accepted_args );
}

function __(string $text, string $domain = 'default'): string {
	return $text;
}

function register_post_type(string $key, array $args): void {
	$GLOBALS['observer_test_post_type'] = array( $key, $args );
}

function register_post_meta(string $post_type, string $key, array $args): void {
	$GLOBALS['observer_test_meta'][ $key ] = array( 'post_type' => $post_type, 'args' => $args );
}

function get_metadata_by_mid(string $meta_type, int $meta_id) {
	if ( 'post' !== $meta_type || ! isset( $GLOBALS['observer_test_meta_by_mid'][ $meta_id ] ) ) {
		return false;
	}

	return (object) array(
		'meta_id'    => $meta_id,
		'post_id'    => 101,
		'meta_key'   => $GLOBALS['observer_test_meta_by_mid'][ $meta_id ],
		'meta_value' => 'test-value',
	);
}

require dirname( __DIR__ ) . '/observer-research-registry.php';

use ObserverResearchRegistry\Badges;
use ObserverResearchRegistry\JsonLd;
use ObserverResearchRegistry\Links;
use ObserverResearchRegistry\MetaSchema;
use ObserverResearchRegistry\Plugin;
use ObserverResearchRegistry\PostType;
use ObserverResearchRegistry\Registry;

$tests = 0;

function observer_assert($condition, string $message): void {
	global $tests;
	++$tests;
	if ( ! $condition ) {
		file_put_contents( 'php://stderr', "FAIL: {$message}\n" );
		exit( 1 );
	}
}

$plugin_root = dirname( __DIR__ );
$canonical_root = dirname( dirname( $plugin_root ) ) . '/registry';

observer_assert(
	file_get_contents( $canonical_root . '/research_index.json' ) === file_get_contents( $plugin_root . '/data/research_index.json' ),
	'bundled research index must be byte-identical to the canonical registry'
);
observer_assert(
	file_get_contents( $canonical_root . '/wordpress_data_model.json' ) === file_get_contents( $plugin_root . '/data/wordpress_data_model.json' ),
	'bundled WordPress data model must be byte-identical to the canonical model'
);

$index = Registry::index();
$model = Registry::model();
$works = Registry::ordered_works( $index );
observer_assert( 5 === count( $works ), 'registry must contain five works' );
observer_assert( array( 1, 2, 3, 4, 5 ) === array_column( $works, 'priority' ), 'registry order must be 1 through 5' );
observer_assert( 22 === count( Registry::machine_meta_keys( $model ) ), 'machine-meta contract must contain 22 exact fields' );
observer_assert( count( Registry::machine_meta_keys( $model ) ) === count( Registry::meta_for_work( $works[0] ) ), 'work projection must cover every machine-meta key' );

$ids = array_column( $works, 'id' );
observer_assert( 5 === count( array_unique( $ids ) ), 'work IDs must be unique' );
observer_assert( 'GOO-1.3.0' === $ids[0] && 'QMD-2.0-rc2' === $ids[4], 'registry boundary order must remain fixed' );

$qmd = Registry::work_by_id( 'QMD-2.0-rc2', $index );
$article_one = Registry::work_by_id( 'WGCG-1.0.0', $index );
$article_two = Registry::work_by_id( 'WGCX-1.0.0', $index );
$crse = Registry::work_by_id( 'CRSE-0.2', $index );
$goo = Registry::work_by_id( 'GOO-1.3.0', $index );

$badge_codes = static function (array $work): array {
	return array_column( Badges::for_work( $work ), 'code' );
};

foreach ( $works as $work ) {
	observer_assert( in_array( 'not-peer-reviewed', $badge_codes( $work ), true ), $work['id'] . ' must disclose absence of peer review' );
}
observer_assert( in_array( 'release-candidate', $badge_codes( $qmd ), true ), 'QMD must be marked release candidate' );
observer_assert( in_array( 'g2-open', $badge_codes( $qmd ), true ) && in_array( 'g6-open', $badge_codes( $qmd ), true ), 'QMD must expose open G2/G6 gates' );
observer_assert( ! in_array( 'doi', $badge_codes( $qmd ), true ), 'QMD must not receive a DOI badge' );
observer_assert( in_array( 'negative-result', $badge_codes( $article_two ), true ), 'Article II must disclose the negative benchmark' );
observer_assert( ! in_array( 'negative-result', $badge_codes( $article_one ), true ), 'Article I must not inherit Article II negative-result status' );

observer_assert( array( 'WGCX-1.0.0' ) === $article_one['companion_work_ids'], 'Article I companion must be Article II' );
observer_assert( array( 'WGCG-1.0.0' ) === $article_two['companion_work_ids'], 'Article II companion must be Article I' );

$claim_url = Registry::source_file_url( $goo, $goo['claim_boundary_path'] );
observer_assert( false !== strpos( $claim_url, $goo['source_contract']['merge_commit'] ), 'claim link must pin the exact source commit' );
observer_assert( false !== strpos( $claim_url, '/KNOWN_LIMITATIONS.md' ), 'claim link must point to the declared boundary file' );
observer_assert( 5 <= count( Links::resources( $goo ) ), 'GOO resources must expose repository, DOI, OSF, release, and evidence' );

$graph = JsonLd::archive( $index, 'https://example.test/', $ids );
$types = array_column( $graph['@graph'], '@type' );
observer_assert( in_array( 'Person', $types, true ) && in_array( 'WebSite', $types, true ), 'JSON-LD must contain global Person and WebSite nodes' );
observer_assert( in_array( 'CollectionPage', $types, true ) && in_array( 'ItemList', $types, true ), 'archive JSON-LD must contain CollectionPage and ItemList' );
$item_list = null;
foreach ( $graph['@graph'] as $node ) {
	if ( 'ItemList' === ( $node['@type'] ?? null ) ) {
		$item_list = $node;
	}
}
observer_assert( 5 === $item_list['numberOfItems'], 'ItemList must contain all five visible works' );
observer_assert( array( 1, 2, 3, 4, 5 ) === array_column( $item_list['itemListElement'], 'position' ), 'ItemList positions must be contiguous' );

$work_nodes = array();
foreach ( $graph['@graph'] as $node ) {
	if ( isset( $node['@id'] ) && substr( $node['@id'], -5 ) === '#work' ) {
		$work_nodes[ $node['@id'] ] = $node;
	}
}
$qmd_node = $work_nodes['https://example.test/research/quantitative-modularity-defects/#work'];
$crse_node = $work_nodes['https://example.test/research/compact-resolvent-spectral-encodings/#work'];
$goo_node = $work_nodes['https://example.test/research/geometry-of-observation/#work'];
observer_assert( ! isset( $qmd_node['identifier'] ), 'QMD JSON-LD must not contain a DOI identifier' );
observer_assert( '0.2' === $crse_node['version'], 'CRSE JSON-LD must use citation version 0.2, not metadata revision 0.2.1' );
observer_assert( isset( $goo_node['creator'] ) && ! isset( $goo_node['author'] ), 'GOO Dataset must use creator semantics' );
observer_assert( 3 === count( array_filter( $types, static function ($type): bool { return 'SoftwareSourceCode' === $type; } ) ), 'three works must expose evidence-backed software entities without guessed languages' );

$malicious = $qmd;
$malicious['title'] = '</script><script>alert(1)</script>';
$malicious_graph = JsonLd::single( $malicious, $index, 'https://example.test/' );
$encoded = json_encode( $malicious_graph, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
observer_assert( false === strpos( $encoded, '</script>' ), 'JSON-LD encoding must neutralize script termination' );

PostType::register();
observer_assert( 'research_output' === $GLOBALS['observer_test_post_type'][0], 'CPT key must be research_output' );
$cpt = $GLOBALS['observer_test_post_type'][1];
observer_assert( true === $cpt['show_in_rest'] && 'research' === $cpt['rest_base'], 'CPT must expose the research REST base' );
observer_assert( 'research' === $cpt['has_archive'] && 'research' === $cpt['rewrite']['slug'], 'CPT archive must own /research/' );
observer_assert( in_array( 'custom-fields', $cpt['supports'], true ), 'CPT must retain custom-fields support required by the REST contract' );
observer_assert( 'do_not_allow' === $cpt['capabilities']['create_posts'], 'manual creation outside registry synchronization must be disabled' );

MetaSchema::register();
observer_assert( 22 === count( $GLOBALS['observer_test_meta'] ), 'all and only 22 machine-meta fields must be registered' );
observer_assert( false === MetaSchema::deny_external_write(), 'ordinary callers must not be allowed to write machine metadata' );
$license_schema = $GLOBALS['observer_test_meta']['observer_license_scope']['args']['show_in_rest']['schema'];
$companion_schema = $GLOBALS['observer_test_meta']['observer_companion_work_ids']['args']['show_in_rest']['schema'];
observer_assert( 'array' === $license_schema['type'] && 'object' === $license_schema['items']['type'], 'license scope REST schema must be an array of objects' );
observer_assert( array( 'scope', 'license' ) === array_keys( $license_schema['items']['properties'] ), 'license objects must expose exactly scope and license' );
observer_assert( 'array' === $companion_schema['type'] && 'string' === $companion_schema['items']['type'], 'companion REST schema must be an array of strings' );

$GLOBALS['observer_test_meta_by_mid'] = array(
	41 => 'observer_work_id',
	42 => '_observer_registry_record',
	43 => 'unrelated_key',
);
observer_assert( false === MetaSchema::block_update_by_mid( null, 41, 'tampered', false ), 'update-by-mid must block writes to public registry metadata' );
observer_assert( false === MetaSchema::block_update_by_mid( null, 42, 'tampered', false ), 'update-by-mid must block writes to protected registry metadata' );
observer_assert( false === MetaSchema::block_update_by_mid( null, 43, 'tampered', 'observer_work_id' ), 'update-by-mid must block renaming an unrelated row to a registry key' );
observer_assert( false === MetaSchema::block_update_by_mid( null, 41, 'tampered', 'unrelated_key' ), 'update-by-mid must block renaming a registry row away from its protected key' );
observer_assert( null === MetaSchema::block_update_by_mid( null, 43, 'allowed', false ), 'update-by-mid must leave unrelated metadata to WordPress' );
observer_assert( null === MetaSchema::block_update_by_mid( null, 999, 'missing', false ), 'update-by-mid must leave missing rows to WordPress' );
observer_assert( false === MetaSchema::block_delete_by_mid( null, 41 ), 'delete-by-mid must block public registry metadata deletion' );
observer_assert( false === MetaSchema::block_delete_by_mid( null, 42 ), 'delete-by-mid must block protected registry metadata deletion' );
observer_assert( null === MetaSchema::block_delete_by_mid( null, 43 ), 'delete-by-mid must leave unrelated metadata to WordPress' );
$internal_mid_result = MetaSchema::with_internal_import_write(
	static function () {
		return array(
			MetaSchema::block_update_by_mid( null, 41, 'authoritative', false ),
			MetaSchema::block_delete_by_mid( null, 42 ),
		);
	}
);
observer_assert( array( null, null ) === $internal_mid_result, 'authoritative importer writes must bypass by-mid guards only inside the internal scope' );

$action_hooks = array_column( $GLOBALS['observer_test_actions'], 0 );
$filter_hooks = array_column( $GLOBALS['observer_test_filters'], 0 );
observer_assert( in_array( 'init', $action_hooks, true ) && in_array( 'rest_api_init', $action_hooks, true ), 'plugin must wire CPT/meta and read-only REST fields' );
observer_assert( in_array( 'admin_post_observer_registry_sync', $action_hooks, true ), 'synchronization must be an explicit authenticated admin POST action' );
observer_assert( in_array( 'rest_pre_insert_research_output', $filter_hooks, true ), 'REST machine-meta writes must be rejected explicitly' );
observer_assert( in_array( 'update_post_metadata_by_mid', $filter_hooks, true ), 'metadata updates by meta ID must be guarded explicitly' );
observer_assert( in_array( 'delete_post_metadata_by_mid', $filter_hooks, true ), 'metadata deletions by meta ID must be guarded explicitly' );
$filter_contracts = array();
foreach ( $GLOBALS['observer_test_filters'] as $hook ) {
	$filter_contracts[ $hook[0] ] = $hook[3];
}
observer_assert( 4 === $filter_contracts['update_post_metadata_by_mid'], 'update-by-mid guard must accept the four-argument WordPress filter signature' );
observer_assert( 2 === $filter_contracts['delete_post_metadata_by_mid'], 'delete-by-mid guard must accept the two-argument WordPress filter signature' );
observer_assert( is_array( $GLOBALS['observer_test_activation'] ) && Plugin::class === $GLOBALS['observer_test_activation'][0], 'activation callback must be registered' );
observer_assert( is_array( $GLOBALS['observer_test_deactivation'] ) && Plugin::class === $GLOBALS['observer_test_deactivation'][0], 'deactivation callback must be registered' );

foreach ( $GLOBALS['observer_test_actions'] as $hook ) {
	$callback = $hook[1];
	observer_assert( ! ( 'init' === $hook[0] && is_array( $callback ) && 'sync' === $callback[1] ), 'import must never run on init' );
}

echo "Observer Research Registry contract verified ({$tests} assertions).\n";
