<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class Links {
	public static function resources(array $work): array {
		$links = array(
			array( 'label' => 'Source repository', 'url' => $work['repository_url'] ),
		);

		if ( null !== ( $work['doi'] ?? null ) ) {
			$links[] = array( 'label' => 'DOI record', 'url' => 'https://doi.org/' . $work['doi'] );
		}
		if ( null !== ( $work['osf_registration_url'] ?? null ) ) {
			$links[] = array( 'label' => 'OSF registration', 'url' => $work['osf_registration_url'] );
		}
		if ( null !== ( $work['github_release_url'] ?? null ) ) {
			$links[] = array( 'label' => 'GitHub release', 'url' => $work['github_release_url'] );
		}

		$claim_url = Registry::source_file_url( $work, $work['claim_boundary_path'] ?? null );
		if ( null !== $claim_url ) {
			$links[] = array( 'label' => 'Claim boundaries', 'url' => $claim_url );
		}

		$reproducibility_url = Registry::source_file_url( $work, $work['reproducibility_path'] ?? null );
		if ( null !== $reproducibility_url ) {
			$links[] = array( 'label' => 'Reproducibility evidence', 'url' => $reproducibility_url );
		}

		return $links;
	}

	public static function companions(array $work, ?array $index = null): array {
		$companions = array();
		foreach ( $work['companion_work_ids'] ?? array() as $companion_id ) {
			$companion = Registry::work_by_id( $companion_id, $index );
			if ( null !== $companion ) {
				$companions[] = $companion;
			}
		}

		return $companions;
	}
}

