<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class Admin {
	public const CAPABILITY = 'manage_observer_registry';

	public static function add_page(): void {
		add_management_page(
			__( 'Observer Research Registry', 'observer-research-registry' ),
			__( 'Research Registry', 'observer-research-registry' ),
			self::CAPABILITY,
			'observer-research-registry',
			array( self::class, 'render_page' )
		);
	}

	public static function handle_sync(): void {
		self::authorize( 'observer_registry_sync' );
		$result = Importer::sync();
		self::store_notice( $result );
		wp_safe_redirect( admin_url( 'tools.php?page=observer-research-registry' ) );
		exit;
	}

	public static function handle_recover(): void {
		self::authorize( 'observer_registry_recover' );
		$result = Importer::recover();
		self::store_notice( $result );
		wp_safe_redirect( admin_url( 'tools.php?page=observer-research-registry' ) );
		exit;
	}

	public static function render_page(): void {
		if ( ! current_user_can( self::CAPABILITY ) ) {
			wp_die( esc_html__( 'You are not allowed to manage the research registry.', 'observer-research-registry' ) );
		}

		self::render_notice();
		$preview = Importer::preview();
		$state = Importer::state();
		?>
		<div class="wrap">
			<h1><?php echo esc_html__( 'Observer Research Registry', 'observer-research-registry' ); ?></h1>
			<p><?php echo esc_html__( 'GitHub remains authoritative for scientific metadata. Synchronization creates drafts and preserves editorial content, excerpts, media, authors, and visibility.', 'observer-research-registry' ); ?></p>
			<p><strong><?php echo esc_html__( 'Bundled registry SHA-256:', 'observer-research-registry' ); ?></strong> <code><?php echo esc_html( Registry::digest() ); ?></code></p>
			<?php if ( isset( $state['imported_at_utc'] ) ) : ?>
				<p><strong><?php echo esc_html__( 'Last successful synchronization:', 'observer-research-registry' ); ?></strong> <?php echo esc_html( $state['imported_at_utc'] ); ?></p>
			<?php endif; ?>

			<?php if ( is_wp_error( $preview ) ) : ?>
				<div class="notice notice-error inline"><p><?php echo esc_html( $preview->get_error_message() ); ?></p></div>
			<?php else : ?>
				<?php $counts = array_count_values( array_column( $preview['operations'], 'action' ) ); ?>
				<table class="widefat striped" style="max-width:48rem">
					<thead><tr><th><?php echo esc_html__( 'Planned action', 'observer-research-registry' ); ?></th><th><?php echo esc_html__( 'Count', 'observer-research-registry' ); ?></th></tr></thead>
					<tbody>
						<?php foreach ( array( 'create', 'update', 'noop' ) as $action ) : ?>
							<tr><td><?php echo esc_html( ucfirst( $action ) ); ?></td><td><?php echo esc_html( (string) ( $counts[ $action ] ?? 0 ) ); ?></td></tr>
						<?php endforeach; ?>
						<tr><td><?php echo esc_html__( 'Orphaned records (preserved)', 'observer-research-registry' ); ?></td><td><?php echo esc_html( (string) count( $preview['orphans'] ) ); ?></td></tr>
					</tbody>
				</table>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>" style="margin-top:1rem">
					<input type="hidden" name="action" value="observer_registry_sync">
					<?php wp_nonce_field( 'observer_registry_sync' ); ?>
					<?php submit_button( __( 'Synchronize pinned registry', 'observer-research-registry' ), 'primary', 'submit', false ); ?>
				</form>
			<?php endif; ?>

			<?php if ( Importer::has_journal() ) : ?>
				<div class="notice notice-warning inline"><p><?php echo esc_html__( 'An incomplete import journal exists. Recover it before synchronizing.', 'observer-research-registry' ); ?></p></div>
				<form method="post" action="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>">
					<input type="hidden" name="action" value="observer_registry_recover">
					<?php wp_nonce_field( 'observer_registry_recover' ); ?>
					<?php submit_button( __( 'Recover incomplete import', 'observer-research-registry' ), 'secondary', 'submit', false ); ?>
				</form>
			<?php endif; ?>
		</div>
		<?php
	}

	public static function grant_capability(): void {
		$role = get_role( 'administrator' );
		if ( null !== $role ) {
			$role->add_cap( self::CAPABILITY );
		}
	}

	public static function revoke_capability(): void {
		$role = get_role( 'administrator' );
		if ( null !== $role ) {
			$role->remove_cap( self::CAPABILITY );
		}
	}

	private static function authorize(string $nonce_action): void {
		if ( ! current_user_can( self::CAPABILITY ) ) {
			wp_die( esc_html__( 'You are not allowed to manage the research registry.', 'observer-research-registry' ), '', array( 'response' => 403 ) );
		}
		check_admin_referer( $nonce_action );
	}

	private static function store_notice($result): void {
		$notice = is_wp_error( $result )
			? array( 'type' => 'error', 'message' => $result->get_error_message() )
			: array( 'type' => 'success', 'message' => __( 'Research registry operation completed.', 'observer-research-registry' ) );
		set_transient( 'observer_registry_notice_' . get_current_user_id(), $notice, 60 );
	}

	private static function render_notice(): void {
		$key = 'observer_registry_notice_' . get_current_user_id();
		$notice = get_transient( $key );
		if ( ! is_array( $notice ) ) {
			return;
		}
		delete_transient( $key );
		$class = 'success' === $notice['type'] ? 'notice-success' : 'notice-error';
		echo '<div class="notice ' . esc_attr( $class ) . ' is-dismissible"><p>' . esc_html( $notice['message'] ) . '</p></div>';
	}
}
