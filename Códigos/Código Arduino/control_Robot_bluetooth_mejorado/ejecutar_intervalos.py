"""
Script para enviar intervalos neuronales al robot cangrejo por Bluetooth.

Columnas configurables desde la sección CONFIGURACIÓN:
  - COL_T  -> columna usada como período (ms)
  - COL_A  -> columna usada como amplitud (mapeada a grados

Formato enviado al Arduino: "A\tT\n"

Requisitos:
  pip install pyserial

Uso:
  python ejecutar_intervalos.py [opcion]

  Opciones:
    --enviar    Conectar al robot y enviar datos
    --analizar  Analizar rangos del archivo sin conectar
    --leer      Leer y mostrar el contenido del archivo
    --todo      Ejecutar las tres acciones en orden
    (sin args)  Mostrar menú interactivo


    rundll32.exe shell32.dll,Control_RunDLL bthprops.cpl,,1
"""

import sys
import time

# -------------------------------------------------------
# CONFIGURACIÓN — cambia estos valores según tu sistema
# -------------------------------------------------------
COM_PORT        = "COM11"                  # Puerto COM del HC-05 en tu PC
BAUD_RATE       = 9600                  # Debe coincidir con el Arduino
ARCHIVO         = "intervalos_hiper.txt"  # Ruta al archivo de i            ntervalos
                    # Segundos entre cada fila

# Columnas del archivo (índice 0 = primera columna)
COL_T = 1    # Columna para el período  (ej: 1 = Periodo H1)
COL_A = 3    # Columna para la amplitud (ej: 3 = Intervalo FS1H1)

# Rango de amplitud del robot (grados)
A_ROBOT_MIN = 5
A_ROBOT_MAX = 35

# Rango de mapeo para la amplitud neuronal.
# Si ambos son None, se usa el rango real de los datos automáticamente (recomendado).
# Si quieres fijar un rango manual, ponlos aquí (ej: VAL_MIN=5.0, VAL_MAX=1000.0).
VAL_MIN = None
VAL_MAX = None

# Rango válido de T para el robot (ms)
T_ROBOT_MIN = 500
T_ROBOT_MAX = 2000
# -------------------------------------------------------


# ═══════════════════════════════════════════════════════
# FUNCIONES CORE
# ═══════════════════════════════════════════════════════

def mapear(valor, in_min, in_max, out_min, out_max):
    """Mapea un valor de un rango a otro con clamp."""
    if in_max == in_min:        # ← añade esto
        return out_min          # ← y esto
    valor = max(in_min, min(in_max, valor))
    return int((valor - in_min) / (in_max - in_min) * (out_max - out_min) + out_min)


def nombre_columna(filepath, col_idx):
    """Devuelve el nombre de la columna según la cabecera del archivo."""
    try:
        with open(filepath, 'r') as f:
            for linea in f:
                if linea.startswith('#'):
                    cols = linea.strip().lstrip('#').split('\t')
                    if col_idx < len(cols):
                        return cols[col_idx].strip()
    except Exception:
        pass
    return f"Columna {col_idx}"


def leer_intervalos(filepath):
    """Lee el archivo y devuelve lista de (T, A) según las columnas configuradas."""
    filas = []
    n_cols_min = max(COL_T, COL_A) + 1
    with open(filepath, 'r') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#'):
                continue
            columnas = linea.split('\t')
            if len(columnas) < n_cols_min:
                continue
            try:
                T_val = float(columnas[COL_T])
                A_val = float(columnas[COL_A])
                filas.append((T_val, A_val))
            except ValueError:
                continue
            if len(filas) >= 400:   # ← añade esto
                break               # ← y esto
    return filas


def resolver_rango(filas):
    """Devuelve (val_min, val_max) usando el rango real si VAL_MIN/MAX son None."""
    A_vals = [f[1] for f in filas]
    v_min = VAL_MIN if VAL_MIN is not None else min(A_vals)
    v_max = VAL_MAX if VAL_MAX is not None else max(A_vals)
    return v_min, v_max


def analizar_rangos(filas):
    """Imprime estadísticas y simula el mapeo con el rango configurado."""
    nombre_T = nombre_columna(ARCHIVO, COL_T)
    nombre_A = nombre_columna(ARCHIVO, COL_A)

    T_vals = [f[0] for f in filas]
    A_vals = [f[1] for f in filas]
    v_min, v_max = resolver_rango(filas)
    modo = "AUTO (rango real)" if VAL_MIN is None else "MANUAL"

    print("=" * 55)
    print("ANÁLISIS DE RANGOS")
    print("=" * 55)
    print(f"Número de filas:      {len(filas)}")
    print(f"Columna T:            [{COL_T}] {nombre_T}")
    print(f"Columna A:            [{COL_A}] {nombre_A}")
    print()
    print(f"T — {nombre_T}:")
    print(f"  Min:   {min(T_vals):.1f} ms")
    print(f"  Max:   {max(T_vals):.1f} ms")
    print(f"  Media: {sum(T_vals)/len(T_vals):.1f} ms")
    print(f"  (T robot limitado a {T_ROBOT_MIN}–{T_ROBOT_MAX} ms)")
    print()
    print(f"A — {nombre_A}:")
    print(f"  Min real:   {min(A_vals):.1f}")
    print(f"  Max real:   {max(A_vals):.1f}")
    print(f"  Media real: {sum(A_vals)/len(A_vals):.1f}")
    print()
    print(f"Mapeo [{modo}]: {nombre_A} {v_min:.1f}–{v_max:.1f} → A robot {A_ROBOT_MIN}–{A_ROBOT_MAX}°")
    A_mapeada = [mapear(v, v_min, v_max, A_ROBOT_MIN, A_ROBOT_MAX) for v in A_vals]
    print(f"  Min mapeado:   {min(A_mapeada)}°")
    print(f"  Max mapeado:   {max(A_mapeada)}°")
    print(f"  Media mapeada: {sum(A_mapeada)/len(A_mapeada):.1f}°")
    print("=" * 55)


def mostrar_filas(filas):
    """Imprime el contenido completo del archivo cargado."""
    nombre_T = nombre_columna(ARCHIVO, COL_T)
    nombre_A = nombre_columna(ARCHIVO, COL_A)
    v_min, v_max = resolver_rango(filas)

    print("=" * 65)
    print("CONTENIDO DEL ARCHIVO")
    print("=" * 65)
    print(f"  T = [{COL_T}] {nombre_T}")
    print(f"  A = [{COL_A}] {nombre_A}")
    print("=" * 65)
    print(f"{'#':>5} | {'T (ms)':>10} | {'A neuronal':>12} | {'A robot':>8}")
    print("-" * 65)
    for i, (T_val, A_val) in enumerate(filas):
        A = mapear(A_val, v_min, v_max, A_ROBOT_MIN, A_ROBOT_MAX)
        print(f"{i:>5} | {T_val:>10.1f} | {A_val:>12.1f} | {A:>7}°")
    print("=" * 65)
    print(f"Total: {len(filas)} filas\n")


def enviar_datos(filas):
    """Conecta al HC-05 y envía las filas al robot."""
    try:
        import serial
    except ImportError:
        print("ERROR: pyserial no está instalado.")
        print("  Ejecuta: pip install pyserial")
        return

    v_min, v_max = resolver_rango(filas)

    print(f"\nConectando al HC-05 en {COM_PORT} a {BAUD_RATE} baudios...")
    try:
        bt = serial.Serial(COM_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)
        print("  -> ¡Conectado!\n")
    except serial.SerialException as e:
        print(f"ERROR: No se pudo abrir {COM_PORT}\n  {e}")
        print("\nComprueba que:")
        print("  1. El HC-05 está emparejado con Windows")
        print("  2. El número de COM es correcto")
        print("  3. El robot está encendido")
        return

    print("Enviando datos al robot... (Ctrl+C para parar)\n")
    print(f"{'Fila':>5} | {'T (ms)':>8} | {'A neuronal':>12} | {'A robot':>8} | {'Enviado':>10} | Estado")
    print("-" * 70)

    try:
        for i, (T_val, A_val) in enumerate(filas):
            T_enviar = int(max(T_ROBOT_MIN, min(T_ROBOT_MAX, T_val)))
            A_enviar = mapear(A_val, v_min, v_max, A_ROBOT_MIN, A_ROBOT_MAX)
            mensaje  = f"{A_enviar}\t{T_enviar}\n"

            bt.write(mensaje.encode('utf-8'))
            confirmado = "enviado"

            print(f"{i:>5} | {T_enviar:>8} | {A_val:>12.1f} | {A_enviar:>7}° | {mensaje.strip():>10} | {confirmado}")
            
            # Esperar exactamente lo que dura el período actual (T está en ms, sleep usa segundos)
            tiempo_espera = T_enviar / 1000.0 
            time.sleep(tiempo_espera)

    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario.")

    finally:
        bt.close()
        print("Conexión cerrada.")


# ═══════════════════════════════════════════════════════
# MENÚ INTERACTIVO
# ═══════════════════════════════════════════════════════

def menu():
    print("\n" + "═" * 40)
    print("  ROBOT CANGREJO — Menú principal")
    print("═" * 40)
    print(f"  Archivo : {ARCHIVO}")
    print(f"  Col T   : [{COL_T}] {nombre_columna(ARCHIVO, COL_T)}")
    print(f"  Col A   : [{COL_A}] {nombre_columna(ARCHIVO, COL_A)}")
    print(f"  Rango A : {'AUTO' if VAL_MIN is None else f'{VAL_MIN}–{VAL_MAX}'}")
    print("─" * 40)
    print("  1. Leer y mostrar el archivo")
    print("  2. Analizar rangos")
    print("  3. Enviar datos al robot")
    print("  4. Ejecutar todo (1 → 2 → 3)")
    print("  0. Salir")
    print("═" * 40)
    return input("Elige una opción: ").strip()


def cargar_archivo():
    """Carga el archivo con manejo de error."""
    print(f"\nLeyendo archivo: {ARCHIVO}")
    try:
        filas = leer_intervalos(ARCHIVO)
        print(f"  -> {len(filas)} filas cargadas.\n")
        return filas
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo '{ARCHIVO}'")
        print("  Comprueba que la ruta es correcta en la configuración.")
        return None


# ═══════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]

    # ── Modo argumentos directos ──────────────────────
    if args:
        opcion = args[0].lower()
        filas  = cargar_archivo()
        if filas is None:
            sys.exit(1)

        if opcion == "--leer":
            mostrar_filas(filas)

        elif opcion == "--analizar":
            analizar_rangos(filas)

        elif opcion == "--enviar":
            enviar_datos(filas)

        elif opcion == "--todo":
            mostrar_filas(filas)
            analizar_rangos(filas)
            input("\nPresiona Enter para comenzar el envío al robot...")
            enviar_datos(filas)

        else:
            print(f"Opción desconocida: '{opcion}'")
            print("Uso: python ejecutar_intervalos.py [--leer | --analizar | --enviar | --todo]")
            sys.exit(1)

        return

    # ── Modo menú interactivo ─────────────────────────
    filas = None

    while True:
        opcion = menu()

        if opcion == "0":
            print("Saliendo.")
            break

        if filas is None:
            filas = cargar_archivo()
            if filas is None:
                continue

        if opcion == "1":
            mostrar_filas(filas)

        elif opcion == "2":
            analizar_rangos(filas)

        elif opcion == "3":
            enviar_datos(filas)

        elif opcion == "4":
            mostrar_filas(filas)
            analizar_rangos(filas)
            input("\nPresiona Enter para comenzar el envío al robot...")
            enviar_datos(filas)

        else:
            print("Opción no válida. Elige entre 0 y 4.")

        input("\nPresiona Enter para volver al menú...")


if __name__ == "__main__":
    main()