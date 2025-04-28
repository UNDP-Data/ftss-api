/*
Migration script to add secondary_location column to signals table.
Run this script to update the database schema.
*/

-- Add secondary_location column to signals table
ALTER TABLE signals ADD COLUMN IF NOT EXISTS secondary_location TEXT[];

-- Update the index to include the new column
DROP INDEX IF EXISTS signals_idx;
CREATE INDEX ON signals (
    status,
    created_by,
    created_for,
    created_unit,
    steep_primary,
    steep_secondary,
    signature_primary,
    signature_secondary,
    sdgs,
    location,
    secondary_location,
    score
); 