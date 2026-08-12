<?php

declare(strict_types=1);

namespace ObserverResearchRegistry;

final class CliCommand {
	public function validate(): void {
		Registry::index();
		Registry::model();
		\WP_CLI::success( 'Bundled registry and manifest are valid. SHA-256: ' . Registry::digest() );
	}

	public function status(): void {
		$preview = Importer::preview();
		if ( is_wp_error( $preview ) ) {
			\WP_CLI::error( $preview->get_error_message() );
		}

		\WP_CLI::log( (string) wp_json_encode( array( 'preview' => $preview, 'state' => Importer::state() ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
	}

	public function sync(): void {
		$result = Importer::sync();
		if ( is_wp_error( $result ) ) {
			\WP_CLI::error( $result->get_error_message() );
		}
		\WP_CLI::success( 'Registry synchronized: ' . wp_json_encode( $result['counts'] ) );
	}

	public function recover(): void {
		$result = Importer::recover();
		if ( is_wp_error( $result ) ) {
			\WP_CLI::error( $result->get_error_message() );
		}
		\WP_CLI::success( $result['message'] );
	}
}

