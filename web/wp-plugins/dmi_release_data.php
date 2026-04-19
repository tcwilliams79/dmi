<?php
/*
Plugin Name: DMI Release Data
Description: Renders DMI release data from releases.json
Version: 0.1.0
Author: Thomas C. Williams
*/

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! function_exists( 'tcw_dmi_format_number' ) ) {
	function tcw_dmi_format_number( $value, $decimals = 2 ) {
		if ( ! is_numeric( $value ) ) {
			return '';
		}
		return number_format_i18n( (float) $value, $decimals );
	}
}

if ( ! function_exists( 'tcw_dmi_format_date' ) ) {
	function tcw_dmi_format_date( $value ) {
		if ( empty( $value ) ) {
			return '';
		}
		$ts = strtotime( $value );
		return $ts ? date_i18n( 'F j, Y', $ts ) : $value;
	}
}

if ( ! function_exists( 'tcw_dmi_release_compare' ) ) {
	function tcw_dmi_release_compare( $a, $b ) {
		$a_id = isset( $a['release_id'] ) ? (string) $a['release_id'] : '';
		$b_id = isset( $b['release_id'] ) ? (string) $b['release_id'] : '';
		return strcmp( $b_id, $a_id ); // descending YYYY-MM
	}
}

if ( ! function_exists( 'tcw_dmi_render_links' ) ) {
	function tcw_dmi_render_links( $urls ) {
		$links = array();

		if ( ! empty( $urls['csv'] ) ) {
			$links[] = '<a href="' . esc_url( $urls['csv'] ) . '">CSV</a>';
		}
		if ( ! empty( $urls['parquet'] ) ) {
			$links[] = '<a href="' . esc_url( $urls['parquet'] ) . '">Parquet</a>';
		}
		if ( ! empty( $urls['release_note'] ) ) {
			$links[] = '<a href="' . esc_url( $urls['release_note'] ) . '">Release note</a>';
		}
		if ( ! empty( $urls['dashboard'] ) ) {
			$links[] = '<a href="' . esc_url( $urls['dashboard'] ) . '">Dashboard</a>';
		}
		if ( ! empty( $urls['repo'] ) ) {
			$links[] = '<a href="' . esc_url( $urls['repo'] ) . '">GitHub</a>';
		}

		return implode( ' | ', $links );
	}
}

if ( ! function_exists( 'tcw_dmi_release_data_shortcode' ) ) {
	function tcw_dmi_release_data_shortcode( $atts = array() ) {
		$manifest_path = trailingslashit( ABSPATH ) . 'data/outputs/releases.json';

		if ( ! file_exists( $manifest_path ) ) {
			return '<p>DMI release data is temporarily unavailable.</p>';
		}

		$json = file_get_contents( $manifest_path );
		if ( false === $json ) {
			return '<p>DMI release data could not be read.</p>';
		}

		$manifest = json_decode( $json, true );
		if ( ! is_array( $manifest ) || empty( $manifest['releases'] ) || ! is_array( $manifest['releases'] ) ) {
			return '<p>DMI release data is temporarily unavailable.</p>';
		}

		$releases = $manifest['releases'];
		usort( $releases, 'tcw_dmi_release_compare' );

		$current_release_id = isset( $manifest['current_release_id'] ) ? (string) $manifest['current_release_id'] : '';
		$current = null;
		$archive = array();

		foreach ( $releases as $release ) {
			$rid    = isset( $release['release_id'] ) ? (string) $release['release_id'] : '';
			$status = isset( $release['status'] ) ? (string) $release['status'] : '';

			if (
				null === $current &&
				(
					( $current_release_id && $rid === $current_release_id ) ||
					( 'current' === $status )
				)
			) {
				$current = $release;
				continue;
			}
		}

		if ( null === $current && ! empty( $releases ) ) {
			$current = $releases[0];
		}

		if ( null === $current ) {
			return '<p>No DMI releases are available yet.</p>';
		}

		foreach ( $releases as $release ) {
			$rid = isset( $release['release_id'] ) ? (string) $release['release_id'] : '';
			if ( $rid !== (string) $current['release_id'] ) {
				$archive[] = $release;
			}
		}

		ob_start();
		?>
		<div class="dmi-release-data">

			<section class="dmi-current-release">
				<h2>Current release</h2>

				<div class="dmi-release-card">
					<p>
						<strong>Release:</strong> <?php echo esc_html( $current['release_id'] ); ?><br>
						<strong>Data through:</strong> <?php echo esc_html( $current['data_through_label'] ); ?><br>
						<strong>Published:</strong> <?php echo esc_html( tcw_dmi_format_date( $current['published_at'] ) ); ?><br>
						<strong>Status:</strong> <?php echo esc_html( ucfirst( $current['status'] ) ); ?><br>
						<strong>Methodology version:</strong> <?php echo esc_html( $current['methodology_version'] ); ?>
					</p>

					<?php if ( ! empty( $current['summary'] ) ) : ?>
						<p><?php echo esc_html( $current['summary'] ); ?></p>
					<?php endif; ?>

					<p><?php echo tcw_dmi_render_links( $current['urls'] ); ?></p>

					<?php if ( ! empty( $current['metrics'] ) && is_array( $current['metrics'] ) ) : ?>
						<h3>Current-release snapshot</h3>
						<ul>
							<?php if ( isset( $current['metrics']['dmi_median'] ) ) : ?>
								<li><strong>DMI Median:</strong> <?php echo esc_html( tcw_dmi_format_number( $current['metrics']['dmi_median'] ) ); ?></li>
							<?php endif; ?>

							<?php if ( isset( $current['metrics']['dmi_stress'] ) ) : ?>
								<li><strong>DMI Stress:</strong> <?php echo esc_html( tcw_dmi_format_number( $current['metrics']['dmi_stress'] ) ); ?></li>
							<?php endif; ?>

							<?php if ( isset( $current['metrics']['income_pressure_gap'] ) ) : ?>
								<li><strong>Income Pressure Gap:</strong> <?php echo esc_html( tcw_dmi_format_number( $current['metrics']['income_pressure_gap'] ) ); ?></li>
							<?php endif; ?>

							<?php if ( isset( $current['metrics']['unemployment'] ) ) : ?>
								<li><strong>National unemployment:</strong> <?php echo esc_html( tcw_dmi_format_number( $current['metrics']['unemployment'], 1 ) ); ?>%</li>
							<?php endif; ?>
						</ul>
					<?php endif; ?>
				</div>
			</section>

			<?php if ( ! empty( $archive ) ) : ?>
				<section class="dmi-release-archive">
					<h2>Release archive</h2>

					<?php foreach ( $archive as $release ) : ?>
						<div class="dmi-archive-item">
							<h3><?php echo esc_html( $release['release_id'] ); ?></h3>

							<p>
								<strong>Data through:</strong> <?php echo esc_html( $release['data_through_label'] ); ?><br>
								<strong>Published:</strong> <?php echo esc_html( tcw_dmi_format_date( $release['published_at'] ) ); ?><br>
								<strong>Status:</strong> <?php echo esc_html( ucfirst( $release['status'] ) ); ?><br>
								<strong>Methodology version:</strong> <?php echo esc_html( $release['methodology_version'] ); ?>
							</p>

							<?php if ( ! empty( $release['summary'] ) ) : ?>
								<p><?php echo esc_html( $release['summary'] ); ?></p>
							<?php endif; ?>

							<p><?php echo tcw_dmi_render_links( $release['urls'] ); ?></p>
						</div>
					<?php endforeach; ?>
				</section>
			<?php endif; ?>

		</div>
		<?php

		return ob_get_clean();
	}

	add_shortcode( 'dmi_release_data', 'tcw_dmi_release_data_shortcode' );
}
