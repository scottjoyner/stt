create table if not exists turns (
  turn_id text primary key,
  conversation_id text not null,
  transcript text,
  created_at text not null
);
create table if not exists tasks (
  task_id text primary key,
  turn_id text not null,
  task_signature text not null,
  priority text not null,
  status text not null,
  created_at text not null
);
create unique index if not exists idx_tasks_dedupe on tasks(turn_id, task_signature);
create table if not exists task_runs (
  run_id text primary key,
  task_id text not null,
  status text not null,
  lease_expires_at text,
  heartbeat_ts text
);
create table if not exists agent_steps (
  step_id text primary key,
  run_id text not null,
  agent_name text not null,
  status text not null,
  summary text not null
);
create table if not exists artifacts (
  artifact_id text primary key,
  run_id text not null,
  kind text not null,
  uri text not null,
  created_at text not null
);
create table if not exists checkpoints (
  consumer text primary key,
  cursor text not null,
  updated_at text not null
);
