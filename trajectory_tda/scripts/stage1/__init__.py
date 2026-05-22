"""Stage 1 matched-L W2 + landscape L2 battery — phase-split package.

Replaces the monolithic ``trajectory_tda/scripts/run_stage1_battery.py``.
Each phase script is independently invocable and writes its result JSON
immediately on completion so a session interruption never loses a finished
phase.
"""
