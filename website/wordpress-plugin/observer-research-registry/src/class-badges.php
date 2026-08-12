<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class Badges {
	public static function for_work(array $work): array {
		$badges = array();

		if ( 'not-peer-reviewed' === $work['review_status'] || 'independent-specialist-review-pending' === $work['review_status'] ) {
			$badges[] = self::badge( 'not-peer-reviewed', 'Not peer reviewed', 'warning' );
		}
		if ( 'independent-specialist-review-pending' === $work['review_status'] ) {
			$badges[] = self::badge( 'specialist-review-pending', 'Independent specialist review pending', 'warning' );
		}
		if ( 'release-candidate' === $work['release_status'] ) {
			$badges[] = self::badge( 'release-candidate', 'Release candidate', 'warning' );
		}
		if ( 'negative-benchmark' === ( $work['result_class'] ?? null ) ) {
			$badges[] = self::badge( 'negative-result', 'Negative result', 'neutral' );
		}
		if ( null !== ( $work['doi'] ?? null ) ) {
			$badges[] = self::badge( 'doi', 'DOI', 'identifier' );
		}
		if ( 'G2-not-passed' === ( $work['novelty_gate'] ?? null ) ) {
			$badges[] = self::badge( 'g2-open', 'G2 novelty gate open', 'warning' );
		}
		if ( 'G6-not-passed' === ( $work['independent_verification_gate'] ?? null ) ) {
			$badges[] = self::badge( 'g6-open', 'G6 verification gate open', 'warning' );
		}

		return $badges;
	}

	private static function badge(string $code, string $label, string $tone): array {
		return array(
			'code'  => $code,
			'label' => $label,
			'tone'  => $tone,
		);
	}
}

