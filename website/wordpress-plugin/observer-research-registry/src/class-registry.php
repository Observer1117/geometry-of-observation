<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

use RuntimeException;

final class Registry {
	private const INDEX_SCHEMA = 'observer-research-index';
	private const INDEX_VERSION = '1.0.0';
	private const MODEL_SCHEMA = 'observer-wordpress-data-model';
	private const MODEL_VERSION = '1.0.0';

	private static $index;
	private static $model;

	public static function index(): array {
		if ( null === self::$index ) {
			self::verify_manifest();
			self::$index = self::load_json( self::index_path() );
			self::validate_index( self::$index );
		}

		return self::$index;
	}

	public static function model(): array {
		if ( null === self::$model ) {
			self::verify_manifest();
			self::$model = self::load_json( self::model_path() );
			self::validate_model( self::$model );
		}

		return self::$model;
	}

	public static function reset_cache(): void {
		self::$index = null;
		self::$model = null;
	}

	public static function index_path(): string {
		return OBSERVER_RESEARCH_REGISTRY_DIR . 'data/research_index.json';
	}

	public static function model_path(): string {
		return OBSERVER_RESEARCH_REGISTRY_DIR . 'data/wordpress_data_model.json';
	}

	public static function manifest_path(): string {
		return OBSERVER_RESEARCH_REGISTRY_DIR . 'data/manifest.json';
	}

	public static function digest(): string {
		$digest = hash_file( 'sha256', self::index_path() );

		if ( false === $digest ) {
			throw new RuntimeException( 'Unable to hash bundled research registry.' );
		}

		return $digest;
	}

	public static function ordered_works(?array $index = null): array {
		$index = $index ?? self::index();
		$works = $index['works'];
		usort(
			$works,
			static function ( array $left, array $right ): int {
				return $left['priority'] <=> $right['priority'];
			}
		);

		return $works;
	}

	public static function work_by_id(string $work_id, ?array $index = null): ?array {
		foreach ( self::ordered_works( $index ) as $work ) {
			if ( $work['id'] === $work_id ) {
				return $work;
			}
		}

		return null;
	}

	public static function machine_meta_keys(?array $model = null): array {
		$model = $model ?? self::model();

		return array_map(
			static function ( array $field ): string {
				return $field['key'];
			},
			$model['machine_meta']
		);
	}

	public static function meta_for_work(array $work): array {
		return array(
			'observer_work_id'                 => $work['id'],
			'observer_metadata_record_version' => $work['metadata_record_version'],
			'observer_citation_version'        => $work['citation_version'],
			'observer_release_tag'             => $work['release_tag'] ?? null,
			'observer_resource_type'           => $work['resource_type'],
			'observer_release_status'          => $work['release_status'],
			'observer_review_status'           => $work['review_status'],
			'observer_doi'                     => $work['doi'] ?? null,
			'observer_doi_scope'               => $work['doi_scope'] ?? null,
			'observer_osf_registration_url'    => $work['osf_registration_url'] ?? null,
			'observer_repository_url'          => $work['repository_url'],
			'observer_github_release_url'      => $work['github_release_url'] ?? null,
			'observer_display_date'            => $work['display_date'],
			'observer_display_date_meaning'    => $work['display_date_meaning'],
			'observer_license_scope'           => $work['license_scope'],
			'observer_claim_boundary_path'     => $work['claim_boundary_path'] ?? null,
			'observer_reproducibility_path'    => $work['reproducibility_path'] ?? null,
			'observer_companion_work_ids'      => $work['companion_work_ids'] ?? array(),
			'observer_schema_primary_type'     => $work['jsonld_profile']['primary_type'],
			'observer_source_repository'       => $work['source_contract']['repository'],
			'observer_source_contract_path'    => $work['source_contract']['path'],
			'observer_source_commit'           => $work['source_contract']['merge_commit'],
		);
	}

	public static function canonical_url(array $work, string $site_base): string {
		return rtrim( $site_base, '/' ) . $work['site_path'];
	}

	public static function source_file_url(array $work, ?string $path): ?string {
		if ( null === $path || '' === $path ) {
			return null;
		}

		$segments = array_map( 'rawurlencode', explode( '/', $path ) );

		return sprintf(
			'https://github.com/%s/blob/%s/%s',
			$work['source_contract']['repository'],
			$work['source_contract']['merge_commit'],
			implode( '/', $segments )
		);
	}

	public static function validate_index(array $index): void {
		$errors = array();
		$schema = $index['schema'] ?? array();

		if ( self::INDEX_SCHEMA !== ( $schema['name'] ?? null ) || self::INDEX_VERSION !== ( $schema['version'] ?? null ) ) {
			$errors[] = 'Unsupported research index schema.';
		}

		if ( 'Stassis Stashkevichyus' !== ( $index['authority']['display_name'] ?? null ) ) {
			$errors[] = 'Author authority mismatch.';
		}

		if ( true === ( $index['project']['author_entity'] ?? true ) ) {
			$errors[] = 'The project must not be represented as a scholarly author.';
		}

		$works = $index['works'] ?? null;
		if ( ! is_array( $works ) || 5 !== count( $works ) ) {
			$errors[] = 'P1.6 requires exactly five registry works.';
			self::fail_if_errors( $errors );
			return;
		}

		$ids = array();
		$slugs = array();
		$paths = array();
		$priorities = array();
		$allowed_release = array( 'public-research-corpus', 'metadata-successor-of-frozen-preprint', 'preprint', 'release-candidate' );
		$allowed_review = array( 'not-peer-reviewed', 'independent-specialist-review-pending' );
		$allowed_types = array( 'Dataset', 'ScholarlyArticle' );
		$allowed_resources = array( 'research-corpus', 'expository-preprint', 'mathematical-biology-preprint', 'external-validation-preprint', 'specialized-quantitative-note-release-candidate' );

		foreach ( $works as $work ) {
			$id = $work['id'] ?? '';
			$slug = $work['slug'] ?? '';
			$path = $work['site_path'] ?? '';
			$priority = $work['priority'] ?? null;
			$source_repository = $work['source_contract']['repository'] ?? '';

			if ( ! is_string( $id ) || 1 !== preg_match( '/^[A-Za-z0-9.-]+$/', $id ) ) {
				$errors[] = 'Invalid work ID.';
			}
			foreach ( array( 'title', 'short_title', 'metadata_record_version', 'citation_version', 'display_date_meaning' ) as $required_text ) {
				if ( ! self::bounded_text( $work[ $required_text ] ?? null, 1, 'title' === $required_text ? 500 : 250 ) ) {
					$errors[] = 'Invalid ' . $required_text . ' for ' . $id . '.';
				}
			}
			if ( ! is_string( $slug ) || 1 !== preg_match( '/^[a-z0-9]+(?:-[a-z0-9]+)*$/', $slug ) ) {
				$errors[] = 'Invalid canonical slug for ' . $id . '.';
			}
			if ( '/research/' . $slug . '/' !== $path ) {
				$errors[] = 'Canonical path mismatch for ' . $id . '.';
			}
			if ( ! in_array( $work['release_status'] ?? null, $allowed_release, true ) ) {
				$errors[] = 'Unknown release status for ' . $id . '.';
			}
			if ( ! in_array( $work['review_status'] ?? null, $allowed_review, true ) ) {
				$errors[] = 'Unknown review status for ' . $id . '.';
			}
			if ( ! in_array( $work['jsonld_profile']['primary_type'] ?? null, $allowed_types, true ) ) {
				$errors[] = 'Unknown primary schema type for ' . $id . '.';
			}
			if ( ! in_array( $work['resource_type'] ?? null, $allowed_resources, true ) ) {
				$errors[] = 'Unknown resource type for ' . $id . '.';
			}
			if ( ! self::valid_date( $work['display_date'] ?? '' ) ) {
				$errors[] = 'Invalid display date for ' . $id . '.';
			}
			if ( 1 !== preg_match( '/^Observer1117\/[a-z0-9-]+$/', $source_repository ) ) {
				$errors[] = 'Invalid source repository for ' . $id . '.';
			}
			if ( 'https://github.com/' . $source_repository !== ( $work['repository_url'] ?? '' ) ) {
				$errors[] = 'Invalid repository URL for ' . $id . '.';
			}
			if ( 1 !== preg_match( '/^[a-f0-9]{40}$/', $work['source_contract']['merge_commit'] ?? '' ) ) {
				$errors[] = 'Invalid pinned source commit for ' . $id . '.';
			}
			if ( ! self::safe_repository_path( $work['source_contract']['path'] ?? '' ) ) {
				$errors[] = 'Unsafe source-contract path for ' . $id . '.';
			}
			if ( null !== ( $work['doi'] ?? null ) && 1 !== preg_match( '/^10\.17605\/OSF\.IO\/[A-Z0-9]+$/', $work['doi'] ) ) {
				$errors[] = 'Invalid DOI for ' . $id . '.';
			}
			if ( ( null === ( $work['doi'] ?? null ) ) !== ( null === ( $work['doi_scope'] ?? null ) ) ) {
				$errors[] = 'DOI and DOI scope must be jointly present or absent for ' . $id . '.';
			}
			if ( null !== ( $work['osf_registration_url'] ?? null ) && 1 !== preg_match( '#^https://osf\.io/[a-z0-9]+/$#', $work['osf_registration_url'] ) ) {
				$errors[] = 'Invalid OSF registration URL for ' . $id . '.';
			}
			if ( null !== ( $work['github_release_url'] ?? null ) && 0 !== strpos( $work['github_release_url'], 'https://github.com/' . $source_repository . '/releases/tag/' ) ) {
				$errors[] = 'Invalid GitHub release URL for ' . $id . '.';
			}
			if ( ! is_array( $work['license_scope'] ?? null ) || array() === $work['license_scope'] ) {
				$errors[] = 'Missing license scope for ' . $id . '.';
			} else {
				foreach ( $work['license_scope'] as $license ) {
					if ( ! self::bounded_text( $license['scope'] ?? null, 1, 160 ) || ! self::bounded_text( $license['license'] ?? null, 1, 100 ) ) {
						$errors[] = 'Invalid license scope for ' . $id . '.';
					}
				}
			}
			foreach ( array( 'claim_boundary_path', 'reproducibility_path' ) as $path_key ) {
				if ( isset( $work[ $path_key ] ) && ! self::safe_repository_path( $work[ $path_key ] ) ) {
					$errors[] = 'Unsafe repository path for ' . $id . ': ' . $path_key . '.';
				}
			}

			$ids[] = $id;
			$slugs[] = $slug;
			$paths[] = $path;
			$priorities[] = $priority;
		}

		if ( count( array_unique( $ids ) ) !== count( $ids ) ) {
			$errors[] = 'Duplicate work ID.';
		}
		if ( count( array_unique( $slugs ) ) !== count( $slugs ) ) {
			$errors[] = 'Duplicate canonical slug.';
		}
		if ( count( array_unique( $paths ) ) !== count( $paths ) ) {
			$errors[] = 'Duplicate canonical path.';
		}
		sort( $priorities );
		if ( array( 1, 2, 3, 4, 5 ) !== $priorities ) {
			$errors[] = 'Priorities must be exactly 1 through 5.';
		}

		foreach ( $works as $work ) {
			foreach ( $work['companion_work_ids'] ?? array() as $companion_id ) {
				$companion = self::work_by_id( $companion_id, $index );
				if ( null === $companion || $companion_id === $work['id'] ) {
					$errors[] = 'Dangling or self companion relation for ' . $work['id'] . '.';
					continue;
				}
				if ( ! in_array( $work['id'], $companion['companion_work_ids'] ?? array(), true ) ) {
					$errors[] = 'Asymmetric companion relation for ' . $work['id'] . '.';
				}
			}
		}

		$qmd = self::work_by_id( 'QMD-2.0-rc2', $index );
		if ( null === $qmd || null !== ( $qmd['doi'] ?? null ) || null !== ( $qmd['github_release_url'] ?? null ) || 'G2-not-passed' !== ( $qmd['novelty_gate'] ?? null ) || 'G6-not-passed' !== ( $qmd['independent_verification_gate'] ?? null ) ) {
			$errors[] = 'QMD release-gate invariant failed.';
		}

		$crse = self::work_by_id( 'CRSE-0.2', $index );
		if ( null === $crse || '0.2.1' !== ( $crse['metadata_record_version'] ?? null ) || '0.2' !== ( $crse['citation_version'] ?? null ) ) {
			$errors[] = 'CRSE metadata/citation version invariant failed.';
		}

		self::fail_if_errors( $errors );
	}

	public static function validate_model(array $model): void {
		$schema = $model['schema'] ?? array();
		if ( self::MODEL_SCHEMA !== ( $schema['name'] ?? null ) || self::MODEL_VERSION !== ( $schema['version'] ?? null ) ) {
			throw new RuntimeException( 'Unsupported WordPress data-model schema.' );
		}

		$cpt = $model['custom_post_type'] ?? array();
		if ( 'research_output' !== ( $cpt['key'] ?? null ) || true !== ( $cpt['show_in_rest'] ?? false ) || 'research' !== ( $cpt['rest_base'] ?? null ) || ! in_array( 'custom-fields', $cpt['supports'] ?? array(), true ) ) {
			throw new RuntimeException( 'WordPress custom-post-type contract mismatch.' );
		}

		$expected = array_keys( self::meta_for_work( self::ordered_works()[0] ) );
		$actual = self::machine_meta_keys( $model );
		sort( $expected );
		sort( $actual );
		if ( $expected !== $actual ) {
			throw new RuntimeException( 'Machine-meta keys do not match the P1.5 contract.' );
		}
	}

	private static function verify_manifest(): void {
		$manifest = self::load_json( self::manifest_path() );
		if ( OBSERVER_RESEARCH_REGISTRY_VERSION !== ( $manifest['plugin_version'] ?? null ) ) {
			throw new RuntimeException( 'Registry manifest plugin-version mismatch.' );
		}
		if ( 'Observer1117/geometry-of-observation' !== ( $manifest['source_repository'] ?? null ) || 'bab4480e50f8abe32087da765a145575a4519f8a' !== ( $manifest['source_commit'] ?? null ) ) {
			throw new RuntimeException( 'Registry manifest source pin mismatch.' );
		}
		if ( array( 'name' => self::INDEX_SCHEMA, 'version' => self::INDEX_VERSION ) !== ( $manifest['registry_schema'] ?? null ) ) {
			throw new RuntimeException( 'Registry manifest schema pin mismatch.' );
		}

		$files = array(
			'research_index.json'       => self::index_path(),
			'wordpress_data_model.json' => self::model_path(),
		);

		foreach ( $files as $name => $path ) {
			$expected = $manifest['files'][ $name ]['sha256'] ?? '';
			$actual = hash_file( 'sha256', $path );
			if ( ! is_string( $actual ) || ! hash_equals( $expected, $actual ) ) {
				throw new RuntimeException( 'Bundled registry hash mismatch: ' . $name . '.' );
			}
		}
	}

	private static function load_json(string $path): array {
		if ( ! is_readable( $path ) || filesize( $path ) > 1048576 ) {
			throw new RuntimeException( 'Registry file is missing, unreadable, or oversized: ' . basename( $path ) . '.' );
		}

		$raw = file_get_contents( $path );
		if ( false === $raw ) {
			throw new RuntimeException( 'Unable to read registry file: ' . basename( $path ) . '.' );
		}

		$data = json_decode( $raw, true, 64 );
		if ( JSON_ERROR_NONE !== json_last_error() || ! is_array( $data ) ) {
			throw new RuntimeException( 'Invalid JSON in registry file: ' . basename( $path ) . '.' );
		}

		return $data;
	}

	private static function safe_repository_path(string $path): bool {
		return '' !== $path
			&& '/' !== $path[0]
			&& false === strpos( $path, '..' )
			&& false === strpbrk( $path, "\0\r\n?#\\" )
			&& 1 === preg_match( '/^[A-Za-z0-9._\/-]+$/', $path );
	}

	private static function valid_date(string $date): bool {
		if ( 1 !== preg_match( '/^\d{4}-\d{2}-\d{2}$/', $date ) ) {
			return false;
		}
		list( $year, $month, $day ) = array_map( 'intval', explode( '-', $date ) );

		return checkdate( $month, $day, $year );
	}

	private static function https_url(string $url): bool {
		return 0 === strpos( $url, 'https://' ) && false !== filter_var( $url, FILTER_VALIDATE_URL );
	}

	private static function bounded_text($value, int $minimum, int $maximum): bool {
		if ( ! is_string( $value ) || strlen( $value ) < $minimum || strlen( $value ) > $maximum ) {
			return false;
		}

		return 1 !== preg_match( '/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/', $value );
	}

	private static function fail_if_errors(array $errors): void {
		if ( $errors ) {
			throw new RuntimeException( implode( ' ', array_unique( $errors ) ) );
		}
	}
}
