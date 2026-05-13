create table if not exists sync_runs (
    sync_run_id bigserial primary key,

    source_name text not null default 'epic_spark_tracks',
    source_url text not null,

    started_at timestamptz not null default now(),
    finished_at timestamptz,

    status text not null default 'running',
    -- running, skipped, success, failed

    source_last_modified timestamptz,
    source_track_count integer,

    import_batch_id bigint references import_batches(import_batch_id)
        on delete set null,

    error_message text,
    notes text,

    constraint chk_sync_runs_status
        check (status in ('running', 'skipped', 'success', 'failed'))
);