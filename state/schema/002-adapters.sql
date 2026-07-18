CREATE TABLE IF NOT EXISTS agent_adapter (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  provider TEXT NOT NULL,
  command_template TEXT NOT NULL,
  availability TEXT NOT NULL DEFAULT 'unknown',
  trust_level TEXT NOT NULL DEFAULT 'project_declared',
  notes TEXT,
  CHECK(availability IN ('present','missing','unknown','inactive')),
  CHECK(trust_level IN ('project_declared','user_declared','verified_local'))
);

ALTER TABLE agent_run ADD COLUMN adapter_id TEXT REFERENCES agent_adapter(id);
ALTER TABLE agent_run ADD COLUMN prompt TEXT;
