/*
The initialisation script to import locations and units data into an empty database,
from within the docker container. This script is automatically executed by docker
compose after `create_tables.sql`.
 */

-- import locations data
\copy locations FROM 'docker-entrypoint-initdb.d/data/locations.csv' DELIMITER ',' CSV HEADER;

-- import units data
\copy units FROM 'docker-entrypoint-initdb.d/data/units.csv' DELIMITER ',' CSV HEADER;
