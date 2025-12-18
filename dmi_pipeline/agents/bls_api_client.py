"""
BLS API Client - Fetch CPI and unemployment data from BLS Public Data API v2.

This module implements the data fetching agent for CPI index levels and 
unemployment (slack) data using the BLS Public Data API.
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import requests
import pandas as pd
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Load environment variables
load_dotenv()

BLS_API_BASE_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_KEY = os.getenv("BLS_API_KEY")

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting configuration
MAX_REQUESTS_PER_DAY = 500  # BLS API limit for registered keys
REQUEST_DELAY_SECONDS = 1.0  # Delay between requests to avoid rate limiting


def get_retry_session(retries=3, backoff_factor=1.0):
    """
    Create a requests session with retry logic.
    
    Args:
        retries: Number of retry attempts
        backoff_factor: Exponential backoff factor (delay = backoff_factor * (2 ** retry_count))
    
    Returns:
        requests.Session with retry configuration
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],  # Retry on server errors
        allowed_methods=["POST", "GET"]  # Retry on these methods
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_cpi_data(
    series_ids: List[str],
    start_year: int,
    end_year: int,
    api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch CPI index levels from BLS API v2.
    
    Args:
        series_ids: List of BLS CPI series IDs (e.g., ["CUUR0000SAF", "CUUR0000SAH"])
        start_year: Start year for data (e.g., 2023)
        end_year: End year for data (e.g., 2024)
        api_key: Optional BLS API key (falls back to env var)
    
    Returns:
        DataFrame with columns [series_id, year, period, period_name, value, footnotes]
    
    Raises:
        ValueError: If API request fails
    """
    api_key = api_key or BLS_API_KEY
    
    if not api_key:
        logger.error("BLS_API_KEY not found in environment variables")
        raise ValueError("BLS_API_KEY not found in environment variables")
    
    # BLS API v2 request payload
    payload = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
        "registrationkey": api_key
    }
    
    logger.info(f"Fetching CPI data for {len(series_ids)} series ({start_year}-{end_year})")
    logger.debug(f"Series IDs: {series_ids}")
    print(f"Fetching CPI data for {len(series_ids)} series ({start_year}-{end_year})...")
    print(f"  Series: {series_ids[:3]}{'...' if len(series_ids) > 3 else ''}")
    
    headers = {"Content-Type": "application/json"}
    
    # Use retry session with exponential backoff
    session = get_retry_session(retries=3, backoff_factor=2.0)
    
    try:
        # Rate limiting: Add delay to avoid exceeding daily limit
        time.sleep(REQUEST_DELAY_SECONDS)
        
        logger.debug(f"POST request to {BLS_API_BASE_URL}")
        response = session.post(
            BLS_API_BASE_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Check response status
        if data.get("status") != "REQUEST_SUCCEEDED":
            error_msg = data.get("message", ["Unknown error"])[0]
            logger.error(f"BLS API error: {error_msg}")
            logger.debug(f"Full response: {json.dumps(data, indent=2)}")
            raise ValueError(f"BLS API error: {error_msg}")
        
        # Parse results
        records = []
        for series in data.get("Results", {}).get("series", []):
            series_id = series["seriesID"]
            for obs in series.get("data", []):
                # Skip observations with missing values (BLS returns '-')
                if obs["value"] == '-' or not obs["value"]:
                    continue
                    
                records.append({
                    "series_id": series_id,
                    "year": int(obs["year"]),
                    "period": obs["period"],
                    "period_name": obs["periodName"],
                    "value": float(obs["value"]),
                    "footnotes": obs.get("footnotes", [])
                })
        
        df = pd.DataFrame(records)
        
        logger.info(f"Successfully fetched {len(df)} observations for {len(series_ids)} series")
        logger.debug(f"Date range: {df['year'].min()}-{df['year'].max()}")
        
        print(f"✓ Fetched {len(df)} observations for {len(series_ids)} series")
        print(f"  Date range: {df['year'].min()}-{df['year'].max()}")
        print(f"  Periods: {df['period'].nunique()} unique periods")
        
        return df
    
    except requests.RequestException as e:
        logger.error(f"Failed to fetch CPI data from BLS API: {e}")
        raise ValueError(f"Failed to fetch CPI data from BLS API: {e}")
    finally:
        session.close()


def fetch_slack_data(
    series_id: str,
    start_year: int,
    end_year: int,
    api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Fetch unemployment (slack) data from BLS API v2.
    
    Args:
        series_id: BLS series ID for unemployment (e.g., "LNS14000000" for U-3)
        start_year: Start year
        end_year: End year
        api_key: Optional BLS API key
    
    Returns:
        DataFrame with columns [series_id, year, period, period_name, value]
    """
    # Use the same function as CPI - BLS API v2 works for both
    return fetch_cpi_data([series_id], start_year, end_year, api_key)


def convert_to_monthly_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert BLS period codes (M01-M12) to YYYY-MM format.
    
    Args:
        df: DataFrame with columns [year, period, value, ...]
    
    Returns:
        DataFrame with additional 'period_yyyymm' column
    """
    df = df.copy()
    
    # Extract month from period (M01 → 01, M12 → 12)
    df['month'] = df['period'].str.replace('M', '').str.zfill(2)
    
    # Create YYYY-MM format
    df['period_yyyymm'] = df['year'].astype(str) + '-' + df['month']
    
    return df


def pivot_cpi_to_categories(
    cpi_df: pd.DataFrame,
    series_catalog: Dict
) -> pd.DataFrame:
    """
    Pivot CPI data from long format to wide format with category columns.
    
    Args:
        cpi_df: Long-format DataFrame with [series_id, period_yyyymm, value]
        series_catalog: Series catalog dict with series_id → category_id mapping
    
    Returns:
        DataFrame with columns [period, CPI_FOOD_BEVERAGES, CPI_HOUSING, ...]
    """
    # Create series_id → category_id mapping
    series_to_category = {}
    for cat in series_catalog["cpi"]["series_sets"][0]["categories"]:
        series_to_category[cat["series_id"]] = cat["category_id"]
    
    # Map series_id to category_id
    cpi_df = cpi_df.copy()
    cpi_df['category_id'] = cpi_df['series_id'].map(series_to_category)
    
    # Pivot to wide format
    pivot_df = cpi_df.pivot_table(
        index='period_yyyymm',
        columns='category_id',
        values='value',
        aggfunc='first'
    ).reset_index()
    
    pivot_df.rename(columns={'period_yyyymm': 'period'}, inplace=True)
    
    return pivot_df


def save_cpi_data(
    cpi_df: pd.DataFrame,
    output_path: Path,
    metadata: Optional[Dict] = None
) -> None:
    """
    Save CPI data to JSON file.
    
    Args:
        cpi_df: DataFrame with CPI index levels
        output_path: Path to save JSON
        metadata: Optional metadata
    """
    output = {
        "data": cpi_df.to_dict(orient='records'),
        "metadata": metadata or {
            "created_at": datetime.utcnow().isoformat() + "Z",
            "source": "BLS Public Data API v2"
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Saved CPI data to {output_path}")


def validate_category_coverage(
    cpi_df: pd.DataFrame,
    required_categories: List[str],
    reference_period: str,
    lookback_months: int = 12
) -> Dict[str, bool]:
    """
    Validate that all required CPI categories have data for reference period and lookback.
    
    Args:
        cpi_df: DataFrame with CPI data (columns = categories)
        required_categories: List of required category_ids
        reference_period: Reference period (YYYY-MM)
        lookback_months: Months to look back (default: 12 for YoY)
    
    Returns:
        Dict with validation results
    """
    # Calculate lookback period
    ref_date = pd.to_datetime(reference_period)
    lookback_date = ref_date - pd.DateOffset(months=lookback_months)
    lookback_period = lookback_date.strftime('%Y-%m')
    
    results = {
        "reference_period": reference_period,
        "lookback_period": lookback_period,
        "valid": True,
        "missing_categories": [],
        "missing_periods": []
    }
    
    # Check reference period
    ref_data = cpi_df[cpi_df['period'] == reference_period]
    if ref_data.empty:
        results["valid"] = False
        results["missing_periods"].append(reference_period)
    else:
        # Check each category
        for cat in required_categories:
            if cat not in ref_data.columns or pd.isna(ref_data[cat].values[0]):
                results["valid"] = False
                results["missing_categories"].append(f"{cat} (t={reference_period})")
    
    # Check lookback period
    lookback_data = cpi_df[cpi_df['period'] == lookback_period]
    if lookback_data.empty:
        results["valid"] = False
        results["missing_periods"].append(lookback_period)
    else:
        for cat in required_categories:
            if cat not in lookback_data.columns or pd.isna(lookback_data[cat].values[0]):
                results["valid"] = False
                results["missing_categories"].append(f"{cat} (t-{lookback_months}={lookback_period})")
    
    return results
