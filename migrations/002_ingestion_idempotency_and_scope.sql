ALTER TABLE public.ingestion_backfill_checkpoints
    ADD COLUMN IF NOT EXISTS deal_id integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS category_id integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS region_id integer NOT NULL DEFAULT 0;

ALTER TABLE public.ingestion_backfill_checkpoints
    DROP CONSTRAINT IF EXISTS ingestion_backfill_checkpoints_pkey;

ALTER TABLE public.ingestion_backfill_checkpoints
    ADD CONSTRAINT ingestion_backfill_checkpoints_pkey
    PRIMARY KEY (schema_name, deal_id, category_id, region_id, window_start, window_end);

DO $DDL$
DECLARE
    schema_name text;
BEGIN
    FOREACH schema_name IN ARRAY ARRAY['sale', 'rent']
    LOOP
        EXECUTE format($f$
            ALTER TABLE %I.listing_api_responses
                ADD COLUMN IF NOT EXISTS request_fingerprint text,
                ADD COLUMN IF NOT EXISTS deal_id integer,
                ADD COLUMN IF NOT EXISTS category_id integer,
                ADD COLUMN IF NOT EXISTS region_id integer,
                ADD COLUMN IF NOT EXISTS window_start date,
                ADD COLUMN IF NOT EXISTS window_end date,
                ADD COLUMN IF NOT EXISTS page_limit integer,
                ADD COLUMN IF NOT EXISTS page_offset integer
        $f$, schema_name);

        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_%I_listing_api_responses_request_fingerprint ON %I.listing_api_responses (request_fingerprint)',
            schema_name,
            schema_name
        );
    END LOOP;
END;
$DDL$;
