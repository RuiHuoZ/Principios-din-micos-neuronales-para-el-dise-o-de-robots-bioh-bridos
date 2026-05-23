"""
Script para enviar intervalos neuronales al robot cangrejo por Bluetooth.
Incluye análisis previo y ajuste de parámetros de calibración en vivo (teclado).

"""
import os
import datetime
import sys
import time
import msvcrt

# -------------------------------------------------------
# CONFIGURACIÓN
# -------------------------------------------------------
COM_PORT        = "COM11"
BAUD_RATE       = 9600
ARCHIVO         = "Intervalos_originales_tramo_3.txt"

DESCARTAR_FILAS = 0

COL_T = -2
COL_A = -1

A_ROBOT_MIN = 5
A_ROBOT_MAX = 30

VAL_MIN = None
VAL_MAX = None

T_ROBOT_MIN = 800
T_ROBOT_MAX = 1550


OFFSET_M  = 3
A_MEDIO   = 12
AJUSTE_DIR = -5

# Número de reintentos de reconexión Bluetooth antes de rendirse
MAX_REINTENTOS_BT = 10
ESPERA_REINTENTO  = 1.0   # segundos entre reintentos


def mapear(valor, in_min, in_max, out_min, out_max):
    if in_max == in_min:
        return out_min
    valor = max(in_min, min(in_max, valor))
    return int((valor - in_min) / (in_max - in_min) * (out_max - out_min) + out_min)


def nombre_columna(filepath, col_idx):
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
    filas = []
    n_cols_min = max(COL_T, COL_A) + 1
    try:
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
                if len(filas) >= 1000:
                    break
    except FileNotFoundError:
        return None

    if DESCARTAR_FILAS > 0 and len(filas) > DESCARTAR_FILAS:
        print(f"  [!] Ignorando las primeras {DESCARTAR_FILAS} filas (Fase de arranque).")
        filas = filas[DESCARTAR_FILAS:]
    elif DESCARTAR_FILAS >= len(filas):
        print("  [ADVERTENCIA] Quieres descartar más filas de las que tiene el archivo.")

    return filas


def resolver_rangos(filas):
    T_vals = [f[0] for f in filas]
    A_vals = [f[1] for f in filas]
    t_min = min(T_vals)
    t_max = max(T_vals)
    a_min = VAL_MIN if VAL_MIN is not None else min(A_vals)
    a_max = VAL_MAX if VAL_MAX is not None else max(A_vals)
    return t_min, t_max, a_min, a_max


def analizar_rangos(filas):
    nombre_T = nombre_columna(ARCHIVO, COL_T)
    nombre_A = nombre_columna(ARCHIVO, COL_A)
    t_min, t_max, a_min, a_max = resolver_rangos(filas)
    modo_A = "AUTO (rango real)" if VAL_MIN is None else "MANUAL"

    print("=" * 65)
    print("ANÁLISIS DE RANGOS (MAPEO DOBLE)")
    print("=" * 65)
    print(f"Número de filas:      {len(filas)}")
    print(f"Columna T:            [{COL_T}] {nombre_T}")
    print(f"Columna A:            [{COL_A}] {nombre_A}")
    print(f"\nT — {nombre_T}:")
    print(f"  Rango en archivo: {t_min:.1f}  →  {t_max:.1f}")
    print(f"  Mapeo configurado: {t_min:.1f}–{t_max:.1f} → T robot {T_ROBOT_MIN}–{T_ROBOT_MAX} ms")
    print(f"\nA — {nombre_A}:")
    print(f"  Rango en archivo: {a_min:.1f}  →  {a_max:.1f}")
    print(f"  Mapeo [{modo_A}]: {a_min:.1f}–{a_max:.1f} → A robot {A_ROBOT_MIN}–{A_ROBOT_MAX}°")
    print("=" * 65)


def mostrar_filas(filas):
    t_min, t_max, a_min, a_max = resolver_rangos(filas)
    print("=" * 65)
    print(f"{'#':>5} | {'T real':>10} | {'T mapeado':>10} | {'A neuronal':>12} | {'A mapeada':>9}")
    print("-" * 65)
    for i, (T_val, A_val) in enumerate(filas):
        T_map = mapear(T_val, t_min, t_max, T_ROBOT_MIN, T_ROBOT_MAX)
        A_map = mapear(A_val, a_min, a_max, A_ROBOT_MIN, A_ROBOT_MAX)
        print(f"{i:>5} | {T_val:>10.1f} | {T_map:>7} ms | {A_val:>12.1f} | {A_map:>8}°")
    print("=" * 65 + "\n")



def conectar_bluetooth(serial_module):
    """Intenta abrir el puerto serie. Reintenta MAX_REINTENTOS_BT veces."""
    for intento in range(1, MAX_REINTENTOS_BT + 1):
        try:
            bt = serial_module.Serial(COM_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)
            print(f"  -> Conectado (intento {intento})")
            return bt
        except serial_module.SerialException as e:
            print(f"  [!] Intento {intento}/{MAX_REINTENTOS_BT} fallido: {e}")
            if intento < MAX_REINTENTOS_BT:
                print(f"      Reintentando en {ESPERA_REINTENTO}s...")
                time.sleep(ESPERA_REINTENTO)
    return None


def enviar_seguro(bt, mensaje, serial_module, log_f=None):
    """
    Envía un mensaje por Bluetooth. Si falla, intenta reconectar y reenviar.
    """
    for intento in range(MAX_REINTENTOS_BT):
        try:
            bt.write(mensaje if isinstance(mensaje, bytes) else mensaje.encode('utf-8'))
            return bt   # éxito
        except Exception as e:
            print(f"\n  [!] Error de envío (intento {intento+1}): {e}")
            print(f"      Intentando reconectar...")
            try:
                bt.close()
            except Exception:
                pass
            bt = conectar_bluetooth(serial_module)
            if bt is None:
                print("  [!!] No se pudo reconectar. Abortando.")
                return None
            # Restaurar ajustes de dirección tras reconexión
            try:
                bt.write(f"D{AJUSTE_DIR}\n".encode())
                time.sleep(0.2)
            except Exception:
                pass
    return None



def ejecucion_interactiva(filas, modo_inicial_archivo=True):
    global OFFSET_M, A_MEDIO, AJUSTE_DIR

    try:
        import serial
    except ImportError:
        print("ERROR: pyserial no está instalado. (pip install pyserial)")
        return

    t_min, t_max, a_min, a_max = resolver_rangos(filas)

    print(f"\nConectando al HC-05 en {COM_PORT} a {BAUD_RATE} baudios...")
    bt = conectar_bluetooth(serial)
    if bt is None:
        print("ERROR: No se pudo establecer conexión Bluetooth.")
        return

    print("  -> Llevando a posición inicial (Offset) y preparando...")
    bt = enviar_seguro(bt, b"H\n", serial)
    if bt is None: return

    print(f"  -> Configurando ajuste de dirección inicial: {AJUSTE_DIR}")
    bt = enviar_seguro(bt, f"D{AJUSTE_DIR}\n", serial)
    if bt is None: return

    time.sleep(1.5)
    print("  -> ¡Listo para enviar datos!\n")

    modo_intervalo = modo_inicial_archivo
    pausado = False
    idx_fila = 0

    print("=" * 65)
    print(" MODO EJECUCIÓN INTERACTIVA (ENVÍO Y CALIBRACIÓN)")
    print("=" * 65)
    print(" Q/A     : Offset Medio  |  W/S : Ajuste Dirección")
    print(" E/D     : Amp. Media    |  Z   : Cambiar (Constante/Archivo)")
    print(" Espacio : Pausa/Reanudar|  X   : Salir ")
    print("-" * 65)

    os.makedirs("data/logs_bluetooth", exist_ok=True)
    nombre_log = f"data/logs_bluetooth/Enviados_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    log_f = open(nombre_log, "w", buffering=1)   
    log_f.write("Timestamp_s\tFila\tT_neuronal\tA_neuronal\tT_Robot_ms\tA_Robot_grados\n")
    print(f"  -> Guardando log en: {nombre_log}")

    ultimo_envio  = 0
    espera_actual = 0
    status_modo   = ""

    try:
        while True:
            tiempo_actual = time.time()

            if not pausado and (tiempo_actual - ultimo_envio >= espera_actual):
                if modo_intervalo and filas:
                    T_val, A_val = filas[idx_fila]
                    A_enviar = mapear(A_val, a_min, a_max, A_ROBOT_MIN, A_ROBOT_MAX)
                    T_enviar = mapear(T_val, t_min, t_max, T_ROBOT_MIN, T_ROBOT_MAX)

                    bt = enviar_seguro(bt, f"{A_enviar}\t{T_enviar}\n", serial, log_f)
                    if bt is None:
                        print("\n[!!] Conexión perdida definitivamente. Guardando log y saliendo.")
                        break

                    try:
                        log_f.write(f"{tiempo_actual:.3f}\t{idx_fila}\t{T_val}\t{A_val}\t{T_enviar}\t{A_enviar}\n")
                    except Exception as e:
                        print(f"\n  [!] Error escribiendo log: {e}")

                    espera_actual = T_enviar / 1000.0
                    ultimo_envio  = time.time()
                    status_modo   = f"ARCHIVO ({idx_fila+1}/{len(filas)}) [A:{A_enviar:02d}° T:{T_enviar}ms]"
                    print(f"\n[Fila {idx_fila+1}] Enviando -> Amplitud: {A_enviar}°, Periodo: {T_enviar} ms")
                    idx_fila = (idx_fila + 1) % len(filas)

                else:
                    bt = enviar_seguro(bt, "25\t1500\n", serial)
                    if bt is None:
                        print("\n[!!] Conexión perdida definitivamente. Saliendo.")
                        break
                    espera_actual = 1.5
                    ultimo_envio  = time.time()
                    status_modo   = "CONSTANTE [A:25° T:1500ms]      "

            if msvcrt.kbhit():
                try:
                    tecla = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                except Exception:
                    tecla = ''

                if tecla == 'x':
                    break
                elif tecla == ' ':
                    pausado = not pausado
                    if pausado:
                        bt = enviar_seguro(bt, b"H\n", serial)
                        status_modo = "PAUSADO (En posicion offset)    "
                    else:
                        ultimo_envio = 0
                elif tecla == 'z':
                    modo_intervalo = not modo_intervalo
                    if not pausado: ultimo_envio = 0
                elif tecla == 'q': OFFSET_M  += 1; bt = enviar_seguro(bt, f"O{OFFSET_M}\n",  serial)
                elif tecla == 'a': OFFSET_M  -= 1; bt = enviar_seguro(bt, f"O{OFFSET_M}\n",  serial)
                elif tecla == 'w': AJUSTE_DIR += 1; bt = enviar_seguro(bt, f"D{AJUSTE_DIR}\n", serial)
                elif tecla == 's': AJUSTE_DIR -= 1; bt = enviar_seguro(bt, f"D{AJUSTE_DIR}\n", serial)
                elif tecla == 'e': A_MEDIO   += 1; bt = enviar_seguro(bt, f"M{A_MEDIO}\n",   serial)
                elif tecla == 'd': A_MEDIO   -= 1; bt = enviar_seguro(bt, f"M{A_MEDIO}\n",   serial)

                # Si algún comando de teclado perdió la conexión, salir limpiamente
                if bt is None:
                    print("\n[!!] Conexión perdida durante ajuste manual. Saliendo.")
                    break

                print(f"\r[{status_modo}] -> Off:{OFFSET_M} | Dir:{AJUSTE_DIR} | A_Med:{A_MEDIO}   ", end="")
                sys.stdout.flush()

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario (Ctrl+C).")
    except Exception as e:

        print(f"\n\n[!!] Error inesperado en el bucle principal: {e}")
    finally:
        # Siempre intentar mandar Home y cerrar limpiamente
        if bt:
            try:
                bt.write(b"H\n")
                time.sleep(0.3)
                bt.close()
            except Exception:
                pass
        log_f.close()
        print("Conexión cerrada. Log guardado.")




def menu():
    print("\n" + "═" * 45)
    print("  ROBOT CANGREJO — Menú principal")
    print("═" * 45)
    print(f"  Archivo : {ARCHIVO}")
    print("─" * 45)
    print("  1. Leer y mostrar el archivo")
    print("  2. Analizar rangos")
    print("  3. Enviar datos al robot (Ajuste en vivo)")
    print("  4. Modo Calibración (Señal Constante)")
    print("  5. Ejecutar todo (1 → 2 → 3)")
    print("  0. Salir")
    print("═" * 45)
    return input("Elige una opción: ").strip()


def cargar_archivo():
    print(f"\nLeyendo archivo: {ARCHIVO}...")
    filas = leer_intervalos(ARCHIVO)
    if filas is None:
        print(f"ERROR: No se encontró o no se pudo leer '{ARCHIVO}'.")
        return None
    print(f"  -> {len(filas)} filas cargadas.\n")
    return filas


def main():
    args = sys.argv[1:]

    if args:
        opcion = args[0].lower()
        filas = cargar_archivo()
        if not filas: sys.exit(1)

        if opcion == "--leer":      mostrar_filas(filas)
        elif opcion == "--analizar": analizar_rangos(filas)
        elif opcion == "--enviar":   ejecucion_interactiva(filas, modo_inicial_archivo=True)
        elif opcion == "--calibrar": ejecucion_interactiva(filas, modo_inicial_archivo=False)
        elif opcion == "--todo":
            mostrar_filas(filas)
            analizar_rangos(filas)
            input("\nPresiona Enter para comenzar el envío al robot...")
            ejecucion_interactiva(filas, modo_inicial_archivo=True)
        return

    filas = None
    while True:
        op = menu()
        if op == "0":
            break

        if filas is None and op in ["1", "2", "3", "4", "5"]:
            filas = cargar_archivo()
            if not filas: continue

        if op == "1":      mostrar_filas(filas)
        elif op == "2":    analizar_rangos(filas)
        elif op == "3":    ejecucion_interactiva(filas, modo_inicial_archivo=True)
        elif op == "4":    ejecucion_interactiva(filas, modo_inicial_archivo=False)
        elif op == "5":
            mostrar_filas(filas)
            analizar_rangos(filas)
            input("\nPresiona Enter para comenzar el envío al robot...")
            ejecucion_interactiva(filas, modo_inicial_archivo=True)
        else:
            print("Opción no válida.")

        if op not in ["3", "4", "5"]:
            input("\nPresiona Enter para volver al menú...")


if __name__ == "__main__":
    main()