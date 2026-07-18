-- v0.9: Completion gates, evidence freshness, scoped approvals, and benchmark scores.

ALTER TABLE route_decision ADD COLUMN optional_capabilities_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE route_decision ADD COLUMN missing_required_capabilities_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE route_decision ADD COLUMN missing_optional_capabilities_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE route_decision ADD COLUMN candidate_tools_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE human_gate ADD COLUMN scope_ref TEXT;
ALTER TABLE human_gate ADD COLUMN expires_at TEXT;

ALTER TABLE benchmark_run ADD COLUMN score_json TEXT NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS completion_report (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  story_id TEXT NOT NULL REFERENCES story(id),
  route_id INTEGER REFERENCES route_decision(id),
  approval_id INTEGER REFERENCES human_gate(id),
  status TEXT NOT NULL,
  evidence_ids TEXT NOT NULL DEFAULT '[]',
  stale_evidence_json TEXT NOT NULL DEFAULT '[]',
  missing_required_capabilities_json TEXT NOT NULL DEFAULT '[]',
  missing_optional_capabilities_json TEXT NOT NULL DEFAULT '[]',
  approval_status TEXT,
  skipped_checks_json TEXT NOT NULL DEFAULT '[]',
  residual_risk TEXT,
  rollback_info TEXT,
  report_json TEXT NOT NULL,
  CHECK(status IN ('pass','blocked','weak'))
);
