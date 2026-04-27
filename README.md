# Moni-Facturas

Aplicación web que automatiza la facturación mensual de **Coworking Labs** (Cámara de Comercio de Bucaramanga), reemplazando un proceso manual en Excel que el coordinador hacía cada mes para varias empresas activas.

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [docs/how-to-run.md](docs/how-to-run.md) | Cómo ejecutar la app en **Windows** (guía paso a paso para perfiles no técnicos) |
| [docs/features.md](docs/features.md) | **Guía de funcionalidades**: pantallas, flujos, botones, columnas y reglas de uso |
| [docs/technical.md](docs/technical.md) | **Documentación técnica**: arquitectura, stack, esquema de base de datos, lógica de cálculo y Excel |

## Inicio rápido (Docker)

Requisitos: [Docker](https://www.docker.com/) y Docker Compose.

```bash
docker compose up -d
docker compose exec app python scripts/import_excel.py   # solo la primera vez: importa desde guías Excel
```

Abre en el navegador: `http://localhost:8000`

- **Cerrar** (los datos de PostgreSQL persisten): `docker compose down`  
- **Reiniciar la app** tras cambios de código Python: `docker compose restart app`  
- Copia de variables de entorno: ver `.env.example` (crear `.env` para credenciales locales).

Comandos adicionales, logs, import y troubleshooting detallado: [docs/how-to-run.md](docs/how-to-run.md) y sección *Comandos útiles* en [docs/technical.md](docs/technical.md).

## Stack (resumen)

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Base de datos | PostgreSQL 16, SQLAlchemy 2 |
| Interfaz | Jinja2, HTMX, Pico CSS (CDN) |
| Excel | openpyxl (plantillas en `guias-excel/`) |
| Contenedores | Docker Compose |

Detalle de versiones y dependencias: [docs/technical.md](docs/technical.md#stack-tecnológico).

## Estructura del repositorio (resumida)

```
.
├── docker-compose.yml
├── .env.example
├── guias-excel/              # Plantillas y CONTROL-GENERAL (import inicial)
├── docs/                     # Documentación detallada
└── backend/
    ├── app/                  # FastAPI: main, modelos, routers, servicios, plantillas
    ├── scripts/
    │   └── import_excel.py # Importación idempotente desde Excel
    ├── Dockerfile
    └── requirements.txt
```

Estructura completa: [docs/technical.md](docs/technical.md#estructura-del-proyecto).

## Funcionalidades principales

- **Dashboard**: resumen de empresas activas, facturación del mes y avisos de límite de permanencia.
- **Empresas**: alta/edición, contratos, espacios (tipos A–D), Fondo Emprender, historial de facturación y marcado de pagos.
- **Facturación**: previsualización por mes/año, cálculo de tarifas por *tier*, meses de transición y generación de Excel.
- **Historial**: descarga de `orden-recaudo` y `facturacion-credito` por período, gestión de estados (pagado, pendiente, revisar).

Flujos y reglas de pantalla: [docs/features.md](docs/features.md).

## Reglas de negocio (muy resumido)

- Tarifas por **años acumulados** (50 % → 25 % → *full*), con límite máximo de **60 meses** de permanencia.  
- Los **meses** se acumulan entre contratos (reingresos). Cálculo con `relativedelta`, no solo diferencia de meses del calendario.  
- **IVA**: tarifas almacenadas con IVA; el sistema descompone para subtotal e impuestos.  
- **Días de concesión** en facturación: 30.  
- **Fecha límite de pago** y archivos generados: ver [docs/features.md](docs/features.md#5-generar-facturación-billing) y [docs/features.md](docs/features.md#7-archivos-excel-generados).

Lógica en código y esquema de datos: [docs/technical.md](docs/technical.md#lógica-de-negocio-central-servicestariffpy).
