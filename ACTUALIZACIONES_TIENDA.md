# Actualizar Tienda Web (VxPlay)

## Tu tienda usa: Python (Flask) + Docker

---

## Cómo subir cambios al servidor

**Siempre el mismo comando:**

```bash
# 1. En tu PC
git add . && git commit -m "Descripción del cambio" && git push

# 2. En SSH
cd /var/www/restaurante && git pull && docker compose up -d --build
```

---

## ¿Por qué siempre con --build?

Tu app está dentro de Docker. Cualquier cambio (HTML, CSS, Python) requiere reconstruir el contenedor.

---

## ¿Se dañan los datos?

**NO.** Git solo actualiza código, nunca la base de datos.

| Qué pasa | Resultado |
|----------|-----------|
| Git pull | Solo actualiza archivos que cambiaste |
| Base de datos | NO se toca, datos intactos |
| Tiendas, pedidos, usuarios | NO se borran |
| Archivos subidos (logos) | NO se tocan |

---

## Ejemplo completo

```bash
# 1. Editaste algo (colores, funciones, etc.)

# 2. En tu PC
git add . && git commit -m "Nuevos colores dashboard" && git push

# 3. Conecta al servidor
ssh root@72.61.72.32

# 4. Actualiza
cd /var/www/restaurante && git pull && docker compose up -d --build

# 5. Listo - cambios en producción
```

---

## Si algo sale mal

```bash
# Deshacer cambios locales (antes de push)
git checkout .

# Ver logs del servidor
docker logs restaurante-web-1 --tail=100
```

---

## Notas

- Siempre usa `--build` porque todo está en Docker
- Los datos de tiendas NUNCA se borran con git pull
- El rebuild toma ~30 segundos
