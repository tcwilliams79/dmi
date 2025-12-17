# DMI Release Calendar

**Version**: 0.1.10  
**Purpose**: Document data release schedule and publication timeline

---

##  BLS Data Release Schedule

### CPI-U (Consumer Price Index - Inflation)

**Publisher**: U.S. Bureau of Labor Statistics  
**Frequency**: Monthly  
**Release Date**: ~13th of each month (±2 days)  
**Covers**: Previous month  
**Example**: November CPI released December 11, 2024

**Official Schedule**: https://www.bls.gov/schedule/news_release/cpi.htm

**Typical Pattern**:
- January CPI: Released mid-February
- February CPI: Released mid-March
- ... and so on

**Holiday Adjustments**: Releases may shift if 13th falls on weekend/holiday

---

### CPS (Current Population Survey - Unemployment)

**Publisher**: U.S. Bureau of Labor Statistics  
**Frequency**: Monthly  
**Release Date**: First Friday of each month  
**Covers**: Previous month  
**Example**: November unemployment released December 6, 2024

**Official Schedule**: https://www.bls.gov/schedule/news_release/empsit.htm

**Typical Pattern**:
- First Friday after month-end
- Occasionally delayed by federal holidays

---

## DMI Publication Timeline

### Target SLA

**Best Effort**: Within **7 days** of CPI release

**Rationale**:
- CPI typically releases after unemployment (13th vs 1st Friday)
- CPI is the constraining data source
- 7 days allows for:
  - Data verification (1-2 days)
  - QA checks (1 day)
  - Deployment preparation (1 day)
  - Buffer for issues (2-3 days)

---

### Monthly Workflow

**Day 0**: BLS Publishes CPI (~13th of month)
- Example: Dec 11 - November CPI published

**Day 1-2**: Data Verification
- Verify BLS API has latest data
- Check for any BLS revisions or corrections
- Run `compute_dmi.py` locally

**Day 3-4**: QA & Review
- Review DMI values for anomalies
- Check inflation contributions make sense
- Validate historical consistency
- Run alternative specifications if needed

**Day 5-6**: Deployment Preparation
- Run `prepare_deployment.sh`
- Update CHANGELOG if methodology changed
- Test deployment package locally

**Day 7**: Publication
- Upload to production
- Verify health.json shows new period
- Run smoke test checklist
- Announce update (optional)

---

### Historical Performance

| Period | CPI Release | DMI Published | Days Elapsed |
|--------|-------------|---------------|--------------|
| 2024-11 | Dec 11 | Dec 17 | 6 days |
| 2024-10 | Nov 13 | -- | (baseline established) |

**Target**: Maintain <7 day average

---

### Known Delay Scenarios

**BLS Delays**:
- Federal government shutdowns
- Natural disasters affecting data collection
- Major holidays (Christmas week, Thanksgiving)
- Technical issues with BLS systems

**Our Delays**:
- Data quality issues requiring investigation
- Methodology updates requiring documentation
- Infrastructure issues
- Weekend timing (may push to Monday)

**Communication**: 
- Monitor https://www.bls.gov/bls/news-release/schedule.htm
- If CPI delayed, DMI inherits delay
- If DMI delayed independently, update health.json status

---

## 2024-2025 Projected Release Dates

### 2024 Remaining

| Month | Est. CPI Release | Target DMI | Notes |
|-------|------------------|------------|-------|
| Dec 2024 | Jan 14, 2025 | Jan 21, 2025 | |

### 2025 Full Year

| Month | Est. CPI Release | Target DMI | Notes |
|-------|------------------|------------|-------|
| Jan 2025 | Feb 12 | Feb 19 | |
| Feb 2025 | Mar 12 | Mar 19 | |
| Mar 2025 | Apr 10 | Apr 17 | |
| Apr 2025 | May 13 | May 20 | |
| May 2025 | Jun 11 | Jun 18 | |
| Jun 2025 | Jul 11 | Jul 18 | |
| Jul 2025 | Aug 13 | Aug 20 | |
| Aug 2025 | Sep 11 | Sep 18 | |
| Sep 2025 | Oct 10 | Oct 17 | |
| Oct 2025 | Nov 13 | Nov 20 | Thanksgiving week |
| Nov 2025 | Dec 10 | Dec 17 | |
| Dec 2025 | Jan 14, 2026 | Jan 21, 2026 | |

**Note**: Dates are estimates based on historical patterns. Check BLS official schedule for confirmed dates.

---

## Monitoring Data Availability

### How to Check if New Data is Available

**Method 1 - BLS Website**:
- Visit https://www.bls.gov/cpi/
- Look for "Latest Numbers" section
- Check period date

**Method 2 - BLS API**:
```bash
curl "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0?latest=true"
# Check response for latest period
```

**Method 3 - Our Health Endpoint**:
```bash
curl https://dmianalysis.org/dashboard/health.json | jq '.latest_period'

# If result < current month-1, data is fresh
# If result = current month-2 or older, data is stale
```

---

## Automation Opportunities

### Current: Manual Monthly

Process:
1. Check BLS website around 13th  
2. Run compute_dmi.py locally
3. Upload manually
4. Verify deployment

**Time**: ~30 minutes/month

---

### Future: Semi-Automated (v0.2.0)

GitHub Actions workflow:
1. Trigger on schedule (15th of month)
2. Fetch latest CPI from BLS API
3. Compute DMI automatically
4. Create deployment package
5. **Manual approval step**
6. Deploy to production

**Time**: 5 minutes/month (just approval)

---

### Future: Fully Automated (v0.3.0)

Requires:
- Robust data validation
- Automatic anomaly detection
- Rollback capability
- Notification system

**Risk**: Publishes bad data if BLS has errors

**Recommendation**: Keep manual review step

---

## Data Staleness Indicators

###  Dashboard Warning (Implemented in v0.1.10)

If `latest_period` > 45 days old:
- Freshness banner shows ⚠️ "Delayed"  
- Color changes to warning yellow
- Indicates attention needed

### Health Endpoint Status

```json
{
  "status": "healthy",     // or "stale" if >45 days
  "latest_period": "2024-11",
  "days_since_update": 35
}
```

Future enhancement: Add computed `days_since_update` field

---

## Communication Plan

### Routine Updates
- No announcement needed (just update health.json)
- Users check dashboard as needed

### Delayed Updates
- If >14 days since CPI: Update health status to "delayed"
- Add note explaining reason (BLS delay, data quality issue, etc.)

### Methodology Changes
- Announce via CHANGELOG
- Email users (if mailing list exists)
- Post on GitHub Releases
- Update methodology note

---

## Support & Contacts

**BLS CPI Questions**: cpi_info@bls.gov  
**BLS CPS Questions**: lausinfo@bls.gov  
**DMI Issues**: https://github.com/tcwilliams79/dmi/issues

---

**Last Updated**: December 17, 2025  
**For**: DMI v0.1.10
