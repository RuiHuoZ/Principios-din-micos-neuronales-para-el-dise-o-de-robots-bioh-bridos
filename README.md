# Principios Dinámicos Neuronales para el Diseño de Robots Biohíbridos

Este repositorio contiene el código, los datos y los análisis del Trabajo de Fin de Grado (TFG) centrado en la transferencia de patrones rítmicos neuronales de un CPG pilórico a un robot cuadrúpedo bioinspirado. El objetivo es investigar si los **invariantes dinámicos secuenciales** presentes en la actividad neuronal biológica se conservan y producen ventajas locomotoras cuando se transfieren a un robot físico.

> 📢 **Nota importante sobre los archivos multimedia:** Debido al gran tamaño y peso de las grabaciones de los ensayos robóticos (más de 7 GB en total), los archivos de vídeo originales no se encuentran almacenados directamente en este repositorio de GitHub. Puedes acceder, visualizar y descargar la estructura completa de vídeos de los experimentos a través del siguiente enlace externo:
> 
> 🔗 **[Acceder a la Carpeta de Vídeos de los Experimentos (Google Drive)](https://drive.google.com/drive/folders/1hR49FI-s2oY7-gN0mP6HcqDo-8m3YOjr?usp=drive_link)**

---

## Tabla de contenidos

- [Contexto del proyecto](#contexto-del-proyecto)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Descripción de los scripts](#descripción-de-los-scripts)
- [Descripción de los notebooks](#descripción-de-los-notebooks)
- [Código Arduino](#código-arduino)
- [Datos y resultados](#datos-y-resultados)
- [Dependencias](#dependencias)
- [Cómo reproducir el pipeline completo](#cómo-reproducir-el-pipeline-completo)

---

## Contexto del proyecto

Los generadores de patrón central (CPG) producen oscilaciones rítmicas con propiedades dinámicas estables. En este trabajo se registran actividades intracelulares de las neuronas **LP** y **PD**, se extraen los intervalos ciclo a ciclo y se mapean directamente como señales de control (amplitud y período) para mover un robot cangrejo con tres servomotores. Los vídeos de los ensayos robóticos se analizan cinemáticamente para comparar la velocidad y la calidad de la marcha según la condición experimental utilizada.

Las condiciones experimentales son:
- **Invariante** — patrón neuronal con invariante de marcha preservado.
- **Variante** — patrón neuronal perturbado.
- **Potencial solo** — solo los potenciales de acción, sin bursts completos.
- **Corto** — tramo temporal reducido del registro neuronal.

---

## Estructura del repositorio
.
├── README.md
├── 17h55m39s-12-May.txt               # Registro neuronal bruto (electrofisiología)
├── intervalos_originales_tramo_1.txt  # Intervalos extraídos, tramo 1
├── intervalos_originales_tramo_2.txt  # Intervalos extraídos, tramo 2
├── intervalos_originales_tramo_3.txt  # Intervalos extraídos, tramo 3
│
├── Códigos/
│   ├── Análisis del invariante/       # Pipeline neuronal (Python + Jupyter)
│   │   ├── deteccionYanalisis.ipynb
│   │   ├── DivisionEnEnsayos.ipynb
│   │   └── enviar_intervalos.py
│   │
│   ├── Análisis del robot/            # Pipeline cinemático (Python + Jupyter)
│   │   ├── seguimiento_cuerpo_pata.py
│   │   ├── AnalisisPataYvelocidad.ipynb
│   │   └── kinematics/                # Datos cinemáticos generados (px y cm)
│   │
│   └── Código Arduino/
│       └── control_Robot_bluetooth_mejorado/
│           ├── control_Robot_bluetooth_mejorado.ino
│           ├── Oscillator.h / Oscillator.cpp
│           └── ejecutar_intervalos.py
│
├── Vídeos/                            # [Alojados en Google Drive debido a su peso]
│   └── (Ver enlace al principio del documento para acceder a las carpetas exp1, exp2, exp3)
│
└── Gráficas/   # PDFs y SVGs exportados del análisis cinemático

---

## Descripción de los scripts

### `Códigos/Análisis del robot/seguimiento_cuerpo_pata.py`

Script principal de **tracking cinemático por visión por computador**. Procesa un vídeo del robot para extraer la posición horizontal del cuerpo (etiquetas verdes) y de la pata delantera (etiqueta azul) frame a frame.

**Funcionamiento:**
1. Abre el primer frame del vídeo y permite seleccionar interactivamente las regiones de interés (ROI) para el cuerpo y la pata mediante dos clics por zona.
2. Recorre todos los frames aplicando segmentación en espacio de color HSV: verde para el cuerpo (dos manchas → bounding rect), azul para la pata (contorno mayor).
3. Interpola los frames donde se pierde la etiqueta, suaviza las trayectorias y calcula la posición relativa pata−cuerpo.
4. Convierte las posiciones de píxeles a centímetros usando el ancho físico conocido del cuerpo (`BODY_WIDTH_CM = 13.0 cm`).
5. Genera tres archivos de salida en `kinematics/`: datos completos, versión en píxeles y versión en centímetros.

**Salida:** `kinematics/<nombre_experimento>_cinematica_completa.txt` (y variantes `_px.txt`, `_cm.txt`).

---

### `Códigos/Análisis del invariante/enviar_intervalos.py`

Script de **control del robot en tiempo real** vía Bluetooth (módulo HC-05). Lee un archivo de intervalos neuronales previamente extraído y los envía al robot mapeando:
- **Período** neuronal (ms) → período de oscilación del servo (800–1550 ms).
- **Amplitud** neuronal (u.a.) → ángulo de oscilación del servo (5–30°).

Incluye un **modo interactivo por teclado** para ajustar en vivo parámetros de calibración sin detener el robot:

| Tecla | Acción |
|-------|--------|
| `Q/A` | Incrementa/decrementa el offset medio del servo central |
| `W/S` | Incrementa/decrementa el ajuste de dirección |
| `E/D` | Incrementa/decrementa la amplitud media |
| `Z`   | Alterna entre modo archivo (neuronal) y modo constante |
| `Espacio` | Pausa/reanuda el movimiento |
| `X`   | Sale y cierra la conexión |

Guarda un log con marca temporal de cada intervalo enviado en `data/logs_bluetooth/`.

**Uso desde línea de comandos:**
```bash
python enviar_intervalos.py --enviar    # Envío con datos neuronales
python enviar_intervalos.py --calibrar  # Señal constante para calibración
python enviar_intervalos.py --todo      # Muestra datos, analiza rangos y envía

Descripción de los notebooksCódigos/Análisis del invariante/deteccionYanalisis.ipynbNotebook de análisis de la señal electrofisiológica registrada. A partir del archivo bruto de electrofisiología (17h55m39s-12-May.txt), realiza:Carga y visualización de las señales intracelulares de las neuronas LP y PD y la actividad extracelular.Filtrado por media móvil con ventanas de distinto tamaño para eliminar ruido y tendencia (detrending).Detección de picos de potencial de acción y de eventos de hiperpolarización mediante umbrales configurables.Detección de ráfagas (bursts): agrupa los picos individuales en eventos de disparo colectivo usando una distancia máxima intra-ráfaga.Extracción de los intervalos inter-ráfaga (período) y la amplitud de cada ráfaga para su posterior uso como señal de control del robot.Códigos/Análisis del invariante/DivisionEnEnsayos.ipynbNotebook complementario que segmenta el registro neuronal largo en ensayos individuales y genera los archivos de intervalos (intervalos_originales_tramo_X.txt) que consume enviar_intervalos.py.Códigos/Análisis del robot/AnalisisPataYvelocidad.ipynbNotebook de análisis cinemático y estadístico del movimiento del robot. Lee los archivos .txt generados por seguimiento_cuerpo_pata.py y realiza:Selección de una región de interés temporal (ROI) sobre la señal de posición relativa pata−cuerpo.Detección de picos y valles de la oscilación para extraer período y amplitud de cada paso.Regresión lineal período–amplitud con cálculo de R² para cuantificar el invariante de la marcha.Búsqueda automática de los parámetros de suavizado (ventana Savitzky-Golay, distancia mínima entre picos) que maximizan el R² mediante barrido de parámetros.Exportación de figuras en PDF y SVG a la carpeta Gráficas/, con una subfigura por experimento y umbral de pasos mínimos.Análisis comparativo de velocidad media entre condiciones experimentales.Código ArduinoCódigos/Código Arduino/control_Robot_bluetooth_mejorado/control_Robot_bluetooth_mejorado.inoFirmware del robot para Arduino. Controla tres servomotores mediante osciladores sinusoidales (librería Oscillator) y escucha comandos vía Bluetooth (HC-05 en pines 4/5 con SoftwareSerial).Protocolo de comandos (texto plano + \n):ComandoDescripciónHHome — detiene el robot llevando los servos a posición de reposoO<n>Ajusta el offset del servo central a n gradosM<n>Ajusta la amplitud media del servo central a n gradosD<n>Ajusta el offset de dirección (asimetría derecha/izquierda) a n grados<A>\t<T>Mueve el robot con amplitud A grados y período T msLibrerías de soporte:Oscillator.h / Oscillator.cpp — implementa osciladores sinusoidales de período y amplitud configurables para cada servo.Datos y resultadosArchivos de datos neuronales (raíz del repositorio)17h55m39s-12-May.txt — registro bruto de electrofisiología (columnas: tiempo, actividad extracelular, intra LP, intra PD).intervalos_originales_tramo_X.txt — intervalos inter-ráfaga y amplitudes extraídos, listos para enviar al robot.Carpeta Códigos/Análisis del robot/kinematics/Archivos .txt tabulados con las trayectorias cinemáticas de cada experimento en tres versiones:*_completa.txt — datos de tracking completos (píxeles, suavizados).*_px.txt — posiciones en píxeles.*_cm.txt — posiciones convertidas a centímetros.El prefijo del nombre indica la condición experimental: invariant, variant, potencialSolo, corto.Carpeta Gráficas/Figuras exportadas automáticamente por AnalisisPataYvelocidad.ipynb:*_MINxx.pdf/svg — scatter período vs. amplitud con regresión, por experimento y umbral de pasos mínimos.speed_vs_distance_*.pdf — comparativas de velocidad vs. distancia recorrida entre condiciones.velocidad_vs_distancia_todos_exp.pdf — resumen conjunto de todos los experimentos.DependenciasPython (≥ 3.9)numpy
pandas
opencv-python
imutils
scipy
scikit-learn
matplotlib
pyserial         # solo para enviar_intervalos.py
ArduinoArduino IDE con soporte para SoftwareSerial (incluido en el SDK estándar).Librería Oscillator — incluida en el directorio Código Arduino/.Cómo reproducir el pipeline completo1. Electrofisiología → Intervalos
   Abrir deteccionYanalisis.ipynb
   → ajustar umbrales de detección de picos/ráfagas
   Abrir DivisionEnEnsayos.ipynb
   → exporta intervalos_originales_tramo_X.txt

2. Envío al robot
   Cargar control_Robot_bluetooth_mejorado.ino en Arduino
   Emparejar HC-05 (COM11, 9600 baudios)
   python enviar_intervalos.py --enviar

3. Captura de vídeo
   Grabar el ensayo con etiquetas de color (verde = cuerpo, azul = pata)
   Descargar o guardar los vídeos pesados en una plataforma externa (Google Drive)

4. Tracking cinemático
   python seguimiento_cuerpo_pata.py
   → seleccionar ROIs de cuerpo y pata con clics
   → genera kinematics/<experimento>_cinematica_completa*.txt

5. Análisis y figuras
   Abrir AnalisisPataYvelocidad.ipynb
   → ajustar lista_experimentos y ROI temporal
   → exporta figuras a Gráficas/
