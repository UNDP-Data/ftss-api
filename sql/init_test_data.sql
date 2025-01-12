/*
The initialisation script to create test data for local development.
This script is automatically executed by docker compose after create_tables.sql
and import_data.sql.
*/

-- Create test users
INSERT INTO users (
    id,
    created_at,
    email,
    role,
    name,
    unit,
    acclab,
    api_key
) VALUES (
    1,  -- This ID is expected by the test suite
    NOW(),
    'test.user@undp.org',
    'ADMIN',
    'Test User',
    'Data Futures Exchange (DFx)',
    false,
    'test-key'
);

-- Reset the sequence to start after our manually inserted IDs
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users)); 