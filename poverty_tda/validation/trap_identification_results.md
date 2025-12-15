# UK Mobility Validation - Poverty Trap Identification

## Morse-Smale Analysis Results

- **Total Critical Points:** 1387
- **Minima (Poverty Traps):** 357
- **Saddles (Barriers):** 693
- **Maxima (Opportunity Peaks):** 337
- **Simplification Threshold:** 5% persistence

## Top 30 Poverty Traps by Severity

| Rank | Score | Mobility | Size | Barrier | Mean Mobility | Area (km²) |
|------|-------|----------|------|---------|---------------|------------|
| 1 | 0.779 | 0.826 | 1.000 | 0.496 | 0.330 | 390.0 |
| 2 | 0.762 | 0.942 | 0.787 | 0.496 | 0.259 | 307.0 |
| 3 | 0.619 | 0.861 | 0.419 | 0.496 | 0.308 | 164.0 |
| 4 | 0.605 | 0.879 | 0.347 | 0.496 | 0.297 | 136.0 |
| 5 | 0.581 | 0.692 | 0.013 | 1.000 | 0.413 | 6.0 |
| 6 | 0.559 | 0.888 | 0.183 | 0.496 | 0.292 | 72.0 |
| 7 | 0.558 | 0.775 | 0.332 | 0.496 | 0.361 | 130.0 |
| 8 | 0.551 | 0.912 | 0.123 | 0.496 | 0.277 | 49.0 |
| 9 | 0.549 | 1.000 | 0.000 | 0.496 | 0.223 | 1.0 |
| 10 | 0.545 | 0.909 | 0.108 | 0.496 | 0.279 | 43.0 |
| 11 | 0.541 | 0.880 | 0.134 | 0.496 | 0.297 | 53.0 |
| 12 | 0.540 | 0.900 | 0.105 | 0.496 | 0.285 | 42.0 |
| 13 | 0.539 | 0.922 | 0.072 | 0.496 | 0.271 | 29.0 |
| 14 | 0.533 | 0.883 | 0.103 | 0.496 | 0.295 | 41.0 |
| 15 | 0.530 | 0.914 | 0.051 | 0.496 | 0.276 | 21.0 |
| 16 | 0.526 | 0.906 | 0.049 | 0.496 | 0.281 | 20.0 |
| 17 | 0.522 | 0.795 | 0.185 | 0.496 | 0.349 | 73.0 |
| 18 | 0.521 | 0.866 | 0.085 | 0.496 | 0.306 | 34.0 |
| 19 | 0.519 | 0.821 | 0.139 | 0.496 | 0.333 | 55.0 |
| 20 | 0.512 | 0.760 | 0.198 | 0.496 | 0.370 | 78.0 |
| 21 | 0.507 | 0.870 | 0.033 | 0.496 | 0.303 | 14.0 |
| 22 | 0.503 | 0.870 | 0.021 | 0.496 | 0.303 | 9.0 |
| 23 | 0.500 | 0.864 | 0.018 | 0.496 | 0.307 | 8.0 |
| 24 | 0.492 | 0.811 | 0.062 | 0.496 | 0.339 | 25.0 |
| 25 | 0.488 | 0.813 | 0.046 | 0.496 | 0.338 | 19.0 |
| 26 | 0.486 | 0.778 | 0.087 | 0.496 | 0.359 | 35.0 |
| 27 | 0.478 | 0.770 | 0.069 | 0.496 | 0.364 | 28.0 |
| 28 | 0.477 | 0.722 | 0.131 | 0.496 | 0.394 | 52.0 |
| 29 | 0.476 | 0.784 | 0.046 | 0.496 | 0.356 | 19.0 |
| 30 | 0.475 | 0.763 | 0.069 | 0.496 | 0.369 | 28.0 |

## Scoring Methodology

- **Total Score:** Weighted combination of mobility, size, and barrier components
- **Mobility Score (60%):** Lower mean mobility = higher severity
- **Size Score:** Larger basin area = more people affected
- **Barrier Score (40%):** Higher persistence = harder to escape

## VTK Files for Visualization

- Original surface: `C:\Projects\TDL\poverty_tda\validation\mobility_surface.vti`
- Simplified surface: `C:\Projects\TDL\poverty_tda\validation\mobility_surface_simplified.vti`

## Next Steps

- Compare trap locations with Social Mobility Commission cold spots
- Validate against known deprived areas
- Map traps to specific LADs for policy relevance
