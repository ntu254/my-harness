ALTER TABLE agent_adapter ADD COLUMN executable TEXT;
ALTER TABLE agent_adapter ADD COLUMN version_command TEXT;
ALTER TABLE agent_adapter ADD COLUMN last_checked_at TEXT;
ALTER TABLE agent_adapter ADD COLUMN last_check_result TEXT;
