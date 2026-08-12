<?php
/**
 * Plugin Name: Observer Research Registry
 * Plugin URI: https://theobserverofmultiverses.info/
 * Description: Registry-driven research pages, immutable scientific metadata, badges, pinned evidence links, and JSON-LD for The Observer of Multiverses.
 * Version: 0.1.0
 * Author: Stassis Stashkevichyus
 * Author URI: https://orcid.org/0009-0000-2294-705X
 * License: GPL-2.0-or-later
 * License URI: https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain: observer-research-registry
 * Requires at least: 6.4
 * Requires PHP: 7.4
 */

declare(strict_types=1);

namespace ObserverResearchRegistry;

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'OBSERVER_RESEARCH_REGISTRY_VERSION', '0.1.0' );
define( 'OBSERVER_RESEARCH_REGISTRY_FILE', __FILE__ );
define( 'OBSERVER_RESEARCH_REGISTRY_DIR', plugin_dir_path( __FILE__ ) );
define( 'OBSERVER_RESEARCH_REGISTRY_URL', plugin_dir_url( __FILE__ ) );

$observer_registry_classes = array(
	'class-registry.php',
	'class-badges.php',
	'class-links.php',
	'class-json-ld.php',
	'class-post-type.php',
	'class-meta-schema.php',
	'class-importer.php',
	'class-rest-fields.php',
	'class-renderer.php',
	'class-admin.php',
	'class-cli-command.php',
	'class-plugin.php',
);

foreach ( $observer_registry_classes as $observer_registry_class ) {
	require_once OBSERVER_RESEARCH_REGISTRY_DIR . 'src/' . $observer_registry_class;
}

register_activation_hook( __FILE__, array( Plugin::class, 'activate' ) );
register_deactivation_hook( __FILE__, array( Plugin::class, 'deactivate' ) );

Plugin::boot();

