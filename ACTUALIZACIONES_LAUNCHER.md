# Sistema de Actualizaciones VxPlay

## Estructura de Archivos

| Carpeta | Qué contiene | Cuándo se modifica |
|---------|--------------|-------------------|
| `static/launcher/` | admin_cloud.py, cocina_cloud.py, api_client.py, updater.py | Cambios en las apps (colores, lógica, funciones) |
| `static/apps/` | VxPlay.exe | Cambios en la ventana inicial (raro) |

## Archivos de Versión

| Archivo | Controla |
|---------|----------|
| `static/launcher/version.json` | Versión de admin/cocina |
| `static/apps/version.json` | Versión del Launcher (EXE) |

---

## Caso 1: Solo tocaste admin/cocina

Ejemplo: Cambiaste colores, arreglaste bug, agregaste función.

```bash
# 1. Edita static/launcher/version.json (sube versión)
#    Ejemplo: "version": "1.0.9"

# 2. Sube a Git
git add . && git commit -m "Update admin/cocina v1.0.9" && git push

# 3. En el servidor (SSH)
cd /var/www/restaurante && git pull
```

---

## Caso 2: Solo tocaste el Launcher (ventana inicial)

Ejemplo: Cambiaste diseño de la ventana, agregaste botón nuevo.

```bash
# 1. Recompila el EXE
pyinstaller --onefile --windowed launcher/main.py -n VxPlay

# 2. Copia el nuevo EXE
copy dist\VxPlay.exe static\apps\VxPlay.exe

# 3. Edita static/apps/version.json (sube versión)
#    Ejemplo: "version": "1.0.9"

# 4. Sube a Git
git add . && git commit -m "Launcher v1.0.9" && git push

# 5. En el servidor (SSH)
cd /var/www/restaurante && git pull
```

---

## Caso 3: Tocaste ambos (admin/cocina + Launcher)

```bash
# 1. Recompila el EXE
pyinstaller --onefile --windowed launcher/main.py -n VxPlay

# 2. Copia el nuevo EXE
copy dist\VxPlay.exe static\apps\VxPlay.exe

# 3. Edita AMBOS version.json (misma versión)
#    - static/launcher/version.json → "version": "1.0.9"
#    - static/apps/version.json → "version": "1.0.9"

# 4. Sube a Git
git add . && git commit -m "Update completo v1.0.9" && git push

# 5. En el servidor (SSH)
cd /var/www/restaurante && git pull
```

---

## Cómo funciona la actualización automática

```
Cliente abre VxPlay.exe
        ↓
Revisa apps/version.json → ¿Hay nuevo EXE? → Descarga
        ↓
Revisa launcher/version.json → ¿Hay nuevos .py? → Descarga
        ↓
Apps actualizadas
```

---

## Notas importantes

- Mantén la misma versión en ambos `version.json` para evitar confusión
- El cliente recibe actualizaciones automáticamente al abrir VxPlay
- Git sube automáticamente todos los archivos que modificaste
