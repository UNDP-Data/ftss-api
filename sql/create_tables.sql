/*
The initialisation script to create tables in an empty database.

The database schema assumes a denormalised form. This allows to insert data "as is", minimising
the differences between the API layer and database layer and making CRUD operations simpler.
Given the expected size of the database, this design will have marginal impact on the efficiency
even in the long run.

The database tables comprise:

1. Users
2. Signals
3. Trends
4. Connections – a junction table for connected signals/trends to model a many-to-many relationship.
5. Locations – stores country and area metadata based on UN M49 that are used for signal location.
6. Units – stores metadata on UNDP units used to assign user units and filter signals.
*/

-- users table and indices
CREATE TABLE users (
	id SERIAL PRIMARY KEY,
	created_at TIMESTAMP NOT NULL DEFAULT NOW(),
	email VARCHAR(255) UNIQUE NOT NULL,
	role VARCHAR(255) NOT NULL,
	name VARCHAR(255),
	unit  VARCHAR(255),
    acclab BOOLEAN
);

CREATE INDEX ON users (email);
CREATE INDEX ON users (role);

-- signals table and indices
CREATE TABLE signals (
	id SERIAL PRIMARY KEY,
	status VARCHAR(255) NOT NULL,
	created_at TIMESTAMP NOT NULL DEFAULT NOW(),
	created_by VARCHAR(255) NOT NULL,
	created_for VARCHAR(255),
	modified_at TIMESTAMP NOT NULL DEFAULT NOW(),
	modified_by VARCHAR(255) NOT NULL,
	headline TEXT,
	description TEXT,
	attachment TEXT,  -- a URL to Azure Blob Storage
	steep_primary TEXT,
	steep_secondary TEXT[],
	signature_primary TEXT,
	signature_secondary TEXT[],
	sdgs TEXT[],
	created_unit VARCHAR(255),
	url TEXT,
	relevance TEXT,
	keywords TEXT[],
	location TEXT,
	score TEXT,
	text_search_field tsvector GENERATED ALWAYS AS (to_tsvector('english', headline || ' ' || description)) STORED
);

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
    score
);
CREATE INDEX ON signals USING GIN (text_search_field);

-- trends table and indices
CREATE TABLE trends (
	id SERIAL PRIMARY KEY,
	status VARCHAR(255) NOT NULL,
	created_at TIMESTAMP NOT NULL DEFAULT NOW(),
	created_by VARCHAR(255) NOT NULL,
	created_for TEXT,
	modified_at TIMESTAMP NOT NULL DEFAULT NOW(),
	modified_by VARCHAR(255) NOT NULL,
	headline TEXT,
	description TEXT,
	attachment TEXT,
	steep_primary TEXT,
	steep_secondary TEXT[],
	signature_primary TEXT,
	signature_secondary TEXT[],
	sdgs TEXT[],
	assigned_to TEXT,
	time_horizon TEXT,
	impact_rating TEXT,
	impact_description TEXT,
	text_search_field tsvector GENERATED ALWAYS AS (to_tsvector('english', headline || ' ' || description)) STORED
);

CREATE INDEX ON trends (
    status,
    created_for,
    assigned_to,
    steep_primary,
    steep_secondary,
    signature_primary,
    signature_secondary,
    sdgs,
    time_horizon,
    impact_rating
);
CREATE INDEX ON trends USING GIN (text_search_field);

-- junction table for connected signals/trends to model many-to-many relationship
CREATE TABLE connections (
    signal_id INT REFERENCES signals(id) ON DELETE CASCADE,
    trend_id INT REFERENCES trends(id) ON DELETE CASCADE,
	created_at TIMESTAMP NOT NULL DEFAULT NOW(),
	created_by VARCHAR(255) NOT NULL,
	CONSTRAINT connection_pk PRIMARY KEY (signal_id, trend_id)
);

-- locations table and indices
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    iso VARCHAR(3),
    region VARCHAR(128) NOT NULL,
    bureau VARCHAR(5)
);
CREATE INDEX ON locations (name, region, bureau);

-- units table and indices
CREATE TABLE units (
	id SERIAL PRIMARY KEY,
	name TEXT NOT NULL,
	region VARCHAR(255)
);
CREATE INDEX ON units (name, region);
