<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class JsonLd {
	public static function archive(array $index, string $site_base, array $visible_work_ids): array {
		$graph = self::global_nodes( $index, $site_base );
		$works = array_values(
			array_filter(
				Registry::ordered_works( $index ),
				static function ( array $work ) use ( $visible_work_ids ): bool {
					return in_array( $work['id'], $visible_work_ids, true );
				}
			)
		);

		$page_id = rtrim( $site_base, '/' ) . '/research/#page';
		$list_id = rtrim( $site_base, '/' ) . '/research/#index';
		$graph[] = array(
			'@id'        => $page_id,
			'@type'      => 'CollectionPage',
			'name'       => 'Research Index',
			'url'        => rtrim( $site_base, '/' ) . '/research/',
			'isPartOf'   => array( '@id' => rtrim( $site_base, '/' ) . '/#website' ),
			'mainEntity' => array( '@id' => $list_id ),
		);

		$list_items = array();
		foreach ( $works as $position => $work ) {
			$nodes = self::work_nodes( $work, $index, $site_base );
			foreach ( $nodes as $node ) {
				$graph[] = $node;
			}
			$list_items[] = array(
				'@type'   => 'ListItem',
				'position'=> $position + 1,
				'item'    => array( '@id' => self::work_id( $work, $site_base ) ),
			);
		}

		$graph[] = array(
			'@id'             => $list_id,
			'@type'           => 'ItemList',
			'name'            => 'Research outputs',
			'itemListOrder'   => 'https://schema.org/ItemListOrderAscending',
			'numberOfItems'   => count( $list_items ),
			'itemListElement' => $list_items,
		);

		return array( '@context' => 'https://schema.org', '@graph' => $graph );
	}

	public static function single(array $work, array $index, string $site_base): array {
		$graph = self::global_nodes( $index, $site_base );
		foreach ( self::work_nodes( $work, $index, $site_base ) as $node ) {
			$graph[] = $node;
		}

		return array( '@context' => 'https://schema.org', '@graph' => $graph );
	}

	private static function global_nodes(array $index, string $site_base): array {
		$person_id = rtrim( $site_base, '/' ) . '/#stassis-stashkevichyus';
		$website_id = rtrim( $site_base, '/' ) . '/#website';

		return array(
			array(
				'@id'      => $person_id,
				'@type'    => 'Person',
				'name'     => $index['authority']['display_name'],
				'url'      => rtrim( $site_base, '/' ) . '/',
				'sameAs'   => array( $index['authority']['orcid'], $index['authority']['github'] ),
				'jobTitle' => $index['authority']['role'],
				'email'    => $index['authority']['email'],
			),
			array(
				'@id'     => $website_id,
				'@type'   => 'WebSite',
				'name'    => $index['project']['name'],
				'url'     => rtrim( $site_base, '/' ) . '/',
				'creator' => array( '@id' => $person_id ),
			),
		);
	}

	private static function work_nodes(array $work, array $index, string $site_base): array {
		$work_id = self::work_id( $work, $site_base );
		$person_id = rtrim( $site_base, '/' ) . '/#stassis-stashkevichyus';
		$node = array(
			'@id'           => $work_id,
			'@type'         => $work['jsonld_profile']['primary_type'],
			'name'          => $work['title'],
			'url'           => Registry::canonical_url( $work, $site_base ),
			'datePublished' => $work['display_date'],
			'version'       => $work['citation_version'],
			'sameAs'        => array( $work['repository_url'] ),
			'license'       => array_values( array_column( $work['license_scope'], 'license' ) ),
			'additionalProperty' => self::additional_properties( $work ),
		);

		if ( 'Dataset' === $work['jsonld_profile']['primary_type'] ) {
			$node['creator'] = array( '@id' => $person_id );
		} else {
			$node['author'] = array( '@id' => $person_id );
			$node['headline'] = $work['title'];
		}

		if ( null !== ( $work['doi'] ?? null ) ) {
			$doi_url = 'https://doi.org/' . $work['doi'];
			$node['identifier'] = array(
				'@type'      => 'PropertyValue',
				'propertyID' => 'DOI',
				'value'      => $work['doi'],
				'url'        => $doi_url,
			);
			$node['sameAs'][] = $doi_url;
		}

		$nodes = array( $node );
		if ( true === ( $work['jsonld_profile']['software_entity'] ?? false ) ) {
			$code_licenses = array();
			foreach ( $work['license_scope'] as $license ) {
				if ( false !== strpos( $license['scope'], 'code' ) ) {
					$code_licenses[] = $license['license'];
				}
			}
			$nodes[] = array(
				'@id'            => Registry::canonical_url( $work, $site_base ) . '#software',
				'@type'          => 'SoftwareSourceCode',
				'name'           => $work['short_title'] . ' — reproducibility source',
				'creator'        => array( '@id' => $person_id ),
				'codeRepository' => $work['repository_url'],
				'version'        => $work['metadata_record_version'],
				'license'        => $code_licenses,
				'isPartOf'       => array( '@id' => $work_id ),
			);
		}

		return $nodes;
	}

	private static function additional_properties(array $work): array {
		$properties = array(
			self::property( 'Release status', $work['release_status'] ),
			self::property( 'Review status', $work['review_status'] ),
		);
		foreach ( array( 'result_class' => 'Result class', 'novelty_gate' => 'Novelty gate', 'independent_verification_gate' => 'Independent verification gate' ) as $key => $label ) {
			if ( isset( $work[ $key ] ) ) {
				$properties[] = self::property( $label, $work[ $key ] );
			}
		}

		return $properties;
	}

	private static function property(string $name, string $value): array {
		return array( '@type' => 'PropertyValue', 'name' => $name, 'value' => $value );
	}

	private static function work_id(array $work, string $site_base): string {
		return Registry::canonical_url( $work, $site_base ) . '#work';
	}
}

