/*
 * Arduino Leonardo Joystick + LED Controller (MAX7219)
 * 
 * Combina:
 * - Joystick USB HID (potenziometri, encoder, matrice pulsanti 5x6)
 * - Serial CDC per ricevere comandi LED da Train Simulator Bridge
 * - 13 LED tramite MAX7219 (SPI software, 3 pin)
 * 
 * Il Leonardo (ATmega32U4) supporta HID + Serial contemporaneamente!
 * 
 * Componenti:
 * - 3 Potenziometri SLIDER 100mm B10K (Assi X, Y, Z)
 * - 1 Encoder rotativo con pulsante (click nella matrice)
 * - 8 Switch ON-OFF-ON momentanei (SW1-SW8, tornano al centro)
 * - 2 Switch ON-OFF-ON Self-Lock (TOGGLE1, TOGGLE2, mantengono posizione)
 * - 1 Rotary switch 4 posizioni (ROT4: 4 ON, nessun OFF)
 * - 1 Rotary switch 3 posizioni (ROT3: OFF + 2)
 * - 1 Pulsante/Pedale (BTN1 + pedale in parallelo + encoder click)
 * - 1 Modulo MAX7219 (WCMCU DISY1) per 13 LED
 * 
 * LED via MAX7219 (DIG0 + DIG1, SEG A-H):
 * - LED1:  DIG0 SEG_A  SIFA Warning (giallo)
 * - LED2:  DIG0 SEG_B  LZB Ende (giallo)
 * - LED3:  DIG0 SEG_C  PZB 70 (blu)
 * - LED4:  DIG0 SEG_D  PZB 85 (blu)
 * - LED5:  DIG0 SEG_E  PZB 55 (blu)
 * - LED6:  DIG0 SEG_F  500Hz (rosso)
 * - LED7:  DIG0 SEG_G  1000Hz (giallo)
 * - LED8:  DIG0 SEG_DP Porte SX (giallo)
 * - LED9:  DIG1 SEG_A  Porte DX (giallo)
 * - LED10: DIG1 SEG_B  LZB Ü Übertragung (blu)
 * - LED11: DIG1 SEG_C  LZB G aktiv (rosso)
 * - LED12: DIG1 SEG_D  LZB S Schnellbremsung (rosso)
 * - LED13: DIG1 SEG_E  Befehl 40 (giallo)
 * 
 * Protocollo seriale (115200 baud):
 * - LED:n:stato  (n=1-13, stato=0/1)
 * - SIFA:stato   (alias LED1)
 * - LZB:stato    (alias LED2)
 * - LZB_UE:stato (alias LED10)
 * - LZB_G:stato  (alias LED11)
 * - LZB_S:stato  (alias LED12)
 * - BEF40:stato  (alias LED13)
 * - OFF          (spegni tutto)
 */

// ============== USB DEVICE NAME ==============
// Modifica qui il nome che appare in Windows
#define USB_PRODUCT "Zusi3 Train Controller"

#include <Joystick.h>
#include <Encoder.h>

// ============== PIN ARDUINO LEONARDO ==============

// Potenziometri (pin analogici)
#define POT_X A0
#define POT_Y A1
#define POT_Z A2

// MAX7219 (SPI software, 3 pin — tutti sullo header analogico)
#define MAX_DIN  A3  // Data In
#define MAX_CLK  A4  // Clock
#define MAX_CS   A5  // Chip Select (LOAD)

// Encoder rotativo (CLK e DT con interrupt)
#define ENCODER_CLK 2
#define ENCODER_DT  3
// ENCODER_SW è nella matrice (ROW0, COL5)

// ============== MATRICE 5x6 ==============
#define MATRIX_ROWS 5
#define MATRIX_COLS 6

const int ROW_PINS[MATRIX_ROWS] = {5, 6, 7, 8, 9};
const int COL_PINS[MATRIX_COLS] = {10, 11, 12, 13, 4, 1};  // COL5 su pin 1 (TX, libero su Leonardo)

// Layout matrice 5x6 (30 posizioni, usiamo 28):
const int MATRIX_MAP[MATRIX_ROWS][MATRIX_COLS] = {
  {17, 18, 19, 20, 21, 16},  // BTN1/PEDALE, ROT4_1, ROT4_2, ROT4_3, ROT4_4, ENC_SW
  {0,  2,  4,  6,  8,  22},  // SW1_UP, SW2_UP, SW3_UP, SW4_UP, SW5_UP, TOG1_UP
  {1,  3,  5,  7,  9,  23},  // SW1_DN, SW2_DN, SW3_DN, SW4_DN, SW5_DN, TOG1_DN
  {10, 12, 14, 24, 25, 26},  // SW6_UP, SW7_UP, SW8_UP, ROT3_1, ROT3_2, TOG2_UP
  {11, 13, 15, -1, -1, 27}   // SW6_DN, SW7_DN, SW8_DN, (vuoto), (vuoto), TOG2_DN
};

// ============== JOYSTICK ==============
#define BUTTON_COUNT 28
#define HAT_SWITCH_COUNT 0

Joystick_ Joystick(
  JOYSTICK_DEFAULT_REPORT_ID,
  JOYSTICK_TYPE_JOYSTICK,
  BUTTON_COUNT,
  HAT_SWITCH_COUNT,
  true, true, true, true,  // X, Y, Z, Rx
  false, false, false, false, false, false, false
);

// ============== ENCODER ==============
Encoder myEncoder(ENCODER_CLK, ENCODER_DT);
long lastEncoderPosition = 0;
const int ENCODER_MIN = 0;
const int ENCODER_MAX = 1023;
const int ENCODER_MULTIPLIER = 4;

// ============== VARIABILI ==============

// Debounce
unsigned long lastDebounceTime[BUTTON_COUNT];
const unsigned long DEBOUNCE_DELAY = 50;
bool buttonStates[BUTTON_COUNT];
bool lastButtonStates[BUTTON_COUNT];

// Potenziometri
const int POT_DEADZONE = 5;
int lastPotValues[3] = {512, 512, 512};
const int SMOOTHING_SAMPLES = 3;
int potHistory[3][SMOOTHING_SAMPLES];
int potHistoryIndex[3] = {0, 0, 0};

// Serial buffer
#define SERIAL_BAUD 115200
#define BUFFER_SIZE 32
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// ============== MAX7219 LED ==============
#define NUM_LEDS 13
bool ledStates[NUM_LEDS] = {false};

// MAX7219 registri
#define REG_NOOP        0x00
#define REG_DIGIT0      0x01
#define REG_DIGIT1      0x02
#define REG_DECODE_MODE 0x09
#define REG_INTENSITY   0x0A
#define REG_SCAN_LIMIT  0x0B
#define REG_SHUTDOWN    0x0C
#define REG_TEST        0x0F

// ============== MAX7219 FUNZIONI ==============

void max7219_send(byte reg, byte data) {
  digitalWrite(MAX_CS, LOW);
  shiftOut(MAX_DIN, MAX_CLK, MSBFIRST, reg);
  shiftOut(MAX_DIN, MAX_CLK, MSBFIRST, data);
  digitalWrite(MAX_CS, HIGH);
}

void max7219_init() {
  pinMode(MAX_DIN, OUTPUT);
  pinMode(MAX_CLK, OUTPUT);
  pinMode(MAX_CS, OUTPUT);
  digitalWrite(MAX_CS, HIGH);

  max7219_send(REG_TEST, 0x00);        // Test mode off
  max7219_send(REG_DECODE_MODE, 0x00); // No BCD decode (raw segments)
  max7219_send(REG_SCAN_LIMIT, 0x01);  // Scan digit 0 e 1 (2 digit)
  max7219_send(REG_INTENSITY, 0x08);   // Luminosità media (0x00-0x0F)
  max7219_send(REG_SHUTDOWN, 0x01);    // Normal operation
  max7219_send(REG_DIGIT0, 0x00);      // Tutti spenti
  max7219_send(REG_DIGIT1, 0x00);      // Tutti spenti
}

void max7219_update() {
  // DIG0: LED1(A) LED2(B) LED3(C) LED4(D) LED5(E) LED6(F) LED7(G) LED8(DP)
  byte dig0 = 0;
  if (ledStates[0])  dig0 |= 0x01;  // SEG_A = LED1 SIFA
  if (ledStates[1])  dig0 |= 0x02;  // SEG_B = LED2 LZB Ende
  if (ledStates[2])  dig0 |= 0x04;  // SEG_C = LED3 PZB 70
  if (ledStates[3])  dig0 |= 0x08;  // SEG_D = LED4 PZB 85
  if (ledStates[4])  dig0 |= 0x10;  // SEG_E = LED5 PZB 55
  if (ledStates[5])  dig0 |= 0x20;  // SEG_F = LED6 500Hz
  if (ledStates[6])  dig0 |= 0x40;  // SEG_G = LED7 1000Hz
  if (ledStates[7])  dig0 |= 0x80;  // SEG_DP = LED8 Porte SX

  // DIG1: LED9(A) LED10(B) LED11(C) LED12(D) LED13(E)
  byte dig1 = 0;
  if (ledStates[8])  dig1 |= 0x01;  // SEG_A = LED9 Porte DX
  if (ledStates[9])  dig1 |= 0x02;  // SEG_B = LED10 LZB Ü
  if (ledStates[10]) dig1 |= 0x04;  // SEG_C = LED11 LZB G
  if (ledStates[11]) dig1 |= 0x08;  // SEG_D = LED12 LZB S
  if (ledStates[12]) dig1 |= 0x10;  // SEG_E = LED13 Befehl 40

  max7219_send(REG_DIGIT0, dig0);
  max7219_send(REG_DIGIT1, dig1);
}

// ============== SETUP ==============

void setup() {
  // Serial per comandi LED
  Serial.begin(SERIAL_BAUD);

  // MAX7219 init
  max7219_init();

  // Encoder (solo CLK e DT, SW è nella matrice)
  myEncoder.write(512 / ENCODER_MULTIPLIER);

  // Matrice 5x6
  for (int r = 0; r < MATRIX_ROWS; r++) {
    pinMode(ROW_PINS[r], OUTPUT);
    digitalWrite(ROW_PINS[r], HIGH);
  }
  for (int c = 0; c < MATRIX_COLS; c++) {
    pinMode(COL_PINS[c], INPUT_PULLUP);
  }

  // Inizializza stati
  for (int i = 0; i < BUTTON_COUNT; i++) {
    buttonStates[i] = false;
    lastButtonStates[i] = false;
    lastDebounceTime[i] = 0;
  }

  // Inizializza storia potenziometri
  for (int i = 0; i < 3; i++) {
    for (int j = 0; j < SMOOTHING_SAMPLES; j++) {
      potHistory[i][j] = 512;
    }
  }

  // Joystick
  Joystick.begin(false);
  Joystick.setXAxisRange(0, 1023);
  Joystick.setYAxisRange(0, 1023);
  Joystick.setZAxisRange(0, 1023);
  Joystick.setRxAxisRange(0, 1023);

  // Test LED all'avvio (tutti in sequenza)
  for (int i = 0; i < NUM_LEDS; i++) {
    ledStates[i] = true;
    max7219_update();
    delay(150);
    ledStates[i] = false;
    max7219_update();
  }

  Serial.println("OK:Joystick+LED Ready (13 LED MAX7219 Leonardo)");
}

// ============== LOOP ==============

void loop() {
  // === JOYSTICK ===
  bool stateChanged = false;
  stateChanged |= readPotentiometers();
  stateChanged |= scanMatrix();
  stateChanged |= updateEncoderAxis();

  if (stateChanged) {
    Joystick.sendState();
  }

  // === SERIAL COMMANDS ===
  processSerial();

  delayMicroseconds(500);
}

// ============== SERIAL COMMANDS ==============

void processSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (bufferIndex > 0) {
        inputBuffer[bufferIndex] = '\0';
        processCommand(inputBuffer);
        bufferIndex = 0;
      }
    } else if (bufferIndex < BUFFER_SIZE - 1) {
      inputBuffer[bufferIndex++] = c;
    }
  }
}

void processCommand(char* cmd) {
  // LED:n:stato (n=1-13, stato=0/1)
  if (strncmp(cmd, "LED:", 4) == 0) {
    char* colonPos = strchr(cmd + 4, ':');
    if (colonPos) {
      int ledNum = atoi(cmd + 4);
      int state = atoi(colonPos + 1);
      if (ledNum >= 1 && ledNum <= NUM_LEDS) {
        setLed(ledNum - 1, state == 1);
      }
    }
  }
  else if (strncmp(cmd, "SIFA:", 5) == 0)      { setLed(0, atoi(cmd + 5) == 1); }
  else if (strncmp(cmd, "LZB:", 4) == 0)       { setLed(1, atoi(cmd + 4) == 1); }
  else if (strncmp(cmd, "PZB70:", 6) == 0)     { setLed(2, atoi(cmd + 6) == 1); }
  else if (strncmp(cmd, "PZB80:", 6) == 0)     { setLed(3, atoi(cmd + 6) == 1); }
  else if (strncmp(cmd, "PZB50:", 6) == 0)     { setLed(4, atoi(cmd + 6) == 1); }
  else if (strncmp(cmd, "500HZ:", 6) == 0)     { setLed(5, atoi(cmd + 6) == 1); }
  else if (strncmp(cmd, "1000HZ:", 7) == 0)    { setLed(6, atoi(cmd + 7) == 1); }
  else if (strncmp(cmd, "TUEREN_L:", 9) == 0)  { setLed(7, atoi(cmd + 9) == 1); }
  else if (strncmp(cmd, "TUEREN_R:", 9) == 0)  { setLed(8, atoi(cmd + 9) == 1); }
  else if (strncmp(cmd, "LZB_UE:", 7) == 0)    { setLed(9, atoi(cmd + 7) == 1); }
  else if (strncmp(cmd, "LZB_G:", 6) == 0)     { setLed(10, atoi(cmd + 6) == 1); }
  else if (strncmp(cmd, "LZB_S:", 6) == 0)     { setLed(11, atoi(cmd + 6) == 1); }
  else if (strncmp(cmd, "BEF40:", 6) == 0)     { setLed(12, atoi(cmd + 6) == 1); }
  else if (strcmp(cmd, "OFF") == 0) {
    for (int i = 0; i < NUM_LEDS; i++) {
      ledStates[i] = false;
    }
    max7219_update();
  }
}

void setLed(int index, bool state) {
  if (index >= 0 && index < NUM_LEDS) {
    ledStates[index] = state;
    max7219_update();
  }
}

// ============== JOYSTICK FUNCTIONS ==============

bool readPotentiometers() {
  bool changed = false;
  const int PINS[3] = {POT_X, POT_Y, POT_Z};

  for (int i = 0; i < 3; i++) {
    int raw = analogRead(PINS[i]);
    potHistory[i][potHistoryIndex[i]] = raw;
    potHistoryIndex[i] = (potHistoryIndex[i] + 1) % SMOOTHING_SAMPLES;

    long sum = 0;
    for (int j = 0; j < SMOOTHING_SAMPLES; j++) {
      sum += potHistory[i][j];
    }
    int smoothed = sum / SMOOTHING_SAMPLES;

    if (abs(smoothed - lastPotValues[i]) > POT_DEADZONE) {
      lastPotValues[i] = smoothed;
      switch (i) {
        case 0: Joystick.setXAxis(smoothed); break;
        case 1: Joystick.setYAxis(smoothed); break;
        case 2: Joystick.setZAxis(smoothed); break;
      }
      changed = true;
    }
  }
  return changed;
}

bool scanMatrix() {
  bool changed = false;

  for (int r = 0; r < MATRIX_ROWS; r++) {
    digitalWrite(ROW_PINS[r], LOW);
    delayMicroseconds(10);

    for (int c = 0; c < MATRIX_COLS; c++) {
      int btnIndex = MATRIX_MAP[r][c];
      if (btnIndex < 0) continue;

      bool reading = (digitalRead(COL_PINS[c]) == LOW);

      if (reading != lastButtonStates[btnIndex]) {
        lastDebounceTime[btnIndex] = millis();
      }

      if ((millis() - lastDebounceTime[btnIndex]) > DEBOUNCE_DELAY) {
        if (reading != buttonStates[btnIndex]) {
          buttonStates[btnIndex] = reading;
          Joystick.setButton(btnIndex, reading);
          changed = true;
        }
      }
      lastButtonStates[btnIndex] = reading;
    }
    digitalWrite(ROW_PINS[r], HIGH);
  }
  return changed;
}

bool updateEncoderAxis() {
  long newPos = myEncoder.read();

  if (newPos != lastEncoderPosition) {
    lastEncoderPosition = newPos;

    int axisValue = newPos * ENCODER_MULTIPLIER;
    axisValue = constrain(axisValue, ENCODER_MIN, ENCODER_MAX);

    if (axisValue <= ENCODER_MIN) {
      myEncoder.write(ENCODER_MIN / ENCODER_MULTIPLIER);
    } else if (axisValue >= ENCODER_MAX) {
      myEncoder.write(ENCODER_MAX / ENCODER_MULTIPLIER);
    }

    Joystick.setRxAxis(axisValue);
    return true;
  }
  return false;
}
