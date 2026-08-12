<?php
/**
 * Bundled single fallback. Themes may override this file at
 * observer-research-registry/single-research_output.php.
 */

defined( 'ABSPATH' ) || exit;

get_header();
?>
<main id="primary" class="site-main observer-research-single">
	<?php while ( have_posts() ) : the_post(); ?>
		<article id="post-<?php the_ID(); ?>" <?php post_class(); ?>>
			<header class="observer-research-header">
				<p class="observer-research-kicker"><?php echo esc_html__( 'Research output', 'observer-research-registry' ); ?></p>
				<h1><?php the_title(); ?></h1>
			</header>
			<div class="observer-research-editorial">
				<?php the_content(); ?>
			</div>
			<?php echo \ObserverResearchRegistry\Renderer::single_html( (int) get_the_ID() ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Renderer context-escapes every value. ?>
		</article>
	<?php endwhile; ?>
</main>
<?php
get_footer();

