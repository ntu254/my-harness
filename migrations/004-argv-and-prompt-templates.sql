ALTER TABLE agent_adapter ADD COLUMN command_mode TEXT NOT NULL DEFAULT 'shell';
ALTER TABLE agent_adapter ADD COLUMN command_argv_json TEXT;
ALTER TABLE agent_run ADD COLUMN command_mode TEXT NOT NULL DEFAULT 'shell';
ALTER TABLE agent_run ADD COLUMN command_argv_json TEXT;
