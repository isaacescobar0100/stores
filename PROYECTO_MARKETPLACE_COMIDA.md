# Proyecto: Marketplace de Comida (Tipo Rappi)

## Instrucciones para Claude
Cuando me des este documento, crea el proyecto de marketplace de comida integrando las tiendas de VxPlay existentes.

---

## 1. Descripcion General

**Nombre**: VxFood (o el que elija el usuario)
**Tipo**: Marketplace de delivery de comida
**Plataformas**: App Android/iOS + Web
**Backend**: Extensión de VxPlay actual

---

## 2. Funcionalidades Core

### 2.1 Para Clientes (App/Web)
- Registro/Login (email, Google, Facebook)
- Ver tiendas cercanas (geolocalización)
- Filtrar por categoría (comida rápida, postres, etc.)
- Ver menú de cada tienda
- Agregar productos al carrito
- Realizar pedido
- Pagar (Wompi)
- Seguir pedido en tiempo real
- Historial de pedidos
- Favoritos
- Calificar tienda/pedido

### 2.2 Para Tiendas (Ya existe en VxPlay)
- Recibir pedidos
- Gestionar menú
- Ver estadísticas
- Configurar horarios
- Gestionar delivery

### 2.3 Para Repartidores (Fase 2)
- App para repartidores
- Ver pedidos disponibles
- Aceptar pedido
- Navegación GPS
- Confirmar entrega

### 2.4 Para Admin (Superadmin VxPlay)
- Ver todas las tiendas
- Aprobar nuevas tiendas
- Ver comisiones
- Reportes generales

---

## 3. Arquitectura Técnica

```
┌─────────────────────────────────────────────────────┐
│                    CLIENTES                         │
├─────────────────┬─────────────────┬─────────────────┤
│   App Android   │    App iOS      │    Web App      │
│  (React Native) │  (React Native) │    (React)      │
└────────┬────────┴────────┬────────┴────────┬────────┘
         │                 │                 │
         └────────────────┬┴─────────────────┘
                          │
                    ┌─────▼─────┐
                    │    API    │
                    │  (Flask)  │
                    │  VxPlay   │
                    └─────┬─────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼────┐    ┌──────▼──────┐   ┌─────▼─────┐
    │  MySQL  │    │   Redis     │   │  Storage  │
    │   BD    │    │   Cache     │   │  Imágenes │
    └─────────┘    └─────────────┘   └───────────┘
```

---

## 4. Stack Tecnológico

| Componente | Tecnología | Justificación |
|------------|------------|---------------|
| **Backend API** | Flask (actual) | Ya existe, solo extender |
| **Base de datos** | MySQL (actual) | Ya existe |
| **App móvil** | React Native | Un código para Android/iOS |
| **Web cliente** | React + Vite | Rápido, moderno |
| **Mapas** | Google Maps API | Más usado, buena documentación |
| **Pagos** | Wompi | Ya integrado |
| **Notificaciones** | Firebase Cloud Messaging | Gratis, confiable |
| **Storage imágenes** | Cloudinary o S3 | Optimización automática |
| **Cache** | Redis (actual) | Ya existe |

---

## 5. Nuevas Tablas de Base de Datos

```sql
-- Clientes del marketplace (diferente a usuarios de tienda)
CREATE TABLE clientes_app (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    telefono VARCHAR(20),
    password_hash VARCHAR(255),
    foto_url VARCHAR(255),
    direccion_default INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Direcciones de clientes
CREATE TABLE direcciones (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cliente_id INT,
    nombre VARCHAR(50),  -- "Casa", "Trabajo"
    direccion TEXT,
    lat DECIMAL(10, 8),
    lng DECIMAL(11, 8),
    referencia VARCHAR(255),
    es_default BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (cliente_id) REFERENCES clientes_app(id)
);

-- Pedidos del marketplace
CREATE TABLE pedidos_marketplace (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cliente_id INT,
    tienda_id INT,
    direccion_id INT,
    estado ENUM('pendiente', 'confirmado', 'preparando', 'en_camino', 'entregado', 'cancelado'),
    subtotal DECIMAL(10,2),
    costo_envio DECIMAL(10,2),
    total DECIMAL(10,2),
    metodo_pago VARCHAR(50),
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes_app(id),
    FOREIGN KEY (tienda_id) REFERENCES tiendas(id)
);

-- Calificaciones
CREATE TABLE calificaciones (
    id INT PRIMARY KEY AUTO_INCREMENT,
    pedido_id INT,
    cliente_id INT,
    tienda_id INT,
    estrellas INT CHECK (estrellas BETWEEN 1 AND 5),
    comentario TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pedido_id) REFERENCES pedidos_marketplace(id)
);

-- Favoritos
CREATE TABLE favoritos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    cliente_id INT,
    tienda_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes_app(id),
    FOREIGN KEY (tienda_id) REFERENCES tiendas(id)
);
```

---

## 6. Nuevos Endpoints API

### Autenticación
```
POST /api/marketplace/auth/register
POST /api/marketplace/auth/login
POST /api/marketplace/auth/google
POST /api/marketplace/auth/forgot-password
```

### Tiendas
```
GET  /api/marketplace/tiendas?lat=X&lng=Y&radio=5km
GET  /api/marketplace/tiendas/:id
GET  /api/marketplace/tiendas/:id/menu
GET  /api/marketplace/tiendas/:id/calificaciones
```

### Pedidos
```
POST /api/marketplace/pedidos
GET  /api/marketplace/pedidos/:id
GET  /api/marketplace/pedidos/historial
PUT  /api/marketplace/pedidos/:id/cancelar
```

### Cliente
```
GET  /api/marketplace/perfil
PUT  /api/marketplace/perfil
GET  /api/marketplace/direcciones
POST /api/marketplace/direcciones
DELETE /api/marketplace/direcciones/:id
GET  /api/marketplace/favoritos
POST /api/marketplace/favoritos/:tienda_id
DELETE /api/marketplace/favoritos/:tienda_id
```

### Pagos
```
POST /api/marketplace/pagos/crear-intencion
POST /api/marketplace/pagos/webhook
```

---

## 7. Pantallas App Móvil

### 7.1 Onboarding
- Splash screen
- Slides de introducción
- Pedir permisos (ubicación, notificaciones)

### 7.2 Autenticación
- Login (email/Google/Facebook)
- Registro
- Recuperar contraseña

### 7.3 Home
- Barra de búsqueda
- Dirección actual (editable)
- Categorías (horizontal scroll)
- Tiendas cercanas (lista/mapa)
- Promociones/banners

### 7.4 Tienda
- Header con foto y logo
- Info (horario, calificación, tiempo entrega)
- Menú por categorías
- Productos con foto, precio, descripción

### 7.5 Producto
- Foto grande
- Nombre, descripción, precio
- Variantes (tamaño, extras)
- Cantidad
- Botón agregar al carrito

### 7.6 Carrito
- Lista de productos
- Editar cantidad
- Subtotal
- Costo de envío
- Total
- Botón pagar

### 7.7 Checkout
- Dirección de entrega
- Método de pago
- Notas para el restaurante
- Resumen del pedido
- Confirmar pedido

### 7.8 Seguimiento
- Estado del pedido (timeline)
- Mapa con ubicación del repartidor
- Info del repartidor (foto, nombre, teléfono)
- Chat con tienda/repartidor

### 7.9 Perfil
- Foto y nombre
- Mis direcciones
- Historial de pedidos
- Favoritos
- Métodos de pago
- Configuración
- Cerrar sesión

---

## 8. Modelo de Negocio

### Comisiones
| Concepto | Porcentaje |
|----------|------------|
| Comisión por pedido | 10-15% |
| Costo de envío (lo paga cliente) | Variable por distancia |

### Ejemplo
```
Pedido: $30,000 COP
Envío: $5,000 COP
Cliente paga: $35,000 COP

Tienda recibe: $25,500 COP (85%)
Plataforma: $4,500 COP (15%)
Repartidor: $5,000 COP (envío)
```

---

## 9. Integraciones Externas

| Servicio | Uso | Costo |
|----------|-----|-------|
| **Google Maps API** | Mapas, geolocalización, rutas | ~$200 USD/mes (alto uso) |
| **Firebase** | Auth, Notificaciones push | Gratis (límites) |
| **Wompi** | Pagos | 2.9% + $900 COP por transacción |
| **Cloudinary** | Imágenes | Gratis hasta 25GB |
| **Twilio** (opcional) | SMS verificación | ~$0.05 USD/SMS |

---

## 10. Fases de Desarrollo

### Fase 1: MVP Web (4-6 semanas)
- [ ] Endpoints API marketplace
- [ ] Web para clientes (ver tiendas, pedir)
- [ ] Integración con Wompi
- [ ] Notificaciones por email

### Fase 2: App Móvil (6-8 semanas)
- [ ] App React Native
- [ ] Login/Registro
- [ ] Geolocalización
- [ ] Push notifications
- [ ] Publicar en Play Store

### Fase 3: Repartidores (4-6 semanas)
- [ ] App para repartidores
- [ ] Sistema de asignación
- [ ] Tracking en tiempo real

### Fase 4: Mejoras (continuo)
- [ ] iOS App Store
- [ ] Chat en app
- [ ] Promociones/cupones
- [ ] Programa de lealtad

---

## 11. Costos Estimados Mensuales

### MVP (primeros meses)
| Concepto | Costo |
|----------|-------|
| VPS actual | $10 USD |
| Google Maps API | $0-50 USD |
| Firebase | Gratis |
| Wompi | Solo comisiones |
| **Total** | ~$10-60 USD |

### Escalado (6+ meses)
| Concepto | Costo |
|----------|-------|
| VPS mejorado (KVM2) | $15-25 USD |
| Google Maps API | $100-300 USD |
| Firebase | $25 USD |
| Cloudinary | $50 USD |
| **Total** | ~$200-400 USD |

---

## 12. Estructura de Proyecto

```
vxfood/
├── backend/           # Extensión de VxPlay actual
│   ├── marketplace_routes.py
│   ├── marketplace_models.py
│   └── ...
│
├── web-cliente/       # React app para clientes
│   ├── src/
│   ├── public/
│   └── package.json
│
├── app-cliente/       # React Native app
│   ├── src/
│   ├── android/
│   ├── ios/
│   └── package.json
│
└── app-repartidor/    # React Native app (Fase 3)
    └── ...
```

---

## 13. Requisitos para Empezar

1. **Google Cloud Console** - API key para Maps
2. **Firebase Project** - Para notificaciones
3. **Cuenta Expo** - Para builds de app
4. **Cuenta Play Store** - $25 USD único
5. **Cuenta App Store** - $99 USD/año (opcional)

---

## 14. Comando para Iniciar

Cuando estés listo, dame este documento y di:
"Empecemos con el marketplace de comida - Fase 1: MVP Web"

O especifica qué parte quieres desarrollar primero.
