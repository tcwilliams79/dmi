# DMI API Documentation

**Version**: 0.1.9  
**Last Updated**: December 2024

---

## Overview

The Distributional Misery Index (DMI) data is available as static JSON files that can be accessed programmatically. While there is no live REST API, the data follows a consistent schema and is updated monthly via automated GitHub Actions workflows.

**Benefits**:
- No authentication required
- No rate limits
- Stable schema across releases
- Programmatic access in any language
- Full historical time series available

---

## Data Access Methods

### Method 1: Direct Download from GitHub

```bash
# Latest monthly release
curl https://raw.githubusercontent.com/[username]/[repo]/main/data/outputs/dmi_release_2024-11.json

# Historical time series (2011-2024)
curl https://raw.githubusercontent.com/[username]/[repo]/main/data/outputs/published/dmi_timeseries_2010_2024.json

# Alternative specifications
curl https://raw.githubusercontent.com/[username]/[repo]/main/data/outputs/dmi_release_2024-11_u6.json
curl https://raw.githubusercontent.com/[username]/[repo]/main/data/outputs/dmi_release_2024-11_core.json

# With confidence intervals
curl https://raw.githubusercontent.com/[username]/[repo]/main/data/outputs/dmi_release_2024-11_with_ci.json
```

### Method 2: Clone Repository

```bash
git clone https://github.com/[username]/[repo].git
cd [repo]/data/outputs

# Access local files
cat dmi_release_2024-11.json
```

### Method 3: Web Dashboard

Visit the interactive dashboard:
- URL: `https://[username].github.io/[repo]`
- Features: Time series charts, historical context, comparative analysis
- Data automatically loaded from JSON files

---

## File Structure

### Latest Monthly Release

**Path**: `data/outputs/dmi_release_YYYY-MM.json`

**Example**: `dmi_release_2024-11.json`

```json
{
  "reference_period": "2024-11",
  "specification": "BASELINE",
  "description": "DMI using U-3 unemployment and headline CPI",
  "parameters": {
    "alpha": 0.5,
    "scale_factor": 2.0,
    "weights_year": 2023
  },
  "dmi_by_group": [
    {
      "group_id": "Q1",
      "dmi": 6.85,
      "inflation": 2.65,
      "slack": 4.2
    }
  ],
  "summary_metrics": {
    "dmi_median": 6.72,
    "dmi_stress": 6.85,
    "dmi_dispersion_q5_q1": -0.24
  },
  "inflation_contributions": [...],
  "metadata": {
    "computed_at": "2024-12-17T14:00:00Z",
    "num_groups": 5
  }
}
```

### Historical Time Series

**Path**: `data/outputs/published/dmi_timeseries_2010_2024.json`

```json
{
  "series_id": "DMI_NATIONAL_QUINTILE",
  "description": "Monthly DMI by income quintile, 2011-2024",
  "start_period": "2011-01",
  "end_period": "2024-11",
  "observations_count": 835,
  "observations": [
    {
      "period": "2011-01",
      "group_id": "Q1",
      "dmi": 10.81,
      "inflation": 1.71,
      "slack": 9.1
    }
  ],
  "metadata": {
    "note": "All periods use 2023 CE weights",
    "weights_vintage": "2023"
  }
}
```

### With Confidence Intervals

**Path**: `data/outputs/dmi_release_YYYY-MM_with_ci.json`

Adds CI fields to each group:

```json
{
  "dmi_by_group": [
    {
      "group_id": "Q1",
      "dmi": 6.88,
      "dmi_ci_lower": 6.83,
      "dmi_ci_upper": 6.94,
      "dmi_se": 0.027,
      "inflation": 2.68,
      "inflation_ci_lower": 2.63,
      "inflation_ci_upper": 2.74,
      "inflation_se": 0.027,
      "slack": 4.2
    }
  ],
  "parameters": {
    "n_bootstrap": 1000,
    "confidence_level": 0.95,
    "weight_cv": 0.05
  }
}
```

---

## Schema Documentation

### DMI Group Record

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `group_id` | string | Yes | Income quintile identifier | `"Q1"`, `"Q2"`, ..., `"Q5"` |
| `dmi` | number | Yes | DMI value (point estimate) | `6.85` |
| `inflation` | number | Yes | 12-month inflation rate (%) | `2.65` |
| `slack` | number | Yes | Unemployment rate (%) | `4.2` |
| `dmi_ci_lower` | number | Optional | 95% CI lower bound | `6.72` |
| `dmi_ci_upper` | number | Optional | 95% CI upper bound | `6.98` |
| `dmi_se` | number | Optional | Standard error | `0.066` |
| `inflation_ci_lower` | number | Optional | Inflation CI lower bound | `2.59` |
| `inflation_ci_upper` | number | Optional | Inflation CI upper bound | `2.71` |
| `inflation_se` | number | Optional | Inflation standard error | `0.030` |

### Summary Metrics

| Field | Type | Description |
|-------|------|-------------|
| `dmi_median` | number | Q3 (middle quintile) DMI |
| `dmi_stress` | number | Q1 (highest DMI) |
| `dmi_dispersion_q5_q1` | number | Q5 - Q1 difference |

### Inflation Contributions

| Field | Type | Description |
|-------|------|-------------|
| `group_id` | string | Income quintile |
| `category_id` | string | CPI category (e.g., `"CPI_FOOD_BEVERAGES"`) |
| `category_inflation` | number | Category-specific inflation (%) |
| `weight` | number | Expenditure weight for this group/category |
| `contribution` | number | Percentage point contribution to total inflation |

---

## Usage Examples

### Python

```python
import requests
import pandas as pd

# Load latest DMI
url = "https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/dmi_release_2024-11.json"
response = requests.get(url)
data = response.json()

# Convert to DataFrame
df = pd.DataFrame(data['dmi_by_group'])
print(df[['group_id', 'dmi', 'inflation', 'slack']])

# Output:
#   group_id   dmi  inflation  slack
# 0       Q1  6.85       2.65    4.2
# 1       Q2  6.82       2.62    4.2
# 2       Q3  6.72       2.52    4.2
# 3       Q4  6.68       2.48    4.2
# 4       Q5  6.62       2.42    4.2

# Load time series
ts_url = "https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/published/dmi_timeseries_2010_2024.json"
ts_data = requests.get(ts_url).json()

# Filter Q1 only
q1_obs = [obs for obs in ts_data['observations'] if obs['group_id'] == 'Q1']
q1_df = pd.DataFrame(q1_obs)

# Plot
import matplotlib.pyplot as plt
plt.plot(q1_df['period'], q1_df['dmi'])
plt.title('Q1 DMI Over Time (2011-2024)')
plt.xlabel('Period')
plt.ylabel('DMI')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

### R

```r
library(jsonlite)
library(ggplot2)

# Load time series
url <- "https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/published/dmi_timeseries_2010_2024.json"
data <- fromJSON(url)

# Filter Q1 only
q1 <- data$observations[data$observations$group_id == "Q1", ]

# Plot
ggplot(q1, aes(x = period, y = dmi)) +
  geom_line(group = 1) +
  labs(title = "Q1 DMI Over Time (2011-2024)",
       x = "Period",
       y = "DMI") +
  theme_minimal() +
  theme(axis.text.x = element_text(angle = 45, hjust = 1))
```

### JavaScript (Browser)

```javascript
// Load latest DMI in browser
fetch('https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/dmi_release_2024-11.json')
  .then(response => response.json())
  .then(data => {
    const q1 = data.dmi_by_group.find(g => g.group_id === 'Q1');
    console.log(`Q1 DMI: ${q1.dmi}`);
    console.log(`Q1 Inflation: ${q1.inflation}%`);
    console.log(`Unemployment: ${q1.slack}%`);
  });

// Load time series
fetch('data/outputs/published/dmi_timeseries_2010_2024.json')
  .then(response => response.json())
  .then(data => {
    // Filter Q1 observations
    const q1_data = data.observations.filter(obs => obs.group_id === 'Q1');
    
    // Extract data for Chart.js
    const labels = q1_data.map(obs => obs.period);
    const values = q1_data.map(obs => obs.dmi);
    
    // Create chart (assuming Chart.js is loaded)
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Q1 DMI',
          data: values
        }]
      }
    });
  });
```

### Command Line (jq)

```bash
# Extract Q1 DMI from latest release
curl -s https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/dmi_release_2024-11.json | \
  jq '.dmi_by_group[] | select(.group_id == "Q1") | .dmi'

# Get all DMI values
curl -s https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/dmi_release_2024-11.json | \
  jq '.dmi_by_group[] | {group_id, dmi}'

# Count time series observations
curl -s https://raw.githubusercontent.com/[user]/[repo]/main/data/outputs/published/dmi_timeseries_2010_2024.json | \
  jq '.observations | length'
```

---

## Update Frequency

- **Monthly releases**: Published around the 15th of each month
- **Automated**: GitHub Actions workflow fetches latest BLS data
- **Historical data**: Backfilled through 2024, static thereafter
- **Breaking changes**: Versioned (v0.2.0, v0.3.0, etc.)

---

## File Naming Conventions

| Pattern | Description | Example |
|---------|-------------|---------|
| `dmi_release_YYYY-MM.json` | Baseline DMI for period | `dmi_release_2024-11.json` |
| `dmi_release_YYYY-MM_u6.json` | U-6 unemployment alternative | `dmi_release_2024-11_u6.json` |
| `dmi_release_YYYY-MM_core.json` | Core CPI alternative | `dmi_release_2024-11_core.json` |
| `dmi_release_YYYY-MM_with_ci.json` | With confidence intervals | `dmi_release_2024-11_with_ci.json` |
| `dmi_timeseries_YYYY_YYYY.json` | Time series dataset | `dmi_timeseries_2010_2024.json` |
| `qa_report_YYYY-MM.json` | QA validation report | `qa_report_2024-11.json` |

---

## Error Handling

**404 Not Found**: Period not yet published or file path incorrect
```python
try:
    response = requests.get(url)
    response.raise_for_status()  # Raises HTTPError for bad status
    data = response.json()
except requests.exceptions.HTTPError as e:
    print(f"Error: {e}")
    print("Period may not be published yet")
```

**JSON Parse Error**: File corrupted or incomplete
```python
try:
    data = response.json()
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

**Schema Validation**: Verify expected fields exist
```python
required_fields = ['reference_period', 'dmi_by_group', 'summary_metrics']
if all(field in data for field in required_fields):
    print("✓ Valid schema")
else:
    print("⚠️  Missing required fields")
```

---

## Rate Limits & Terms of Use

**No rate limits**: Static files served via GitHub/CDN, no throttling

**Attribution**: Please cite the DMI methodology note when using the data:
> Williams, T. (2024). Distributional Misery Index: Measuring Economic Pressure Across Income Groups. Methodology Note v0.1.9.

**Open data**: Free for research, policy analysis, journalism, and education

**Contributions**: Report issues or suggest improvements via GitHub Issues

**Modifications**: If you fork/modify, please share improvements back to the community

---

## Support & Contact

- **GitHub Issues**: Report bugs or request features
- **Documentation**: See `docs/DMI_Methodology_Note.md` for complete methodology
- **Alternative Specs**: See `docs/Alternative_Specifications.md` for guidance

---

## Changelog

### v0.1.9 (December 2024)
- Added bootstrap confidence intervals
- Historical time series (2011-2024) backfilled
- U-6 and Core CPI alternatives implemented
- API documentation created
- Web dashboard with interactive charts

### v0.1.8 (November 2024)
- Initial public release
- Monthly DMI computation
- GitHub Actions automation
- Basic web dashboard

---

## Future API Enhancements (v0.2.0+)

Planned features:
- **Live REST API**: Real-time data access with endpoints
- **Regional DMI**: State and metro-level variants
- **Demographics**: Age, family structure breakdowns
- **GraphQL**: Flexible query interface
- **Webhooks**: Notifications for new releases

---

**Questions?** Open an issue on GitHub or consult the methodology documentation.
