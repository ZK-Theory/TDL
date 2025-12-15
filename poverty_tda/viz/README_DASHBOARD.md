# Poverty TDA Basin Dashboard - Quick Reference

## Access
**URL:** http://localhost:8503

## Start Dashboard
```bash
cd /c/Projects/TDL
.venv/Scripts/streamlit run poverty_tda/viz/dashboard.py --server.port 8503
```

## Features at a Glance

### 📊 Statistics (Step 2)
- **Single Basin:** 4 metric cards with color-coded trap scores
- **Multi-Basin:** Comparison table with gradient backgrounds

### 👥 Demographics (Step 3)
- IMD Decile Distribution (bar chart)
- Quintile Distribution (pie chart)
- Domain Scores (income, employment, education, health)

### 🗺️ Geography (Step 4)
- **Interactive Map:** Color-coded basin markers with popups
- **3D Terrain:** Labeled valleys showing trap topology

## Regions Available
1. North West
2. North East
3. Yorkshire and The Humber
4. East Midlands
5. West Midlands
6. East of England
7. London
8. South East
9. South West
10. Wales

## Trap Score Color Key
- 🔴 **Dark Red (#8B0000):** Critical (0.8-1.0)
- 🟠 **Orange Red (#FF4500):** Severe (0.6-0.8)
- 🟡 **Orange (#FFA500):** Moderate (0.4-0.6)
- 💛 **Gold (#FFD700):** Low (0.2-0.4)
- 🟢 **Light Green (#90EE90):** Minimal (0.0-0.2)

## Testing
Run comprehensive validation:
```bash
.venv/Scripts/python.exe poverty_tda/viz/test_dashboard_validation.py
```

## Files
- **Dashboard:** `poverty_tda/viz/dashboard.py` (1100+ lines)
- **Tests:** `poverty_tda/viz/test_dashboard_*.py` (4 files)
- **Docs:** `poverty_tda/viz/DASHBOARD_COMPLETE.md`

## Status
✅ All 5 steps complete
✅ All automated tests passing
✅ Ready for real data integration
