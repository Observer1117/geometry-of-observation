<?php
/**
 * Preserve research posts and machine metadata. Only operational state and the
 * dedicated administrator capability are removed when the plugin is uninstalled.
 */

defined( 'WP_UNINSTALL_PLUGIN' ) || exit;

delete_option( '_observer_registry_import_lock' );
delete_option( '_observer_registry_import_journal' );
delete_option( '_observer_registry_import_state' );

$administrator = get_role( 'administrator' );
if ( null !== $administrator ) {
	$administrator->remove_cap( 'manage_observer_registry' );
}

