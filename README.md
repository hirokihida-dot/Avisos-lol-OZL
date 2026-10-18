# 🎮 Avisos del equipo de LoL

Bot de recordatorios automáticos para el canal de anuncios de Discord del equipo.
Avisa de **partidos**, **entrenamientos**, **deadlines** y **encuestas** sin que nadie
tenga que acordarse de escribir el mensaje.

Funciona con **GitHub Actions**: GitHub ejecuta el script cada 10 minutos en sus
servidores, así que no hace falta tener ningún ordenador encendido.

---

## ✏️ Cómo añadir un evento

Todo el calendario está en **`eventos.yaml`**. Para editarlo:

1. Abre `eventos.yaml` en GitHub y pulsa el icono del lápiz ✏️.
2. Añade el evento al final de la lista `eventos:`.
3. Pulsa **Commit changes**.

No hace falta parar ni reiniciar nada: la siguiente ejecución (como mucho en 10 minutos)
ya usa la versión nueva.

### Ejemplo

```yaml
eventos:
  - tipo: partido
    titulo: "Jornada 4 vs UMH"
    fecha: "2026-10-29 19:00"
    detalles: "Conectaos **30 min antes** al canal de voz."

  - tipo: deadline
    titulo: "Enviar disponibilidad de noviembre"
    fecha: "2026-10-24 23:59"
    enlace: "https://forms.gle/xxxxx"
```

### Campos

| Campo      | Obligatorio | Descripción |
|------------|:-----------:|-------------|
| `tipo`     | ✅ | `partido`, `entrenamiento`, `deadline` o `encuesta` |
| `titulo`   | ✅ | Texto que aparece en el título del aviso |
| `fecha`    | ✅ | `"AAAA-MM-DD HH:MM"`, **entre comillas** y en hora de España |
| `detalles` | ❌ | Texto extra. Admite markdown de Discord (`**negrita**`, `*cursiva*`, `\|\|spoiler\|\|`) |
| `enlace`   | ❌ | URL de un formulario, encuesta, bracket, etc. |

> ⚠️ **Cuidado con la sangría.** El YAML es sensible a los espacios: cada evento empieza
> con `  - ` (dos espacios, guion, espacio) y sus campos van alineados debajo con cuatro
> espacios. Si el archivo queda mal escrito, esa ejecución falla y no se envían avisos
> hasta corregirlo (GitHub avisa por correo).

---

## 🔁 Entrenamientos semanales

Los entrenamientos fijos se escriben una sola vez y se repiten cada semana:

```yaml
entrenamientos_semanales:
  - dia: martes
    hora: "21:00"
    titulo: "Entrenamiento semanal"
    detalles: "Revisión de VODs + scrims"
```

Días válidos: `lunes`, `martes`, `miércoles`, `jueves`, `viernes`, `sábado`, `domingo`
(con o sin tilde, en mayúsculas o minúsculas).

Para **cancelar un entrenamiento concreto** (festivos, exámenes…), añade la fecha a:

```yaml
saltar_entrenamientos:
  - "2026-12-08"
```

---

## ⏰ Cuándo se envía cada aviso

| Tipo            | Avisos |
|-----------------|--------|
| 🏆 Partido       | A las 10:00 del mismo día y 1 h antes |
| 🎯 Entrenamiento | 2 h antes |
| ⏰ Deadline      | 24 h antes y 3 h antes |
| 📊 Encuesta      | 24 h antes y 3 h antes |

Para cambiarlo, edita el bloque `AVISOS` al principio de `avisos.py`:

```python
AVISOS = {
    "partido": [("mañana-del-dia", a_las(10)), ("1h", antes(hours=1))],
    ...
}
```

- `antes(hours=2)`, `antes(minutes=30)`, `antes(days=2)` → un tiempo antes del evento.
- `a_las(10)`, `a_las(9, 30)` → a esa hora el mismo día del evento.
- El primer texto de cada pareja (`"1h"`, `"mañana-del-dia"`…) es un nombre interno;
  puede ser cualquiera, pero no puede repetirse dentro del mismo tipo.

> GitHub a veces retrasa unos minutos las ejecuciones programadas, así que los avisos
> pueden llegar con algo de retraso. Si un aviso lleva más de 2 h de retraso (por ejemplo,
> porque el evento se añadió tarde), se omite para no mandar avisos desfasados.

---

## 🎨 Formato de los mensajes

- **Colores, emojis y títulos** de cada tipo: bloque `ESTILO` en `avisos.py`
  (el color va en hexadecimal, p. ej. `0xE74C3C`).
- **Estructura del mensaje** (imágenes, pie, columnas…): función `construir_mensaje`.
- **Nombre y foto del bot**: en la configuración del webhook en Discord.
- La fecha se muestra con el formato de Discord, así que cada persona la ve en su hora
  local y con cuenta atrás ("dentro de 2 horas").

### Mencionar a un rol

1. En Discord, activa el modo desarrollador (*Ajustes → Avanzado*).
2. Clic derecho en el rol → **Copiar ID**.
3. Pégalo en `eventos.yaml`:

```yaml
rol_mencion: "123456789012345678"
mencionar_en: [partido, deadline, encuesta]   # tipos que mencionan al rol
```

---

## 🧪 Probar que funciona

1. Añade un evento de prueba con un título nuevo, por ejemplo un `deadline` con fecha
   entre **1 y 3 horas a partir de ahora** (así toca el aviso de "3 h antes").
2. Ve a la pestaña **Actions → Avisos Discord → Run workflow**.
3. Comprueba que el mensaje aparece en el canal y **borra el evento de prueba**.

> El script recuerda los avisos ya enviados (por título y fecha). Si repites una prueba
> con los mismos datos, no se volverá a enviar: cambia el título o la fecha.

---

## 🛠️ Cómo está montado

```
├── avisos.py                    # Script que decide qué avisos tocan y los envía
├── eventos.yaml                 # Calendario (lo único que se edita normalmente)
├── enviados.json                # Avisos ya enviados (lo actualiza el bot solo)
├── requirements.txt             # Dependencias de Python
└── .github/workflows/avisos.yml # Programación en GitHub Actions (cada 10 min)
```

Configuración necesaria en el repositorio:

- **Secreto `DISCORD_WEBHOOK`** (*Settings → Secrets and variables → Actions*) con la URL
  del webhook del canal. **No la pegues nunca en ningún archivo**: el repositorio es público.
- **Permisos de escritura** para Actions (*Settings → Actions → General → Workflow
  permissions → Read and write permissions*), para que el bot pueda guardar `enviados.json`.

Para que otros miembros puedan editar el calendario, añádelos en *Settings → Collaborators*.

### Ejecutarlo en local (opcional)

```bash
pip install -r requirements.txt
python avisos.py --listar   # muestra los próximos avisos programados
python avisos.py --prueba   # muestra lo que se enviaría ahora, sin enviar nada
```

---

## ❓ Problemas frecuentes

| Problema | Solución |
|----------|----------|
| La ejecución sale en ❌ rojo | Entra en ella en *Actions* y mira el paso que falla. Casi siempre es un error de formato en `eventos.yaml` (sangría o fecha sin comillas). |
| `Fecha no válida` | Usa el formato `"AAAA-MM-DD HH:MM"` y ponlo entre comillas. |
| Se repiten avisos | Revisa que Actions tenga permisos de escritura (ver arriba). |
| No llega ningún aviso | Comprueba que el secreto `DISCORD_WEBHOOK` existe y que el webhook no se ha borrado en Discord. |
| La programación se ha parado | GitHub desactiva los workflows programados tras ~60 días sin cambios en el repo. Reactívalo en *Actions* o haz cualquier cambio. |
