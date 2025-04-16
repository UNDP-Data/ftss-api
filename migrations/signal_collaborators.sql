-- Add is_draft column to signals table
ALTER TABLE signals ADD COLUMN IF NOT EXISTS is_draft BOOLEAN NOT NULL DEFAULT TRUE;

-- Create user groups table
CREATE TABLE IF NOT EXISTS user_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create user group members table
CREATE TABLE IF NOT EXISTS user_group_members (
    group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (group_id, user_email)
);

-- Create signal collaborators tables
CREATE TABLE IF NOT EXISTS signal_collaborators (
    signal_id INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (signal_id, user_email)
);

CREATE TABLE IF NOT EXISTS signal_collaborator_groups (
    signal_id INTEGER NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (signal_id, group_id)
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_group_members_user ON user_group_members(user_email);
CREATE INDEX IF NOT EXISTS idx_signal_collaborators_user ON signal_collaborators(user_email);
CREATE INDEX IF NOT EXISTS idx_signal_collaborator_groups_group ON signal_collaborator_groups(group_id); 