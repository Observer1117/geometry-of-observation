<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class Plugin {
	private static $booted = false;

	public static function boot(): void {
		if ( self::$booted ) {
			return;
		}
		self::$booted = true;

		add_action( 'init', array( PostType::class, 'register' ), 5 );
		add_action( 'init', array( MetaSchema::class, 'register' ), 6 );
		add_action( 'rest_api_init', array( RestFields::class, 'register' ) );
		add_action( 'pre_get_posts', array( PostType::class, 'order_archive' ) );
		add_action( 'wp_enqueue_scripts', array( Renderer::class, 'enqueue_assets' ) );
		add_action( 'wp_head', array( Renderer::class, 'emit_json_ld' ), 20 );
		add_action( 'admin_menu', array( Admin::class, 'add_page' ) );
		add_action( 'admin_post_observer_registry_sync', array( Admin::class, 'handle_sync' ) );
		add_action( 'admin_post_observer_registry_recover', array( Admin::class, 'handle_recover' ) );

		add_filter( 'is_protected_meta', array( MetaSchema::class, 'protect_meta' ), 10, 3 );
		add_filter( 'add_post_metadata', array( MetaSchema::class, 'block_add' ), 10, 5 );
		add_filter( 'update_post_metadata', array( MetaSchema::class, 'block_update' ), 10, 5 );
		add_filter( 'delete_post_metadata', array( MetaSchema::class, 'block_delete' ), 10, 5 );
		add_filter( 'update_post_metadata_by_mid', array( MetaSchema::class, 'block_update_by_mid' ), 10, 4 );
		add_filter( 'delete_post_metadata_by_mid', array( MetaSchema::class, 'block_delete_by_mid' ), 10, 2 );
		add_filter( 'wp_insert_post_data', array( PostType::class, 'enforce_canonical_slug' ), 10, 2 );
		add_filter( 'map_meta_cap', array( PostType::class, 'restrict_deletion' ), 10, 4 );
		add_filter( 'template_include', array( PostType::class, 'template' ), 20 );
		add_filter( 'rest_pre_insert_' . PostType::KEY, array( RestFields::class, 'reject_machine_meta_write' ), 10, 2 );

		if ( defined( 'WP_CLI' ) && WP_CLI ) {
			\WP_CLI::add_command( 'observer registry', CliCommand::class );
		}
	}

	public static function activate(): void {
		Registry::index();
		Registry::model();
		PostType::register();
		MetaSchema::register();
		Admin::grant_capability();
		flush_rewrite_rules();
	}

	public static function deactivate(): void {
		flush_rewrite_rules();
	}
}
