-- Create a single user groups table with direct arrays for signals and users
CREATE TABLE IF NOT EXISTS user_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    signal_ids INTEGER[] NOT NULL DEFAULT '{}',
    user_ids INTEGER[] NOT NULL DEFAULT '{}',
    -- Store collaborator relationships as JSON
    -- Format: {"signal_id": [user_id1, user_id2], ...}
    collaborator_map JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create GIN indexes for faster array lookups
CREATE INDEX IF NOT EXISTS idx_user_groups_signal_ids ON user_groups USING GIN (signal_ids);
CREATE INDEX IF NOT EXISTS idx_user_groups_user_ids ON user_groups USING GIN (user_ids);
CREATE INDEX IF NOT EXISTS idx_user_groups_collaborator_map ON user_groups USING GIN (collaborator_map); 