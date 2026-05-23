#include "Oscillator.h"
#include <Servo.h>
#include <SoftwareSerial.h>

SoftwareSerial BTSerial(4, 5); // RX=4, TX=5

// --- Parámetros de movimiento ---
unsigned int A = 25;
unsigned int T = 1500;
unsigned int limite_A = 30;

Oscillator osc_middle, osc_right, osc_left;

// --- Parámetros de Calibración ---
int offsetM = 5;
int A_medio = 13;
int ajuste_direccion = 2; // El ajuste que equilibra los pasos

// --- Control de Estado ---
bool moviendo = false;

const int LED_PIN = 7;
String inputBuffer = "";

void setup() {
  Serial.begin(19200);
  BTSerial.begin(9600);
  
  osc_middle.attach(2);
  osc_right.attach(10);
  osc_left.attach(8);

  actualizarCalibracion();

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, HIGH);

  // Al encender el robot, forzamos que vaya a su posición inicial (Offsets) y se quede quieto.
  detenerRobot();

  osc_middle.SetPh(DEG2RAD(90));
  osc_left.SetPh(DEG2RAD(0));
  osc_right.SetPh(DEG2RAD(0));
}

void loop() {
  // Los refrescos se siguen llamando, pero como la amplitud es 0 al inicio, se mantienen fijos.
  osc_middle.refresh();
  osc_right.refresh();
  osc_left.refresh();

  while (BTSerial.available() > 0) {
    char c = BTSerial.read();
    if (c == '\n') {
      procesarComando(inputBuffer);
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}

void actualizarCalibracion() {
  osc_middle.SetO(offsetM);
  // Forzamos 0 en los laterales 
  osc_right.SetO(0); 
  osc_left.SetO(0);
}

void detenerRobot() {
  moviendo = false;
  // Al poner la amplitud a 0, los motores van a su posición central (offset) y dejan de andar.
  osc_middle.SetA(0);
  osc_right.SetA(0);
  osc_left.SetA(0);
}

void aplicarAmplitudes() {
  // Aplicamos el ajuste de dirección proporcionalmente a la amplitud
  int ajuste_dinamico = map(A, 5, limite_A, 0, ajuste_direccion);
  osc_right.SetA(A + ajuste_dinamico);
  osc_left.SetA(A);
  osc_middle.SetA(A_medio); 
  
  osc_middle.SetT(T);
  osc_right.SetT(T);
  osc_left.SetT(T);
}

void setMovimiento(int nuevaA, int nuevoT) {
  A = nuevaA;
  T = nuevoT;
  
  if (A > limite_A) A = limite_A;
  if (A < 5) A = 5;
  if (T > 2500) T = 2500;
  if (T < 800) T = 800;

  // Solo enviamos las amplitudes a los motores si el robot NO está en pausa
  if (moviendo) {
    aplicarAmplitudes();
  }
}

void procesarComando(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  // COMANDO HOME / PARAR: "H"
  if (cmd.startsWith("H")) {
    detenerRobot();
    BTSerial.println("ROBOT_EN_OFFSET");
  }
  // COMANDO OFFSET MEDIO: "O valor"
  else if (cmd.startsWith("O")) {
    offsetM = cmd.substring(1).toInt();
    actualizarCalibracion();
    BTSerial.print("OFFSET_M_OK: "); BTSerial.println(offsetM);
  } 
  // COMANDO AMPLITUD MEDIA: "M valor"
  else if (cmd.startsWith("M")) {
    A_medio = cmd.substring(1).toInt();
    if (moviendo) aplicarAmplitudes();
    BTSerial.print("AMEDIO_OK: "); BTSerial.println(A_medio);
  }
  // COMANDO AJUSTE DIRECCIÓN: "D valor"
  else if (cmd.startsWith("D")) {
    ajuste_direccion = cmd.substring(1).toInt();
    if (moviendo) aplicarAmplitudes();
    BTSerial.print("DIR_OK: "); BTSerial.println(ajuste_direccion);
  }
  // COMANDO MOVIMIENTO: "A T"
  else {
    int spacePos = cmd.indexOf('\t');
    if (spacePos == -1) spacePos = cmd.indexOf(' ');
    
    if (spacePos != -1) {
      int nuevaA = cmd.substring(0, spacePos).toInt();
      int nuevoT = cmd.substring(spacePos + 1).toInt();
      
      // Al recibir coordenadas, reactivamos el movimiento
      moviendo = true;
      setMovimiento(nuevaA, nuevoT);
    }
  }
}
