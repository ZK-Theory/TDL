from research_system.evals.scenarios import FoundationPorts, run_gate3_scenario


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
