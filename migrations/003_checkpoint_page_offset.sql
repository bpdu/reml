ALTER TABLE public.ingestion_backfill_checkpoints
    RENAME COLUMN IF EXISTS offset TO page_offset;

ALTER TABLE public.ingestion_backfill_checkpoints
    ADD COLUMN IF NOT EXISTS page_offset integer NOT NULL DEFAULT 0;
