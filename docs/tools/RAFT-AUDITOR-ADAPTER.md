# Raft Auditor Adapter

RaftLMTrainedModelAdapter loads raft-lm export_manifest.json bundles and exposes:
- reason(event) -> DecisionTrace
- propose_from_event(event) -> ProposedAction

This provides compatibility between raft-lm checkpoint exports and RADA decision loop integration.
