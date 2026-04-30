-- =============================================================================
-- seed.sql — Datos iniciales de Moni-Facturas
-- Fuente: guias-excel/CONTROL-GENERAL-2026.xlsx (hoja "Control Pagos-2026")
-- Empresas ordenadas por INICIÓ VINCULACIÓN (más antiguo primero).
--
-- Uso:
--   docker compose exec -T db psql -U moni -d monifacturas < backend/scripts/seed.sql
--
-- NOTA: Los festivos colombianos y las tarifas también son sembrados
-- automáticamente por main.py al iniciar la app. Este script los incluye
-- para que el estado de la BD sea completo antes del primer arranque.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Limpiar todas las tablas y reiniciar secuencias
-- -----------------------------------------------------------------------------
TRUNCATE TABLE
    monthly_billings,
    contract_spaces,
    contracts,
    companies,
    tariff_rates,
    colombian_holidays
RESTART IDENTITY CASCADE;

-- -----------------------------------------------------------------------------
-- 2. Tarifas (con IVA incluido)
-- Normalmente sembradas por main.py en startup; se incluyen aquí para
-- garantizar integridad si el SQL se corre antes del primer arranque.
-- -----------------------------------------------------------------------------
INSERT INTO tariff_rates (id, space_type, year_number, monthly_rate_with_iva) VALUES
    (1,  'A', 1,  250879),
    (2,  'A', 2,  376319),
    (3,  'A', 3,  501759),
    (4,  'B', 1,  430079),
    (5,  'B', 2,  645118),
    (6,  'B', 3,  860158),
    (7,  'C', 1, 1003517),
    (8,  'C', 2, 1505276),
    (9,  'C', 3, 2007035),
    (10, 'D', 1, 1254397),
    (11, 'D', 2, 1881595),
    (12, 'D', 3, 2508794);

-- -----------------------------------------------------------------------------
-- 3. Empresas — ordenadas por INICIÓ VINCULACIÓN
-- billing_email: solo el primer correo (mismo criterio que import_excel.py)
-- address: NULL (no estaba en el Excel; se puede actualizar desde la UI)
-- is_affiliated: false por defecto (actualizar desde la UI si corresponde)
-- -----------------------------------------------------------------------------
INSERT INTO companies (id, name, nit, billing_email, address, is_affiliated, is_fondo_emprender, fondo_emprender_ref) VALUES
    (1,  'SWEETCARE SAS',                                     '901581424', 'contactenos@sweetcare.com.co',   NULL, false, false, NULL),
    (2,  'SOLENIUM SAS',                                      '901097244', 'facturacion@solenium.co',        NULL, false, false, NULL),
    (3,  'INSMART TECHNOLOGY SAS',                            '901703496', 'leonelc964@gmail.com',           NULL, false, false, NULL),
    (4,  'BFREE ACTIVE TRAVEL SAS',                           '901815791', 'hmaya_7@hotmail.com',            NULL, false, false, NULL),
    (5,  'INNOVACION Y DESARROLLO COLOMBIA IDCO SAS',         '900816899', 'crojas@idco.com.co',             NULL, false, false, NULL),
    (6,  'PROSPECTIVE ING SAS',                               '901080910', 'infoprospectiveing@gmail.com',   NULL, false, false, NULL),
    (7,  'ESTANDAR & EXCELENCIA SAS BIC',                     '901818306', 'gerenciaeyesas@gmail.com',       NULL, false, false, NULL),
    (8,  'ENG FORMACION & CONSULTORIA SAS',                   '901890871', 'gerencia@deelicitaciones.com',   NULL, false, false, NULL),
    (9,  'GROUND LIGHTNING SAS',                              '900759077', 'contabilidad@glground.co',       NULL, false, false, NULL),
    (10, 'FUNDACIÓN ISABERRY',                                '901988137', 'BUSINESSKIDSBGA@GMAIL.COM',      NULL, false, false, NULL),
    (11, 'PIXEL CAP SAS',                                     '901943456', 'LUISFF.AYALA@GMAIL.COM',         NULL, false, true,  104001),
    (12, 'TI&CON SAS',                                        '900748137', 'financiero@ticon.com.co',        NULL, false, false, NULL);

-- -----------------------------------------------------------------------------
-- 4. Contratos — uno por empresa, todos activos
-- contract_number: tomado de NRO. CONTRATO del Excel (NULL si estaba vacío)
-- ceco: limpio, sin sufijo " (2025)" ni similares
-- -----------------------------------------------------------------------------
INSERT INTO contracts (id, company_id, contract_number, ceco, start_date, end_date, is_active) VALUES
    (1,  1,  '24',  'W0414-24', '2022-05-01', NULL, true),  -- SWEETCARE
    (2,  2,  '25',  'W0414-25', '2022-10-01', NULL, true),  -- SOLENIUM
    (3,  3,  '23',  'W0414-23', '2023-07-01', NULL, true),  -- INSMART
    (4,  4,  '35',  'W0414-36', '2024-06-01', NULL, true),  -- BFREE
    (5,  5,  '32',  'W0414-30', '2024-10-01', NULL, true),  -- IDCO
    (6,  6,  '28',  'W0414-31', '2025-03-01', NULL, true),  -- PROSPECTIVE ING
    (7,  7,  '29',  'W0414-32', '2025-03-01', NULL, true),  -- ESTANDAR & EXCELENCIA
    (8,  8,  NULL,  'W0414-33', '2025-04-01', NULL, true),  -- ENG FORMACION (sin nro.)
    (9,  9,  '34',  'W0414-34', '2025-04-09', NULL, true),  -- GROUND LIGHTNING
    (10, 10, '43',  'W0414-42', '2025-09-27', NULL, true),  -- FUNDACIÓN ISABERRY
    (11, 11, '44',  'W0414-41', '2025-10-01', NULL, true),  -- PIXEL CAP
    (12, 12, '45',  'W0414-43', '2025-12-15', NULL, true);  -- TI&CON

-- -----------------------------------------------------------------------------
-- 5. Espacios contratados — 13 filas (PROSPECTIVE ING tiene C + B)
-- start_date = start_date del contrato padre
-- -----------------------------------------------------------------------------
INSERT INTO contract_spaces (id, contract_id, space_type, quantity, start_date, end_date, is_active) VALUES
    (1,  1,  'A', 1, '2022-05-01', NULL, true),  -- SWEETCARE:          1×A
    (2,  2,  'A', 4, '2022-10-01', NULL, true),  -- SOLENIUM:           4×A
    (3,  3,  'B', 1, '2023-07-01', NULL, true),  -- INSMART:            1×B
    (4,  4,  'A', 1, '2024-06-01', NULL, true),  -- BFREE:              1×A
    (5,  5,  'D', 1, '2024-10-01', NULL, true),  -- IDCO:               1×D
    (6,  6,  'C', 1, '2025-03-01', NULL, true),  -- PROSPECTIVE ING:    1×C
    (7,  6,  'B', 1, '2025-03-01', NULL, true),  -- PROSPECTIVE ING:    1×B
    (8,  7,  'B', 1, '2025-03-01', NULL, true),  -- ESTANDAR:           1×B
    (9,  8,  'A', 1, '2025-04-01', NULL, true),  -- ENG FORMACION:      1×A
    (10, 9,  'A', 1, '2025-04-09', NULL, true),  -- GROUND LIGHTNING:   1×A
    (11, 10, 'A', 1, '2025-09-27', NULL, true),  -- FUNDACIÓN ISABERRY: 1×A
    (12, 11, 'A', 1, '2025-10-01', NULL, true),  -- PIXEL CAP:          1×A
    (13, 12, 'A', 1, '2025-12-15', NULL, true);  -- TI&CON:             1×A

COMMIT;
