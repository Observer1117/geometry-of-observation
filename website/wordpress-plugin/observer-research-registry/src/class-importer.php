<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

use RuntimeException;
use Throwable;
use WP_Error;

final class Importer {
	private const LOCK_OPTION = '_observer_registry_import_lock';
	private const JOURNAL_OPTION = '_observer_registry_import_journal';
	private const STATE_OPTION = '_observer_registry_import_state';
	private const ADVISORY_LOCK_PREFIX = 'observer_registry_';
	private const INTERNAL_META = array(
		'_observer_registry_record',
		'_observer_registry_digest',
		'_observer_import_generation',
	);

	public static function sync() {
		try {
			$index = Registry::index();
			Registry::model();
		} catch ( Throwable $error ) {
			return new WP_Error( 'observer_registry_invalid', $error->getMessage() );
		}

		$token = self::token();
		$lock = self::acquire_lock( $token );
		if ( is_wp_error( $lock ) ) {
			return $lock;
		}

		try {
			if ( false !== get_option( self::JOURNAL_OPTION, false ) ) {
				throw new RuntimeException( 'An incomplete import journal exists. Run registry recovery before synchronizing.' );
			}

			self::refresh_lock( $token );
			$plan = self::preflight( $index );
			if ( is_wp_error( $plan ) ) {
				return $plan;
			}
			self::refresh_lock( $token );

			$journal = self::build_journal( $token, $plan );
			self::refresh_lock( $token );
			$lock_state = get_option( self::LOCK_OPTION, false );
			$journal_added = is_array( $lock_state ) && 'option-fallback' === ( $lock_state['backend'] ?? '' )
				? add_option( self::JOURNAL_OPTION, $journal, '', false )
				: self::add_option_fenced( self::JOURNAL_OPTION, $journal, $token );
			if ( ! $journal_added || ! self::option_matches( self::JOURNAL_OPTION, $journal ) ) {
				throw new RuntimeException( 'Unable to create the durable import journal.' );
			}
			self::refresh_lock( $token );

			$result = self::execute( $index, $plan, $journal );
			self::assert_integrity( $index );
			self::assert_created_records_draft( $journal['created_ids'] );
			self::refresh_lock( $token );

			$state = array(
				'plugin_version'          => OBSERVER_RESEARCH_REGISTRY_VERSION,
				'registry_schema_version' => $index['schema']['version'],
				'registry_sha256'         => Registry::digest(),
				'source_commit'            => 'bab4480e50f8abe32087da765a145575a4519f8a',
				'imported_at_utc'          => gmdate( 'c' ),
				'counts'                   => $result,
				'orphan_post_ids'          => $plan['orphans'],
			);
			$previous_journal = $journal;
			$journal['pending_state'] = $state;
			self::persist_journal_transition( $previous_journal, $journal, $token );
			self::commit_state( $journal['previous_state'], $state, $token );
			self::delete_journal_checked( $journal, $token );

			return $state;
		} catch ( Throwable $error ) {
			$journal = get_option( self::JOURNAL_OPTION, false );
			if ( is_array( $journal ) && ( $journal['token'] ?? '' ) === $token ) {
				if ( ! self::lock_owned_by( $token ) ) {
					return new WP_Error( 'observer_registry_lock_lost', $error->getMessage() . ' The import lease was lost; recovery now owns any incomplete journal.' );
				}
				$rollback = self::rollback( $journal, $token );
				if ( true === $rollback ) {
					try {
						self::delete_journal_checked( $journal, $token );
					} catch ( Throwable $cleanup_error ) {
						return new WP_Error( 'observer_registry_rollback_failed', $error->getMessage() . ' Automatic rollback completed, but its journal could not be removed; run recovery before retrying.' );
					}
				} else {
					return new WP_Error( 'observer_registry_rollback_failed', $error->getMessage() . ' Automatic rollback was incomplete; run recovery before retrying.' );
				}
			}

			return new WP_Error( 'observer_registry_sync_failed', $error->getMessage() );
		} finally {
			self::release_lock( $token );
		}
	}

	public static function preview() {
		try {
			return self::preflight( Registry::index() );
		} catch ( Throwable $error ) {
			return new WP_Error( 'observer_registry_preview_failed', $error->getMessage() );
		}
	}

	public static function recover() {
		$token = self::token();
		$lock = self::acquire_recovery_lock( $token );
		if ( is_wp_error( $lock ) ) {
			return $lock;
		}

		try {
			$journal = get_option( self::JOURNAL_OPTION, false );
			if ( ! is_array( $journal ) ) {
				return array( 'recovered' => false, 'message' => 'No incomplete import journal exists.' );
			}

			self::refresh_lock( $token );
			if ( ! self::rollback( $journal, $token ) ) {
				return new WP_Error( 'observer_registry_recovery_failed', 'The import journal could not be fully rolled back.' );
			}
			self::refresh_lock( $token );

			try {
				self::delete_journal_checked( $journal, $token );
			} catch ( Throwable $error ) {
				return new WP_Error( 'observer_registry_recovery_failed', 'The import was rolled back, but its journal could not be removed.' );
			}

			return array( 'recovered' => true, 'message' => 'The incomplete import was rolled back.' );
		} catch ( Throwable $error ) {
			return new WP_Error( 'observer_registry_recovery_failed', $error->getMessage() );
		} finally {
			self::release_lock( $token );
		}
	}

	public static function state(): array {
		$state = get_option( self::STATE_OPTION, array() );

		return is_array( $state ) ? $state : array();
	}

	public static function has_journal(): bool {
		return false !== get_option( self::JOURNAL_OPTION, false );
	}

	public static function post_id_for_work(string $work_id): ?int {
		$ids = get_posts(
			array(
				'post_type'      => PostType::KEY,
				'post_status'    => array_keys( get_post_stati() ),
				'numberposts'    => 2,
				'fields'         => 'ids',
				'no_found_rows'  => true,
				'suppress_filters'=> true,
				'meta_key'       => 'observer_work_id',
				'meta_value'     => $work_id,
			)
		);

		return 1 === count( $ids ) ? (int) $ids[0] : null;
	}

	private static function preflight(array $index) {
		$errors = array();
		$posts = get_posts(
			array(
				'post_type'       => PostType::KEY,
				'post_status'     => array_keys( get_post_stati() ),
				'numberposts'     => -1,
				'orderby'         => 'ID',
				'order'           => 'ASC',
				'suppress_filters'=> true,
			)
		);

		$by_work = array();
		$by_slug = array();
		$known_ids = array_column( $index['works'], 'id' );
		$orphans = array();

		foreach ( $posts as $post ) {
			$work_id = (string) get_post_meta( $post->ID, 'observer_work_id', true );
			if ( '' !== $work_id ) {
				$by_work[ $work_id ][] = $post;
				if ( ! in_array( $work_id, $known_ids, true ) ) {
					$orphans[] = (int) $post->ID;
				}
			}
			$by_slug[ $post->post_name ][] = $post;
		}

		foreach ( $by_work as $work_id => $matches ) {
			if ( count( $matches ) > 1 ) {
				$errors[] = 'Duplicate WordPress records for observer_work_id ' . $work_id . '.';
			}
		}

		$archive_pages = get_posts(
			array(
				'post_type'       => 'page',
				'post_status'     => array_keys( get_post_stati() ),
				'name'            => 'research',
				'numberposts'     => -1,
				'suppress_filters'=> true,
			)
		);
		if ( $archive_pages ) {
			$errors[] = 'A WordPress Page already occupies /research/ and conflicts with the research_output archive.';
		}

		$operations = array();
		foreach ( Registry::ordered_works( $index ) as $work ) {
			$matches = $by_work[ $work['id'] ] ?? array();
			$post = 1 === count( $matches ) ? $matches[0] : null;
			$slug_matches = $by_slug[ $work['slug'] ] ?? array();

			foreach ( $slug_matches as $slug_post ) {
				if ( null === $post || (int) $slug_post->ID !== (int) $post->ID ) {
					$errors[] = 'Canonical slug collision at /research/' . $work['slug'] . '/.';
				}
			}

			if ( null === $post ) {
				$operations[] = array( 'action' => 'create', 'work_id' => $work['id'], 'post_id' => null, 'mutates' => true );
				continue;
			}

			$meta = Registry::meta_for_work( $work );
			$needs_meta = ! self::stored_meta_matches( (int) $post->ID, $meta, $work );
			$needs_slug = $post->post_name !== $work['slug'];
			$operations[] = array(
				'action'  => ( $needs_meta || $needs_slug ) ? 'update' : 'noop',
				'work_id' => $work['id'],
				'post_id' => (int) $post->ID,
				'mutates' => $needs_meta || $needs_slug,
			);
		}

		if ( $errors ) {
			return new WP_Error( 'observer_registry_preflight_failed', implode( ' ', array_unique( $errors ) ) );
		}

		return array( 'operations' => $operations, 'orphans' => $orphans );
	}

	private static function build_journal(string $token, array $plan): array {
		$snapshots = array();
		$create_intents = array();
		$author_id = get_current_user_id();
		$post_date = current_time( 'mysql' );
		$post_date_gmt = current_time( 'mysql', true );
		foreach ( $plan['operations'] as $operation ) {
			if ( 'create' === $operation['action'] ) {
				$work = Registry::work_by_id( $operation['work_id'] );
				if ( null === $work ) {
					throw new RuntimeException( 'Import plan references an unknown work while journaling.' );
				}
				$create_intents[ $operation['work_id'] ] = array(
					'work_id'   => $operation['work_id'],
					'marker'    => self::row_marker( $token, $operation['work_id'] ),
					'title'     => $work['title'],
					'slug'      => $work['slug'],
					'author_id' => $author_id,
					'post_date' => $post_date,
					'post_date_gmt' => $post_date_gmt,
					'guid'      => 'urn:observer-research-registry:' . rawurlencode( $operation['work_id'] ),
				);
			}
			if ( 'update' === $operation['action'] && $operation['mutates'] ) {
				$post_id = (int) $operation['post_id'];
				$post = get_post( $post_id );
				if ( null === $post ) {
					throw new RuntimeException( 'A preflighted post disappeared before journaling.' );
				}
				$snapshots[ (string) $post_id ] = array(
					'post_name' => $post->post_name,
					'meta'      => self::snapshot_meta( $post_id ),
				);
			}
		}

		return array(
			'token'       => $token,
			'created_at'  => gmdate( 'c' ),
			'registry_sha256' => Registry::digest(),
			'snapshots'   => $snapshots,
			'create_intents' => $create_intents,
			'created_ids' => array(),
			'previous_state' => self::snapshot_option( self::STATE_OPTION ),
		);
	}

	private static function execute(array $index, array $plan, array &$journal): array {
		$counts = array( 'created' => 0, 'updated' => 0, 'unchanged' => 0 );

		foreach ( $plan['operations'] as $operation ) {
			self::refresh_lock( (string) $journal['token'] );
			$work = Registry::work_by_id( $operation['work_id'], $index );
			if ( null === $work ) {
				throw new RuntimeException( 'Import plan references an unknown work.' );
			}

			if ( 'noop' === $operation['action'] ) {
				++$counts['unchanged'];
				continue;
			}

			if ( 'create' === $operation['action'] ) {
				$intent = $journal['create_intents'][ $work['id'] ] ?? null;
				if ( ! is_array( $intent ) || '' === (string) ( $intent['marker'] ?? '' ) ) {
					throw new RuntimeException( 'Import journal is missing a durable create intent.' );
				}
				$marker = (string) $intent['marker'];
				$marker_filter = static function (array $data, array $postarr) use ( $marker ): array {
					if ( PostType::KEY === ( $data['post_type'] ?? '' ) && $marker === ( $postarr['post_content_filtered'] ?? '' ) && MetaSchema::internal_post_write_active() ) {
						$data['post_content_filtered'] = $marker;
					}

					return $data;
				};
				add_filter( 'wp_insert_post_data', $marker_filter, PHP_INT_MAX, 2 );
				try {
					$post_id = MetaSchema::with_internal_import_write(
						static function () use ( $work, $journal, $marker, $intent ) {
							return wp_insert_post(
								array(
									'post_type'             => PostType::KEY,
									'post_status'    => 'draft',
									'post_title'            => $work['title'],
									'post_name'             => $work['slug'],
									'post_author'           => (int) $intent['author_id'],
									'post_date'             => (string) $intent['post_date'],
									'post_date_gmt'         => (string) $intent['post_date_gmt'],
									'guid'                  => (string) $intent['guid'],
									'post_content'          => '',
									'post_excerpt'          => '',
									'post_content_filtered' => $marker,
									'comment_status'        => 'closed',
									'ping_status'           => 'closed',
									'meta_input'            => array(
										'observer_work_id'            => $work['id'],
										'_observer_import_generation' => $journal['token'],
									),
								),
								true
							);
						}
					);
				} finally {
					remove_filter( 'wp_insert_post_data', $marker_filter, PHP_INT_MAX );
				}
				if ( is_wp_error( $post_id ) ) {
					throw new RuntimeException( $post_id->get_error_message() );
				}
				$post_id = (int) $post_id;
				self::refresh_lock( (string) $journal['token'] );
				self::verify_row_marker( $post_id, $marker );
				MetaSchema::write_internal(
					$post_id,
					array(
						'observer_work_id'            => $work['id'],
						'_observer_import_generation' => $journal['token'],
					)
				);
				if ( $work['id'] !== (string) get_post_meta( $post_id, 'observer_work_id', true ) || $journal['token'] !== (string) get_post_meta( $post_id, '_observer_import_generation', true ) ) {
					throw new RuntimeException( 'The created record could not persist its import identity before marker clearing.' );
				}
				if ( ! self::created_post_safe_to_delete( $post_id, $intent, (string) $journal['token'], false ) ) {
					throw new RuntimeException( 'A hook changed the created record before its durable identity was committed.' );
				}
				self::refresh_lock( (string) $journal['token'] );
				$previous_journal = $journal;
				$journal['create_intents'][ $work['id'] ]['assigned_post_id'] = $post_id;
				$journal['created_ids'][] = $post_id;
				self::persist_journal_transition( $previous_journal, $journal, (string) $journal['token'] );
				self::refresh_lock( (string) $journal['token'] );
				self::clear_row_marker( $post_id, $marker, (string) $journal['token'] );
				++$counts['created'];
			} else {
				$post_id = (int) $operation['post_id'];
				$post = get_post( $post_id );
				if ( null === $post ) {
					throw new RuntimeException( 'A preflighted post disappeared during import.' );
				}
				if ( $post->post_name !== $work['slug'] ) {
					$updated = MetaSchema::with_internal_post_write(
						static function () use ( $post_id, $work ) {
							return wp_update_post( array( 'ID' => $post_id, 'post_name' => $work['slug'] ), true );
						}
					);
					if ( is_wp_error( $updated ) ) {
						throw new RuntimeException( $updated->get_error_message() );
					}
				}
				++$counts['updated'];
			}

			self::refresh_lock( (string) $journal['token'] );
			self::write_record( $post_id, $work, $journal['token'] );
			self::refresh_lock( (string) $journal['token'] );
			self::verify_post( $post_id, $work, 'create' === $operation['action'] ? 'draft' : null );
		}

		return $counts;
	}

	private static function write_record(int $post_id, array $work, string $generation): void {
		$encoded = self::encode_record( $work );
		MetaSchema::write_authoritative( $post_id, Registry::meta_for_work( $work ) );
		MetaSchema::write_internal(
			$post_id,
			array(
				'_observer_registry_record'     => $encoded,
				'_observer_registry_digest'     => hash( 'sha256', $encoded ),
				'_observer_import_generation'   => $generation,
			)
		);
	}

	private static function verify_row_marker(int $post_id, string $marker): void {
		$post = get_post( $post_id );
		if ( null === $post || PostType::KEY !== $post->post_type || $marker !== (string) $post->post_content_filtered ) {
			throw new RuntimeException( 'WordPress changed or rejected the durable import row marker.' );
		}
	}

	private static function clear_row_marker(int $post_id, string $marker, string $owner_token): void {
		global $wpdb;

		self::verify_row_marker( $post_id, $marker );
		$lock = get_option( self::LOCK_OPTION, false );
		if ( ! is_array( $lock ) || (string) ( $lock['token'] ?? '' ) !== $owner_token || ! isset( $wpdb->posts ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'query' ) ) {
			throw new RuntimeException( 'Unable to fence durable marker clearing.' );
		}

		if ( 'mysql-advisory' === ( $lock['backend'] ?? '' ) ) {
			$query = $wpdb->prepare(
				"UPDATE {$wpdb->posts} SET post_content_filtered = '' WHERE ID = %d AND post_content_filtered = %s AND IS_USED_LOCK(%s) = CONNECTION_ID()",
				$post_id,
				$marker,
				(string) ( $lock['advisory_name'] ?? '' )
			);
		} elseif ( 'option-fallback' === ( $lock['backend'] ?? '' ) && self::lock_owned_by( $owner_token ) ) {
			$query = $wpdb->prepare(
				"UPDATE {$wpdb->posts} SET post_content_filtered = '' WHERE ID = %d AND post_content_filtered = %s",
				$post_id,
				$marker
			);
		} else {
			throw new RuntimeException( 'Unable to fence durable marker clearing on this database backend.' );
		}

		if ( 1 !== (int) $wpdb->query( $query ) ) {
			throw new RuntimeException( 'Unable to clear the durable import row marker.' );
		}

		clean_post_cache( $post_id );
		$post = get_post( $post_id );
		if ( null === $post || '' !== (string) $post->post_content_filtered || ! self::lock_owned_by( $owner_token ) ) {
			throw new RuntimeException( 'The durable import row marker remained after clearing.' );
		}
	}

	private static function verify_post(int $post_id, array $work, ?string $expected_status = null): void {
		$post = get_post( $post_id );
		if ( null === $post || PostType::KEY !== $post->post_type || $work['slug'] !== $post->post_name ) {
			throw new RuntimeException( 'WordPress changed or rejected the canonical research slug.' );
		}
		if ( null !== $expected_status && $expected_status !== $post->post_status ) {
			throw new RuntimeException( 'A newly imported research record did not remain in the required draft status.' );
		}

		if ( ! self::stored_meta_matches( $post_id, Registry::meta_for_work( $work ), $work ) ) {
			throw new RuntimeException( 'Post-import machine metadata verification failed for ' . $work['id'] . '.' );
		}
	}

	private static function assert_integrity(array $index): void {
		$seen_post_ids = array();
		foreach ( Registry::ordered_works( $index ) as $work ) {
			$ids = get_posts(
				array(
					'post_type'       => PostType::KEY,
					'post_status'     => array_keys( get_post_stati() ),
					'numberposts'     => -1,
					'fields'          => 'ids',
					'suppress_filters'=> true,
					'meta_key'        => 'observer_work_id',
					'meta_value'      => $work['id'],
				)
			);
			if ( 1 !== count( $ids ) ) {
				throw new RuntimeException( 'Global uniqueness verification failed for ' . $work['id'] . '.' );
			}
			$post_id = (int) $ids[0];
			if ( in_array( $post_id, $seen_post_ids, true ) ) {
				throw new RuntimeException( 'One WordPress record is mapped to multiple work IDs.' );
			}
			$seen_post_ids[] = $post_id;
			self::verify_post( $post_id, $work );
		}
	}

	private static function assert_created_records_draft(array $post_ids): void {
		foreach ( $post_ids as $post_id ) {
			$post = get_post( (int) $post_id );
			if ( null === $post || PostType::KEY !== $post->post_type || 'draft' !== $post->post_status || '' !== (string) $post->post_content_filtered ) {
				throw new RuntimeException( 'A newly imported research record did not remain in the required draft status.' );
			}
		}
	}

	private static function stored_meta_matches(int $post_id, array $meta, array $work): bool {
		foreach ( Registry::machine_meta_keys() as $key ) {
			$expected = $meta[ $key ] ?? null;
			$exists = metadata_exists( 'post', $post_id, $key );
			if ( null === $expected || ( 'observer_companion_work_ids' === $key && array() === $expected ) ) {
				if ( $exists ) {
					return false;
				}
				continue;
			}
			if ( ! $exists || self::canonical_compare( $expected ) !== self::canonical_compare( get_post_meta( $post_id, $key, true ) ) ) {
				return false;
			}
		}

		$encoded = self::encode_record( $work );
		return hash( 'sha256', $encoded ) === (string) get_post_meta( $post_id, '_observer_registry_digest', true )
			&& $encoded === (string) get_post_meta( $post_id, '_observer_registry_record', true );
	}

	private static function snapshot_meta(int $post_id): array {
		$snapshot = array();
		foreach ( array_merge( Registry::machine_meta_keys(), self::INTERNAL_META ) as $key ) {
			$snapshot[ $key ] = array(
				'exists' => metadata_exists( 'post', $post_id, $key ),
				'value'  => get_post_meta( $post_id, $key, true ),
			);
		}

		return $snapshot;
	}

	private static function row_marker(string $token, string $work_id): string {
		return 'observer-registry-import:' . $token . ':' . hash( 'sha256', $token . '|' . $work_id );
	}

	private static function created_post_safe_to_delete(int $post_id, array $intent, string $token, bool $marker_may_be_cleared): bool {
		global $wpdb;

		try {
			$post = get_post( $post_id );
			$work_id = (string) ( $intent['work_id'] ?? '' );
			$work = Registry::work_by_id( $work_id );
			if ( is_wp_error( $post ) || null === $post || null === $work || $post_id !== (int) $post->ID || PostType::KEY !== $post->post_type ) {
				return false;
			}

			$expected_post_fields = array(
				'post_author'       => (int) ( $intent['author_id'] ?? -1 ),
				'post_date'         => (string) ( $intent['post_date'] ?? '' ),
				'post_date_gmt'     => (string) ( $intent['post_date_gmt'] ?? '' ),
				'post_content'      => '',
				'post_title'        => $work['title'],
				'post_excerpt'      => '',
				'post_status'       => 'draft',
				'comment_status'    => 'closed',
				'ping_status'       => 'closed',
				'post_password'     => '',
				'post_name'         => $work['slug'],
				'to_ping'           => '',
				'pinged'            => '',
				'post_modified'     => (string) ( $intent['post_date'] ?? '' ),
				'post_modified_gmt' => (string) ( $intent['post_date_gmt'] ?? '' ),
				'post_parent'       => 0,
				'guid'              => (string) ( $intent['guid'] ?? '' ),
				'menu_order'        => 0,
				'post_mime_type'    => '',
				'comment_count'     => 0,
			);
			foreach ( $expected_post_fields as $field => $expected ) {
				if ( ! property_exists( $post, $field ) ) {
					return false;
				}
				$actual = $post->{$field} ?? null;
				if ( is_int( $expected ) ? (int) $actual !== $expected : (string) $actual !== $expected ) {
					return false;
				}
			}

			$expected_marker = self::row_marker( $token, $work_id );
			if ( $expected_marker !== (string) ( $intent['marker'] ?? '' ) ) {
				return false;
			}
			$actual_marker = (string) $post->post_content_filtered;
			if ( $expected_marker !== $actual_marker && ( ! $marker_may_be_cleared || '' !== $actual_marker ) ) {
				return false;
			}

			if ( ! isset( $wpdb->postmeta, $wpdb->comments, $wpdb->term_relationships, $wpdb->posts ) || ! property_exists( $wpdb, 'last_error' ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'get_results' ) || ! method_exists( $wpdb, 'get_var' ) ) {
				return false;
			}
			$meta_query = $wpdb->prepare( "SELECT meta_key, meta_value FROM {$wpdb->postmeta} WHERE post_id = %d ORDER BY meta_id ASC", $post_id );
			$wpdb->last_error = '';
			$meta_rows = $wpdb->get_results( $meta_query, ARRAY_A );
			if ( '' !== (string) $wpdb->last_error || is_wp_error( $meta_rows ) || ! is_array( $meta_rows ) ) {
				return false;
			}
			$allowed_meta = array_fill_keys( array_merge( Registry::machine_meta_keys(), self::INTERNAL_META ), true );
			$raw_meta = array();
			foreach ( $meta_rows as $row ) {
				$key = is_array( $row ) ? (string) ( $row['meta_key'] ?? '' ) : '';
				if ( '' === $key || ! isset( $allowed_meta[ $key ] ) || array_key_exists( $key, $raw_meta ) ) {
					return false;
				}
				$raw_meta[ $key ] = maybe_unserialize( $row['meta_value'] ?? null );
			}
			if ( array_key_exists( '_thumbnail_id', $raw_meta ) ) {
				return false;
			}

			$count_queries = array(
				$wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->comments} WHERE comment_post_ID = %d", $post_id ),
				$wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->term_relationships} WHERE object_id = %d", $post_id ),
				$wpdb->prepare( "SELECT COUNT(*) FROM {$wpdb->posts} WHERE post_parent = %d", $post_id ),
			);
			foreach ( $count_queries as $count_query ) {
				$wpdb->last_error = '';
				$count = $wpdb->get_var( $count_query );
				if ( '' !== (string) $wpdb->last_error || is_wp_error( $count ) || null === $count || ! is_numeric( $count ) || 0 !== (int) $count ) {
					return false;
				}
			}

			$stored_work_id = isset( $raw_meta['observer_work_id'] ) ? (string) $raw_meta['observer_work_id'] : '';
			if ( $marker_may_be_cleared ) {
				return $work_id === $stored_work_id && isset( $raw_meta['_observer_import_generation'] ) && $token === (string) $raw_meta['_observer_import_generation'];
			}

			return '' === $stored_work_id || $work_id === $stored_work_id;
		} catch ( Throwable $error ) {
			return false;
		}
	}

	private static function rollback(array $journal, string $owner_token): bool {
		if ( ! self::rollback_fence( $owner_token ) ) {
			return false;
		}
		$success = true;
		$token = (string) ( $journal['token'] ?? '' );
		if ( '' === $token ) {
			return false;
		}
		$snapshot_ids = array_map( 'intval', array_keys( $journal['snapshots'] ?? array() ) );
		$marker_intents = array();
		$intents_by_work = array();
		$durable_id_proofs = array();
		foreach ( $journal['create_intents'] ?? array() as $intent ) {
			$work_id = (string) ( $intent['work_id'] ?? '' );
			$marker = (string) ( $intent['marker'] ?? '' );
			$work = Registry::work_by_id( $work_id );
			$post_date = (string) ( $intent['post_date'] ?? '' );
			$post_date_gmt = (string) ( $intent['post_date_gmt'] ?? '' );
			$guid = (string) ( $intent['guid'] ?? '' );
			if ( '' === $work_id || null === $work || $marker !== self::row_marker( $token, $work_id ) || isset( $marker_intents[ $marker ] ) || isset( $intents_by_work[ $work_id ] ) || (string) ( $intent['title'] ?? '' ) !== $work['title'] || (string) ( $intent['slug'] ?? '' ) !== $work['slug'] || (int) ( $intent['author_id'] ?? -1 ) < 0 || 1 !== preg_match( '/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/', $post_date ) || 1 !== preg_match( '/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/', $post_date_gmt ) || $guid !== 'urn:observer-research-registry:' . rawurlencode( $work_id ) ) {
				$success = false;
				continue;
			}
			$marker_intents[ $marker ] = $work_id;
			$intents_by_work[ $work_id ] = $intent;
			$assigned_post_id = (int) ( $intent['assigned_post_id'] ?? 0 );
			if ( $assigned_post_id > 0 ) {
				if ( isset( $durable_id_proofs[ $assigned_post_id ] ) ) {
					$success = false;
					continue;
				}
				$durable_id_proofs[ $assigned_post_id ] = $work_id;
			}
		}

		$marker_matches = array_fill_keys( array_keys( $marker_intents ), array() );
		$all_posts = get_posts(
			array(
				'post_type'        => PostType::KEY,
				'post_status'      => array_keys( get_post_stati() ),
				'numberposts'      => -1,
				'orderby'          => 'ID',
				'order'            => 'ASC',
				'suppress_filters' => true,
			)
		);
		foreach ( $all_posts as $post ) {
			$marker = (string) $post->post_content_filtered;
			if ( isset( $marker_matches[ $marker ] ) ) {
				$marker_matches[ $marker ][] = (int) $post->ID;
			}
		}

		$marker_proofs = array();
		foreach ( $marker_matches as $marker => $post_ids ) {
			if ( count( $post_ids ) > 1 ) {
				$success = false;
				continue;
			}
			if ( 1 === count( $post_ids ) ) {
				$marker_proofs[ (int) $post_ids[0] ] = array( 'marker' => $marker, 'work_id' => $marker_intents[ $marker ] );
			}
		}

		$discovered_ids = get_posts(
			array(
				'post_type'       => PostType::KEY,
				'post_status'     => array_keys( get_post_stati() ),
				'numberposts'     => -1,
				'fields'          => 'ids',
				'suppress_filters'=> true,
				'meta_key'        => '_observer_import_generation',
				'meta_value'      => $token,
			)
		);
		$created_ids = array_unique( array_merge( $journal['created_ids'] ?? array(), $discovered_ids, array_keys( $marker_proofs ), array_keys( $durable_id_proofs ) ) );

		foreach ( array_reverse( $created_ids ) as $post_id ) {
			if ( ! self::rollback_fence( $owner_token ) ) {
				return false;
			}
			$post_id = (int) $post_id;
			if ( in_array( $post_id, $snapshot_ids, true ) ) {
				continue;
			}
			if ( null === get_post( $post_id ) ) {
				continue;
			}
			if ( PostType::KEY !== get_post_type( $post_id ) ) {
				$success = false;
				continue;
			}
			$generation_proof = $token === (string) get_post_meta( $post_id, '_observer_import_generation', true );
			$marker_proof = $marker_proofs[ $post_id ] ?? null;
			$durable_work_id = $durable_id_proofs[ $post_id ] ?? null;
			$stored_work_id = (string) get_post_meta( $post_id, 'observer_work_id', true );
			$durable_id_proof = is_string( $durable_work_id ) && $durable_work_id === $stored_work_id;
			if ( is_array( $marker_proof ) ) {
				$post = get_post( $post_id );
				if ( null === $post || (string) $post->post_content_filtered !== $marker_proof['marker'] || ( '' !== $stored_work_id && $stored_work_id !== $marker_proof['work_id'] ) ) {
					$marker_proof = null;
				}
			}
			if ( ! $generation_proof && ! is_array( $marker_proof ) && ! $durable_id_proof ) {
				$success = false;
				continue;
			}
			$expected_work_id = is_array( $marker_proof ) ? (string) $marker_proof['work_id'] : ( is_string( $durable_work_id ) ? $durable_work_id : '' );
			$intent = $intents_by_work[ $expected_work_id ] ?? null;
			if ( ! is_array( $intent ) || ! self::created_post_safe_to_delete( $post_id, $intent, $token, $durable_id_proof ) ) {
				$success = false;
				continue;
			}
			if ( false === wp_delete_post( $post_id, true ) && null !== get_post( $post_id ) ) {
				$success = false;
			}
		}

		foreach ( $journal['snapshots'] ?? array() as $post_id_string => $snapshot ) {
			if ( ! self::rollback_fence( $owner_token ) ) {
				return false;
			}
			$post_id = (int) $post_id_string;
			if ( PostType::KEY !== get_post_type( $post_id ) ) {
				$success = false;
				continue;
			}

			try {
				$updated = MetaSchema::with_internal_post_write(
					static function () use ( $post_id, $snapshot ) {
						return wp_update_post( array( 'ID' => $post_id, 'post_name' => $snapshot['post_name'] ), true );
					}
				);
			} catch ( Throwable $error ) {
				$success = false;
				continue;
			}
			if ( is_wp_error( $updated ) || $post_id !== (int) $updated ) {
				$success = false;
			}

			try {
				MetaSchema::write_internal( $post_id, array_fill_keys( array_merge( Registry::machine_meta_keys(), self::INTERNAL_META ), null ) );
				$restore = array();
				foreach ( $snapshot['meta'] as $key => $entry ) {
					if ( true === $entry['exists'] ) {
						$restore[ $key ] = $entry['value'];
					}
				}
				MetaSchema::write_internal( $post_id, $restore );
			} catch ( Throwable $error ) {
				$success = false;
			}

			$post = get_post( $post_id );
			if ( null === $post || (string) $snapshot['post_name'] !== $post->post_name || ! self::snapshot_meta_matches( $post_id, $snapshot['meta'] ) ) {
				$success = false;
			}
		}

		if ( isset( $journal['previous_state'] ) && ! self::restore_option_snapshot( self::STATE_OPTION, $journal['previous_state'], $owner_token, $journal['pending_state'] ?? null ) ) {
			$success = false;
		}

		return $success && self::rollback_fence( $owner_token );
	}

	private static function rollback_fence(string $owner_token): bool {
		try {
			self::refresh_lock( $owner_token );

			return true;
		} catch ( Throwable $error ) {
			return false;
		}
	}

	private static function acquire_lock(string $token) {
		$now = time();
		$lock = array(
			'token'              => $token,
			'created_at'         => gmdate( 'c', $now ),
			'created_at_epoch'   => $now,
			'heartbeat_at_epoch' => $now,
		);

		if ( self::mysql_advisory_lock_supported() ) {
			$lock['backend'] = 'mysql-advisory';
			$lock['advisory_name'] = self::advisory_lock_name();
			if ( ! self::acquire_mysql_advisory_lock( $lock['advisory_name'] ) ) {
				return new WP_Error( 'observer_registry_locked', 'Another registry operation owns the database advisory lock.' );
			}

			if ( ! self::install_lock_diagnostic( $lock, true ) ) {
				self::release_mysql_advisory_lock( $lock['advisory_name'] );

				return new WP_Error( 'observer_registry_lock_state_failed', 'The database lock was acquired, but its diagnostic state could not be persisted.' );
			}

			return true;
		}

		// SQLite and unknown wpdb backends retain clean-run support through an
		// atomic option mutex. It is deliberately not reclaimed after a crash:
		// without a connection-owned primitive, takeover cannot be fenced safely.
		$lock['backend'] = 'option-fallback';
		if ( self::install_lock_diagnostic( $lock, false ) ) {
			return true;
		}

		return new WP_Error( 'observer_registry_locked', 'Another registry operation owns the fail-closed option lock. This database backend cannot safely reclaim that lock after a crashed request.' );
	}

	private static function acquire_recovery_lock(string $token) {
		return self::acquire_lock( $token );
	}

	private static function mysql_advisory_lock_supported(): bool {
		global $wpdb;

		if ( ! is_object( $wpdb ) || false !== stripos( get_class( $wpdb ), 'sqlite' ) ) {
			return false;
		}

		return ! empty( $wpdb->is_mysql ) && method_exists( $wpdb, 'prepare' ) && method_exists( $wpdb, 'get_var' );
	}

	private static function advisory_lock_name(): string {
		global $wpdb;

		$database = defined( 'DB_NAME' ) ? (string) DB_NAME : '';
		$scope = $database . '|' . (string) ( $wpdb->options ?? '' );

		return self::ADVISORY_LOCK_PREFIX . substr( hash( 'sha256', $scope ), 0, 40 );
	}

	private static function acquire_mysql_advisory_lock(string $name): bool {
		global $wpdb;

		$query = $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $name );

		return 1 === (int) $wpdb->get_var( $query );
	}

	private static function release_mysql_advisory_lock(string $name): void {
		global $wpdb;

		if ( ! self::mysql_advisory_lock_supported() ) {
			return;
		}
		$query = $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $name );
		$wpdb->get_var( $query );
	}

	private static function mysql_advisory_lock_owned(string $name): bool {
		global $wpdb;

		if ( ! self::mysql_advisory_lock_supported() ) {
			return false;
		}
		$query = $wpdb->prepare( 'SELECT IS_USED_LOCK(%s) = CONNECTION_ID()', $name );

		return 1 === (int) $wpdb->get_var( $query );
	}

	private static function install_lock_diagnostic(array $lock, bool $replace_existing): bool {
		$current = get_option( self::LOCK_OPTION, null );
		if ( null === $current ) {
			return add_option( self::LOCK_OPTION, $lock, '', false ) && self::option_matches( self::LOCK_OPTION, $lock );
		}
		if ( ! $replace_existing ) {
			return false;
		}

		return self::compare_and_swap_option( self::LOCK_OPTION, $current, $lock ) && self::option_matches( self::LOCK_OPTION, $lock );
	}

	private static function compare_and_swap_option(string $name, $expected, $replacement): bool {
		global $wpdb;

		if ( ! isset( $wpdb->options ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'query' ) ) {
			return false;
		}

		$query = $wpdb->prepare(
			"UPDATE {$wpdb->options} SET option_value = %s WHERE option_name = %s AND option_value = %s",
			maybe_serialize( $replacement ),
			$name,
			maybe_serialize( $expected )
		);
		if ( 1 !== (int) $wpdb->query( $query ) ) {
			return false;
		}

		self::clean_option_cache( $name );

		return true;
	}

	private static function compare_and_delete_option(string $name, $expected): bool {
		global $wpdb;

		if ( ! isset( $wpdb->options ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'query' ) ) {
			return false;
		}

		$query = $wpdb->prepare(
			"DELETE FROM {$wpdb->options} WHERE option_name = %s AND option_value = %s",
			$name,
			maybe_serialize( $expected )
		);
		if ( 1 !== (int) $wpdb->query( $query ) ) {
			return false;
		}

		self::clean_option_cache( $name );

		return true;
	}

	private static function add_option_fenced(string $name, $value, string $owner_token): bool {
		global $wpdb;

		$lock = get_option( self::LOCK_OPTION, false );
		if ( ! is_array( $lock ) || (string) ( $lock['token'] ?? '' ) !== $owner_token ) {
			return false;
		}
		if ( 'option-fallback' === ( $lock['backend'] ?? '' ) ) {
			return add_option( $name, $value, '', false ) && self::option_matches( $name, $value ) && self::lock_owned_by( $owner_token );
		}
		if ( 'mysql-advisory' !== ( $lock['backend'] ?? '' ) || ! self::mysql_advisory_lock_owned( (string) ( $lock['advisory_name'] ?? '' ) ) || ! isset( $wpdb->options ) || ! method_exists( $wpdb, 'query' ) ) {
			return false;
		}

		$query = $wpdb->prepare(
			"INSERT IGNORE INTO {$wpdb->options} (option_name, option_value, autoload) SELECT %s, %s, 'no' WHERE IS_USED_LOCK(%s) = CONNECTION_ID()",
			$name,
			maybe_serialize( $value ),
			(string) $lock['advisory_name']
		);
		if ( 1 !== (int) $wpdb->query( $query ) ) {
			return false;
		}
		self::clean_option_cache( $name );

		return self::option_matches( $name, $value ) && self::lock_owned_by( $owner_token );
	}

	private static function compare_and_swap_option_fenced(string $name, $expected, $replacement, string $owner_token): bool {
		global $wpdb;

		$lock = get_option( self::LOCK_OPTION, false );
		if ( ! is_array( $lock ) || (string) ( $lock['token'] ?? '' ) !== $owner_token ) {
			return false;
		}
		if ( 'option-fallback' === ( $lock['backend'] ?? '' ) ) {
			return self::compare_and_swap_option( $name, $expected, $replacement ) && self::lock_owned_by( $owner_token );
		}
		if ( 'mysql-advisory' !== ( $lock['backend'] ?? '' ) || ! isset( $wpdb->options ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'query' ) ) {
			return false;
		}

		$query = $wpdb->prepare(
			"UPDATE {$wpdb->options} SET option_value = %s WHERE option_name = %s AND option_value = %s AND IS_USED_LOCK(%s) = CONNECTION_ID()",
			maybe_serialize( $replacement ),
			$name,
			maybe_serialize( $expected ),
			(string) ( $lock['advisory_name'] ?? '' )
		);
		if ( 1 !== (int) $wpdb->query( $query ) ) {
			return false;
		}
		self::clean_option_cache( $name );

		return self::option_matches( $name, $replacement ) && self::lock_owned_by( $owner_token );
	}

	private static function compare_and_delete_option_fenced(string $name, $expected, string $owner_token): bool {
		global $wpdb;

		$lock = get_option( self::LOCK_OPTION, false );
		if ( ! is_array( $lock ) || (string) ( $lock['token'] ?? '' ) !== $owner_token ) {
			return false;
		}
		if ( 'option-fallback' === ( $lock['backend'] ?? '' ) ) {
			return self::compare_and_delete_option( $name, $expected ) && self::lock_owned_by( $owner_token );
		}
		if ( 'mysql-advisory' !== ( $lock['backend'] ?? '' ) || ! isset( $wpdb->options ) || ! method_exists( $wpdb, 'prepare' ) || ! method_exists( $wpdb, 'query' ) ) {
			return false;
		}

		$query = $wpdb->prepare(
			"DELETE FROM {$wpdb->options} WHERE option_name = %s AND option_value = %s AND IS_USED_LOCK(%s) = CONNECTION_ID()",
			$name,
			maybe_serialize( $expected ),
			(string) ( $lock['advisory_name'] ?? '' )
		);
		if ( 1 !== (int) $wpdb->query( $query ) ) {
			return false;
		}
		self::clean_option_cache( $name );

		return null === get_option( $name, null ) && self::lock_owned_by( $owner_token );
	}

	private static function clean_option_cache(string $name): void {
		wp_cache_delete( $name, 'options' );

		wp_cache_delete( 'alloptions', 'options' );
		wp_cache_delete( 'notoptions', 'options' );
	}

	private static function refresh_lock(string $token): void {
		$lock = get_option( self::LOCK_OPTION, false );
		if ( ! is_array( $lock ) || (string) ( $lock['token'] ?? '' ) !== $token ) {
			throw new RuntimeException( 'The registry operation no longer owns the import lock.' );
		}
		if ( 'mysql-advisory' === ( $lock['backend'] ?? '' ) && ! self::mysql_advisory_lock_owned( (string) ( $lock['advisory_name'] ?? '' ) ) ) {
			throw new RuntimeException( 'The registry operation no longer owns the database advisory lock.' );
		}
		if ( 'option-fallback' === ( $lock['backend'] ?? '' ) ) {
			return;
		}
		if ( 'mysql-advisory' !== ( $lock['backend'] ?? '' ) ) {
			throw new RuntimeException( 'The registry import lock uses an unknown backend.' );
		}

		$replacement = $lock;
		$replacement['heartbeat_at_epoch'] = time();
		$replacement['heartbeat_sequence'] = (int) ( $lock['heartbeat_sequence'] ?? 0 ) + 1;
		if ( ! self::compare_and_swap_option_fenced( self::LOCK_OPTION, $lock, $replacement, $token ) || ! self::option_matches( self::LOCK_OPTION, $replacement ) || ! self::mysql_advisory_lock_owned( (string) $replacement['advisory_name'] ) ) {
			throw new RuntimeException( 'The registry operation could not fence its diagnostic lock state.' );
		}
	}

	private static function lock_owned_by(string $token): bool {
		$lock = get_option( self::LOCK_OPTION, false );

		if ( ! is_array( $lock ) || (string) ( $lock['token'] ?? '' ) !== $token ) {
			return false;
		}
		if ( 'mysql-advisory' === ( $lock['backend'] ?? '' ) ) {
			return self::mysql_advisory_lock_owned( (string) ( $lock['advisory_name'] ?? '' ) );
		}

		return 'option-fallback' === ( $lock['backend'] ?? '' );
	}

	private static function release_lock(string $token): void {
		$lock = get_option( self::LOCK_OPTION, false );
		if ( is_array( $lock ) && (string) ( $lock['token'] ?? '' ) === $token ) {
			self::compare_and_delete_option( self::LOCK_OPTION, $lock );
		}
		if ( self::mysql_advisory_lock_supported() ) {
			self::release_mysql_advisory_lock( self::advisory_lock_name() );
		}
	}

	private static function persist_journal_transition(array $expected, array $replacement, string $owner_token): void {
		if ( (string) ( $expected['token'] ?? '' ) !== $owner_token || (string) ( $replacement['token'] ?? '' ) !== $owner_token ) {
			throw new RuntimeException( 'Import journal transition token mismatch.' );
		}

		self::refresh_lock( $owner_token );
		if ( ! self::compare_and_swap_option_fenced( self::JOURNAL_OPTION, $expected, $replacement, $owner_token ) || ! self::option_matches( self::JOURNAL_OPTION, $replacement ) ) {
			throw new RuntimeException( 'Unable to persist a fenced import journal transition.' );
		}
		self::refresh_lock( $owner_token );
	}

	private static function delete_journal_checked(array $journal, string $owner_token): void {
		$current = get_option( self::JOURNAL_OPTION, null );
		if ( ! is_array( $current ) || $current !== $journal || '' === (string) ( $journal['token'] ?? '' ) ) {
			throw new RuntimeException( 'The import journal changed ownership before deletion.' );
		}

		self::refresh_lock( $owner_token );
		if ( ! self::compare_and_delete_option_fenced( self::JOURNAL_OPTION, $journal, $owner_token ) || null !== get_option( self::JOURNAL_OPTION, null ) ) {
			throw new RuntimeException( 'Unable to remove the exact fenced import journal.' );
		}
		self::refresh_lock( $owner_token );
	}

	private static function commit_state(array $previous_state, array $state, string $owner_token): void {
		self::refresh_lock( $owner_token );
		$current = get_option( self::STATE_OPTION, null );
		if ( true === ( $previous_state['exists'] ?? false ) ) {
			$expected = $previous_state['value'] ?? null;
			if ( $expected !== $current ) {
				throw new RuntimeException( 'Registry state changed after the import journal snapshot.' );
			}
			if ( $state !== $expected && ! self::compare_and_swap_option_fenced( self::STATE_OPTION, $expected, $state, $owner_token ) ) {
				throw new RuntimeException( 'Unable to commit registry state with compare-and-swap.' );
			}
		} else {
			if ( null !== $current || ! self::add_option_fenced( self::STATE_OPTION, $state, $owner_token ) ) {
				throw new RuntimeException( 'Unable to commit registry state with add-only semantics.' );
			}
		}
		if ( ! self::option_matches( self::STATE_OPTION, $state ) ) {
			throw new RuntimeException( 'Committed registry state failed read-back verification.' );
		}
		self::refresh_lock( $owner_token );
	}

	private static function option_matches(string $name, $expected): bool {
		return $expected === get_option( $name, null );
	}

	private static function snapshot_option(string $name): array {
		$value = get_option( $name, null );

		return array( 'exists' => null !== $value, 'value' => $value );
	}

	private static function restore_option_snapshot(string $name, array $snapshot, string $owner_token, $allowed_committed_value = null): bool {
		try {
			self::refresh_lock( $owner_token );
			$current = get_option( $name, null );
			if ( true === ( $snapshot['exists'] ?? false ) ) {
				$expected = $snapshot['value'] ?? null;
				if ( $current !== $expected ) {
					if ( null === $allowed_committed_value || $current !== $allowed_committed_value || ! self::compare_and_swap_option_fenced( $name, $current, $expected, $owner_token ) ) {
						return false;
					}
				}
				self::refresh_lock( $owner_token );

				return self::option_matches( $name, $expected );
			}

			if ( null !== $current ) {
				if ( null === $allowed_committed_value || $current !== $allowed_committed_value || ! self::compare_and_delete_option_fenced( $name, $current, $owner_token ) ) {
					return false;
				}
			}
			self::refresh_lock( $owner_token );

			return null === get_option( $name, null );
		} catch ( Throwable $error ) {
			return false;
		}
	}

	private static function snapshot_meta_matches(int $post_id, array $snapshot): bool {
		foreach ( $snapshot as $key => $entry ) {
			$expected_exists = true === ( $entry['exists'] ?? false );
			$exists = metadata_exists( 'post', $post_id, (string) $key );
			if ( $expected_exists !== $exists ) {
				return false;
			}
			if ( $exists && self::canonical_compare( $entry['value'] ?? null ) !== self::canonical_compare( get_post_meta( $post_id, (string) $key, true ) ) ) {
				return false;
			}
		}

		return true;
	}

	private static function token(): string {
		if ( function_exists( 'wp_generate_uuid4' ) ) {
			return wp_generate_uuid4();
		}

		return bin2hex( random_bytes( 16 ) );
	}

	private static function encode_record(array $work): string {
		$encoded = json_encode( $work, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
		if ( false === $encoded ) {
			throw new RuntimeException( 'Unable to encode a canonical registry record.' );
		}

		return $encoded;
	}

	private static function canonical_compare($value): string {
		$encoded = json_encode( $value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );

		return false === $encoded ? '' : $encoded;
	}
}
