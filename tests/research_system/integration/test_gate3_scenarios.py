from research_system.evals.scenarios import FoundationPorts, run_gate3_scenario
from research_system.evals.lifecycle import EvaluationLifecycleRuntime


class RecordingFoundation(FoundationPorts):
    def __init__(self):
        super().__init__()
        self.calls = []

    def produce_and_verify(self):
        self.calls.append("produce_and_verify")
        return super().produce_and_verify()

    def reroute_outage(self):
        self.calls.append("reroute_outage")
        return super().reroute_outage()

    def stop_and_resume(self):
        self.calls.append("stop_and_resume")
        return super().stop_and_resume()

    def recover_writer(self):
        self.calls.append("recover_writer")
        return super().recover_writer()

    def deny_restricted_issue(self):
        self.calls.append("deny_restricted_issue")
        return super().deny_restricted_issue()


def test_scenarios_are_derived_from_composed_foundation_ports():
    foundation = RecordingFoundation()
    results = [run_gate3_scenario(item, foundation) for item in "ABCDE"]
    assert foundation.calls == [
        "produce_and_verify",
        "reroute_outage",
        "stop_and_resume",
        "recover_writer",
        "deny_restricted_issue",
    ]
    assert results[0].producer_actor_id != results[0].verifier_actor_id
    assert results[1].original_requirement_id == results[1].reroute_requirement_id
    assert results[1].provider_command_count == 0
    assert results[2].resume_epoch == results[2].initial_epoch + 1
    assert results[3].published_batch_count in {0, 1}
    assert results[3].replay_integrity == "pass"
    assert results[4].decision_reason == "restricted_data_denied"
    assert "ProviderCommandIssued" not in results[4].event_types


def test_scenario_a_actors_derive_from_distinct_family_route_records():
    result = run_gate3_scenario("A")
    assert result.producer_actor_id != result.verifier_actor_id
    assert result.producer_actor_id.startswith("actor-claude")
    assert result.verifier_actor_id.startswith("actor-codex")
    assert result.event_types.index("RouteSelected") < result.event_types.index("ProviderCommandIssued")
    assert result.provider_command_count == 1


def test_scenario_a_release_snapshot_contract_matches_produced_trace():
    """remediation-red: the frozen release trace must match the active producer."""
    from research_system.evals.release_snapshot import _SCENARIO_CONTRACT

    result = run_gate3_scenario("A")

    assert result.event_types == (
        "RouteSelected",
        "RouteSelected",
        "ProviderCommandIssued",
    )
    assert _SCENARIO_CONTRACT["A"]["event_types"] == result.event_types


def test_scenario_a_provider_command_count_is_derived_from_recorded_issue_events(monkeypatch):
    from research_system.evals import scenarios

    original_submit = scenarios._ScenarioContextWriter.submit_context

    def submit_twice_when_issued(self, **kwargs):
        result = original_submit(self, **kwargs)
        if kwargs["command_type"] == "IssueContextPacket":
            self.events.append(dict(self.events[-1]))
        return result

    monkeypatch.setattr(scenarios._ScenarioContextWriter, "submit_context", submit_twice_when_issued)

    result = run_gate3_scenario("A")

    assert result.event_types.count("ProviderCommandIssued") == 2
    assert result.provider_command_count == 2


def test_evaluation_lifecycle_runtime_retains_its_class_docstring():
    assert EvaluationLifecycleRuntime.__doc__ == (
        "Own one durable temporary lifecycle store for a bounded evaluation run."
    )


def test_scenario_b_reroute_reevaluates_and_preserves_the_request():
    result = run_gate3_scenario("B")
    assert result.original_requirement_id == result.reroute_requirement_id
    assert result.provider_command_count == 0
    assert result.event_types == (
        "RouteSelectionFailed",
        "RerouteEvaluated",
        "RouteSelected",
    )
