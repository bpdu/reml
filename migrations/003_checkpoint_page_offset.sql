ALTER TABLE public.ingestion_backfill_checkpoints
    ADD COLUMN IF NOT EXISTS page_offset integer NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'ingestion_backfill_checkpoints'
          AND column_name = 'offset'
    ) THEN
        EXECUTE 'ALTER TABLE public.ingestion_backfill_checkpoints RENAME COLUMN "offset" TO page_offset';
    END IF;
END
$$;
