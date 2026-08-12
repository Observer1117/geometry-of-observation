<?php
/**
 * Bundled archive fallback. Themes may override this file at
 * observer-research-registry/archive-research_output.php.
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main observer-research-archive">
	<header class="observer-research-header">
		<p class="observer-research-kicker"><?php echo esc_html__( 'The Observer of Multiverses', 'observer-research-registry' ); ?></p>
		<h1><?php echo esc_html__( 'Research Index', 'observer-research-registry' ); ?></h1>
		<p><?php echo esc_html__( 'Versioned research outputs with explicit review status, claim boundaries, source provenance, and reproducibility evidence.', 'observer-research-registry' ); ?></p>
	</header>
	<?php echo \ObserverResearchRegistry\Renderer::archive_html(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Renderer context-escapes every value. ?>
</main>
<?php
get_footer();

