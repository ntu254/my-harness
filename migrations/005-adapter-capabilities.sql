-- v0.7: Adapter capabilities taxonomy and verification modes

-- Add capability tracking and verification modes to adapters
ALTER TABLE agent_adapter ADD COLUMN capabilities_json TEXT DEFAULT '[]';
ALTER TABLE agent_adapter ADD COLUMN max_prompt_length INTEGER DEFAULT 100000;
ALTER TABLE agent_adapter ADD COLUMN supports_raw_prompt BOOLEAN DEFAULT FALSE;
ALTER TABLE agent_adapter ADD COLUMN supports_templates BOOLEAN DEFAULT TRUE;
ALTER TABLE agent_adapter ADD COLUMN supports_argv BOOLEAN DEFAULT TRUE;
ALTER TABLE agent_adapter ADD COLUMN verification_mode TEXT DEFAULT 'shell' CHECK(verification_mode IN ('shell', 'argv', 'native'));

-- Create adapter_capability table for easier querying
CREATE TABLE IF NOT EXISTS adapter_capability (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  adapter_id TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(adapter_id) REFERENCES agent_adapter(id)
);

-- Create verification_template table for storing verification command templates per adapter
CREATE TABLE IF NOT EXISTS verification_template (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  adapter_id TEXT NOT NULL,
  template_key TEXT NOT NULL,
  template_value TEXT NOT NULL,
  mode TEXT DEFAULT 'shell' CHECK(mode IN ('shell', 'argv')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(adapter_id) REFERENCES agent_adapter(id),
  UNIQUE(adapter_id, template_key, mode)
);
