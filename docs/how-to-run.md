# Cómo ejecutar Moni-Facturas en Windows

Esta guía está escrita para una persona sin conocimientos técnicos de programación. Sigue los pasos en orden y el sistema quedará funcionando.

---

## Qué necesitas instalar (solo la primera vez)

### Paso 1 — Instalar Docker Desktop

Docker es el programa que ejecuta toda la aplicación. Solo necesitas instalarlo una vez.

1. Abre el navegador y ve a: **https://www.docker.com/products/docker-desktop/**
2. Haz clic en el botón **"Download for Windows"**.
3. Abre el archivo descargado (`Docker Desktop Installer.exe`) y sigue las instrucciones.
4. Cuando termine, **reinicia el computador** si te lo pide.
5. Después del reinicio, busca **Docker Desktop** en el menú de inicio y ábrelo.
6. Espera a que aparezca la ballena verde en la barra de tareas (abajo a la derecha). Eso significa que Docker está listo.

> **¿Ves un error sobre WSL 2?** Haz clic en el enlace que te muestra Docker para instalar la actualización, reinicia y vuelve a abrir Docker Desktop.

---

## Obtener los archivos del proyecto

Si ya tienes la carpeta `Moni-facturas` en tu computador (por ejemplo, descargada por el desarrollador), pasa al siguiente paso.

Si no la tienes, pídele al administrador del sistema que te envíe la carpeta comprimida (`.zip`) y descomprímela en una ubicación fácil de encontrar, por ejemplo:
```
C:\Usuarios\TuNombre\Documentos\Moni-facturas\
```

---

## Ejecutar la aplicación (cada vez que quieras usarla)

### Paso 2 — Abrir la Terminal de Windows

1. Presiona la tecla **Windows** en el teclado.
2. Escribe `cmd` y presiona **Enter**.
3. Se abrirá una ventana negra llamada "Símbolo del sistema".

### Paso 3 — Ir a la carpeta del proyecto

En la ventana negra, escribe el siguiente comando y presiona **Enter**. Reemplaza la ruta con la ubicación real de tu carpeta:

```
cd C:\Usuarios\TuNombre\Documentos\Moni-facturas
```

> **Tip:** puedes arrastrar la carpeta `Moni-facturas` desde el Explorador de archivos y soltarla en la ventana negra — aparecerá la ruta automáticamente. Luego escribe `cd ` (con espacio) antes de la ruta.

### Paso 4 — Iniciar la aplicación

Escribe este comando y presiona **Enter**:

```
docker compose up -d
```

La primera vez tardará varios minutos porque descarga los programas necesarios. Las veces siguientes tardará solo unos segundos.

Cuando veas el mensaje:
```
Container moni-facturas-app-1  Started
```
...la aplicación está lista.

### Paso 5 — Abrir en el navegador

Abre tu navegador (Chrome, Edge, etc.) y escribe en la barra de direcciones:

```
http://localhost:8000
```

Presiona **Enter**. Deberías ver el Dashboard de Moni-Facturas.

---

## Primera vez: importar los datos

Solo la **primera vez** que uses la aplicación (o si instalas en un computador nuevo), debes importar las empresas desde el archivo Excel de control. Sigue estos pasos:

1. Asegúrate de que la aplicación esté corriendo (pasos 2–4 completados).
2. En la ventana negra (Terminal), escribe este comando y presiona **Enter**:

```
docker compose exec app python scripts/import_excel.py
```

3. Espera a que aparezca el mensaje:
```
✅ Importación completa.
```

4. Recarga la página en el navegador (`F5`). Ahora verás las empresas cargadas.

---

## Cerrar la aplicación

Cuando termines de trabajar y quieras apagar la aplicación, escribe en la Terminal:

```
docker compose down
```

Los datos quedan guardados en la base de datos — no se pierden al cerrar.

> **Nota:** Docker Desktop puede seguir corriendo en la barra de tareas aunque hayas cerrado la aplicación. Eso está bien y no consume recursos significativos.

---

## Resumen de comandos del día a día

| Acción | Comando a escribir en la Terminal |
|---|---|
| Iniciar la aplicación | `docker compose up -d` |
| Cerrar la aplicación | `docker compose down` |
| Ver si hay errores | `docker compose logs app` |

---

## Solución de problemas frecuentes

### "docker: command not found" o "no se reconoce el comando"
Docker Desktop no está instalado o no está corriendo. Ábrelo desde el menú de inicio y espera a que aparezca la ballena verde antes de intentar de nuevo.

### La página no carga en el navegador
- Verifica que Docker Desktop esté corriendo (ballena verde en la barra de tareas).
- Verifica que hayas ejecutado `docker compose up -d` en la Terminal.
- Espera 30 segundos y vuelve a intentarlo.

### "port 8000 is already in use"
Otro programa está usando el puerto 8000. Cierra la aplicación con `docker compose down`, espera un momento y vuelve a iniciarla.

### Perdí todos los datos
Los datos están guardados en un volumen de Docker llamado `moni-facturas_postgres_data`. Mientras no ejecutes el comando `docker compose down -v` (con la letra `-v`), los datos están seguros. Si los perdiste accidentalmente, puedes volver a importar las empresas desde el Excel con el comando del paso de importación.

### Quiero usar la aplicación desde otro computador en la misma red
La configuración actual solo permite acceso desde el mismo computador (`localhost`). Para acceso en red local o desde internet, contacta al desarrollador para configurar el servidor VPS mencionado en el ROADMAP.

---

## Actualizar la aplicación (cuando el desarrollador envíe cambios)

Si el desarrollador te envía una versión actualizada de la carpeta:

1. Reemplaza los archivos de la carpeta (excepto el archivo `.env` — ese guárdalo).
2. Abre la Terminal, ve a la carpeta y ejecuta:
```
docker compose down
docker compose up -d --build
```
3. Espera a que termine y abre el navegador en `http://localhost:8000`.
