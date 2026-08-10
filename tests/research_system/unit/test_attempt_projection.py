from research_system.command.reducers import replay_control_plane


def test_replay_control_plane_tracks_only_nonterminal_attempt_streams():
    attempt_id = "att_01978abc-3012-7000-8000-000000003012"
    rule_id = "val_01978abc-3013-7000-8000-000000003013"
    created = {
        "event_type": "AttemptCreated",
        "stream_id": attempt_id,
        "stream_version": 1,
        "payload": {
            "new_attempt_id": attempt_id,
            "creation_kind": "initial",
            "task_id": "tsk_01978abc-3011-7000-8000-000000003011",
            "task_revision": 1,
            "dispatch_id": "dsp_01978abc-3014-7000-8000-000000003014",
            "attempt_ordinal": 1,
            "execution_epoch": 1,
        },
    }
    claimed = {
        "event_type": "AttemptClaimed",
        "stream_id": attempt_id,
        "stream_version": 2,
        "payload": {
            "attempt_id": attempt_id,
            "task_id": created["payload"]["task_id"],
            "task_revision": 1,
            "dispatch_id": created["payload"]["dispatch_id"],
            "lease_id": "els_01978abc-3015-7000-8000-000000003015",
        },
    }
    started = {
        "event_type": "AttemptStarted",
        "stream_id": attempt_id,
        "stream_version": 3,
        "payload": {"attempt_id": attempt_id},
    }
    completed = {
        "event_type": "AttemptCompleted",
        "stream_id": attempt_id,
        "stream_version": 4,
        "payload": {"attempt_id": attempt_id},
    }
    rule = {
        "event_type": "RuleEvaluationRecorded",
        "stream_id": rule_id,
        "stream_version": 1,
        "payload": {
            "new_rule_evaluation_id": rule_id,
            "input_ids": [],
            "input_hashes": [],
        },
    }

    active = replay_control_plane((created, rule))
    terminal = replay_control_plane((created, claimed, started, completed, rule))

    assert active.active_attempt_ids == frozenset({attempt_id})
    assert terminal.active_attempt_ids == frozenset()
