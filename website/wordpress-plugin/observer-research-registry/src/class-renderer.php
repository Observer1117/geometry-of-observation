<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class Renderer {
	public static function enqueue_assets(): void {
		if ( is_post_type_archive( PostType::KEY ) || is_singular( PostType::KEY ) ) {
			wp_enqueue_style(
				'observer-research-registry',
				OBSERVER_RESEARCH_REGISTRY_URL . 'assets/registry.css',
				array(),
				OBSERVER_RESEARCH_REGISTRY_VERSION
			);
		}
	}

	public static function archive_html(): string {
		$cards = array();
		foreach ( Registry::ordered_works() as $work ) {
			$post_id = Importer::post_id_for_work( $work['id'] );
			if ( null === $post_id || 'publish' !== get_post_status( $post_id ) ) {
				continue;
			}
			$cards[] = self::card( $work, $post_id );
		}

		if ( ! $cards ) {
			return '<p class="observer-registry-empty">' . esc_html__( 'No research outputs are public yet.', 'observer-research-registry' ) . '</p>';
		}

		return '<div class="observer-research-grid">' . implode( '', $cards ) . '</div>';
	}

	public static function single_html(int $post_id): string {
		$work = self::work_for_post( $post_id );
		if ( null === $work ) {
			return '<p>' . esc_html__( 'This page is not linked to a valid research-registry record.', 'observer-research-registry' ) . '</p>';
		}

		$html = self::badges_html( $work );
		$html .= '<dl class="observer-research-facts">';
		$html .= self::fact( 'Version', $work['citation_version'] );
		$html .= self::fact( 'Release status', self::humanize( $work['release_status'] ) );
		$html .= self::fact( 'Review status', self::humanize( $work['review_status'] ) );
		$html .= self::fact( 'Display date', $work['display_date'] );
		if ( null !== ( $work['doi'] ?? null ) ) {
			$html .= self::fact( 'DOI scope', $work['doi_scope'] );
		}
		$html .= '</dl>';

		$html .= '<section class="observer-research-resources"><h2>' . esc_html__( 'Research objects and evidence', 'observer-research-registry' ) . '</h2><ul>';
		foreach ( Links::resources( $work ) as $link ) {
			$html .= '<li><a href="' . esc_url( $link['url'] ) . '" rel="noopener noreferrer">' . esc_html( $link['label'] ) . '</a></li>';
		}
		$html .= '</ul></section>';

		$html .= self::licenses_html( $work );
		$html .= self::companions_html( $work );
		$html .= '<p class="observer-registry-provenance">' . esc_html(
			sprintf(
				/* translators: 1: repository, 2: commit SHA. */
				__( 'Scientific metadata source: %1$s at commit %2$s.', 'observer-research-registry' ),
				$work['source_contract']['repository'],
				$work['source_contract']['merge_commit']
			)
		) . '</p>';

		return $html;
	}

	public static function emit_json_ld(): void {
		if ( is_admin() || is_feed() || wp_doing_ajax() ) {
			return;
		}

		$index = Registry::index();
		$site_base = home_url( '/' );
		$document = null;

		if ( is_post_type_archive( PostType::KEY ) ) {
			$visible = array();
			foreach ( Registry::ordered_works( $index ) as $work ) {
				$post_id = Importer::post_id_for_work( $work['id'] );
				if ( null !== $post_id && 'publish' === get_post_status( $post_id ) ) {
					$visible[] = $work['id'];
				}
			}
			$document = JsonLd::archive( $index, $site_base, $visible );
		} elseif ( is_singular( PostType::KEY ) ) {
			$work = self::work_for_post( (int) get_queried_object_id() );
			if ( null !== $work && 'publish' === get_post_status( get_queried_object_id() ) ) {
				$document = JsonLd::single( $work, $index, $site_base );
			}
		}

		if ( null === $document ) {
			return;
		}

		$document = apply_filters( 'observer_research_registry_json_ld', $document );
		if ( ! is_array( $document ) ) {
			return;
		}

		$flags = JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE;
		$json = wp_json_encode( $document, $flags );
		if ( false !== $json ) {
			echo "\n<script type=\"application/ld+json\">" . $json . "</script>\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON_HEX flags make the script context safe.
		}
	}

	private static function card(array $work, int $post_id): string {
		$excerpt = get_the_excerpt( $post_id );
		$html = '<article class="observer-research-card">';
		$html .= self::badges_html( $work );
		$html .= '<h2><a href="' . esc_url( get_permalink( $post_id ) ) . '">' . esc_html( $work['short_title'] ) . '</a></h2>';
		$html .= '<p class="observer-research-version">' . esc_html( 'v' . $work['citation_version'] . ' · ' . $work['display_date'] ) . '</p>';
		if ( '' !== $excerpt ) {
			$html .= '<p>' . esc_html( $excerpt ) . '</p>';
		}
		$html .= '</article>';

		return $html;
	}

	private static function badges_html(array $work): string {
		$html = '<ul class="observer-research-badges" aria-label="' . esc_attr__( 'Publication status', 'observer-research-registry' ) . '">';
		foreach ( Badges::for_work( $work ) as $badge ) {
			$html .= '<li class="observer-badge observer-badge--' . esc_attr( $badge['tone'] ) . '">' . esc_html( $badge['label'] ) . '</li>';
		}
		$html .= '</ul>';

		return $html;
	}

	private static function licenses_html(array $work): string {
		$html = '<section class="observer-license-map"><h2>' . esc_html__( 'License map', 'observer-research-registry' ) . '</h2><table><thead><tr><th>' . esc_html__( 'Scope', 'observer-research-registry' ) . '</th><th>' . esc_html__( 'License', 'observer-research-registry' ) . '</th></tr></thead><tbody>';
		foreach ( $work['license_scope'] as $license ) {
			$html .= '<tr><td>' . esc_html( self::humanize( $license['scope'] ) ) . '</td><td>' . esc_html( $license['license'] ) . '</td></tr>';
		}
		$html .= '</tbody></table></section>';

		return $html;
	}

	private static function companions_html(array $work): string {
		$items = array();
		foreach ( Links::companions( $work ) as $companion ) {
			$post_id = Importer::post_id_for_work( $companion['id'] );
			if ( null !== $post_id && 'publish' === get_post_status( $post_id ) ) {
				$items[] = '<li><a href="' . esc_url( get_permalink( $post_id ) ) . '">' . esc_html( $companion['short_title'] ) . '</a></li>';
			}
		}

		if ( ! $items ) {
			return '';
		}

		return '<section class="observer-companions"><h2>' . esc_html__( 'Companion work', 'observer-research-registry' ) . '</h2><ul>' . implode( '', $items ) . '</ul></section>';
	}

	private static function fact(string $label, string $value): string {
		return '<div><dt>' . esc_html( $label ) . '</dt><dd>' . esc_html( $value ) . '</dd></div>';
	}

	private static function humanize(string $value): string {
		return ucwords( str_replace( '-', ' ', $value ) );
	}

	private static function work_for_post(int $post_id): ?array {
		$work_id = (string) get_post_meta( $post_id, 'observer_work_id', true );

		return Registry::work_by_id( $work_id );
	}
}

