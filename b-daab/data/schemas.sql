-- B-DAAB Database Schema
-- Bengali NL-to-SQL Benchmark

-- Healthcare domain
CREATE TABLE IF NOT EXISTS hospitals (
    id      INTEGER PRIMARY KEY,
    name    VARCHAR NOT NULL,
    city    VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id          INTEGER PRIMARY KEY,
    name        VARCHAR NOT NULL,
    hospital_id INTEGER REFERENCES hospitals(id)
);

-- Education domain
CREATE TABLE IF NOT EXISTS schools (
    id      INTEGER PRIMARY KEY,
    name    VARCHAR NOT NULL,
    city    VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id        INTEGER PRIMARY KEY,
    name      VARCHAR NOT NULL,
    school_id INTEGER REFERENCES schools(id)
);

-- Commerce domain
CREATE TABLE IF NOT EXISTS shops (
    id         INTEGER PRIMARY KEY,
    name       VARCHAR NOT NULL,
    owner_name VARCHAR NOT NULL,
    city       VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id      INTEGER PRIMARY KEY,
    name    VARCHAR NOT NULL,
    shop_id INTEGER REFERENCES shops(id),
    price   DECIMAL(10, 2) NOT NULL
)
