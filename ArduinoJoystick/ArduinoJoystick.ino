/*
 * Arduino Leonardo Joystick + Zusi3 LED Controller (Charlieplexing)
 * 
 * Combina:
 * - Joystick USB HID (potenziometri, encoder, matrice pulsanti 5x6)
 * - Serial CDC per ricevere comandi LED da Zusi3 Bridge
 * - 12 LED con Charlieplexing (4 pin)
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
 * - 12 LED Charlieplexing (pin A3, 0, 1, A4)
 * 
 * LED Charlieplexing (4 pin = 12 possibili, usiamo 12):
 * - LED1:  SIFA Warning (giallo)         - A3→0
 * - LED2:  LZB Ende (giallo)             - 0→A3
 * - LED3:  PZB 70 (blu)                  - A3→1
 * - LED4:  PZB 80 (blu)                  - 1→A3
 * - LED5:  PZB 50 (blu)                  - 0→1
 * - LED6:  500Hz (rosso)                 - 1→0
 * - LED7:  1000Hz (giallo)               - A3→A4
 * - LED8:  Porte SX (giallo)             - A4→A3
 * - LED9:  Porte DX (giallo)             - 0→A4
 * - LED10: LZB Ü Übertragung (blu)       - 1→A4
 * - LED11: LZB G aktiv (rosso)            - A4→0
 * - LED12: LZB S Schnellbremsung (rosso) - A4→1
 * 
 * Protocollo seriale (115200 baud):
 * - LED:n:stato  (n=1-12, stato=0/1)
 * - SIFA:stato   (alias LED1)
 * - LZB:stato    (alias LED2)
 * - LZB_UE:stato (alias LED10)
 * - LZB_G:stato  (alias LED11)
 * - LZB_S:stato  (alias LED12)
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

// LED Charlieplexing (4 pin = 12 possibili, usiamo 12)
#define LED_PIN_A A3  // Pin A
#define LED_PIN_B 0   // Pin B (RX)
#define LED_PIN_C 1   // Pin C (TX)
#define LED_PIN_D A4  // Pin D

// Encoder rotativo (CLK e DT con interrupt)
#define ENCODER_CLK 2
#define ENCODER_DT  3
// ENCODER_SW è nella matrice (ROW0, COL5)

// ============== MATRICE 5x6 ==============
#define MATRIX_ROWS 5
#define MATRIX_COLS 6

const int ROW_PINS[MATRIX_ROWS] = {5, 6, 7, 8, 9};
const int COL_PINS[MATRIX_COLS] = {10, 11, 12, 13, 4, A5};  // 6 colonne per Leonardo

// Layout matrice 5x6 (30 posizioni, usiamo 28):
// 8 switch ON-OFF-ON (SW1-SW8): 16 posizioni
// TOGGLE1 self-lock: 2 posizioni
// TOGGLE2 self-lock: 2 posizioni
// ROT4 (4 pos): 4 posizioni
// ROT3 (2 pos attive): 2 posizioni
// BTN1/PEDALE (parallelo): 1 posizione
// ENC_SW: 1 posizione
// Totale: 28 posizioni (2 vuoti)

const int MATRIX_MAP[MATRIX_ROWS][MATRIX_COLS] = {
  {17, 18, 19, 20, 21, 16},  // BTN1/PEDALE, ROT4_1, ROT4_2, ROT4_3, ROT4_4, ENC_SW
  {0,  2,  4,  6,  8,  22},  // SW1_UP, SW2_UP, SW3_UP, SW4_UP, SW5_UP, TOG1_UP
  {1,  3,  5,  7,  9,  23},  // SW1_DN, SW2_DN, SW3_DN, SW4_DN, SW5_DN, TOG1_DN
  {10, 12, 14, 24, 25, 26},  // SW6_UP, SW7_UP, SW8_UP, ROT3_1, ROT3_2, TOG2_UP
  {11, 13, 15, -1, -1, 27}   // SW6_DN, SW7_DN, SW8_DN, (vuoto), (vuoto), TOG2_DN
};

// ============== JOYSTICK ==============
#define BUTTON_COUNT 28  // 28 pulsanti totali nella matrice 5x6
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

// ============== LED CHARLIEPLEXING ==============
// 12 LED con 4 pin (A, B, C, D)
// LED1:  A→B (A3→0)   SIFA
// LED2:  B→A (0→A3)   LZB Ende
// LED3:  A→C (A3→1)   PZB70
// LED4:  C→A (1→A3)   PZB80
// LED5:  B→C (0→1)    PZB50
// LED6:  C→B (1→0)    500Hz
// LED7:  A→D (A3→A4)  1000Hz
// LED8:  D→A (A4→A3)  Porte SX
// LED9:  B→D (0→A4)   Porte DX
// LED10: C→D (1→A4)   LZB Ü
// LED11: D→B (A4→0)   LZB G
// LED12: D→C (A4→1)   LZB S

#define NUM_LEDS 12
bool ledStates[NUM_LEDS] = {false, false, false, false, false, false, false, false, false, false, false, false};
int currentLedIndex = 0;
unsigned long lastLedUpdate = 0;
const unsigned long LED_MULTIPLEX_DELAY = 2;  // 2ms per LED = ~62Hz refresh

// ============== SETUP ==============

void setup() {
  // Serial per comandi Zusi3
  Serial.begin(SERIAL_BAUD);
  
  // LED Charlieplexing - tutti i pin in Hi-Z (spenti)
  allLedsOff();
  
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
    lightLed(i);
    delay(150);
    ledStates[i] = false;
    allLedsOff();
  }
  
  Serial.println("OK:Joystick+Zusi Ready (12 LED Charlieplex Leonardo)");
}

// ============== LOOP ==============

void loop() {
  // === JOYSTICK ===
  bool stateChanged = false;
  stateChanged |= readPotentiometers();
  stateChanged |= scanMatrix();  // Include ENC_SW ora
  stateChanged |= updateEncoderAxis();
  
  if (stateChanged) {
    Joystick.sendState();
  }
  
  // === LED CHARLIEPLEXING ===
  updateLedMultiplex();
  
  // === SERIAL ZUSI3 ===
  processSerial();
  
  delayMicroseconds(500);  // Ridotto per LED multiplexing
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
  // LED:n:stato (n=1-12, stato=0/1)
  if (strncmp(cmd, "LED:", 4) == 0) {
    // Trova il ':' dopo il numero
    char* colonPos = strchr(cmd + 4, ':');
    if (colonPos) {
      int ledNum = atoi(cmd + 4);
      int state = atoi(colonPos + 1);
      if (ledNum >= 1 && ledNum <= NUM_LEDS) {
        setLed(ledNum - 1, state == 1);
      }
    }
  }
  // SIFA:stato (alias LED1)
  else if (strncmp(cmd, "SIFA:", 5) == 0) {
    int state = atoi(cmd + 5);
    setLed(0, state == 1);  // LED1 = SIFA
  }
  // LZB:stato (alias LED2)
  else if (strncmp(cmd, "LZB:", 4) == 0) {
    int state = atoi(cmd + 4);
    setLed(1, state == 1);  // LED2 = LZB
  }
  // PZB70:stato (alias LED3)
  else if (strncmp(cmd, "PZB70:", 6) == 0) {
    int state = atoi(cmd + 6);
    setLed(2, state == 1);  // LED3 = PZB 70
  }
  // PZB80:stato (alias LED4)
  else if (strncmp(cmd, "PZB80:", 6) == 0) {
    int state = atoi(cmd + 6);
    setLed(3, state == 1);  // LED4 = PZB 80
  }
  // PZB50:stato (alias LED5)
  else if (strncmp(cmd, "PZB50:", 6) == 0) {
    int state = atoi(cmd + 6);
    setLed(4, state == 1);  // LED5 = PZB 50
  }
  // 500HZ:stato (alias LED6)
  else if (strncmp(cmd, "500HZ:", 6) == 0) {
    int state = atoi(cmd + 6);
    setLed(5, state == 1);  // LED6 = 500Hz
  }
  // 1000HZ:stato (alias LED7)
  else if (strncmp(cmd, "1000HZ:", 7) == 0) {
    int state = atoi(cmd + 7);
    setLed(6, state == 1);  // LED7 = 1000Hz
  }
  // TUEREN_L:stato (alias LED8 - Porte Sinistra)
  else if (strncmp(cmd, "TUEREN_L:", 9) == 0) {
    int state = atoi(cmd + 9);
    setLed(7, state == 1);  // LED8 = Porte SX
  }
  // TUEREN_R:stato (alias LED9 - Porte Destra)
  else if (strncmp(cmd, "TUEREN_R:", 9) == 0) {
    int state = atoi(cmd + 9);
    setLed(8, state == 1);  // LED9 = Porte DX
  }
  // LZB_UE:stato (alias LED10 - LZB Ü Übertragung)
  else if (strncmp(cmd, "LZB_UE:", 7) == 0) {
    int state = atoi(cmd + 7);
    setLed(9, state == 1);  // LED10 = LZB Ü
  }
  // LZB_G:stato (alias LED11 - LZB G aktiv)
  else if (strncmp(cmd, "LZB_G:", 6) == 0) {
    int state = atoi(cmd + 6);
    setLed(10, state == 1);  // LED11 = LZB G
  }
  // LZB_S:stato (alias LED12 - LZB S Schnellbremsung)
  else if (strncmp(cmd, "LZB_S:", 6) == 0) {
    int state = atoi(cmd + 6);
    setLed(11, state == 1);  // LED12 = LZB S
  }
  // OFF - spegni tutto
  else if (strcmp(cmd, "OFF") == 0) {
    for (int i = 0; i < NUM_LEDS; i++) {
      ledStates[i] = false;
    }
    allLedsOff();
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

// ============== LED CHARLIEPLEXING ==============

void allLedsOff() {
  // Tutti i 4 pin in Hi-Z (input senza pullup)
  pinMode(LED_PIN_A, INPUT);
  pinMode(LED_PIN_B, INPUT);
  pinMode(LED_PIN_C, INPUT);
  pinMode(LED_PIN_D, INPUT);
}

void setLed(int index, bool state) {
  if (index >= 0 && index < NUM_LEDS) {
    ledStates[index] = state;
  }
}


void updateLedMultiplex() {
  // Multiplexing: accende un LED alla volta, molto velocemente
  if (millis() - lastLedUpdate < LED_MULTIPLEX_DELAY) return;
  lastLedUpdate = millis();
  
  // Spegni tutti prima
  allLedsOff();
  
  // Trova prossimo LED acceso
  for (int i = 0; i < NUM_LEDS; i++) {
    currentLedIndex = (currentLedIndex + 1) % NUM_LEDS;
    if (ledStates[currentLedIndex]) {
      lightLed(currentLedIndex);
      return;
    }
  }
}

void lightLed(int index) {
  // Charlieplexing 4 pin: imposta direzione corrente
  // LED1:  A→B   LED2:  B→A   LED3:  A→C   LED4:  C→A
  // LED5:  B→C   LED6:  C→B   LED7:  A→D   LED8:  D→A
  // LED9:  B→D   LED10: C→D   LED11: D→B   LED12: D→C
  
  int pinHigh, pinLow;
  
  switch (index) {
    case 0:  pinHigh = LED_PIN_A; pinLow = LED_PIN_B; break;  // SIFA
    case 1:  pinHigh = LED_PIN_B; pinLow = LED_PIN_A; break;  // LZB Ende
    case 2:  pinHigh = LED_PIN_A; pinLow = LED_PIN_C; break;  // PZB70
    case 3:  pinHigh = LED_PIN_C; pinLow = LED_PIN_A; break;  // PZB80
    case 4:  pinHigh = LED_PIN_B; pinLow = LED_PIN_C; break;  // PZB50
    case 5:  pinHigh = LED_PIN_C; pinLow = LED_PIN_B; break;  // 500Hz
    case 6:  pinHigh = LED_PIN_A; pinLow = LED_PIN_D; break;  // 1000Hz
    case 7:  pinHigh = LED_PIN_D; pinLow = LED_PIN_A; break;  // Porte SX
    case 8:  pinHigh = LED_PIN_B; pinLow = LED_PIN_D; break;  // Porte DX
    case 9:  pinHigh = LED_PIN_C; pinLow = LED_PIN_D; break;  // LZB Ü
    case 10: pinHigh = LED_PIN_D; pinLow = LED_PIN_B; break;  // LZB G
    case 11: pinHigh = LED_PIN_D; pinLow = LED_PIN_C; break;  // LZB S
    default: return;
  }
  
  // Imposta i due pin attivi, gli altri in Hi-Z
  pinMode(pinHigh, OUTPUT);
  pinMode(pinLow, OUTPUT);
  digitalWrite(pinHigh, HIGH);
  digitalWrite(pinLow, LOW);
}
