-- v0.8: Alignment release for planned skill/capability routing, human gates, and benchmarks.

CREATE TABLE IF NOT EXISTS route_decision (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  summary TEXT NOT NULL,
  intent TEXT NOT NULL,
  work_type TEXT NOT NULL,
  scope TEXT NOT NULL,
  uncertainty TEXT NOT NULL,
  reversibility TEXT NOT NULL,
  risk TEXT NOT NULL,
  lane TEXT NOT NULL,
  workflow TEXT NOT NULL,
  skills_json TEXT NOT NULL DEFAULT '[]',
  required_capabilities_json TEXT NOT NULL DEFAULT '[]',
  available_tools_json TEXT NOT NULL DEFAULT '[]',
  missing_capabilities_json TEXT NOT NULL DEFAULT '[]',
  proof_policy TEXT NOT NULL,
  human_gate_required BOOLEAN NOT NULL DEFAULT FALSE,
  rationale_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS human_gate (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  resolved_at TEXT,
  story_id TEXT REFERENCES story(id),
  summary TEXT NOT NULL,
  risk TEXT NOT NULL,
  requested_by TEXT NOT NULL DEFAULT 'harness',
  resolved_by TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  notes TEXT,
  decision_notes TEXT,
  CHECK(status IN ('pending','approved','rejected','cancelled'))
);

CREATE TABLE IF NOT EXISTS benchmark_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  suite TEXT NOT NULL,
  case_count INTEGER NOT NULL,
  pass_count INTEGER NOT NULL,
  fail_count INTEGER NOT NULL,
  result_json TEXT NOT NULL,
  notes TEXT
);
