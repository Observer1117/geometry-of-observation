<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class MetaSchema {
	private static $internal_meta_write = false;
	private static $internal_post_write = false;

	public static function register(): void {
		foreach ( Registry::model()['machine_meta'] as $field ) {
			$type = self::primary_type( $field['type'] );
			$schema = self::rest_schema( $field, $type );
			register_post_meta(
				PostType::KEY,
				$field['key'],
				array(
					'type'              => $type,
					'single'            => true,
					'show_in_rest'      => array( 'schema' => $schema ),
					'auth_callback'     => array( self::class, 'deny_external_write' ),
					'sanitize_callback' => array( self::class, 'sanitize_registered_value' ),
					'description'       => 'Read-only projection of the pinned Observer research registry.',
				)
			);
		}
	}

	public static function deny_external_write(): bool {
		return self::$internal_meta_write;
	}

	public static function sanitize_registered_value($value, string $meta_key, string $object_type, string $object_subtype = '') {
		if ( 0 !== strpos( $meta_key, 'observer_' ) ) {
			return $value;
		}

		$field = self::field_by_key( $meta_key );
		if ( null === $field ) {
			return $value;
		}

		$type = self::primary_type( $field['type'] );
		if ( 'array' === $type ) {
			return is_array( $value ) ? $value : array();
		}

		return is_scalar( $value ) ? (string) $value : '';
	}

	public static function protect_meta(bool $protected, string $meta_key, string $meta_type): bool {
		if ( 'post' === $meta_type && ( 0 === strpos( $meta_key, 'observer_' ) || 0 === strpos( $meta_key, '_observer_' ) ) ) {
			return true;
		}

		return $protected;
	}

	public static function block_add($check, int $object_id, string $meta_key, $meta_value, bool $unique) {
		return self::block_external_write( $check, $meta_key );
	}

	public static function block_update($check, int $object_id, string $meta_key, $meta_value, $previous_value) {
		return self::block_external_write( $check, $meta_key );
	}

	public static function block_delete($check, int $object_id, string $meta_key, $meta_value, bool $delete_all) {
		return self::block_external_write( $check, $meta_key );
	}

	public static function block_update_by_mid($check, int $meta_id, $meta_value, $meta_key) {
		if ( self::$internal_meta_write ) {
			return $check;
		}

		// update_metadata_by_mid() can rename a row, so protect both the current
		// key and a newly supplied key.
		if ( is_string( $meta_key ) && self::is_managed_meta_key( $meta_key ) ) {
			return false;
		}

		return self::block_external_write_by_mid( $check, $meta_id );
	}

	public static function block_delete_by_mid($check, int $meta_id) {
		return self::block_external_write_by_mid( $check, $meta_id );
	}

	public static function write_authoritative(int $post_id, array $meta): void {
		self::$internal_meta_write = true;
		try {
			foreach ( Registry::machine_meta_keys() as $key ) {
				$value = array_key_exists( $key, $meta ) ? $meta[ $key ] : null;
				if ( null === $value || ( 'observer_companion_work_ids' === $key && array() === $value ) ) {
					delete_post_meta( $post_id, $key );
				} else {
					update_post_meta( $post_id, $key, $value );
				}
			}
		} finally {
			self::$internal_meta_write = false;
		}
	}

	public static function write_internal(int $post_id, array $values): void {
		self::$internal_meta_write = true;
		try {
			foreach ( $values as $key => $value ) {
				if ( null === $value ) {
					delete_post_meta( $post_id, $key );
				} else {
					update_post_meta( $post_id, $key, $value );
				}
			}
		} finally {
			self::$internal_meta_write = false;
		}
	}

	public static function with_internal_post_write(callable $callback) {
		self::$internal_post_write = true;
		try {
			return $callback();
		} finally {
			self::$internal_post_write = false;
		}
	}

	public static function with_internal_import_write(callable $callback) {
		self::$internal_meta_write = true;
		self::$internal_post_write = true;
		try {
			return $callback();
		} finally {
			self::$internal_post_write = false;
			self::$internal_meta_write = false;
		}
	}

	public static function internal_post_write_active(): bool {
		return self::$internal_post_write;
	}

	private static function block_external_write($check, string $meta_key) {
		if ( self::$internal_meta_write || ! self::is_managed_meta_key( $meta_key ) ) {
			return $check;
		}

		return false;
	}

	private static function block_external_write_by_mid($check, int $meta_id) {
		if ( self::$internal_meta_write ) {
			return $check;
		}

		$meta = get_metadata_by_mid( 'post', $meta_id );
		if ( ! is_object( $meta ) || ! isset( $meta->meta_key ) ) {
			return $check;
		}

		return self::block_external_write( $check, (string) $meta->meta_key );
	}

	private static function is_managed_meta_key(string $meta_key): bool {
		return 0 === strpos( $meta_key, 'observer_' ) || 0 === strpos( $meta_key, '_observer_' );
	}

	private static function field_by_key(string $key): ?array {
		foreach ( Registry::model()['machine_meta'] as $field ) {
			if ( $field['key'] === $key ) {
				return $field;
			}
		}

		return null;
	}

	private static function primary_type($type): string {
		if ( is_array( $type ) ) {
			foreach ( $type as $candidate ) {
				if ( 'null' !== $candidate ) {
					return $candidate;
				}
			}
		}

		return (string) $type;
	}

	private static function rest_schema(array $field, string $type): array {
		$schema = array( 'type' => $type, 'readonly' => true );
		if ( isset( $field['format'] ) ) {
			$schema['format'] = $field['format'];
		}
		if ( 'array' === $type ) {
			$schema['items'] = $field['items'] ?? array( 'type' => 'string' );
			if ( 'object' === ( $schema['items']['type'] ?? null ) ) {
				$schema['items']['properties'] = array(
					'scope'   => array( 'type' => 'string' ),
					'license' => array( 'type' => 'string' ),
				);
				$schema['items']['additionalProperties'] = false;
			}
		}

		return $schema;
	}
}
