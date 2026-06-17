<?php
/*
Plugin Name: DMI Latest Info
Description: Renders DMI latest release data from latest.json
Version: 0.2.0
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

if ( ! function_exists( 'tcw_dmi_get_metric_value' ) ) {
	function tcw_dmi_get_metric_value( $metrics, $key, $fallback = null ) {
		if ( ! is_array( $metrics ) ) {
			return $fallback;
		}

		if ( isset( $metrics[ $key ] ) && is_numeric( $metrics[ $key ] ) ) {
			return (float) $metrics[ $key ];
		}

		return $fallback;
	}
}

if ( ! function_exists( 'tcw_dmi_get_income_pressure_spread' ) ) {
	function tcw_dmi_get_income_pressure_spread( $metrics ) {
		if ( ! is_array( $metrics ) ) {
			return null;
		}

		// Schema 2.0.0+: explicit nonnegative spread.
		if ( isset( $metrics['income_pressure_spread'] ) && is_numeric( $metrics['income_pressure_spread'] ) ) {
			return (float) $metrics['income_pressure_spread'];
		}

		// Legacy schema: income_pressure_gap was signed in some releases.
		// When presenting as spread, use absolute value.
		if ( isset( $metrics['income_pressure_gap'] ) && is_numeric( $metrics['income_pressure_gap'] ) ) {
			return abs( (float) $metrics['income_pressure_gap'] );
		}

		return null;
	}
}

if ( ! function_exists( 'tcw_dmi_get_income_pressure_tilt' ) ) {
	function tcw_dmi_get_income_pressure_tilt( $metrics ) {
		if ( ! is_array( $metrics ) ) {
			return null;
		}

		// Schema 2.0.0+: explicit signed Q1-Q5 tilt.
		if ( isset( $metrics['income_pressure_tilt'] ) && is_numeric( $metrics['income_pressure_tilt'] ) ) {
			return (float) $metrics['income_pressure_tilt'];
		}

		// Legacy fallback: preserve signed gap as tilt.
		if ( isset( $metrics['income_pressure_gap'] ) && is_numeric( $metrics['income_pressure_gap'] ) ) {
			return (float) $metrics['income_pressure_gap'];
		}

		return null;
	}
}

if ( ! function_exists( 'tcw_dmi_format_metric_or_na' ) ) {
	function tcw_dmi_format_metric_or_na( $value, $decimals = 2 ) {
		if ( null === $value || ! is_numeric( $value ) ) {
			return 'N/A';
		}

		return tcw_dmi_format_number( $value, $decimals );
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

		$dmi_median = tcw_dmi_get_metric_value( $latest_metrics, 'dmi_median' );
		$dmi_stress = tcw_dmi_get_metric_value( $latest_metrics, 'dmi_stress' );
		$income_pressure_spread = tcw_dmi_get_income_pressure_spread( $latest_metrics );
		$income_pressure_tilt = tcw_dmi_get_income_pressure_tilt( $latest_metrics );
		$unemployment = tcw_dmi_get_metric_value( $latest_metrics, 'unemployment' );

		$most_pressured_group = ! empty( $latest_metrics['most_pressured_group'] )
			? (string) $latest_metrics['most_pressured_group']
			: 'N/A';

		$least_pressured_group = ! empty( $latest_metrics['least_pressured_group'] )
			? (string) $latest_metrics['least_pressured_group']
			: 'N/A';


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
						<td><strong>DMI Median (typical pressure across income groups):</strong></td><td> <?php echo esc_html( tcw_dmi_format_metric_or_na( $dmi_median ) ); ?></td>
						</tr>
						<tr>
						<td><strong>DMI Stress (highest DMI across income groups):</strong></td> <td><?php echo esc_html( tcw_dmi_format_metric_or_na( $dmi_stress ) ); ?></td>
						</tr>
						<tr>
						<td><strong>Most-Pressured Group (the income fifth under greatest strain):</strong></td> <td><?php if ( 'N/A' !== $most_pressured_group ) : ?> <?php echo esc_html( $most_pressured_group ); ?><?php endif; ?></td>
						</tr>
						<tr>
						<td><strong>Income Pressure Spread (gap between the most- and least-pressured groups):</strong></td><td><?php echo esc_html( tcw_dmi_format_metric_or_na( $income_pressure_spread ) ); ?></td>
						</tr>
						<tr>
						<td><strong>Income Pressure Tilt (Q1 DMI - Q5 DMI. Positive = more pressure in Q1; negative = more pressure in Q5):</strong></td><td><?php echo esc_html( tcw_dmi_format_metric_or_na( $income_pressure_tilt ) ); ?></td>
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
