# Moni-Facturas — Documentación Técnica

## Arquitectura general

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                       │
│                                                       │
│  ┌─────────────────┐      ┌────────────────────────┐ │
│  │   app (FastAPI)  │─────▶│   db (PostgreSQL 16)   │ │
│  │   puerto 8000    │      │   puerto 5432          │ │
│  └────────┬─────────┘      └────────────────────────┘ │
│           │                                           │
│           │ volumen (read-only)                       │
│           ▼                                           │
│  ┌──────────────────┐                                 │
│  │  ./guias-excel/  │  (plantillas Excel originales)  │
│  └──────────────────┘                                 │
└─────────────────────────────────────────────────────┘
```

## Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Python | 3.12 |
| Framework web | FastAPI | 0.111.1 |
| Servidor ASGI | Uvicorn (con watchfiles) | 0.30.1 |
| ORM | SQLAlchemy | 2.0.31 |
| Driver de base de datos | psycopg2-binary | 2.9.9 |
| Base de datos | PostgreSQL | 16 |
| Plantillas HTML | Jinja2 | 3.1.4 |
| Manejo de formularios | python-multipart | 0.0.9 |
| Generación/lectura Excel | openpyxl | 3.1.5 |
| Festivos colombianos | holidays | 0.54 |
| Aritmética de fechas | python-dateutil | 2.9.0 |
| Análisis de datos (import) | pandas | 2.2.2 |
| CSS (CDN) | Pico CSS | v2 |
| Contenedores | Docker Compose | — |

---

## Estructura del proyecto

```
CWL-MANAGER-APP/
├── docker-compose.yml          # Servicios: app + db
├── .env                        # Variables de entorno (creado desde .env.example)
├── .env.example                # Plantilla de variables de entorno
├── guias-excel/                # Plantillas Excel (montadas como volumen read-only)
│   ├── orden-recaudo.xlsx
│   ├── facturacion-credito.xlsx
│   └── CONTROL-GENERAL-2026.xlsx
├── docs/                       # Documentación
│   ├── features.md
│   ├── technical.md
│   ├── how-to-run.md
│   └── ROADMAP-v2.md
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── scripts/
    │   └── import_excel.py     # Script de importación inicial
    └── app/
        ├── __init__.py
        ├── main.py             # App FastAPI + startup (seed de tarifas y festivos)
        ├── database.py         # Engine SQLAlchemy + sesión
        ├── models.py           # Modelos ORM (tablas)
        ├── routers/
        │   ├── companies.py    # CRUD de empresas, contratos y espacios
        │   ├── billing.py      # Generación, descarga e historial de facturación
        │   └── payments.py     # Marcado de estado de pagos
        ├── services/
        │   ├── tariff.py       # Cálculo de tier y valores de facturación
        │   ├── holiday_calc.py # Festivos colombianos y 3er día hábil
        │   └── excel_gen.py    # Generación de archivos Excel en memoria
        └── templates/
            ├── base.html
            ├── dashboard.html
            ├── companies/
            │   ├── list.html
            │   ├── detail.html
            │   └── form.html
            └── billing/
                ├── generate.html
                └── history.html
```

---

## Base de datos

### Esquema

#### `tariff_rates`
Tabla de referencia, sembrada en startup. Nunca cambia en producción.

| Columna | Tipo | Descripción |
|---|---|---|
| id | SERIAL PK | — |
| space_type | CHAR(1) | A, B, C o D |
| year_number | INTEGER | 1 (50%), 2 (25%), 3 (Full) |
| monthly_rate_with_iva | NUMERIC(12,2) | Tarifa mensual con IVA incluido |

Valores sembrados:

| Tipo | Año 1 | Año 2 | Año 3 (Full) |
|---|---|---|---|
| A | 250,879 | 376,319 | 501,759 |
| B | 430,079 | 645,118 | 860,158 |
| C | 1,003,517 | 1,505,276 | 2,007,035 |
| D | 1,254,397 | 1,881,595 | 2,508,794 |

#### `companies`

| Columna | Tipo | Descripción |
|---|---|---|
| id | SERIAL PK | — |
| name | VARCHAR(255) | Razón social |
| nit | VARCHAR(20) UNIQUE | NIT (sin dígito de verificación) |
| billing_email | VARCHAR(255) | Correo de facturación |
| address | TEXT | Dirección (para el Excel) |
| is_affiliated | BOOLEAN | ¿Afiliado a Cámara? |
| is_fondo_emprender | BOOLEAN | Si es true, va al archivo `facturacion-credito.xlsx` |
| fondo_emprender_ref | INTEGER | Código REF del SENA |
| created_at | TIMESTAMPTZ | Fecha de creación del registro |

#### `contracts`

| Columna | Tipo | Descripción |
|---|---|---|
| id | SERIAL PK | — |
| company_id | FK → companies | — |
| contract_number | VARCHAR(50) | Número de contrato |
| ceco | VARCHAR(30) UNIQUE | Código del centro de costos |
| start_date | DATE | Inicio del contrato (base para el cálculo de tier) |
| end_date | DATE | Fin del contrato (NULL si activo) |
| is_active | BOOLEAN | Contrato vigente |

Una empresa puede tener múltiples contratos a lo largo del tiempo (re-ingresos). El tier se calcula sumando los meses activos de **todos** los contratos.

#### `contract_spaces`

| Columna | Tipo | Descripción |
|---|---|---|
| id | SERIAL PK | — |
| contract_id | FK → contracts | — |
| space_type | CHAR(1) | A, B, C o D |
| quantity | INTEGER | Número de espacios de ese tipo |
| start_date | DATE | Desde cuándo aplica este espacio |
| end_date | DATE | Hasta cuándo (NULL si activo) |
| is_active | BOOLEAN | Espacio vigente |

#### `monthly_billings`

| Columna | Tipo | Descripción |
|---|---|---|
| id | SERIAL PK | — |
| company_id | FK → companies | — |
| billing_month | INTEGER | 1–12 |
| billing_year | INTEGER | Año |
| days_count | INTEGER | Siempre 30 |
| daily_rate_without_iva | NUMERIC(14,4) | VALOR DÍA = subtotal / 30 |
| subtotal_without_iva | NUMERIC(12,2) | Base gravable |
| total_with_iva | NUMERIC(12,2) | Total = subtotal × 1.19 |
| payment_deadline | DATE | 3er día hábil del mes siguiente |
| status | VARCHAR(20) | `pendiente`, `pagado`, `revisar` |
| order_reference | VARCHAR(50) | Referencia ORD-FRA cuando se paga |
| generated_at | TIMESTAMPTZ | Cuándo se generó el registro |

Restricción UNIQUE sobre `(company_id, billing_month, billing_year)` — solo existe un registro por empresa por mes.

#### `colombian_holidays`

| Columna | Tipo | Descripción |
|---|---|---|
| id | SERIAL PK | — |
| holiday_date | DATE UNIQUE | Fecha del festivo |
| description | VARCHAR(100) | Nombre del festivo |

Poblada al inicio con festivos de Colombia del 2025 al 2030 usando la librería `holidays`.

---

## Lógica de negocio central (`services/tariff.py`)

### Cálculo del tier

```
_total_active_months_before(company, billing_year, billing_month)
```

Para cada contrato de la empresa, calcula los meses completos entre `start_date` y el primer día del mes a facturar (`target`). Usa `relativedelta` (no aritmética simple) para manejar correctamente meses de inicio distintos al día 1.

```
tier = 1   si total_months < 12    (50% descuento)
tier = 2   si 12 ≤ total_months < 24  (25% descuento)
tier = 3   si 24 ≤ total_months < 60  (Full)
bloqueada  si total_months ≥ 60
```

### Detección de mes de transición

Si `tier(months_before) ≠ tier(months_before + 1)` hay una transición dentro del mes de facturación.

La fecha exacta de transición se calcula como:
```python
boundary = 12 if tier_start == 1 else 24
months_into_current_contract = boundary - months_before_current_contract_started
transition_date = current_contract.start_date + relativedelta(months=months_into_current_contract)
```

### Cálculo del valor en mes de transición

```python
days_old = transition_date.day - 1   # días al principio del mes con tarifa vieja
days_new = 30 - days_old             # días restantes con tarifa nueva

subtotal = (daily_rate_old * days_old + daily_rate_new * days_new) * quantity
daily_rate = subtotal / 30           # tasa diaria ponderada (para VALOR DÍA)
total = subtotal * 1.19
```

### Cálculo estándar (sin transición)

```python
daily_rate_without_iva = (monthly_rate_with_iva / 1.19) / 30
subtotal_without_iva   = daily_rate_without_iva * 30  # = monthly_rate / 1.19
total_with_iva         = subtotal_without_iva * 1.19  # = monthly_rate
```

---

## Generación de Excel (`services/excel_gen.py`)

El sistema **lee la plantilla original** (desde `/app/guias-excel/`) usando openpyxl, borra las filas de datos existentes y escribe los nuevos valores como literales (no fórmulas). El archivo se guarda en memoria (`BytesIO`) y se entrega como descarga HTTP.

### Mapeo de columnas — `orden-recaudo.xlsx` (hoja OrdRecaudo)

| Col | Campo Excel | Fuente |
|---|---|---|
| A | # | Índice secuencial |
| B | PRODUCTO | Constante 11036 |
| C | ID VENDEDOR | Constante 2 |
| D | PROMOTOR | Constante "VENDEDOR GENERAL" |
| E | CLIENTE | `company.name` |
| F | ID CLIENTE | `company.nit` (entero) |
| G | CECO | `contract.ceco` (sin sufijo de año) |
| H | CORREO FACTURACIÓN | `company.billing_email` |
| I | OBSERVACIÓN | Generado dinámicamente (ver abajo) |
| J | MES A FACTURAR | Abreviatura española: ENE, FEB… |
| K | DÍAS DE CONCESIÓN | Constante 30 |
| L | VALOR DÍA (Sin IVA) | `billing.daily_rate_without_iva` |
| M | V.SUBTOTAL (Sin IVA) | `billing.subtotal_without_iva` |
| N | VALOR TOTAL (IVA incluido) | `billing.total_with_iva` |
| O | FECHA 1 LÍMITE pago | `billing.payment_deadline` (formato MM/DD/YYYY) |
| P | DIRECCIÓN | `company.address` |
| Q | ¿ES AFILIADO? | "SI" / "NO" |

### Plantilla de OBSERVACIÓN (orden-recaudo)

```
Pago DEL SERVICIO PROG. COWORKING LABS: {DESCRIPCIÓN_ESPACIOS}
CECO:{CECO} [MES {MES}].
Remitir comprobante de pago a: coordinador.coworking@camaradirecta.com y
tesoreria.ccb@camaradirecta.com. Genere su pago exacto sin redondear valores.
```

`DESCRIPCIÓN_ESPACIOS` usa palabras en español: "UN (1) ESPACIO DE TRABAJO (TIPO B)", "CUATRO (4) ESPACIOS DE TRABAJO (TIPO A)", etc. Si la empresa tiene múltiples tipos de espacio, se separan con " Y ".

### Mapeo de columnas — `facturacion-credito.xlsx` (hoja Detalle Facturación CWL26)

| Col | Campo Excel | Fuente |
|---|---|---|
| B | # | Índice secuencial |
| C | PRODUCTO | Constante 11036 |
| D | CENTRO DE COSTO | `contract.ceco` |
| E | REF | `company.fondo_emprender_ref` |
| F | ENTIDAD - CLIENTE | `company.name` |
| G | NIT | `company.nit` |
| H | CONCEPTO | Generado dinámicamente |
| I | MES A FACTURAR | Abreviatura española |
| J | DÍAS DE CONCESIÓN | Constante 30 |
| K | VALOR DÍA (Antes de IVA) | `billing.daily_rate_without_iva` |
| L | V.SUBTOTAL (Antes de IVA) | `billing.subtotal_without_iva` |
| M | VALOR TOTAL (IVA 19% incluido) | `billing.total_with_iva` |
| N | TIEMPO DE PAGO | Constante "10 días" |
| O | OBSERVACIONES | Instrucciones bancarias fijas |

---

## Festivos colombianos (`services/holiday_calc.py`)

Usa la librería `holidays` con `holidays.Colombia(years=year)` para obtener todos los festivos del año. Se persisten en la tabla `colombian_holidays` al iniciar la aplicación (solo agrega los que no existen, es idempotente).

### Cálculo de la fecha límite

```python
def last_day_of_month(year, month):
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)
```

---

## Variables de entorno

| Variable | Ejemplo | Descripción |
|---|---|---|
| `POSTGRES_DB` | `monifacturas` | Nombre de la base de datos |
| `POSTGRES_USER` | `moni` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `changeme` | Contraseña de PostgreSQL |
| `DATABASE_URL` | (construida por docker-compose) | URL de conexión SQLAlchemy |

La variable `DATABASE_URL` es construida automáticamente por docker-compose usando las tres anteriores. No es necesario definirla manualmente.

---

## Comandos útiles

```bash
# Iniciar la aplicación
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f app

# Detener la aplicación
docker compose down

# Importar datos iniciales desde Excel
docker compose exec app python scripts/import_excel.py

# Acceder a la base de datos directamente
docker compose exec db psql -U moni -d monifacturas

# Reconstruir la imagen (después de cambios en requirements.txt)
docker compose up -d --build

# Reiniciar solo el servidor web (después de cambios en código Python)
docker compose restart app
```

---

## Script de importación (`scripts/import_excel.py`)

Lee la hoja `Control Pagos-2026` del archivo `CONTROL-GENERAL-2026.xlsx` y crea los registros en la base de datos. Es idempotente: si una empresa con el mismo NIT ya existe, la omite.

**Lógica de importación:**
1. Lee fila por fila a partir de la fila 4 (encabezados en fila 3).
2. Si `NOMBRE ENTIDAD` está vacío, para.
3. Limpia el CECO (elimina el sufijo ` (2025)` u otros años).
4. Maneja tipos de espacio compuestos (ej. `"C | B"` con `"1 | 1"`).
5. Identifica empresas Fondo Emprender por NIT (hardcoded en el script para los conocidos).
6. Crea: `Company` → `Contract` → `ContractSpace` (uno por tipo de espacio).

**Para agregar nuevas empresas Fondo Emprender al script**, editar el set `FONDO_EMPRENDER_NITS` y el dict `FONDO_EMPRENDER_REFS` en `backend/scripts/import_excel.py`.

---

## Extensión del sistema

### Agregar nuevas tarifas
Si Cámara actualiza los valores de tarifa, modificar la función `_seed_tariffs` en `backend/app/main.py`. Los valores actuales son los de 2025-2026.

### Agregar más años de festivos
La función `seed_holidays` en `holiday_calc.py` acepta `from_year` y `to_year`. Por defecto siembra hasta 2030. Para extender:
```python
seed_holidays(db, from_year=2025, to_year=2035)
```
O ejecutar desde el shell del contenedor:
```bash
docker compose exec app python3 -c "
from app.database import SessionLocal
from app.services.holiday_calc import seed_holidays
db = SessionLocal()
seed_holidays(db, from_year=2031, to_year=2035)
db.close()
print('Festivos agregados')
"
```
