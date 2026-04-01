/*
 * Arduino Leonardo — Serial LED Controller (MAX7219)
 * 
 * Versione SEMPLIFICATA: solo comandi seriali per i 13 LED.
 * Niente joystick, niente encoder, niente matrice pulsanti.
 * Usa solo 3 pin + USB per controllare 13 LED via MAX7219.
 * 
 * Ideale per chi vuole SOLO il pannello MFA con LED fisici,
 * senza il controller joystick completo.
 * 
 * Componenti necessari:
 * - 1x Arduino Leonardo (ATmega32U4)
 * - 1x Modulo MAX7219 (WCMCU DISY1 o simile)
 * - 13x LED 5mm (1 bianco/giallo, 5 giallo, 4 blu, 3 rosso)
 * - Cavetti, breadboard o PCB
 * - Nessun resistore individuale (RSET già sul modulo)
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
 * - BEF40:stato  (alias LED13)
 * - OFF          (spegni tutto)
 * 
 * Compatibile al 100% con Train Simulator Bridge (stesso protocollo).
 */

// ============== PIN MAX7219 ==============
#define MAX_DIN  A3  // Data In
#define MAX_CLK  A4  // Clock
#define MAX_CS   A5  // Chip Select (LOAD)

// ============== SERIAL ==============
#define SERIAL_BAUD 115200
#define BUFFER_SIZE 32
char inputBuffer[BUFFER_SIZE];
int bufferIndex = 0;

// ============== LED MAX7219 ==============
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
  Serial.begin(SERIAL_BAUD);

  // MAX7219 init
  max7219_init();

  // Test LED all'avvio (sequenza)
  for (int i = 0; i < NUM_LEDS; i++) {
    ledStates[i] = true;
    max7219_update();
    delay(150);
    ledStates[i] = false;
    max7219_update();
  }

  Serial.println("OK:SerialOnly Ready (13 LED MAX7219 Leonardo)");
}

// ============== LOOP ==============

void loop() {
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
