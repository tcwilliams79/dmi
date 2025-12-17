# v0.1.9 Roadmap

**Status**: 🔵 Planned  
**Timeline**: TBD  
**Focus**: Research Tool + Public Communication

---

## Phase A: Automation & Historical ⏳ IN PROGRESS

### Automation (Highest Priority)
- [ ] GitHub Actions workflow (`.github/workflows/monthly_dmi.yml`)
- [ ] Error handling & resilience
- [ ] Retry logic with exponential backoff
- [ ] Structured logging

### Historical Backfill
- [ ] Backfill script (`scripts/backfill_historical.py`)
- [ ] Compute DMI for 2010-2024 (175+ months)
- [ ] Apply vintage-appropriate CE weights
- [ ] Create time series dataset

**Estimated**: 8-10 hours

---

## Phase B: Visualization & Alternatives 🔜 NEXT
- [ ] Time series charts (Chart.js/Plotly)
- [ ] U-6 unemployment alternative
- [ ] Core CPI alternative

**Estimated**: 6-8 hours

---

## Phase C: Uncertainty & Documentation 📝 PLANNED
- [ ] Confidence intervals
- [ ] Methodology note (PDF)
- [ ] API documentation

**Estimated**: 8-10 hours

---

**Total v0.1.9 Effort**: 22-28 hours
