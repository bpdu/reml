CREATE SCHEMA IF NOT EXISTS sale;
CREATE SCHEMA IF NOT EXISTS rent;

CREATE TABLE IF NOT EXISTS public.ingestion_backfill_checkpoints (
    schema_name text NOT NULL CHECK (schema_name IN ('sale', 'rent')),
    window_start date NOT NULL,
    window_end date NOT NULL,
    status text NOT NULL,
    records_loaded integer NOT NULL DEFAULT 0,
    offset integer NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (schema_name, window_start, window_end)
);

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $DDL$
DECLARE
    schema_name text;
BEGIN
    FOREACH schema_name IN ARRAY ARRAY['sale', 'rent']
    LOOP
        EXECUTE format($f$
            CREATE TABLE IF NOT EXISTS %I.listing_api_responses (
                id bigserial PRIMARY KEY,
                endpoint text NOT NULL,
                request_params jsonb NOT NULL,
                response_payload jsonb NOT NULL,
                fetched_at timestamptz NOT NULL DEFAULT now(),
                records_count integer NOT NULL
            )
        $f$, schema_name);

        EXECUTE format($f$
            CREATE TABLE IF NOT EXISTS %I.listing_objects (
                id bigserial PRIMARY KEY,
                external_id bigint NOT NULL UNIQUE,
                url text,
                phone text,
                first_seen_at timestamptz NOT NULL,
                last_seen_at timestamptz NOT NULL,
                source_time timestamptz,
                first_published_at timestamptz,
                created_at_source timestamptz,
                region text,
                city text,
                address text,
                metro text,
                rooms_count integer,
                floor_number integer,
                floors_count integer,
                area_total numeric,
                area_kitchen numeric,
                area_living numeric,
                area_land numeric,
                building_year integer,
                deal_type text,
                repair_type text,
                person_type text,
                building_material_type text,
                category text,
                subcategory text,
                category_id integer,
                region_id integer,
                city_id integer,
                lat numeric,
                lng numeric,
                layout text,
                class_type text,
                condition_type text,
                published_user_id bigint,
                external_user_id bigint,
                images text,
                images_hash text,
                description text,
                description_hash text,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            )
        $f$, schema_name);

        EXECUTE format('DROP TRIGGER IF EXISTS trg_set_updated_at ON %I.listing_objects', schema_name);
        EXECUTE format($f$
            CREATE TRIGGER trg_set_updated_at
            BEFORE UPDATE ON %I.listing_objects
            FOR EACH ROW
            EXECUTE FUNCTION public.set_updated_at()
        $f$, schema_name);

        EXECUTE format($f$
            CREATE TABLE IF NOT EXISTS %I.listing_price_observations (
                id bigserial PRIMARY KEY,
                listing_id bigint NOT NULL REFERENCES %I.listing_objects(id),
                external_id bigint NOT NULL,
                observed_at timestamptz NOT NULL DEFAULT now(),
                source_time timestamptz,
                time_publish timestamptz,
                price numeric NOT NULL,
                raw_response_id bigint REFERENCES %I.listing_api_responses(id),
                UNIQUE (listing_id, observed_at)
            )
        $f$, schema_name, schema_name, schema_name);

        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_listing_api_responses_fetched_at ON %I.listing_api_responses (fetched_at)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_listing_objects_last_seen_at ON %I.listing_objects (last_seen_at)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_listing_objects_first_published_at ON %I.listing_objects (first_published_at)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_listing_objects_external_user_id ON %I.listing_objects (external_user_id)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_price_listing_id_observed_at ON %I.listing_price_observations (listing_id, observed_at)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_price_external_id_observed_at ON %I.listing_price_observations (external_id, observed_at)', schema_name, schema_name);
        EXECUTE format('CREATE INDEX IF NOT EXISTS idx_%I_price_observed_at ON %I.listing_price_observations (observed_at)', schema_name, schema_name);
    END LOOP;
END;
$DDL$;
