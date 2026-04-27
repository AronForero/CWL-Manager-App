# Moni-Facturas — Contexto del proyecto

Aplicación web que automatiza la facturación mensual de **Coworking Labs** (Cámara de Comercio de Bucaramanga). Reemplaza un proceso manual de Excel que el coordinador hacía cada mes para ~12 empresas activas.

## Stack

- **Backend**: FastAPI 0.111 + Python 3.12
- **Base de datos**: PostgreSQL 16
- **Frontend**: Jinja2 templates + HTMX + Pico CSS (CDN)
- **Excel**: openpyxl (lee plantillas, escribe valores calculados)
- **Contenedores**: Docker Compose (local ahora, VPS en el futuro)

## Cómo correr la aplicación

```bash
docker compose up -d                                        # iniciar
docker compose exec app python scripts/import_excel.py      # solo la primera vez
# Abrir http://localhost:8000

docker compose restart app   # recargar código Python
docker compose down          # apagar (los datos persisten)
```

## Estructura clave

```
Moni-facturas/
├── docker-compose.yml
├── .env                          # credenciales DB (no commitear)
├── guias-excel/                  # plantillas Excel originales (read-only en Docker)
│   ├── orden-recaudo.xlsx        # empresas regulares
│   ├── facturacion-credito.xlsx  # Fondo Emprender
│   └── CONTROL-GENERAL-2026.xlsx # fuente de la importación inicial
├── docs/
│   ├── features.md               # guía de funcionalidades
│   ├── technical.md              # documentación técnica detallada
│   ├── how-to-run.md             # guía Windows para no-técnicos
│   └── ROADMAP-v2.md             # feature de email pendiente
└── backend/
    ├── app/
    │   ├── main.py               # startup: siembra tarifas + festivos
    │   ├── models.py             # ORM: Company, Contract, ContractSpace, MonthlyBilling, ColombianHoliday
    │   ├── routers/
    │   │   ├── companies.py      # CRUD empresas/contratos/espacios
    │   │   ├── billing.py        # generación y descarga de Excel
    │   │   └── payments.py       # marcado de estado de pagos
    │   └── services/
    │       ├── tariff.py         # ← lógica de negocio principal
    │       ├── holiday_calc.py   # festivos CO + 3er día hábil
    │       └── excel_gen.py      # escribe los .xlsx en memoria
    └── scripts/
        └── import_excel.py       # bootstrap desde CONTROL-GENERAL-2026.xlsx
```

## Reglas de negocio críticas

### Tiers de tarifa
| Meses acumulados | Descuento | Tier |
|---|---|---|
| 1 – 12 | 50% | 1 |
| 13 – 24 | 25% | 2 |
| 25 – 60 | Sin descuento | 3 (Full) |
| 61+ | Bloqueada | — |

- Los meses se acumulan a través de **múltiples contratos** (re-ingresos continúan el conteo).
- El cálculo usa `relativedelta` — no aritmética simple — para manejar correctamente meses con inicio distinto al día 1.

### Mes de transición de tarifa
Cuando el aniversario del tier cae **dentro** del mes de facturación:
```
días_vieja_tarifa = transition_date.day - 1
días_nueva_tarifa = 30 - días_vieja_tarifa
subtotal = (daily_old × días_vieja) + (daily_new × días_nueva)
VALOR_DÍA = subtotal / 30   ← siempre subtotal/30, nunca vacío
```

### Fórmulas IVA
```
daily_rate  = (monthly_rate_with_iva / 1.19) / 30
subtotal    = daily_rate * 30
total       = subtotal * 1.19
```

### Fecha límite de pago
Último día calendario del mes facturado (p. ej. mayo → 31 de mayo). Función: `last_day_of_month(year, month)` en `holiday_calc.py`.

## Tarifas actuales (con IVA incluido)

| Tipo | Año 1 | Año 2 | Full |
|---|---|---|---|
| A (móvil) | 250,879 | 376,319 | 501,759 |
| B (semi-privado) | 430,079 | 645,118 | 860,158 |
| C (oficina 6p) | 1,003,517 | 1,505,276 | 2,007,035 |
| D (oficina 7p) | 1,003,517 | 1,505,276 | 2,007,035 |

## Empresas actuales (12 activas)

| NIT | Empresa | Tipo | Notas |
|---|---|---|---|
| 901703496 | INSMART TECHNOLOGY SAS | Regular | 1×B |
| 901581424 | SWEETCARE SAS | Regular | 1×A |
| 901097244 | SOLENIUM SAS | Regular | 4×A |
| 901815791 | BFREE ACTIVE TRAVEL SAS | Regular | 1×A |
| 900816899 | INNOVACION Y DESARROLLO COLOMBIA IDCO SAS | Regular | 1×D |
| 901080910 | PROSPECTIVE ING SAS | Regular | 1×C + 1×B |
| 901818306 | ESTANDAR & EXCELENCIA SAS BIC | Regular | 1×B |
| 901890871 | ENG FORMACION & CONSULTORIA SAS | Regular | 1×A |
| 900759077 | GROUND LIGHTNING SAS | Regular | 1×A |
| 901943456 | PIXEL CAP SAS | **Fondo Emprender** | 1×A, REF 104001 |
| 901988137 | FUNDACIÓN ISABERRY | Regular | 1×A |
| 900748137 | TI&CON SAS | Regular | 1×A |

**Fondo Emprender**: PIXEL CAP usa el archivo `facturacion-credito.xlsx` en lugar del `orden-recaudo.xlsx`. Si se agrega otra empresa FE, marcar `is_fondo_emprender = true` en su perfil.

## Excel generado

- **Empresas regulares** → `orden-recaudo-[MES][AÑO].xlsx` (hoja OrdRecaudo, datos desde fila 3)
- **Fondo Emprender** → `facturacion-credito-[MES][AÑO].xlsx` (hoja Detalle Facturación CWL26, datos desde fila 4)
- Columnas A vacía en credito (datos empiezan en col B)
- `producto=11036`, `id_vendedor=2`, `promotor="VENDEDOR GENERAL"` son constantes iguales para todas las empresas

## Gotchas importantes

- **`relativedelta` es obligatorio** para contar meses. La aritmética simple `(end.year-start.year)*12 + (end.month-start.month)` falla cuando el contrato inicia en un día distinto al 1 (ej. GROUND LIGHTNING inicia el 9 de abril).
- **El CECO en CONTROL-GENERAL tiene sufijo de año** (`"W0414-23 (2025)"`). La función `_clean_ceco()` en `excel_gen.py` lo elimina antes de escribir al Excel.
- **El volumen de Docker mapea `./backend:/app:rw`** con recarga automática. Si uvicorn no detecta el cambio, usar `docker compose restart app`.
- **La importación es idempotente**: si una empresa ya existe (mismo NIT), se omite sin error.
- **Los festivos se siembran en startup** (`seed_holidays` en `main.py`). Solo agrega los que no existen.

## Próximas features (ver docs/ROADMAP-v2.md)

- Envío automático de facturas por email al generar (SMTP/Resend)
- Campo `sent_at` en `monthly_billings`
