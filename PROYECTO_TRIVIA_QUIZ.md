# Proyecto: Trivia Quiz Mobile App

## Instrucciones para Claude
Cuando me des este documento, crea el proyecto completo de juego Trivia/Quiz para mobile usando Godot 4. Sigue todas las especificaciones abajo.

---

## 1. Descripcion General

**Nombre**: SabeloTodo (o el que elija el usuario)
**Tipo**: Juego de trivia/quiz casual
**Plataformas**: Android, iOS, Web
**Engine**: Godot 4.x
**Lenguaje**: GDScript

---

## 2. Funcionalidades Core

### 2.1 Modos de Juego
- **Clasico**: 10 preguntas, sin limite de tiempo por pregunta
- **Contrarreloj**: 10 preguntas, 15 segundos por pregunta
- **Infinito**: Juega hasta fallar 3 veces
- **Diario**: 5 preguntas nuevas cada dia (mismas para todos)

### 2.2 Categorias
- Cultura General
- Ciencia
- Historia
- Geografia
- Deportes
- Entretenimiento (cine, musica, series)
- Tecnologia
- Arte y Literatura

### 2.3 Sistema de Preguntas
- 4 opciones de respuesta (A, B, C, D)
- Solo 1 respuesta correcta
- Dificultad: Facil, Media, Dificil
- Preguntas almacenadas en JSON local
- Posibilidad de cargar preguntas desde API (futuro)

### 2.4 Progresion y Recompensas
- Puntos por respuesta correcta (base: 100)
- Bonus por racha de aciertos (x1.5, x2, x2.5...)
- Bonus por tiempo restante (modo contrarreloj)
- Monedas virtuales al completar partidas
- Niveles de experiencia (XP)

### 2.5 Estadisticas
- Total preguntas respondidas
- Porcentaje de aciertos global
- Porcentaje por categoria
- Mejor racha
- Partidas jugadas

---

## 3. Pantallas/Escenas

### 3.1 Menu Principal
- Logo del juego
- Boton "Jugar" (abre selector de modo)
- Boton "Categorias" (activar/desactivar)
- Boton "Estadisticas"
- Boton "Tienda" (futuro: compras in-app)
- Boton "Ajustes" (sonido, vibracion)
- Indicador de monedas/XP arriba

### 3.2 Selector de Modo
- Cards para cada modo de juego
- Descripcion breve de cada uno
- Icono de candado si esta bloqueado

### 3.3 Pantalla de Juego
- Barra de progreso (pregunta X de 10)
- Categoria actual
- Texto de la pregunta
- 4 botones de respuesta
- Timer (si aplica)
- Puntuacion actual
- Indicador de vidas (modo infinito)

### 3.4 Resultado de Pregunta
- Animacion correcta (verde, confeti) o incorrecta (rojo, shake)
- Mostrar respuesta correcta si fallo
- Dato curioso opcional
- Boton "Siguiente"

### 3.5 Pantalla de Fin de Partida
- Puntuacion final
- Respuestas correctas / total
- XP ganado
- Monedas ganadas
- Boton "Jugar de nuevo"
- Boton "Menu principal"
- Boton "Compartir" (captura de pantalla)

### 3.6 Estadisticas
- Graficas simples de rendimiento
- Lista de categorias con porcentaje
- Records personales

### 3.7 Ajustes
- Toggle sonido
- Toggle vibracion
- Toggle notificaciones
- Boton "Borrar progreso"
- Creditos

---

## 4. Estructura de Datos

### 4.1 Pregunta (JSON)
```json
{
  "id": 1,
  "categoria": "ciencia",
  "dificultad": "media",
  "pregunta": "Cual es el planeta mas grande del sistema solar?",
  "opciones": ["Marte", "Jupiter", "Saturno", "Neptuno"],
  "respuesta_correcta": 1,
  "dato_curioso": "Jupiter es tan grande que podrian caber 1,300 Tierras dentro."
}
```

### 4.2 Progreso del Jugador (guardado local)
```json
{
  "xp": 1500,
  "nivel": 5,
  "monedas": 340,
  "partidas_jugadas": 47,
  "preguntas_totales": 420,
  "respuestas_correctas": 315,
  "mejor_racha": 12,
  "stats_por_categoria": {
    "ciencia": {"total": 50, "correctas": 38},
    "historia": {"total": 45, "correctas": 30}
  },
  "modos_desbloqueados": ["clasico", "contrarreloj"],
  "fecha_ultimo_diario": "2025-12-18"
}
```

---

## 5. Monetizacion (Fase 2)

### 5.1 Ads
- Banner en menu principal (opcional)
- Interstitial cada 3 partidas
- Rewarded video: duplicar monedas, vida extra

### 5.2 Compras In-App
- Pack sin ads: $2.99 USD (pago unico)
- Pack de monedas: $0.99 / $2.99 / $4.99
- Pack de categorias premium: $0.99 c/u

---

## 6. Assets Necesarios

### 6.1 Graficos
- Logo del juego
- Iconos de categorias (8)
- Iconos de UI (botones, monedas, XP, vidas)
- Fondos para cada categoria o fondo generico
- Animaciones: confeti, shake, timer

### 6.2 Audio
- Musica de fondo (loop relajado)
- SFX: click boton, respuesta correcta, respuesta incorrecta
- SFX: fin de partida (victoria/derrota)
- SFX: tick del timer

---

## 7. Estructura de Proyecto Godot

```
trivia-quiz/
├── project.godot
├── scenes/
│   ├── Main.tscn (autoload/manager)
│   ├── MenuPrincipal.tscn
│   ├── SelectorModo.tscn
│   ├── Juego.tscn
│   ├── ResultadoPregunta.tscn
│   ├── FinPartida.tscn
│   ├── Estadisticas.tscn
│   └── Ajustes.tscn
├── scripts/
│   ├── GameManager.gd (autoload)
│   ├── QuestionManager.gd
│   ├── SaveManager.gd
│   ├── AudioManager.gd
│   └── [scripts de cada escena]
├── data/
│   ├── preguntas_cultura.json
│   ├── preguntas_ciencia.json
│   ├── preguntas_historia.json
│   └── ...
├── assets/
│   ├── fonts/
│   ├── images/
│   ├── audio/
│   └── themes/
└── export/
    ├── android/
    └── ios/
```

---

## 8. Colores y Estilo Visual

### Paleta sugerida
- Primario: #6C5CE7 (morado)
- Secundario: #00CEC9 (turquesa)
- Exito: #00B894 (verde)
- Error: #FF7675 (rojo coral)
- Fondo: #2D3436 (gris oscuro)
- Texto: #FFFFFF
- Texto secundario: #B2BEC3

### Estilo
- Bordes redondeados (16px)
- Sombras suaves
- Iconos flat/minimal
- Fuente: Sans-serif moderna (Poppins, Nunito)

---

## 9. Preguntas Iniciales (Minimo 50)

Crear al menos 50 preguntas distribuidas asi:
- Cultura General: 10
- Ciencia: 8
- Historia: 8
- Geografia: 8
- Deportes: 6
- Entretenimiento: 6
- Tecnologia: 4

Mezcla de dificultades: 40% facil, 40% media, 20% dificil.

---

## 10. Backend API (Opcional - Fase 2)

Si se quiere conectar a servidor (vxplay.online):

### Endpoints
- `GET /api/trivia/preguntas?categoria=X&cantidad=10`
- `POST /api/trivia/resultado` (guardar partida)
- `GET /api/trivia/leaderboard`
- `GET /api/trivia/diario` (pregunta del dia)

---

## 11. Entregables Esperados

1. Proyecto Godot 4 completo y funcional
2. Todas las escenas listadas
3. Sistema de guardado local funcionando
4. Al menos 50 preguntas en JSON
5. Modos Clasico y Contrarreloj funcionales
6. Pantalla de estadisticas basica
7. Exportable a Android (APK)
8. Instrucciones de como agregar mas preguntas

---

## 12. Notas Adicionales

- Priorizar que funcione bien en mobile (touch)
- UI responsive para diferentes tamaños de pantalla
- Optimizar para bajo consumo de bateria
- El juego debe funcionar 100% offline (fase 1)
- Preparar estructura para ads pero no implementar aun

---

## Comando para iniciar

Cuando estes listo, dame este documento y di:
"Crea el proyecto de Trivia Quiz segun el documento PROYECTO_TRIVIA_QUIZ.md"
