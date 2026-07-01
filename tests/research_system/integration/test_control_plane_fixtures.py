from tests.research_system.factories import (
    claim_dispatch_command,
    control_plane,
    create_task_command,
)


def test_s001_s002_f001_f002_control_plane_flow(tmp_path):
    harness = control_plane(tmp_path)
    task_id = 'tsk_01978abc-3001-7000-8000-000000003001'
    dispatch_id = 'dsp_01978abc-3002-7000-8000-000000003002'
    create = create_task_command(
        'cmd_01978abc-3003-7000-8000-000000003003',
        'integration-create',
        task_id,
        {'title': 'Integrated'},
    )
    assert harness.service.submit(create) == harness.service.submit(create)
    first = claim_dispatch_command(
        'cmd_01978abc-3004-7000-8000-000000003004',
        'actor-a',
        dispatch_id,
        expected_version=0,
    )
    second = claim_dispatch_command(
        'cmd_01978abc-3005-7000-8000-000000003005',
        'actor-b',
        dispatch_id,
        expected_version=0,
    )
    assert harness.service.submit(first).status == 'accepted'
    assert harness.service.submit(second).status == 'conflict'
    assert len(tuple(harness.ledger.iter_batches())) == 2
    assert len(harness.replay().active_attempt_ids) == 1
