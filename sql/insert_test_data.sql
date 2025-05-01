CREATE OR REPLACE FUNCTION insert_test_signals()
RETURNS void AS $$
DECLARE
    signals jsonb;
    signal_record jsonb;
BEGIN
    -- Read the JSON file
    signals := (pg_read_file('/docker-entrypoint-initdb.d/test_data.json')::jsonb)->'signals';
    
    -- Loop through each signal and insert
    FOR signal_record IN SELECT * FROM jsonb_array_elements(signals) LOOP
        WITH arrays AS (
            SELECT 
                array(SELECT * FROM jsonb_array_elements_text(signal_record->'keywords')) as keywords,
                array(SELECT * FROM jsonb_array_elements_text(signal_record->'steep_secondary')) as steep_secondary,
                array(SELECT * FROM jsonb_array_elements_text(signal_record->'signature_secondary')) as signature_secondary,
                array(SELECT * FROM jsonb_array_elements_text(signal_record->'sdgs')) as sdgs
        )
        INSERT INTO signals (
            status, created_by, modified_by, headline, description, url,
            relevance, keywords, location, steep_primary, steep_secondary,
            signature_primary, signature_secondary, sdgs, created_unit
        ) 
        SELECT
            signal_record->>'status',
            signal_record->>'created_by',
            signal_record->>'modified_by',
            signal_record->>'headline',
            signal_record->>'description',
            signal_record->>'url',
            signal_record->>'relevance',
            keywords,
            signal_record->>'location',
            signal_record->>'steep_primary',
            steep_secondary,
            signal_record->>'signature_primary',
            signature_secondary,
            sdgs,
            signal_record->>'created_unit'
        FROM arrays;
    END LOOP;
END;
$$ LANGUAGE plpgsql; 