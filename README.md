# Distributional Misery Index (DMI) v0.1.9

![Status](https://img.shields.io/badge/status-production--ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Data](https://img.shields.io/badge/data-2011--2024-blue)
![Coverage](https://img.shields.io/badge/tests-passing-success)

**A transparent, reproducible measure of economic pressure across income groups.**

📊 **[Live Dashboard](https://dmianalysis.org/dashboard/)** | 📖 **[Methodology](docs/DMI_Methodology_Note.md)** | 🔌 **[API Docs](docs/API.md)**

---

## Overview

The DMI combines group-weighted inflation (π) with labor market slack (S) to reveal how economic pressure varies across income groups.

**Formula**: `DMI(g,r,t) = 2 × [0.5 × π(g,r,t) + 0.5 × S(r,t)]`

**Core Principles**:
- ✅ **Deterministic**: Same inputs → identical outputs
- ✅ **Transparent**: All methodology documented and public
- ✅ **Auditable**: Full audit trail from raw data to published results
- ✅ **Research-Ready**: Bootstrap confidence intervals & alternative specifications

---

## Recent Enhancements (v0.1.11)

Version 0.1.11 improves dashboard clarity and interpretability:

- **Data Freshness Banner**
  - Displays data coverage period and publication date
  - Automatically flags potentially stale data
  - Driven by machine-readable metadata (`health.json`)

- **Top Contributors Panel**
  - Shows leading inflation drivers by category
  - Switchable by income quintile (Q1 / Q3 / Q5)
  - Helps answer "What's driving inflation right now?" in a distribution-aware way

These enhancements strengthen transparency and reader trust without altering the underlying DMI methodology.

---

## ✨ v0.1.9 Features

### 📈 Historical Data (2011-2024)
- **835 observations**: 167 periods × 5 income quintiles
- **13+ years** of time series data
- **Complete backfill** with consistent methodology
- Monthly updates via GitHub Actions

### 📊 Interactive Visualizations
- **Time series charts** showing DMI evolution (2011-2024)
- **Historical context**: Percentile rank, vs average, trend analysis
- **Chart.js integration** for smooth, responsive charts
- Current DMI at **15th percentile** historically (Nov 2024)

### 🔬 Alternative Specifications
- **U-6 Unemployment**: Broader labor slack measure (+3.5 DMI points vs baseline)
- **Core CPI**: Excludes food/beverages to isolate underlying inflation
- **Comparison documentation** with use case guidance

### 📉 Confidence Intervals
- **Bootstrap simulation** (1000 iterations) for statistical rigor
- **95% CI widths**: ~0.12 DMI points (Nov 2024)
- Quantifies uncertainty from CE weights sampling error

### 📚 Comprehensive Documentation
- **[Methodology Note](docs/DMI_Methodology_Note.md)**: 20+ pages, academic-style, citable
- **[API Documentation](docs/API.md)**: Multi-language examples (Python, R, JavaScript)
- **[Alternative Specs Guide](docs/Alternative_Specifications.md)**: When to use which variant

---

## Project Structure

```
dmi/
├── dmi_calculator/          # Pure deterministic calculator
│   ├── core.py              # DMI computation engine
│   └── uncertainty.py       # Bootstrap confidence intervals
├── dmi_pipeline/            # Data pipeline + agents
│   └── agents/              
│       └── bls_api_client.py  # Enhanced with retry logic & rate limiting
├── scripts/                 # Computation scripts
│   ├── compute_dmi.py       # Baseline DMI
│   ├── compute_dmi_u6.py    # U-6 alternative
│   ├── compute_dmi_core.py  # Core CPI alternative
│   ├── compute_dmi_with_ci.py  # With confidence intervals
│   └── backfill_historical.py  # Historical time series
├── web/                     # Static web dashboard
│   ├── index.html           # Interactive charts & visualizations
│   └── data/                # Symlinked data files
├── data/                    # 4-layer storage
│   ├── curated/             # CE weights (2023)
│   └── outputs/            
│       ├── published/       # Time series + historical releases
│       │   ├── dmi_timeseries_2010_2024.json (151 KB, 835 obs)
│       │   └── historical/  # 167 individual period files
│       ├── dmi_release_2024-11.json
│       ├── dmi_release_2024-11_u6.json
│       ├── dmi_release_2024-11_core.json
│       └── dmi_release_2024-11_with_ci.json
├── registry/                # Authoritative source declarations
│   └── series_catalog_v0_1.json
├── docs/                    # Documentation
│   ├── DMI_Methodology_Note.md     # Comprehensive methodology
│   ├── API.md                       # Programmatic access guide
│   └── Alternative_Specifications.md  # Spec comparison
└── tests/                   # Unit + integration tests
```

---

## Quick Start

### Prerequisites

- Python 3.9+
- BLS API key (register at https://data.bls.gov/registrationEngine/)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/tcwilliams79/dmi.git
   cd dmi
   ```

2. **Set up Python environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your BLS_API_KEY
   ```

4. **Run DMI calculation**:
   ```bash
   ./venv/bin/python -m scripts.compute_dmi
   ```

---

## Usage Examples

### Compute Latest DMI
```bash
# Baseline (U-3, headline CPI)
./venv/bin/python -m scripts.compute_dmi

# With confidence intervals
./venv/bin/python -m scripts.compute_dmi_with_ci --period 2024-11 --bootstrap 1000

# U-6 alternative (broader unemployment)
./venv/bin/python -m scripts.compute_dmi_u6

# Core CPI alternative (excluding food)
./venv/bin/python -m scripts.compute_dmi_core
```

### Access Data Programmatically

**Python**:
```python
import requests
import pandas as pd

# Load time series
url = "https://raw.githubusercontent.com/tcwilliams79/dmi/main/data/outputs/published/dmi_timeseries_2010_2024.json"
data = requests.get(url).json()

# Filter Q1 observations
q1 = [obs for obs in data['observations'] if obs['group_id'] == 'Q1']
df = pd.DataFrame(q1)
print(df[['period', 'dmi', 'inflation', 'slack']])
```

**R**:
```r
library(jsonlite)

url <- "https://raw.githubusercontent.com/tcwilliams79/dmi/main/data/outputs/published/dmi_timeseries_2010_2024.json"
data <- fromJSON(url)
q1 <- data$observations[data$observations$group_id == "Q1", ]
```

See [API.md](docs/API.md) for complete documentation.

---

## Web Dashboard

### Local Preview
```bash
cd web
python3 -m http.server 8000
# Visit http://localhost:8000
```

### Production Deployment

See `prepare_deployment.sh` to generate production-ready files:
```bash
./prepare_deployment.sh
# Upload deploy/ directory to web host
```

**Features**:
- Interactive time series (2011-2024)
- Historical context (percentile, vs average, trend)
- Current vs historical comparison
- Quintile-specific analysis

---

## Data Sources

- **BLS CPI-U**: Monthly category index levels (inflation)
- **BLS CE Tables**: Annual expenditure shares by income group (weights)
- **BLS CPS**: National unemployment (U-3 baseline, U-6 alternative)

**Current Data**:
- CPI: December 2009 - November 2024
- CE Weights: 2023 vintage
- Unemployment: December 2009 - November 2024
- Time Series: 167 periods (January 2011 - November 2024)

---

## Implementation Status

**Version**: v0.1.9 (December 2024)

### ✅ Phase A: Automation & Historical Backfill
- [x] Enhanced BLS API client (retry logic, rate limiting, logging)
- [x] Historical backfill script (2011-2024)
- [x] GitHub Actions workflow (monthly automation)
- [x] Time series dataset generation (835 observations)
- [x] Data catalog fixes

### ✅ Phase B: Visualizations & Alternative Specifications
- [x] Interactive Chart.js time series visualization
- [x] Historical context panel
- [x] U-6 unemployment alternative
- [x] Core CPI alternative
- [x] Alternative specifications documentation

### ✅ Phase C: Uncertainty & Documentation
- [x] Bootstrap confidence intervals (1000 iterations)
- [x] Uncertainty quantification module
- [x] Comprehensive methodology note (20+ pages)
- [x] API documentation (multi-language examples)
- [x] Production deployment preparation

---

## Key Results (November 2024)

| Quintile | DMI | 95% CI | Inflation | Slack |
|----------|-----|--------|-----------|-------|
| **Q1** (Lowest income) | 6.88 | [6.83, 6.94] | 2.68% | 4.2% |
| **Q2** | 6.85 | [6.79, 6.90] | 2.65% | 4.2% |
| **Q3** (Middle income) | 6.75 | [6.69, 6.81] | 2.55% | 4.2% |
| **Q4** | 6.71 | [6.65, 6.77] | 2.51% | 4.2% |
| **Q5** (Highest income) | 6.65 | [6.59, 6.71] | 2.45% | 4.2% |

**Historical Context**:
- Current Q1 DMI: **15th percentile** (only 15% of historical periods had lower DMI)
- **2.85 points below** 2011-2024 average
- **Trend**: ↓ Decreasing (from 2020 COVID peak)

---

## Documentation

- **[Methodology Note](docs/DMI_Methodology_Note.md)**: Complete technical documentation
- **[API Documentation](docs/API.md)**: Programmatic access guide
- **[Alternative Specifications](docs/Alternative_Specifications.md)**: U-6 & Core CPI guidance
- **[Specification](docs/DMI_v0.1.9_Spec.md)**: Original design specification
- **[Roadmap](docs/ROADMAP_v0.1.9.md)**: Implementation roadmap

---

## Contributing

This is a measurement tool under active development. Contributions should:
- Maintain deterministic calculator properties
- Follow conservative governance (no silent methodology changes)
- Include tests and documentation
- Align with v0.1.9 specification

**Areas for Contribution**:
- Regional DMI variants (state/metro level)
- Historical CE weights integration (2011-2022 vintages)
- Demographic breakdowns (age, family structure)
- Enhanced visualizations

---

## Citation

**Suggested Format**:

> Williams, T.C. (2024). Distributional Misery Index: Measuring Economic Pressure Across Income Groups. Methodology Note v0.1.9.

**BibTeX**:
```bibtex
@techreport{williams2024dmi,
  title={Distributional Misery Index: Measuring Economic Pressure Across Income Groups},
  author={Williams, T.C.},
  year={2024},
  institution={Independent Research},
  type={Methodology Note},
  version={0.1.9},
  url={https://github.com/tcwilliams79/dmi}
}
```

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Contact

**Repository**: https://github.com/tcwilliams79/dmi  
**Website**: https://dmianalysis.org  
**Owner**: Thomas C. Williams

---

## Acknowledgments

Built following the DMI v0.1.9 specification developed with ChatGPT and Antigravity (Google Deepmind).

Data sources: U.S. Bureau of Labor Statistics (BLS).

Special thanks to the open-source community for tools that made this possible: pandas, numpy, Chart.js, and the BLS Public Data API.

---

**Last Updated**: December 2024
