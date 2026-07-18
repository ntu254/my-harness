PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS intake (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  intent TEXT NOT NULL,
  work_type TEXT NOT NULL,
  scope TEXT NOT NULL,
  uncertainty TEXT NOT NULL,
  reversibility TEXT NOT NULL,
  risk TEXT NOT NULL,
  lane TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0,
  summary TEXT NOT NULL,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS story (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  lane TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned',
  contract_ref TEXT,
  verify_command TEXT,
  evidence TEXT,
  notes TEXT,
  revision INTEGER NOT NULL DEFAULT 1,
  CHECK(status IN ('planned','in_progress','verifying','completed','blocked','failed','cancelled','superseded','needs_human')),
  CHECK(lane IN ('tiny','normal','high_risk','approval_required'))
);

CREATE TABLE IF NOT EXISTS evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  kind TEXT NOT NULL,
  target TEXT NOT NULL,
  command TEXT,
  result TEXT NOT NULL,
  artifact TEXT,
  story_id TEXT REFERENCES story(id),
  notes TEXT,
  git_head TEXT,
  dirty_files TEXT,
  trust TEXT NOT NULL DEFAULT 'tool_generated',
  CHECK(result IN ('pass','fail','skipped','partial')),
  CHECK(trust IN ('tool_generated','human_asserted','agent_claim'))
);

CREATE TABLE IF NOT EXISTS trace (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  summary TEXT NOT NULL,
  outcome TEXT NOT NULL,
  intake_id INTEGER REFERENCES intake(id),
  story_id TEXT REFERENCES story(id),
  files_read TEXT,
  files_changed TEXT,
  evidence_ids TEXT,
  friction TEXT,
  notes TEXT,
  CHECK(outcome IN ('completed','partial','blocked','failed'))
);

CREATE TABLE IF NOT EXISTS tool (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  capability TEXT NOT NULL,
  command TEXT NOT NULL,
  availability TEXT NOT NULL DEFAULT 'unknown',
  trust_level TEXT NOT NULL DEFAULT 'project_declared',
  notes TEXT,
  CHECK(availability IN ('present','missing','unknown','inactive'))
);

CREATE TABLE IF NOT EXISTS agent_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT,
  intake_id INTEGER REFERENCES intake(id),
  story_id TEXT REFERENCES story(id),
  lane TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'in_progress',
  agent_command TEXT NOT NULL,
  verify_command TEXT NOT NULL,
  timeout_seconds INTEGER NOT NULL DEFAULT 1800,
  agent_exit_code INTEGER,
  verify_exit_code INTEGER,
  evidence_ids TEXT,
  log_dir TEXT,
  notes TEXT,
  CHECK(lane IN ('tiny','normal','high_risk','approval_required')),
  CHECK(status IN ('in_progress','completed','failed','blocked','needs_human'))
);
