<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class PostType {
	public const KEY = 'research_output';

	public static function register(): void {
		$model = Registry::model()['custom_post_type'];
		register_post_type(
			self::KEY,
			array(
				'labels' => array(
					'name'          => __( 'Research outputs', 'observer-research-registry' ),
					'singular_name' => __( 'Research output', 'observer-research-registry' ),
					'edit_item'     => __( 'Edit research presentation', 'observer-research-registry' ),
					'view_item'     => __( 'View research output', 'observer-research-registry' ),
					'all_items'     => __( 'Research outputs', 'observer-research-registry' ),
					'add_new_item'  => __( 'Registry synchronization creates research outputs', 'observer-research-registry' ),
				),
				'public'              => true,
				'hierarchical'        => false,
				'has_archive'         => $model['archive_slug'],
				'rewrite'             => array( 'slug' => $model['rewrite_slug'], 'with_front' => false ),
				'show_in_rest'        => true,
				'rest_base'           => $model['rest_base'],
				'supports'            => $model['supports'],
				'map_meta_cap'        => true,
				'capability_type'      => 'post',
				'capabilities'         => array( 'create_posts' => 'do_not_allow' ),
				'publicly_queryable'  => true,
				'exclude_from_search' => false,
				'delete_with_user'    => false,
				'menu_icon'           => 'dashicons-welcome-learn-more',
			)
		);
	}

	public static function order_archive($query): void {
		if ( is_admin() || ! $query->is_main_query() || ! $query->is_post_type_archive( self::KEY ) ) {
			return;
		}

		$post_ids = array();
		foreach ( Registry::ordered_works() as $work ) {
			$post_id = Importer::post_id_for_work( $work['id'] );
			if ( null !== $post_id && 'publish' === get_post_status( $post_id ) ) {
				$post_ids[] = $post_id;
			}
		}

		$query->set( 'post__in', $post_ids ?: array( 0 ) );
		$query->set( 'orderby', 'post__in' );
		$query->set( 'posts_per_page', -1 );
		$query->set( 'no_found_rows', true );
	}

	public static function enforce_canonical_slug(array $data, array $postarr): array {
		if ( self::KEY !== ( $data['post_type'] ?? '' ) || MetaSchema::internal_post_write_active() ) {
			return $data;
		}

		$post_id = isset( $postarr['ID'] ) ? (int) $postarr['ID'] : 0;
		if ( $post_id <= 0 ) {
			return $data;
		}

		$work_id = (string) get_post_meta( $post_id, 'observer_work_id', true );
		$work = Registry::work_by_id( $work_id );
		if ( null !== $work ) {
			$data['post_name'] = $work['slug'];
		}

		return $data;
	}

	public static function template(string $template): string {
		if ( is_post_type_archive( self::KEY ) ) {
			return self::locate_template( 'archive-research_output.php', $template );
		}
		if ( is_singular( self::KEY ) ) {
			return self::locate_template( 'single-research_output.php', $template );
		}

		return $template;
	}

	public static function restrict_deletion(array $caps, string $cap, int $user_id, array $args): array {
		if ( 'delete_post' !== $cap || empty( $args[0] ) ) {
			return $caps;
		}

		$post = get_post( (int) $args[0] );
		if ( null !== $post && self::KEY === $post->post_type ) {
			return array( Admin::CAPABILITY );
		}

		return $caps;
	}

	private static function locate_template(string $name, string $fallback): string {
		$theme_template = locate_template( 'observer-research-registry/' . $name );
		if ( '' !== $theme_template ) {
			return $theme_template;
		}

		$plugin_template = OBSERVER_RESEARCH_REGISTRY_DIR . 'templates/' . $name;

		return is_readable( $plugin_template ) ? $plugin_template : $fallback;
	}
}
