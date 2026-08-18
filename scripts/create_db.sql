-- Elektron Kutubxona uchun PostgreSQL bazasi va foydalanuvchisini yaratadi.
--
-- Ishga tushirish (Windows PowerShell):
--   & "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -f scripts\create_db.sql
--
-- Ishga tushirish (Linux / macOS):
--   sudo -u postgres psql -f scripts/create_db.sql
--
-- Parolni o'zgartirsangiz, .env faylidagi DB_PASSWORD ni ham o'zgartiring.

CREATE USER kutubxona_user WITH PASSWORD 'kutubxona_pass123';

CREATE DATABASE kutubxona_db OWNER kutubxona_user ENCODING 'UTF8';

GRANT ALL PRIVILEGES ON DATABASE kutubxona_db TO kutubxona_user;
