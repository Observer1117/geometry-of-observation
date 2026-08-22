<?php

declare(strict_types=1);

/**
 * P1.7 target-environment probe.
 *
 * Run only from an authenticated shell with:
 *
 *     wp eval-file website/staging/p1-7-environment-probe.php
 *
 * The JSON document is deliberately limited to the P1.7 environment allowlist.
 * It never emits option dumps, database connection details, users, filesystem
 * paths, salts, tokens, or the ephemeral advisory-lock name/connection ID.
 */

function observer_p17_emit(array $document, int $exit_code): void {
	$flags = JSON_PRETTY_PRINT
		| JSON_UNESCAPED_SLASHES
		| JSON_UNESCAPED_UNICODE
		| JSON_HEX_TAG
		| JSON_HEX_AMP
		| JSON_HEX_APOS
		| JSON_HEX_QUOT;
	$encoded = wp_json_encode( $document, $flags );

	if ( ! is_string( $encoded ) ) {
		$encoded = '{"schema_version":"observer-p1.7-environment-probe/v1","status":"fail","error_codes":["json_encoding_failed"]}';
		$exit_code = 1;
	}

	echo $encoded . "\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON is encoded with the JSON_HEX flags above.
	exit( $exit_code );
}

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	observer_p17_emit(
		array(
			'schema_version' => 'observer-p1.7-environment-probe/v1',
			'status'         => 'fail',
			'error_codes'    => array( 'wp_cli_required' ),
		),
		1
	);
}

/**
 * Keep version-like values bounded and free of paths or arbitrary metadata.
 */
function observer_p17_safe_version($value): ?string {
	if ( ! is_scalar( $value ) ) {
		return null;
	}

	$value = trim( (string) $value );
	if ( '' === $value ) {
		return null;
	}

	if ( ! preg_match( '/^[0-9A-Za-z][0-9A-Za-z._+~-]{0,63}$/', $value ) ) {
		return null;
	}

	return $value;
}

/**
 * Return a relative, display-safe component identifier, never a local path.
 */
function observer_p17_safe_component_id($value): string {
	$value = str_replace( '\\', '/', trim( (string) $value ) );
	$is_absolute = '' === $value
		|| '/' === substr( $value, 0, 1 )
		|| 1 === preg_match( '/^[A-Za-z]:\//', $value )
		|| false !== strpos( $value, '../' )
		|| '..' === $value;

	if ( $is_absolute || ! preg_match( '/^[0-9A-Za-z._\/-]{1,191}$/', $value ) ) {
		return 'redacted-' . substr( hash( 'sha256', $value ), 0, 12 );
	}

	return $value;
}

/**
 * Allow only HTTP(S) scheme, host, optional port, and path from site/home URLs.
 * User information, query strings, and fragments are intentionally discarded.
 */
function observer_p17_public_url($value): ?string {
	$parts = wp_parse_url( trim( (string) $value ) );
	if ( ! is_array( $parts ) ) {
		return null;
	}

	$scheme = strtolower( (string) ( $parts['scheme'] ?? '' ) );
	$host = strtolower( (string) ( $parts['host'] ?? '' ) );
	if ( ! in_array( $scheme, array( 'http', 'https' ), true ) || '' === $host ) {
		return null;
	}

	if ( 1 !== preg_match( '/^[0-9a-z.\-:\[\]]{1,253}$/', $host ) ) {
		return null;
	}

	$url = $scheme . '://' . $host;
	if ( isset( $parts['port'] ) ) {
		$port = (int) $parts['port'];
		if ( $port < 1 || $port > 65535 ) {
			return null;
		}
		$url .= ':' . (string) $port;
	}

	$path = (string) ( $parts['path'] ?? '' );
	if ( false !== strpos( $path, '\\' ) || false !== strpos( $path, "\0" ) ) {
		return null;
	}

	return $url . $path;
}

/**
 * Reduce raw SERVER_SOFTWARE to an allowlisted product family and version.
 */
function observer_p17_server_signature($raw): array {
	$raw = is_scalar( $raw ) ? (string) $raw : '';
	$families = array(
		'nginx'         => '/\bnginx(?:\/([0-9][0-9A-Za-z._+-]{0,31}))?/i',
		'apache'        => '/\bApache(?:\/([0-9][0-9A-Za-z._+-]{0,31}))?/i',
		'litespeed'     => '/\bLiteSpeed(?:\/([0-9][0-9A-Za-z._+-]{0,31}))?/i',
		'openlitespeed' => '/\bOpenLiteSpeed(?:\/([0-9][0-9A-Za-z._+-]{0,31}))?/i',
		'iis'           => '/\bMicrosoft-IIS(?:\/([0-9][0-9A-Za-z._+-]{0,31}))?/i',
		'caddy'         => '/\bCaddy(?:\/([0-9][0-9A-Za-z._+-]{0,31}))?/i',
	);

	foreach ( $families as $family => $pattern ) {
		if ( 1 === preg_match( $pattern, $raw, $match ) ) {
			return array(
				'family'  => $family,
				'version' => observer_p17_safe_version( $match[1] ?? null ),
			);
		}
	}

	return array(
		'family'  => 'unknown',
		'version' => null,
	);
}

function observer_p17_sort_components(array &$components): void {
	usort(
		$components,
		static function (array $left, array $right): int {
			return strcmp( (string) $left['id'], (string) $right['id'] );
		}
	);
}

/**
 * Inventory all ordinary plugins while exposing only relative ID, version,
 * active state, and network-active state.
 */
function observer_p17_plugins(): array {
	if ( ! function_exists( 'get_plugins' ) ) {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';
	}

	// Explicit option allowlist: active_plugins and active_sitewide_plugins.
	$active = array_map( 'plugin_basename', (array) get_option( 'active_plugins', array() ) );
	$network_active = is_multisite()
		? array_keys( (array) get_site_option( 'active_sitewide_plugins', array() ) )
		: array();
	$network_active = array_map( 'plugin_basename', $network_active );
	$components = array();

	foreach ( get_plugins() as $file => $headers ) {
		$file = plugin_basename( (string) $file );
		$components[] = array(
			'id'             => observer_p17_safe_component_id( $file ),
			'version'        => observer_p17_safe_version( $headers['Version'] ?? null ),
			'active'         => in_array( $file, $active, true ),
			'network_active' => in_array( $file, $network_active, true ),
		);
	}

	observer_p17_sort_components( $components );
	return $components;
}

function observer_p17_mu_plugins(): array {
	if ( ! function_exists( 'get_mu_plugins' ) ) {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';
	}

	$components = array();
	foreach ( get_mu_plugins() as $file => $headers ) {
		$components[] = array(
			'id'      => observer_p17_safe_component_id( plugin_basename( (string) $file ) ),
			'version' => observer_p17_safe_version( $headers['Version'] ?? null ),
		);
	}

	observer_p17_sort_components( $components );
	return $components;
}

function observer_p17_dropins(): array {
	if ( ! function_exists( 'get_dropins' ) ) {
		require_once ABSPATH . 'wp-admin/includes/plugin.php';
	}

	$components = array();
	foreach ( get_dropins() as $file => $headers ) {
		$components[] = array(
			'id'      => observer_p17_safe_component_id( plugin_basename( (string) $file ) ),
			'version' => observer_p17_safe_version( $headers['Version'] ?? null ),
		);
	}

	observer_p17_sort_components( $components );
	return $components;
}

/**
 * Execute one scalar query without allowing a database error to escape into
 * stdout. The caller receives only a success boolean and the scalar result.
 */
function observer_p17_db_scalar(string $sql, bool &$query_ok) {
	global $wpdb;

	$previous_suppression = $wpdb->suppress_errors( true );
	$wpdb->last_error = '';
	$value = $wpdb->get_var( $sql ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared -- every dynamic statement is prepared at its call site.
	$query_ok = '' === (string) $wpdb->last_error;
	$wpdb->suppress_errors( $previous_suppression );

	return $value;
}

/**
 * Prove connection-owned MySQL/MariaDB advisory-lock semantics. The random
 * lock name and numeric connection ID are intentionally never returned.
 */
function observer_p17_advisory_lock_probe(): array {
	global $wpdb;

	$checks = array(
		'connection_id_available'       => false,
		'get_lock_acquired'             => false,
		'is_used_lock_query_succeeded'  => false,
		'owner_matches_connection'      => false,
		'connection_id_stable'          => false,
		'release_lock_succeeded'        => false,
		'released_state_confirmed'      => false,
		'cleanup_release_succeeded'     => true,
	);
	$error_code = null;
	$lock_acquired = false;
	$lock_name = '';

	try {
		$lock_name = 'observer_p17_' . bin2hex( random_bytes( 16 ) );

		$query_ok = false;
		$connection_before = observer_p17_db_scalar( 'SELECT CONNECTION_ID()', $query_ok );
		$checks['connection_id_available'] = $query_ok && is_numeric( $connection_before ) && (int) $connection_before > 0;

		$get_lock = observer_p17_db_scalar(
			$wpdb->prepare( 'SELECT GET_LOCK(%s, %d)', $lock_name, 0 ),
			$query_ok
		);
		$checks['get_lock_acquired'] = $query_ok && 1 === (int) $get_lock;
		$lock_acquired = $checks['get_lock_acquired'];

		$owner = observer_p17_db_scalar(
			$wpdb->prepare( 'SELECT IS_USED_LOCK(%s)', $lock_name ),
			$query_ok
		);
		$checks['is_used_lock_query_succeeded'] = $query_ok;
		$checks['owner_matches_connection'] = $query_ok
			&& $checks['connection_id_available']
			&& is_numeric( $owner )
			&& (int) $owner === (int) $connection_before;

		$connection_during = observer_p17_db_scalar( 'SELECT CONNECTION_ID()', $query_ok );
		$checks['connection_id_stable'] = $query_ok
			&& $checks['connection_id_available']
			&& is_numeric( $connection_during )
			&& (int) $connection_during === (int) $connection_before;

		$released = observer_p17_db_scalar(
			$wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock_name ),
			$query_ok
		);
		$checks['release_lock_succeeded'] = $query_ok && 1 === (int) $released;
		if ( $checks['release_lock_succeeded'] ) {
			$lock_acquired = false;
		}

		$owner_after_release = observer_p17_db_scalar(
			$wpdb->prepare( 'SELECT IS_USED_LOCK(%s)', $lock_name ),
			$query_ok
		);
		$checks['released_state_confirmed'] = $query_ok && null === $owner_after_release;

		$connection_after = observer_p17_db_scalar( 'SELECT CONNECTION_ID()', $query_ok );
		$checks['connection_id_stable'] = $checks['connection_id_stable']
			&& $query_ok
			&& is_numeric( $connection_after )
			&& (int) $connection_after === (int) $connection_before;
	} catch ( Throwable $error ) {
		$error_code = 'advisory_lock_probe_exception';
	} finally {
		if ( $lock_acquired && '' !== $lock_name ) {
			$cleanup = observer_p17_db_scalar(
				$wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock_name ),
				$query_ok
			);
			$checks['cleanup_release_succeeded'] = $query_ok && 1 === (int) $cleanup;
		}
	}

	$passed = ! in_array( false, array_values( $checks ), true );
	if ( ! $passed && null === $error_code ) {
		$error_code = 'advisory_lock_contract_failed';
	}

	return array(
		'status'     => $passed ? 'pass' : 'fail',
		'checks'     => $checks,
		'error_code' => $error_code,
	);
}

try {
	global $wp_version, $wpdb;

	// Explicit scalar-option allowlist: siteurl, home, permalink_structure, and blog_public.
	$site_url = observer_p17_public_url( get_option( 'siteurl', '' ) );
	$home_url = observer_p17_public_url( get_option( 'home', '' ) );
	$permalink_structure = (string) get_option( 'permalink_structure', '' );
	$search_visibility = 1 === (int) get_option( 'blog_public', 1 );

	$theme = wp_get_theme();
	$stylesheet = observer_p17_safe_component_id( get_stylesheet() );
	$template = observer_p17_safe_component_id( get_template() );
	$template_theme = wp_get_theme( get_template() );
	$plugins = observer_p17_plugins();
	$mu_plugins = observer_p17_mu_plugins();
	$dropins = observer_p17_dropins();
	$dropin_ids = array_column( $dropins, 'id' );

	$db_version = observer_p17_safe_version( $wpdb->db_version() );
	$db_server_info = method_exists( $wpdb, 'db_server_info' ) ? (string) $wpdb->db_server_info() : '';
	$db_engine = false !== stripos( $db_server_info, 'mariadb' )
		? 'mariadb'
		: ( null !== $db_version ? 'mysql' : 'unknown' );
	$lock_probe = observer_p17_advisory_lock_probe();

	$error_codes = array();
	if ( null === $site_url ) {
		$error_codes[] = 'invalid_siteurl';
	}
	if ( null === $home_url ) {
		$error_codes[] = 'invalid_home';
	}
	if ( 'pass' !== $lock_probe['status'] ) {
		$error_codes[] = (string) $lock_probe['error_code'];
	}
	sort( $error_codes, SORT_STRING );

	$server_software = $_SERVER['SERVER_SOFTWARE'] ?? '';
	$document = array(
		'schema_version' => 'observer-p1.7-environment-probe/v1',
		'status'         => empty( $error_codes ) ? 'pass' : 'fail',
		'wordpress'      => array(
			'version'          => observer_p17_safe_version( $wp_version ),
			'multisite'        => is_multisite(),
			'environment_type' => observer_p17_safe_component_id( wp_get_environment_type() ),
		),
		'runtime'        => array(
			'php'      => array(
				'version' => observer_p17_safe_version( PHP_VERSION ),
				'sapi'    => observer_p17_safe_component_id( PHP_SAPI ),
			),
			'database' => array(
				'engine'  => $db_engine,
				'version' => $db_version,
			),
			'server'   => observer_p17_server_signature( $server_software ),
		),
		'urls'           => array(
			'siteurl' => $site_url,
			'home'    => $home_url,
		),
		'permalinks'     => array(
			'structure' => substr( sanitize_text_field( $permalink_structure ), 0, 191 ),
			'pretty'    => '' !== $permalink_structure,
		),
		'https'          => array(
			'siteurl_uses_https' => null !== $site_url && 0 === strpos( $site_url, 'https://' ),
			'home_uses_https'    => null !== $home_url && 0 === strpos( $home_url, 'https://' ),
			'wordpress_uses_https' => function_exists( 'wp_is_using_https' ) ? wp_is_using_https() : null,
			'current_request_is_ssl' => is_ssl(),
		),
		'theme'          => array(
			'stylesheet'        => $stylesheet,
			'stylesheet_version'=> observer_p17_safe_version( $theme->get( 'Version' ) ),
			'template'          => $template,
			'template_version'  => observer_p17_safe_version( $template_theme->get( 'Version' ) ),
			'is_child'          => $stylesheet !== $template,
		),
		'plugins'        => $plugins,
		'mu_plugins'     => $mu_plugins,
		'cache'          => array(
			'using_external_object_cache' => wp_using_ext_object_cache(),
			'wp_cache_constant'           => defined( 'WP_CACHE' ) && true === WP_CACHE,
			'object_cache_dropin'         => in_array( 'object-cache.php', $dropin_ids, true ),
			'advanced_cache_dropin'       => in_array( 'advanced-cache.php', $dropin_ids, true ),
		),
		'dropins'        => $dropins,
		'search'         => array(
			'public_indexing_enabled' => $search_visibility,
		),
		'advisory_lock'  => $lock_probe,
		'error_codes'    => $error_codes,
	);

	observer_p17_emit( $document, empty( $error_codes ) ? 0 : 1 );
} catch ( Throwable $error ) {
	observer_p17_emit(
		array(
			'schema_version' => 'observer-p1.7-environment-probe/v1',
			'status'         => 'fail',
			'error_codes'    => array( 'environment_collection_failed' ),
		),
		1
	);
}
