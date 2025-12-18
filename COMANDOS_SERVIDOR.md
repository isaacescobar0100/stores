# Comandos del Servidor VxPlay

## Conexion SSH
```bash
ssh root@72.61.72.32
```

---

## Comandos Docker (los mas usados)

| Comando | Que hace |
|---------|----------|
| `docker compose up -d --build` | Reconstruye y reinicia la app (deploy) |
| `docker compose restart` | Reinicia sin reconstruir |
| `docker compose down` | Detiene la app |
| `docker compose logs -f` | Ver logs en tiempo real |
| `docker compose logs --tail=100` | Ver ultimos 100 logs |
| `docker logs restaurante-web-1` | Logs del contenedor especifico |
| `docker ps` | Ver contenedores corriendo |
| `docker system prune -af` | Limpiar imagenes/cache no usados |

---

## Git (actualizar codigo)

| Comando | Que hace |
|---------|----------|
| `git pull` | Descargar cambios del repositorio |
| `git status` | Ver archivos modificados |
| `git log --oneline -5` | Ver ultimos 5 commits |

---

## Deploy completo (actualizar produccion)
```bash
cd /var/www/restaurante
git pull && docker compose up -d --build
```

---

## Sistema

| Comando | Que hace |
|---------|----------|
| `df -h` | Ver espacio en disco |
| `free -h` | Ver memoria RAM |
| `htop` | Monitor de recursos (CPU, RAM) |
| `ls -la` | Listar archivos con detalles |
| `pwd` | Ver directorio actual |

---

## Rutas importantes

| Ruta | Contenido |
|------|-----------|
| `/var/www/restaurante/` | Codigo de VxPlay |
| `/var/www/serviya/` | Proyecto Serviya (separado) |

---

## Flujo de deploy tipico

1. Hacer cambios en el codigo local
2. `git add . && git commit -m "descripcion"` (local)
3. `git push` (local)
4. SSH al servidor: `ssh root@72.61.72.32`
5. `cd /var/www/restaurante`
6. `git pull && docker compose up -d --build`
7. Verificar: `docker logs restaurante-web-1 --tail=50`

---

## Errores comunes

**App no responde:**
```bash
docker compose restart
docker logs restaurante-web-1 --tail=100
```

**Disco lleno:**
```bash
df -h
docker system prune -af
```

**Ver si la app esta corriendo:**
```bash
docker ps
```

---

## Notas
- IP del servidor: 72.61.72.32
- Usuario: root
- App corre en Docker (contenedor: restaurante-web-1)
- Base de datos: PostgreSQL (dentro de Docker)
- Los archivos se suben via Git, no FTP
