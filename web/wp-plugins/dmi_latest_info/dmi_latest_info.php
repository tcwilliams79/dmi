<?php
/*
Plugin Name: DMI Latest Info
Description: Renders DMI latest release data from latest.json
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

if ( ! function_exists( 'tcw_dmi_latest_info_shortcode' ) ) {
	function tcw_dmi_latest_info_shortcode( $atts = array() ) {
		$manifest_path = trailingslashit( ABSPATH ) . 'data/outputs/latest.json';

		if ( ! file_exists( $manifest_path ) ) {
			return '<p>Latest DMI data is temporarily unavailable.</p>';
		}

		$json = file_get_contents( $manifest_path );
		if ( false === $json ) {
			return '<p>Latest DMI data could not be read.</p>';
		}

		$latest = json_decode( $json, true );
		
		$latest_release = $latest['releases'][0];

        $latest_metrics = $latest_release['metrics'];

		ob_start();
		?>
		<div class="dmi-latest-data">

			<section class="dmi-current-release">
				<div class="dmi-latest-data-card">
					<strong>Current Release:</strong> <a href="https://dmianalysis.org/data/"> <?php echo esc_html( $latest_release['release_id'] ); ?> </a>
					<table>
					    <tr>
    					<td><strong>Data through:</strong></td><td> <?php echo esc_html( $latest_release['data_through_label'] ); ?></td>
    					</tr>
						<tr>
						<td><strong>DMI Median (typical pressure across income groups):</strong></td><td> <?php echo esc_html( tcw_dmi_format_number($latest_metrics['dmi_median']) ); ?></td>
						</tr>
						<tr>
						<td><strong>Most-Pressured Group (the income fifth under greatest strain):</strong></td> <td><?php echo esc_html( tcw_dmi_format_number($latest_metrics['dmi_stress']) ); ?></td>
						</tr>
						<tr>
						<td><strong>Income Pressure Gap (spread between the most- and least-pressured groups):</strong></td><td><?php echo esc_html( tcw_dmi_format_number($latest_metrics['income_pressure_gap']) ); ?></td>
						</tr>
					</table>
					<p><font size=2> Snapshot metrics summarize current distributional economic pressure; see Methods for construction details.</font> </p>
				</div>
			</section>
		</div>
		<?php

		return ob_get_clean();
	}

}

add_shortcode( 'dmi_latest_info', 'tcw_dmi_latest_info_shortcode' );
