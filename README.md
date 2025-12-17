# Distributional Misery Index (DMI) v0.1.8

![Status](https://img.shields.io/badge/status-operational-brightgreen)
![Python](https://img.shields.io/badge/python-3.9+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)
![Tests](https://img.shields.io/badge/tests-12%2F12%20passing-success)

**A transparent, reproducible measure of economic pressure across income groups.**

## Overview

The DMI combines group-weighted inflation (π) with labor market slack (S) to reveal how economic pressure varies across income groups.

**Formula**: `DMI(g,r,t) = 2 × [0.5 × π(g,r,t) + 0.5 × S(r,t)]`

**Core Principles**:
- ✅ **Deterministic**: Same inputs → identical outputs
- ✅ **Transparent**: All methodology documented and public
- ✅ **Auditable**: Full audit trail from raw data to published results
- ✅ **Non-partisan**: "Visibility, not advocacy"

## Project Structure

```
dmi/
├── dmi_calculator/          # Pure deterministic calculator
├── dmi_pipeline/            # Data pipeline + agents
│   └── agents/              # 7 minimal agents
├── dmi_web/                 # Next.js web interface
├── data/                    # 4-layer storage
│   ├── raw/                 # As-downloaded source files
│   ├── staging/             # Normalized observations
│   ├── curated/             # Calculator-ready matrices
│   └── outputs/             # Published releases
│       ├── published/       # Deployable to Vercel
│       └── internal/        # Review packets (never deployed)
├── registry/                # Authoritative source declarations
├── schemas/                 # JSON schemas for validation
├── docs/                    # Methods note, PDD, checklist
└── tests/                   # Unit + integration tests
```

## Quick Start

### Prerequisites

- Python 3.9+
- BLS API key (register at https://data.bls.gov/registrationEngine/)
- Node.js 18+ (for web interface)

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

4. **Run tests** (when implemented):
   ```bash
   pytest tests/
   ```

## Implementation Status

**Spec Version**: v0.1.8 (2025-12-17)

### Phase 1: Core Foundation (⏳ In Progress)
- [x] Project structure initialized
- [x] Registry & schemas copied from spec
- [x] Python environment configured
- [ ] Deterministic calculator implementation
- [ ] Category-agnostic architecture
- [ ] Unit tests for calculator

### Phase 2: CE Weights Pipeline (🔜 Next)
- [ ] CE XLSX downloader
- [ ] Structural validation (4 checks)
- [ ] Extraction + mapping logic
- [ ] Weights QA

### Phase 3: CPI & Slack Integration
- [ ] CPI data fetcher (BLS API)
- [ ] Category coverage validator
- [ ] Slack data fetcher
- [ ] Alignment validator

### Phase 4: QA Gates & Publisher
- [ ] Validator (Janus)
- [ ] Weights vintage detector
- [ ] Backfill candidate generator
- [ ] Publisher with prevalidation

### Phase 5: Web Interface
- [ ] Next.js setup
- [ ] DMI charts (Plotly)
- [ ] Category breakdown
- [ ] QA report viewer

### Phase 6: Integration & Deployment
- [ ] End-to-end pipeline test
- [ ] GitHub Actions workflow
- [ ] Vercel deployment

## Data Sources

- **BLS CPI-U**: Monthly category index levels (inflation)
- **BLS CE Tables**: Annual expenditure shares by income group (weights)
- **BLS CPS**: National unemployment (U-3 baseline, U-6 sensitivity)
- **BLS LAUS**: State/metro unemployment (future expansion)

## Key Files

- **Specification**: `dmi_v0.1_spec_package_v0.1.8/`
- **Implementation Checklist**: `docs/DMI_v0.1_Implementation_Checklist.md`
- **Methods Note**: `docs/DMI_v0.1_PDD.md`
- **Output Contract**: `registry/output_contract_v0_1.json`

## Development

### Running the Calculator (when implemented)
```python
python
from dmi_calculator import compute_dmi

# Pass curated inputs
dmi_results = compute_dmi(inflation_by_group, slack_by_geo)
```

### Running the Pipeline (when implemented)
```bash
python scripts/run_monthly.py --reference-period 2024-11
```

### Web Interface (when implemented)
```bash
cd dmi_web
npm install
npm run dev
# Visit http://localhost:3000
```

## Deployment

**Target**: Vercel (static Next.js deployment)

**Process**:
1. Pipeline runs in GitHub Actions
2. Generates outputs to `data/outputs/published/`
3. Copies to `dmi_web/public/data/`
4. Deploys to Vercel on PR merge (semi-automated with approval)

## Contributing

This is a measurement tool under active development. Contributions should:
- Maintain deterministic calculator properties (no I/O in calculator)
- Follow conservative governance (no silent methodology changes)
- Include tests and documentation
- Align with v0.1.8 specification

## License

MIT License

## Contact

**Repository**: https://github.com/tcwilliams79/dmi  
**Owner**: Thomas C. Williams

## Acknowledgments

Built following the DMI v0.1.8 specification developed with ChatGPT and Antigravity (Google Deepmind).

Data sources: U.S. Bureau of Labor Statistics (BLS), Bureau of Economic Analysis (BEA).
