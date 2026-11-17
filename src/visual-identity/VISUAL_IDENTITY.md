# Identidad visual — ObsAgent

## 1. Esencia de marca

ObsAgent convierte señales financieras complejas en decisiones claras. Su identidad combina la
precisión de una plataforma de riesgo con una expresión visual más humana, contemporánea y
editorial.

**Atributos:** inteligente, confiable, directa, humana y proactiva.

**Principio visual:** “Claridad en la complejidad”. Las interfaces deben mostrar mucha información
sin sentirse pesadas: jerarquía tipográfica fuerte, superficies amplias, datos resaltados y
explicaciones breves.

## 2. Paleta de color

### Colores principales

| Token         | Hex       | Uso                                                |
| ------------- | --------- | -------------------------------------------------- |
| `--ink-950`   | `#071522` | Fondos inmersivos, navegación y hero               |
| `--ink-900`   | `#0B2030` | Superficies oscuras secundarias                    |
| `--teal-500`  | `#18B9AA` | Acción principal, datos positivos y gráficas       |
| `--teal-300`  | `#80F4DC` | Luz, énfasis sobre fondos oscuros                  |
| `--coral-500` | `#FF5D45` | Alertas, llamadas editoriales y puntos de atención |

### Neutros

| Token         | Hex       | Uso                        |
| ------------- | --------- | -------------------------- |
| `--cloud-50`  | `#F4F7F6` | Fondo general              |
| `--white`     | `#FFFFFF` | Tarjetas y texto invertido |
| `--slate-700` | `#40505D` | Texto secundario           |
| `--line`      | `#DDE6E4` | Bordes y divisores         |

### Semántica

- **Positivo / verificado:** `#18B9AA`
- **Atención:** `#E7A33E`
- **Crítico:** `#E45555`
- **Información:** `#4779D9`

No usar el coral como color de éxito. En superficies oscuras, preferir `--teal-300` para conservar
contraste.

## 3. Tipografía

- **Display y titulares:** `Manrope`, pesos 600–700. Uso editorial, tracking negativo moderado.
- **Interfaz y datos:** `DM Sans`, pesos 400–700. Botones, tablas, etiquetas y cifras.
- **Cifras destacadas:** Manrope 700, cifras tabulares cuando estén disponibles.

Escala recomendada:

- Hero: `clamp(2.35rem, 4vw, 4.7rem)`, interlineado 0.96.
- Título de página: 1.6–2rem.
- Título de tarjeta: 0.875–1rem.
- Cuerpo: 0.75–0.875rem.
- Etiqueta: 0.6–0.7rem, mayúsculas y tracking de 0.08–0.14em.

## 4. Fotografía y creativos

- Mostrar personas tomando decisiones, equipos analizando información y tecnología en contexto.
- Preferir encuadres amplios o medios con espacio negativo para superponer contenido.
- Aplicar gradientes azul petróleo para integrar la foto con la interfaz.
- Evitar fotografías genéricas de apretones de manos, monedas apiladas o sonrisas posadas.
- Los recursos gráficos propios usan órbitas finas, halos luminosos, curvas de datos y bloques de
  color coral. Deben acompañar el contenido, nunca competir con las métricas.
- Toda imagen externa debe incluir texto alternativo y atribución cuando la licencia lo requiera.

## 5. Superficies, forma y profundidad

- Radio base de tarjetas: 12–18 px.
- Hero y superficies destacadas: 24–28 px.
- Botones: radio completo o 8–12 px según jerarquía.
- Bordes finos y fríos (`--line`); sombras amplias y suaves.
- Sobre fotografía se permite vidrio oscuro: fondo semitransparente, borde blanco al 15% y
  `backdrop-filter`.

## 6. Iconografía y visualización de datos

- Iconos lineales, 1.8 px, extremos redondeados y formas sencillas.
- Evitar mezclar familias o usar emojis.
- Series principales en teal; umbrales en ámbar; anomalías críticas en rojo.
- Las razones se muestran como razón de sumas, nunca como promedio de tasas por fila.
- Toda gráfica debe tener título, contexto temporal, leyenda y un hallazgo narrativo.

## 7. Voz y microcopy

- Frases directas y orientadas a decisión: “Explorar hallazgos”, “Revisar segmento”.
- Titulares editoriales breves: “Claridad para decidir. Inteligencia para actuar.”
- Explicar cambios en lenguaje natural y siempre incluir magnitud, periodo y segmento.
- Evitar tecnicismos innecesarios, tono promocional excesivo o afirmaciones sin respaldo.

## 8. Accesibilidad y movimiento

- Contraste mínimo WCAG AA.
- Nunca comunicar estado solo con color; acompañar con icono o texto.
- Foco visible para controles interactivos.
- Transiciones entre 160 y 260 ms; respetar `prefers-reduced-motion`.
- La versión móvil conserva primero: título, estado de cartera, KPIs y hallazgos críticos.
