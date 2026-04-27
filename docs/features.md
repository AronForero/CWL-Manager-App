# Moni-Facturas — Guía de Funcionalidades

Esta guía describe todas las pantallas, funciones y botones disponibles en la versión actual del sistema.

---

## Navegación principal

La barra de navegación en la parte superior de todas las pantallas tiene cuatro enlaces:

| Enlace | Destino | Para qué sirve |
|---|---|---|
| 🏢 Coworking Labs | Dashboard | Volver al inicio |
| Empresas | `/companies/` | Lista de todas las empresas |
| Facturación | `/billing/` | Generar la facturación mensual |
| Historial | `/billing/history` | Ver y descargar facturas pasadas |

---

## 1. Dashboard (`/`)

La página de inicio muestra un resumen del estado actual del programa.

### Tarjetas de resumen
- **Empresas activas**: cuántas empresas tienen contrato vigente en este momento.
- **Total históricas**: total de empresas registradas (activas + inactivas).
- **Facturas [MES] [AÑO]**: cuántas facturas ya fueron generadas para el próximo mes a facturar.
- **Pendientes de pago**: cuántas facturas del próximo mes aún no han sido marcadas como pagadas.

### Alertas de límite de 5 años
Si alguna empresa está a **6 meses o menos** de cumplir su límite de permanencia (60 meses = 5 años), aparece una advertencia en color naranja con el nombre de la empresa y los meses que le quedan.

### Sección de facturación del mes
Muestra el estado de la facturación para el próximo mes:
- Si **no ha sido generada**: aparece un botón "Generar ahora →" que lleva directamente a la página de facturación.
- Si **ya fue generada**: aparece la etiqueta "✓ Generada" y dos botones de descarga:
  - **⬇ Descargar Recaudo**: descarga el archivo `orden-recaudo-[MES][AÑO].xlsx` (empresas regulares).
  - **⬇ Descargar Crédito**: descarga el archivo `facturacion-credito-[MES][AÑO].xlsx` (Fondo Emprender).
- Etiquetas de estado (pagadas / pendientes / por revisar).

### Accesos rápidos
- Botón **+ Nueva empresa**: lleva al formulario de creación.
- Enlace **Ver todas las empresas →**: lleva a la lista completa.

---

## 2. Lista de empresas (`/companies/`)

Tabla con todas las empresas registradas en el sistema.

### Columnas de la tabla
| Columna | Descripción |
|---|---|
| Empresa | Nombre de la empresa. La etiqueta azul **FE** indica que es Fondo Emprender. |
| NIT | Número de identificación tributaria. |
| CECO | Código del centro de costos del contrato activo. |
| Espacios | Espacios contratados actualmente (p. ej. `1×B`, `4×A`). |
| Tarifa | Tarifa vigente: **Año 1 (50%)**, **Año 2 (25%)** o **Full**. |
| Meses | Total de meses acumulados desde el inicio del primer contrato. La etiqueta naranja ⚠ indica que quedan ≤ 6 meses antes del límite. |
| Estado | **Activa** (contrato vigente) o **Inactiva** (contrato cerrado). |
| Ver → | Enlace al detalle de la empresa. |

### Botón "+ Nueva empresa"
Abre el formulario para registrar una empresa nueva. Ver sección 4.

---

## 3. Detalle de empresa (`/companies/{id}`)

Pantalla completa con toda la información de una empresa.

### Panel: Información
Muestra y permite editar:
- Nombre, NIT, email de facturación, dirección.
- Si es **afiliado a Cámara** (afecta la columna "¿ES AFILIADO?" en el Excel).
- Si es **Fondo Emprender** (y su código REF del SENA).

### Panel: Contrato activo
Muestra:
- CECO, número de contrato, fecha de inicio.
- Meses activos acumulados y tarifa actual.
- Meses restantes antes del límite de 5 años (se resalta en naranja si ≤ 6 meses, rojo si ya alcanzó el límite).

Si la empresa **no tiene contrato activo**, aparece un formulario de reactivación (ver más abajo).

### Tabla: Espacios contratados
Lista todos los espacios (activos e inactivos) del contrato actual:
- Tipo (A/B/C/D), cantidad, fecha de inicio, estado.
- Botón **Quitar**: desvincula un espacio activo, registrando la fecha de fin.

#### Expandible: "+ Agregar espacio"
Formulario inline para añadir un nuevo espacio al contrato:
- **Tipo**: A (Móvil), B (Semi-privado), C (Oficina 6p), D (Oficina 7p).
- **Cantidad**: número de puestos de ese tipo.
- **Fecha inicio**: desde cuándo aplica el nuevo espacio.

### Expandible: "⚠ Desvincular empresa"
Formulario para cerrar el contrato activo:
- Campo **Fecha de desvinculación** (por defecto: hoy).
- Botón **Confirmar desvinculación**: pide confirmación antes de ejecutar. Cierra el contrato y todos sus espacios activos.

### Formulario: Reactivar empresa
Aparece solo cuando la empresa no tiene contrato activo. Permite crear un nuevo contrato (con nuevo CECO y fecha de inicio). El contador de meses acumulados continúa sumando desde donde quedó en contratos anteriores.

### Tabla: Historial de facturación
Lista todas las facturas generadas para esta empresa, ordenadas de más reciente a más antigua:
- Mes/año, total con IVA, estado, referencia de orden.
- Botón **✓ Pago** + campo de referencia: marca la factura como pagada y guarda el número de orden (ORD-FRA).
- Botón **↩ Revertir**: devuelve una factura pagada al estado "pendiente".

### Botón "Editar"
Abre el formulario de edición de los datos básicos de la empresa (nombre, email, dirección, flags de afiliado y Fondo Emprender).

---

## 4. Formulario de empresa (`/companies/new` y `/companies/{id}/edit`)

### Campos del formulario

**Datos de la empresa:**
| Campo | Obligatorio | Descripción |
|---|---|---|
| Nombre | Sí | Razón social completa |
| NIT | Sí (solo al crear) | No se puede cambiar después de creado |
| Email de facturación | No | Correo al que se enviará la factura (v2) |
| Dirección | No | Aparece en la columna DIRECCIÓN del Excel |
| ¿Es afiliado a Cámara? | No | Checkbox; define "¿ES AFILIADO?" en el Excel (SI/NO) |
| ¿Fondo Emprender? | No | Checkbox; si se activa, la empresa va al archivo `facturacion-credito.xlsx` |
| REF (código SENA) | Solo si FE | Número de referencia del crédito Fondo Emprender |

**Contrato inicial (solo al crear):**
| Campo | Obligatorio | Descripción |
|---|---|---|
| CECO | Sí | Código del centro de costos (p. ej. `W0414-50`) |
| N° Contrato | No | Número interno del contrato |
| Fecha de inicio | Sí | Desde esta fecha se empieza a contar el tiempo para la tarifa |

> **Nota:** los espacios se agregan desde el detalle de la empresa, no desde este formulario.

---

## 5. Generar facturación (`/billing/`)

### Selector de mes y año
En la parte superior se puede cambiar el mes y año a facturar. Por defecto muestra el mes siguiente al actual.

### Alerta de fecha límite de pago
Muestra el **último día calendario** del mes facturado.

### Tabla de previsualización
Una fila por empresa activa con:
| Columna | Descripción |
|---|---|
| Empresa | Nombre con enlace al detalle. Etiqueta **FE** si es Fondo Emprender. |
| Espacios | Espacios activos en ese mes. |
| Tarifa | Año 1, Año 2 o Full para ese mes. |
| Valor Día (sin IVA) | Valor diario = Subtotal / 30 |
| Subtotal (sin IVA) | Base gravable del mes |
| Total (c/IVA) | Valor final = Subtotal × 1.19 |
| Aviso | Etiquetas especiales: **Cambio tarifa** (mes de transición de tier), **Límite 5 años** (empresa inelegible), **Existente** (ya se generó esta factura antes). |

Al final hay una fila de **Total general** con la suma de todos los valores con IVA.

### Cálculo en meses de transición de tarifa
Cuando una empresa cumple su aniversario de año (p. ej. el día 9 del mes) dentro del mes a facturar, el sistema calcula automáticamente:
- Días anteriores al aniversario × tarifa anterior.
- Días desde el aniversario hasta el día 30 × tarifa nueva.
- El **Valor Día** mostrado es el promedio ponderado (subtotal/30).
- En el Excel, VALOR DÍA = V.SUBTOTAL / 30.

### Botones de acción
- **⬇ Generar y descargar**: calcula todos los valores, los guarda en la base de datos y redirige a la descarga del archivo `orden-recaudo`. El archivo `facturacion-credito` también queda disponible.
- **⟳ Regenerar y descargar** (aparece si ya existe): sobreescribe los valores anteriores y descarga de nuevo.
- **⬇ Solo descargar Recaudo** / **⬇ Solo descargar Crédito** (aparecen si ya existe): descargan sin recalcular.

---

## 6. Historial de facturación (`/billing/history`)

Lista de todos los períodos de facturación generados, agrupados por mes/año (el más reciente aparece abierto por defecto).

### Por cada período
- Encabezado con el mes/año, conteo de facturas pagadas y pendientes, y el total del período.
- Botones **⬇ Recaudo** y **⬇ Crédito** para descargar los Excel de ese mes.

### Tabla de facturas del período
| Columna | Descripción |
|---|---|
| Empresa | Enlace al detalle |
| Subtotal (sin IVA) | Base gravable |
| Total (c/IVA) | Valor final |
| Vence | Fecha límite de pago |
| Estado | Pagado / Pendiente / Revisar |
| Referencia | Número de orden (ORD-FRA) si fue registrado |
| Acción | Botones de gestión de estado |

### Botones de gestión de estado
| Botón | Acción |
|---|---|
| **✓** (verde) + campo referencia | Marca como "Pagado" y guarda la referencia de la orden |
| **!** (rojo) | Marca como "Revisar" (para casos con inconsistencias) |
| **↩** | Devuelve al estado "Pendiente" |

---

## 7. Archivos Excel generados

### `orden-recaudo-[MES][AÑO].xlsx`
Contiene todas las empresas **regulares** (no Fondo Emprender). Sigue el formato de `guias-excel/orden-recaudo.xlsx`:
- Hoja: **OrdRecaudo**
- Una fila por empresa, con las columnas: #, PRODUCTO, ID VENDEDOR, PROMOTOR, CLIENTE, ID CLIENTE, CECO, CORREO FACTURACIÓN, OBSERVACIÓN, MES A FACTURAR, DÍAS DE CONCESIÓN, VALOR DÍA (Sin IVA), V.SUBTOTAL (Sin IVA), VALOR TOTAL (IVA incluido), FECHA 1 LÍMITE pago, DIRECCIÓN, ¿ES AFILIADO?

### `facturacion-credito-[MES][AÑO].xlsx`
Contiene las empresas de **Fondo Emprender**. Sigue el formato de `guias-excel/facturacion-credito.xlsx`:
- Hoja: **Detalle Facturación CWL26**
- Columnas: #, PRODUCTO, CENTRO DE COSTO, REF, ENTIDAD-CLIENTE, NIT, CONCEPTO, MES A FACTURAR, DÍAS DE CONCESIÓN, VALOR DÍA (Antes de IVA), V.SUBTOTAL (Antes de IVA), VALOR TOTAL (IVA 19% incluido), TIEMPO DE PAGO (10 días), OBSERVACIONES.

---

## 8. Reglas de negocio importantes

| Regla | Detalle |
|---|---|
| Tiers de tarifa | Año 1: 50% descuento (meses 1–12). Año 2: 25% descuento (meses 13–24). Full: sin descuento (mes 25 en adelante). |
| Límite máximo | Las empresas pueden permanecer máximo **60 meses (5 años)**. Al llegar al mes 61 el sistema las bloquea del proceso de facturación. |
| Re-ingreso | Si una empresa se desvinculó y vuelve a ingresar, el contador de meses acumula los períodos anteriores. El tier actual depende del total histórico. |
| IVA | Todos los valores de tarifa en el sistema ya incluyen IVA (19%). El sistema los descompone internamente para calcular Subtotal = Tarifa / 1.19 y luego Total = Subtotal × 1.19. |
| DÍAS DE CONCESIÓN | Siempre 30, independientemente del número real de días del mes. |
| Fecha límite de pago | Siempre es el último día calendario del mes facturado (p. ej. abril → 30 de abril, mayo → 31 de mayo). |
