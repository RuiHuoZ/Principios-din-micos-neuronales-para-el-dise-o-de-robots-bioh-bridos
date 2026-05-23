import cv2
import numpy as np
import pandas as pd
import imutils
from pathlib import Path

# ── 1. Configuración de Rutas y Variables ────────────────────────────────────
video_folder  = "videos_robot/exp2"
videofile     = "invarianeditexp2.mp4"
display_width = 1200

script_dir      = Path(__file__).parent
project_root    = script_dir.parent
video_full_path = script_dir / video_folder / videofile
exp_name        = video_full_path.stem

outfile = project_root / "data" / "kinematics" / f"{exp_name}_cinematica_completa.txt"
outfile.parent.mkdir(parents=True, exist_ok=True)

# ── PARÁMETROS HSV ──
# Verde (Cuerpo) — dos etiquetas cuadradas
lower_green = np.array([40, 50, 50])
upper_green = np.array([90, 255, 255])

lower_blue = np.array([82, 120, 80])
upper_blue = np.array([112, 255, 240])

# Ancho real del cuerpo en cm (distancia entre los extremos del bounding rect)
# Ajusta este valor a tu robot
BODY_WIDTH_CM = 14.0

data_list = []

# ── 2. Leer primer frame para seleccionar ROIs ────────────────────────────────
cap_calib = cv2.VideoCapture(str(video_full_path))
if not cap_calib.isOpened():
    raise ValueError(f"No se pudo abrir el vídeo: {video_full_path}")
ret, first_frame = cap_calib.read()
cap_calib.release()
if not ret:
    raise ValueError("No se pudo leer el primer frame.")

roi_img_disp = imutils.resize(first_frame, width=display_width)
scale_ratio  = first_frame.shape[1] / float(display_width)

# ── Función genérica de selección de ROI por clics ───────────────────────────
def seleccionar_roi_lineas(nombre_ventana, imagen, color=(0, 255, 255)):
    """
    Muestra la imagen y espera 2 clics para definir límite superior e inferior.
    Devuelve (y_top_4k, y_bottom_4k) en coordenadas del frame original.
    """
    puntos = []
    img_copy = imagen.copy()

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(puntos) < 2:
            puntos.append(y)
            cv2.line(img_copy, (0, y), (img_copy.shape[1], y), color, 2)
            cv2.imshow(nombre_ventana, img_copy)

    cv2.namedWindow(nombre_ventana, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(nombre_ventana, on_click, img_copy)
    cv2.imshow(nombre_ventana, img_copy)

    print(f">>> [{nombre_ventana}] Haz clic en el límite SUPERIOR y luego en el INFERIOR. <<<")
    while len(puntos) < 2:
        if (cv2.waitKey(20) & 0xFF) == 27:
            raise SystemExit("Selección cancelada.")
    cv2.destroyWindow(nombre_ventana)

    y_top    = int(min(puntos) * scale_ratio)
    y_bottom = int(max(puntos) * scale_ratio)
    print(f"  ROI 4K real: Y={y_top} → Y={y_bottom}\n")
    return y_top, y_bottom

# Seleccionar ROI del Cuerpo (verde)
y_top_body, y_bot_body = seleccionar_roi_lineas(
    "CUERPO (VERDE) — limite superior e inferior", roi_img_disp, color=(0, 255, 0))

# Seleccionar ROI de la Pata (azul)
y_top_leg, y_bot_leg = seleccionar_roi_lineas(
    "PATA (AZUL) — limite superior e inferior", roi_img_disp, color=(255, 100, 0))

# ── 3. Bucle principal de tracking ───────────────────────────────────────────
cap = cv2.VideoCapture(str(video_full_path))
print("\nProcesando video... Pulsa ESC para interrumpir.\n")

def y4k_to_disp(y):
    return int(y / scale_ratio)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0  # segundos

    # ── Pre-procesado: GaussianBlur ANTES de HSV (clave para reducir vibrado) ──
    blurred = cv2.GaussianBlur(frame, (11, 11), 0)
    hsv     = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # ── Tracking del Cuerpo (Verde) — dos etiquetas, bounding rect ───────────
    mask_body = cv2.inRange(hsv, lower_green, upper_green)
    mask_body[:y_top_body, :] = 0   # Anular fuera de ROI
    mask_body[y_bot_body:, :] = 0
    mask_body = cv2.erode(mask_body,  None, iterations=2)
    mask_body = cv2.dilate(mask_body, None, iterations=6)  # igual que tracking_body_ORIG: fusiona las dos etiquetas en un solo blob

    cnts_body = cv2.findContours(mask_body.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts_body = imutils.grab_contours(cnts_body)

    body_x, body_y, body_scale = np.nan, np.nan, np.nan
    if len(cnts_body) >= 2:
        # Las dos manchas verdes más grandes → rectángulo que las engloba
        top2 = sorted(cnts_body, key=cv2.contourArea, reverse=True)[:2]
        all_pts = np.vstack(top2)
        rx, ry, rw, rh = cv2.boundingRect(all_pts)
        body_x = rx + rw // 2
        body_y = ry + rh // 2
        body_scale = BODY_WIDTH_CM / rw  # cm por píxel
        cv2.drawContours(frame, top2, -1, (0, 255, 0), 2)
        cv2.rectangle(frame, (rx, ry), (rx + rw, ry + rh), (0, 200, 0), 2)
        cv2.circle(frame, (body_x, body_y), 6, (0, 200, 0), -1)
    elif len(cnts_body) == 1:
        # Fallback: una sola etiqueta visible
        cv2.drawContours(frame, cnts_body, -1, (0, 165, 0), 2)
        M = cv2.moments(cnts_body[0])
        if M["m00"] > 0:
            body_x = int(M["m10"] / M["m00"])
            body_y = int(M["m01"] / M["m00"])
            cv2.circle(frame, (body_x, body_y), 6, (0, 165, 0), -1)

    # ── Tracking de la Pata (Azul) ────────────────────────────────────────────
    mask_leg = cv2.inRange(hsv, lower_blue, upper_blue)
    mask_leg[:y_top_leg, :] = 0
    mask_leg[y_bot_leg:, :] = 0
    mask_leg = cv2.erode(mask_leg,  None, iterations=2)
    mask_leg = cv2.dilate(mask_leg, None, iterations=2)

    cnts_leg = cv2.findContours(mask_leg.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts_leg = imutils.grab_contours(cnts_leg)

    leg_x, leg_y = np.nan, np.nan
    if len(cnts_leg) > 0:
        c_leg = max(cnts_leg, key=cv2.contourArea)
        cv2.drawContours(frame, [c_leg], 0, (255, 0, 0), 2)
        M = cv2.moments(c_leg)
        if M["m00"] > 0:
            leg_x = int(M["m10"] / M["m00"])
            leg_y = int(M["m01"] / M["m00"])
            cv2.circle(frame, (leg_x, leg_y), 6, (255, 0, 0), -1)

    data_list.append({'time': frame_time, 'body_x': body_x, 'leg_x': leg_x, 'scale': body_scale})

    # ── Visualización redimensionada ──────────────────────────────────────────
    frame_display = imutils.resize(frame, width=display_width)

    cv2.line(frame_display, (0, y4k_to_disp(y_top_body)), (display_width, y4k_to_disp(y_top_body)), (0, 255, 0), 1)
    cv2.line(frame_display, (0, y4k_to_disp(y_bot_body)), (display_width, y4k_to_disp(y_bot_body)), (0, 255, 0), 1)
    cv2.line(frame_display, (0, y4k_to_disp(y_top_leg)),  (display_width, y4k_to_disp(y_top_leg)),  (255, 100, 0), 1)
    cv2.line(frame_display, (0, y4k_to_disp(y_bot_leg)),  (display_width, y4k_to_disp(y_bot_leg)),  (255, 100, 0), 1)

    cv2.imshow('Tracking Dual (Verde=Cuerpo, Azul=Pata) — ESC para salir', frame_display)
    if (cv2.waitKey(1) & 0xFF) == 27:
        break

cap.release()
cv2.destroyAllWindows()

# ── 4. Post-procesado y filtrado ──────────────────────────────────────────────
print("\nAplicando filtrado y calculando cinematica relativa...")

df = pd.DataFrame(data_list)

# Interpolar NaNs (frames donde se perdio la etiqueta)
df['body_x'] = df['body_x'].interpolate(method='linear', limit_direction='both')
df['leg_x']  = df['leg_x'].interpolate(method='linear', limit_direction='both')
df['scale']  = df['scale'].interpolate(method='linear', limit_direction='both')
df = df.bfill().ffill()

# Suavizado simetrico — ventana de 34 frames igual que tracking_body_ORIG
window_size = 60 if len(df) > 60 else len(df)
window_leg  = 15 if len(df) > 15 else len(df)   # suavizado suave para preservar picos de la pata

df['body_x_smooth'] = df['body_x'].rolling(window=window_size, center=True).mean()
df['leg_x_smooth']  = df['leg_x'].rolling(window=window_leg,  center=True).mean()
df['scale_smooth']  = df['scale'].rolling(window=window_size, center=True).mean()

# Rellenar extremos (NaN por center=True) con la senal interpolada
df['body_x_smooth'] = df['body_x_smooth'].fillna(df['body_x'])
df['leg_x_smooth']  = df['leg_x_smooth'].fillna(df['leg_x'])
df['scale_smooth']  = df['scale_smooth'].fillna(df['scale'])

# Posicion relativa pata − cuerpo (pixeles)
df['x_relativa'] = df['leg_x_smooth'] - df['body_x_smooth']

# ── Conversion a centimetros (igual que tracking_body_ORIG) ──────────────────
scales_smooth = df['scale_smooth'].values

# Cuerpo en cm: integrar desplazamientos pixel x escala
dx_body_px = np.diff(df['body_x_smooth'].values, prepend=df['body_x_smooth'].values[0])
body_x_cm  = np.cumsum(dx_body_px * scales_smooth)

# Pata en cm
dx_leg_px = np.diff(df['leg_x_smooth'].values, prepend=df['leg_x_smooth'].values[0])
leg_x_cm  = np.cumsum(dx_leg_px * scales_smooth)

# Posicion relativa en cm
x_relativa_cm = leg_x_cm - body_x_cm

df['body_x_cm']     = body_x_cm
df['leg_x_cm']      = leg_x_cm
df['x_relativa_cm'] = x_relativa_cm

# ── 5. Guardar datos ──────────────────────────────────────────────────────────
# Archivo original: cinematica_completa (el que lee el notebook)
df.to_csv(outfile, index=False, sep='\t', columns=[
    'time', 'x_relativa', 'leg_x', 'body_x', 'leg_x_smooth', 'body_x_smooth'
])

# Archivo px: igual que el original, con sufijo explícito
outfile_px = str(outfile).replace('.txt', '_px.txt')
df.to_csv(outfile_px, index=False, sep='\t', columns=[
    'time', 'x_relativa', 'leg_x', 'body_x', 'leg_x_smooth', 'body_x_smooth'
])

# Archivo cm: trayectorias convertidas a centimetros
outfile_cm = str(outfile).replace('.txt', '_cm.txt')
df.to_csv(outfile_cm, index=False, sep='\t', columns=[
    'time', 'x_relativa_cm', 'leg_x_cm', 'body_x_cm'
])

print(f"\n✅ Proceso completado.")
print(f"   Cinematica completa -> {outfile}")
print(f"   Pixeles             -> {outfile_px}")
print(f"   Cm                  -> {outfile_cm}")
print("Columnas px : time | x_relativa | leg_x | body_x | leg_x_smooth | body_x_smooth")
print("Columnas cm : time | x_relativa_cm | leg_x_cm | body_x_cm")