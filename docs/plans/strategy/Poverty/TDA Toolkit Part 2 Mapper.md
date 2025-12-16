Deep Dive: The Mapper Algorithm
1. What Mapper Does (Conceptual)
Mapper is fundamentally about simplifying complex high-dimensional data into a graph that captures its essential shape. It's like creating a map of a mountain range—you lose detail but gain understanding.

INPUT: Point cloud X ⊂ ℝⁿ (e.g., LSOAs in 7D deprivation space)
       Filter function f: X → ℝᵏ (e.g., overall IMD score)
       Cover of f(X) (overlapping intervals)
       Clustering algorithm
OUTPUT: A graph (simplicial complex) where:
        - Nodes = clusters of points with similar filter values
        - Edges = clusters that share points (from overlap)
The graph reveals:
- Clusters (disconnected components)
- Branches (linear structures)
- Loops (circular dependencies)
- Flares (points of divergence)
2. The Algorithm Step by Step
MAPPER ALGORITHM
═══════════════════════════════════════════════════════════════════
Step 1: FILTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apply a filter function f: X → ℝ (or ℝ²) to your data.
For poverty data, filter choices:
- f = Overall IMD score (simplest)
- f = (Income score, Education score) - 2D filter
- f = First principal component
- f = Eccentricity (distance to most different LSOA)
- f = Density (local point cloud density)
Example:
  LSOA_1 → f(LSOA_1) = 0.23  (low deprivation)
  LSOA_2 → f(LSOA_2) = 0.87  (high deprivation)
  ...
Step 2: COVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Create overlapping intervals that cover the range of f.
Parameters:
- n_cubes: Number of intervals
- overlap: Fraction of overlap (typically 0.3-0.5)
Example with n_cubes=5, overlap=0.3:
  Interval 1: [0.00, 0.28]
  Interval 2: [0.18, 0.46]  ← overlaps with 1 and 3
  Interval 3: [0.36, 0.64]
  Interval 4: [0.54, 0.82]
  Interval 5: [0.72, 1.00]
Step 3: PULLBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each interval, find all points whose filter value falls in that interval.
  Pullback(Interval 3) = {LSOA_5, LSOA_12, LSOA_17, ...}
                         All LSOAs with IMD score in [0.36, 0.64]
Step 4: CLUSTER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Within each pullback, cluster points using the FULL feature space
(not just filter value).
This is key: The filter sorts points by one dimension, but clustering
uses all 7 deprivation dimensions.
  Pullback(Interval 3) clustering:
    → Cluster 3a: {LSOA_5, LSOA_12}   (urban poverty type)
    → Cluster 3b: {LSOA_17, LSOA_23}  (rural poverty type)
Points with same filter value but different deprivation profiles
end up in different clusters.
Step 5: BUILD GRAPH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Each cluster becomes a NODE
- If clusters from adjacent intervals share any points (due to overlap),
  add an EDGE between them
  Cluster 2b ←→ Cluster 3a  (share LSOA_12 due to interval overlap)
The overlap is crucial: it detects when the same data points
appear in multiple intervals, revealing connectivity.
Step 6: INTERPRET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The resulting graph reveals data topology:
  ●━━━●━━━●     Linear branch: gradual transition
                  (low deprivation → high deprivation)
  ●━┳━●         Fork: same IMD level, different types
    ┗━●           (urban vs coastal poverty)
    ●
   / \
  ●   ●         Convergence: different paths to same IMD level
   \ /            (manufacturing decline vs service economy loss)
    ●
  ●━●━●         Loop: circular structure
  │   │           (poverty cycle? gentrification loop?)
  ●━●━●
3. Why Mapper Matters for Poverty Analysis
Mapper reveals structure that neither Morse-Smale nor clustering captures:

Question	Morse-Smale Answer	LISA Answer	Mapper Answer
"Are there types of poverty?"	No (basins don't distinguish types)	Partially (HH vs LL)	Yes (branches = types)
"Do poverty types merge?"	No	No	Yes (branch mergers visible)
"Is there a poverty cycle?"	No (detects basins, not cycles)	No	Yes (loops in graph)
"What's the transition path?"	Yes (separatrices)	No	Yes (edge paths)
"How similar are two areas?"	Via distance functions	Via spatial autocorrelation	Via graph distance
4. Concrete Application: Deprivation Typology Discovery
Current approach (in paper): All LSOAs treated as varying in degree (more/less deprived)

Mapper insight: LSOAs vary in both degree and kind

python
# Conceptual example of Mapper on deprivation data
# Input: Each LSOA as point in 7D (Income, Employment, Education, 
#        Health, Crime, Housing, Environment)
# Filter: Overall IMD score
# Hypothetical output graph:
"""
                    AFFLUENCE
                        ●
                       /│\
                      / │ \
           SUBURBAN  ●  ●  ●  COMMUTER
           MIXED     │     │  AFFLUENT
                     │     │
                     ●─────●
                     │     │
        URBAN   ●────●     ●────●  RURAL
        WORKING      │     │       STRUGGLING
        CLASS        │     │
                     ●     ●
                     │     │
        POST     ●───●     ●───●  COASTAL
        INDUSTRIAL   │     │      DECLINE
                     │     │
                     ●─────●
                        │
                    SEVERE
                   DEPRIVATION
"""
# INTERPRETATION:
# - Two main "arms" of deprivation: Urban/Industrial vs Rural/Coastal
# - They merge at extremes (severe deprivation looks similar everywhere)
# - Affluence branches into suburban vs commuter types
# - A loop might indicate areas that cycle between classifications
Policy insight from Mapper:

"Post-industrial decline areas (Blackpool, Middlesbrough) share a structural position in the data—they can be grouped for coordinated intervention. Coastal decline areas (Jaywick, Skegness) are on a different branch with different deprivation profile. Generic 'deprivation interventions' may miss this heterogeneity."

