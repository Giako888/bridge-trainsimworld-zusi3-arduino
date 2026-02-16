/*
 * Arduino Leonardo — Serial LED Controller (Charlieplexing)
 * 
 * Versione SEMPLIFICATA: solo comandi seriali per i 12 LED.
 * Niente joystick, niente encoder, niente matrice pulsanti.
 * Usa solo 4 pin + USB per controllare 12 LED in Charlieplexing.
 * 
 * Ideale per chi vuole SOLO il pannello MFA con LED fisici,
 * senza il controller joystick completo.
 * 
 * Componenti necessari:
 * - 1x Arduino Leonardo (ATmega32U4)
 * - 12x LED 5mm (1 bianco/giallo, 4 giallo, 4 blu, 3 rosso)
 * - 12x Resistore 220Ω
 * - Cavetti, breadboard o PCB
 * 
 * LED Charlieplexing (4 pin = 12 LED):
 * - LED1:  SIFA Warning (giallo)         - A3→0
 * - LED2:  LZB Ende (giallo)             - 0→A3
 * - LED3:  PZB 70 (blu)                  - A3→1
 * - LED4:  PZB 85 (blu)                  - 1→A3
 * - LED5:  PZB 55 (blu)                  - 0→1
 * - LED6:  500Hz (rosso)                 - 1→0
 * - LED7:  1000Hz (giallo)               - A3→A4
 * - LED8:  Porte SX (giallo)             - A4→A3
 * - LED9:  Porte DX (giallo)             - 0→A4
 * - LED10: LZB Ü Übertragung (blu)       - 1→A4
 * - LED11: LZB G aktiv (rosso)           - A4→0
 * - LED12: LZB S Schnellbremsung (rosso) - A4→1
 * 
 * Protocollo seriale (115200 baud):
 * - LED:n:stato  (n=1-12, stato=0/1)
 * - SIFA:stato   (alias LED1)
 * - LZB:stato    (alias LED2)
 * - PZB70:stato  (alias LED3)
 * - PZB80:stato  (alias LED4)
 * - PZB50:stato  (alias LED5)
 * - 500HZ:stato  (alias LED6)
 * - 1000HZ:stato (alias LED7)
 * - TUEREN_L:stato (alias LED8)
 * - TUEREN_R:stato (alias LED9)
 * - LZB_UE:stato (alias LED10)
 * - LZB_G:stato  (alias LED11)
 * - LZB_S:stato  (alias LED12)
 * - OFF          (spegni tutto)
 * 
 * Compatibile al 100% con Train Simulator Bridge (stesso protocollo).
 */

// ============== PIN LED CHARLIEPLEXING ==============
#define LED_PIN_A A3  // Pin A
#define LED_PIN_B 0   // Pin B (RX — OK, Serial è su USB!)
#define LED_PIN_C 1   // Pin C (TX — OK, Serial è su USB!)
#define LED_PIN_D A4  // Pin D

// ============== SERIAL ==============
#define SERIAL_BAUD 115200
#define BUFFER_SIZE 32
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// ============== LED CHARLIEPLEXING ==============
// 12 LED con 4 pin (A, B, C, D)
// LED1:  A→B (A3→0)   SIFA
// LED2:  B→A (0→A3)   LZB Ende
// LED3:  A→C (A3→1)   PZB70
// LED4:  C→A (1→A3)   PZB85
// LED5:  B→C (0→1)    PZB55
// LED6:  C→B (1→0)    500Hz
// LED7:  A→D (A3→A4)  1000Hz
// LED8:  D→A (A4→A3)  Porte SX
// LED9:  B→D (0→A4)   Porte DX
// LED10: C→D (1→A4)   LZB Ü
// LED11: D→B (A4→0)   LZB G
// LED12: D→C (A4→1)   LZB S

#define NUM_LEDS 12
bool ledStates[NUM_LEDS] = {false};
int currentLedIndex = 0;
unsigned long lastLedUpdate = 0;
const unsigned long LED_MULTIPLEX_DELAY = 2;  // 2ms per LED = ~62Hz refresh

// ============== SETUP ==============

void setup() {
  Serial.begin(SERIAL_BAUD);
  
  // LED Charlieplexing — tutti i pin in Hi-Z (spenti)
  allLedsOff();
  
  // Test LED all'avvio (sequenza)
  for (int i = 0; i < NUM_LEDS; i++) {
    ledStates[i] = true;
    lightLed(i);
    delay(150);
    ledStates[i] = false;
    allLedsOff();
  }
  
  Serial.println("OK:SerialOnly Ready (12 LED Charlieplex Leonardo)");
}

// ============== LOOP ==============

void loop() {
  // LED Charlieplexing multiplexing
  updateLedMultiplex();
  
  // Comandi seriali
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
  // LED:n:stato (n=1-12, stato=0/1)
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
  // SIFA:stato (alias LED1)
  else if (strncmp(cmd, "SIFA:", 5) == 0) {
    setLed(0, atoi(cmd + 5) == 1);
  }
  // LZB:stato (alias LED2)
  else if (strncmp(cmd, "LZB:", 4) == 0) {
    setLed(1, atoi(cmd + 4) == 1);
  }
  // PZB70:stato (alias LED3)
  else if (strncmp(cmd, "PZB70:", 6) == 0) {
    setLed(2, atoi(cmd + 6) == 1);
  }
  // PZB80:stato (alias LED4)
  else if (strncmp(cmd, "PZB80:", 6) == 0) {
    setLed(3, atoi(cmd + 6) == 1);
  }
  // PZB50:stato (alias LED5)
  else if (strncmp(cmd, "PZB50:", 6) == 0) {
    setLed(4, atoi(cmd + 6) == 1);
  }
  // 500HZ:stato (alias LED6)
  else if (strncmp(cmd, "500HZ:", 6) == 0) {
    setLed(5, atoi(cmd + 6) == 1);
  }
  // 1000HZ:stato (alias LED7)
  else if (strncmp(cmd, "1000HZ:", 7) == 0) {
    setLed(6, atoi(cmd + 7) == 1);
  }
  // TUEREN_L:stato (alias LED8 - Porte Sinistra)
  else if (strncmp(cmd, "TUEREN_L:", 9) == 0) {
    setLed(7, atoi(cmd + 9) == 1);
  }
  // TUEREN_R:stato (alias LED9 - Porte Destra)
  else if (strncmp(cmd, "TUEREN_R:", 9) == 0) {
    setLed(8, atoi(cmd + 9) == 1);
  }
  // LZB_UE:stato (alias LED10 - LZB Ü Übertragung)
  else if (strncmp(cmd, "LZB_UE:", 7) == 0) {
    setLed(9, atoi(cmd + 7) == 1);
  }
  // LZB_G:stato (alias LED11 - LZB G aktiv)
  else if (strncmp(cmd, "LZB_G:", 6) == 0) {
    setLed(10, atoi(cmd + 6) == 1);
  }
  // LZB_S:stato (alias LED12 - LZB S Schnellbremsung)
  else if (strncmp(cmd, "LZB_S:", 6) == 0) {
    setLed(11, atoi(cmd + 6) == 1);
  }
  // OFF - spegni tutto
  else if (strcmp(cmd, "OFF") == 0) {
    for (int i = 0; i < NUM_LEDS; i++) {
      ledStates[i] = false;
    }
    allLedsOff();
  }
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
    case 3:  pinHigh = LED_PIN_C; pinLow = LED_PIN_A; break;  // PZB85
    case 4:  pinHigh = LED_PIN_B; pinLow = LED_PIN_C; break;  // PZB55
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
