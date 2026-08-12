<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

use WP_Error;

final class RestFields {
	public static function register(): void {
		self::register_field( 'observer_registry_record', 'object', array( self::class, 'registry_record' ) );
		self::register_field( 'observer_badges', 'array', array( self::class, 'badges' ), array( 'type' => 'object' ) );
		self::register_field( 'observer_claim_boundary_url', array( 'string', 'null' ), array( self::class, 'claim_url' ) );
		self::register_field( 'observer_reproducibility_url', array( 'string', 'null' ), array( self::class, 'reproducibility_url' ) );
		self::register_field( 'observer_companion_links', 'array', array( self::class, 'companion_links' ), array( 'type' => 'object' ) );
	}

	public static function reject_machine_meta_write($prepared_post, $request) {
		$meta = $request->get_param( 'meta' );
		if ( ! is_array( $meta ) ) {
			return $prepared_post;
		}

		foreach ( array_keys( $meta ) as $key ) {
			if ( 0 === strpos( (string) $key, 'observer_' ) || 0 === strpos( (string) $key, '_observer_' ) ) {
				return new WP_Error(
					'observer_registry_read_only',
					__( 'Scientific registry metadata is read-only. Use the authenticated registry synchronizer.', 'observer-research-registry' ),
					array( 'status' => 403 )
				);
			}
		}

		return $prepared_post;
	}

	public static function registry_record(array $object): ?array {
		return self::work_for_object( $object );
	}

	public static function badges(array $object): array {
		$work = self::work_for_object( $object );

		return null === $work ? array() : Badges::for_work( $work );
	}

	public static function claim_url(array $object): ?string {
		$work = self::work_for_object( $object );

		return null === $work ? null : Registry::source_file_url( $work, $work['claim_boundary_path'] ?? null );
	}

	public static function reproducibility_url(array $object): ?string {
		$work = self::work_for_object( $object );

		return null === $work ? null : Registry::source_file_url( $work, $work['reproducibility_path'] ?? null );
	}

	public static function companion_links(array $object): array {
		$work = self::work_for_object( $object );
		if ( null === $work ) {
			return array();
		}

		$links = array();
		foreach ( Links::companions( $work ) as $companion ) {
			$post_id = Importer::post_id_for_work( $companion['id'] );
			if ( null !== $post_id && 'publish' === get_post_status( $post_id ) ) {
				$links[] = array(
					'work_id' => $companion['id'],
					'label'   => $companion['short_title'],
					'url'     => get_permalink( $post_id ),
				);
			}
		}

		return $links;
	}

	private static function register_field(string $name, $type, callable $callback, ?array $items = null): void {
		$schema = array(
			'description' => 'Read-only field derived from the pinned Observer research registry.',
			'type'        => $type,
			'context'     => array( 'view', 'edit' ),
			'readonly'    => true,
		);
		if ( null !== $items ) {
			$schema['items'] = $items;
		}

		register_rest_field(
			PostType::KEY,
			$name,
			array(
				'get_callback' => $callback,
				'schema'       => $schema,
			)
		);
	}

	private static function work_for_object(array $object): ?array {
		$post_id = isset( $object['id'] ) ? (int) $object['id'] : 0;
		if ( $post_id <= 0 ) {
			return null;
		}

		$work_id = (string) get_post_meta( $post_id, 'observer_work_id', true );

		return Registry::work_by_id( $work_id );
	}
}

