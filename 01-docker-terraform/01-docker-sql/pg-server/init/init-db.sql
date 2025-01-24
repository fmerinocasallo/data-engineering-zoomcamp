-- Update schemas in the current database (de_zoomcamp)
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA nyc_taxi;

-- Update password from postgres (admin)
ALTER USER postgres WITH ENCRYPTED PASSWORD 'SCRAM-SHA-256$4096:2e6SBLkCNpp+FljVIo5vrw==$2+9d4e1jr+i27dnxoEnIH28fdAhRmJvYsa9x+UVnwVw=:ZlUtYDmeJbA+BT0q2QudXoTa4BAFTpVp4Rj7w3n3rXI=';

-- Create a new writer role (read & write)
CREATE ROLE writer NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN NOREPLICATION NOBYPASSRLS;
GRANT CONNECT, CREATE ON DATABASE de_zoomcamp TO writer;
GRANT USAGE, CREATE ON SCHEMA nyc_taxi TO writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA nyc_taxi TO writer;

-- Create a new reader role (read-only)
CREATE ROLE reader NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOLOGIN NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE de_zoomcamp TO reader;
GRANT USAGE ON SCHEMA nyc_taxi TO reader;
GRANT SELECT ON ALL TABLES IN SCHEMA nyc_taxi TO reader;

-- Create a new user (fmerinocasallo_writer) and grant read & write access to
-- all already created tables in the `nyc_taxi` schema
CREATE USER fmerinocasallo_writer WITH ENCRYPTED PASSWORD 'SCRAM-SHA-256$4096:uMOkAQtSqAJPKkji13KPXw==$zXz1/xO0Cg8sFm4dPIvxOJ9aO3RUqV585NCGkiW0LV4=:4YlfgP03ujHDmQZoqutpmFKne63CBO22ehWGIRgLQoI=';
GRANT writer TO fmerinocasallo_writer;

-- Create a new user (fmerinocasallo) and grant read-only access to all already
-- created tables in the `nyc_taxi` schema
CREATE USER fmerinocasallo_reader WITH ENCRYPTED PASSWORD 'SCRAM-SHA-256$4096:8z57J5HjIF2XAoJqM7axwg==$xjrHp0IfcQ6qRb1Cnezz769zns/FvIvJx5Yfi/88lK4=:/Fjc1UjOOLHa99p6/aOqYuV8f6EZjAJe6vwHiAkbMto=';
GRANT reader TO fmerinocasallo_reader;
