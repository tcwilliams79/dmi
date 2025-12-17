# Changelog

All notable changes to the Distributional Misery Index will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.11] - 2025-12-17

### Added - Dashboard Polish
- Freshness banner showing data currency (latest period, publish date, staleness indicator)
- Data staleness warning (⚠️ if >45 days old)
- Top contributors panel showing top 5 inflation drivers by category
- Interactive quintile switching (Q1, Q3, Q5) for contributors
- Category label mapping for readable chart labels
- Chart.js horizontal bar charts for contribution visualization

### Changed - User Experience
- Updated dashboard version to v0.1.11
- Enhanced transparency with automatic health.json integration
- Improved interpretability with "What's driving inflation?"  insights

### Fixed
- None

---

## [0.1.10] - 2025-12-17

### Added - Production Hardening
- Health/status endpoint (`health.json`) generated during deployment
- Metadata file (`metadata.json`) for programmatic dataset discovery
- Freshness banner on dashboard showing latest period and publish date
- Data staleness indicator (⚠️ if data >45 days old)
- CITATION.cff for proper academic citation (GitHub standard)
- Formal JSON Schema for time series data (`schemas/dmi_timeseries_schema.json`)
- Generic deployment guide supporting cPanel, Plesk, DirectAdmin, Nginx, and custom hosts
- Release calendar documenting BLS data sources and publication timeline
- Platform-specific deployment notes for major hosting providers
- Enhanced smoke test checklist with common issues troubleshooting
- Rollback procedures for deployment

### Changed - Documentation
- Deployment instructions now platform-agnostic (not host-specific)
- `prepare_deployment.sh` generates health.json and metadata.json
- Enhanced deployment package with build metadata

### Fixed
- None

---

## [0.1.9] - 2025-12-17

### Added - Feature Complete
- Historical time series backfill (2011-2024, 835 observations)
- Interactive Chart.js time series visualization
- Historical context panel (percentile rank, vs average, trend analysis)
- Bootstrap confidence intervals (1000 iterations, ~0.12 DMI point width)
- U-6 unemployment alternative specification
- Core CPI alternative specification (excluding food/beverages)
- Comprehensive methodology note (20+ pages, academic-style, citable)
- API documentation with multi-language examples (Python, R, JavaScript)
- Alternative specifications documentation
- Deployment preparation script

### Changed - Infrastructure
- Enhanced BLS API client with retry logic, rate limiting, and structured logging
- Improved error handling in data fetching

### Fixed
- Duplicate series ID in catalog (CPI_OTHER)
- Backfill script column mapping issue
- Symlink handling in deployment

---

## [0.1.8] - 2025-12-16

### Added - Initial Release
- Basic DMI calculation (5 income quintiles)
- Monthly GitHub Actions workflow
- CE weights extraction (2023 vintage)
- CPI data fetching from BLS API
- U-3 unemployment integration
- QA validation framework
- Simple web dashboard

### Methodology
- Formula: DMI = 2.0 × (0.5 × Inflation + 0.5 × Slack)
- Weights: CE Survey 2023, Table 1203
- Inflation: 12-month CPI-U percent change
- Slack: U-3 unemployment rate (national)

---

## Change Categories

**Added**: New features, endpoints, documentation  
**Changed**: Modifications to existing functionality  
**Deprecated**: Soon-to-be removed features  
**Removed**: Deleted features  
**Fixed**: Bug fixes  
**Security**: Security vulnerability patches  
**Methodology**: Changes to DMI calculation formula or data sources (RARE - requires version note)

---

## Versioning Policy

**Patch versions (0.1.x)**: Bug fixes, documentation, non-breaking enhancements  
**Minor versions (0.x.0)**: New features, alternative specifications, significant enhancements  
**Major versions (x.0.0)**: Breaking changes, methodology changes affecting DMI values

**Methodology Changes** (special case):
- Any change to weights source, formula, or data that alters DMI values
- Requires explicit user notification in release notes
- Backward compatibility maintained (old data not recalculated)
- Example: Switching from 2023 to 2024 CE weights

---

## Links

- [GitHub Releases](https://github.com/tcwilliams79/dmi/releases)
- [Methodology Note](docs/DMI_Methodology_Note.md)
- [API Documentation](docs/API.md)
