@echo off
REM ============================================================
REM Build TSW6 Arduino Bridge v2.0
REM Compila l'applicazione Python in un EXE standalone
REM
REM Lo sketch Arduino è nel progetto separato arduino-train
REM (Arduino Leonardo con 12 LED Charlieplexing)
REM ============================================================

echo.
echo ========================================
echo  TSW6 Arduino Bridge - Build
echo ========================================
echo.

REM Verifica Python
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Python non trovato!
    echo Installa Python da https://www.python.org/
    pause
    exit /b 1
)

REM Installa dipendenze
echo [1/2] Installazione dipendenze Python...
pip install -r requirements.txt

REM Build EXE
echo.
echo [2/2] Compilazione GUI (EXE)...
pyinstaller --onefile --windowed ^
    --name "TSW6_Arduino_Bridge" ^
    tsw6_arduino_gui.py

REM Crea pacchetto finale
set DIST_DIR=dist\TSW6_Arduino_Bridge_v2.0
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

REM Copia EXE
if exist "dist\TSW6_Arduino_Bridge.exe" copy "dist\TSW6_Arduino_Bridge.exe" "%DIST_DIR%\"

REM Crea README
(
echo # TSW6 Arduino Bridge v2.0
echo.
echo ## Descrizione
echo Collega Train Sim World 6 ad Arduino Leonardo per controllare
echo 12 LED fisici ^(Charlieplexing^) basati sui dati del treno in tempo reale.
echo.
echo ## Requisiti
echo - Train Sim World 6 con parametro -HTTPAPI abilitato
echo - Arduino Leonardo con lo sketch ArduinoJoystick.ino caricato
echo - Cavo USB per Arduino
echo.
echo ## LED Disponibili ^(Charlieplexing su 4 pin^)
echo  1. SIFA Warning ^(giallo^)
echo  2. LZB Ende ^(giallo^)
echo  3. PZB 70 ^(blu^)
echo  4. PZB 80 ^(blu^)
echo  5. PZB 50 ^(blu^)
echo  6. 500 Hz ^(rosso^)
echo  7. 1000 Hz ^(giallo^)
echo  8. Porte Sinistra ^(giallo^)
echo  9. Porte Destra ^(giallo^)
echo 10. LZB U ^(blu^)
echo 11. LZB G aktiv ^(blu^)
echo 12. LZB S ^(rosso^)
echo.
echo ## Setup TSW6
echo 1. In Steam: tasto destro su TSW6 ^> Proprieta ^> Opzioni di avvio
echo 2. Aggiungere: -HTTPAPI
echo 3. Avviare il gioco una volta e uscire ^(genera la CommAPIKey^)
echo.
echo ## Setup Arduino
echo Lo sketch Arduino e nel progetto separato arduino-train.
echo 1. Aprire ArduinoJoystick/ArduinoJoystick.ino nell'IDE Arduino
echo 2. Selezionare la board "Arduino Leonardo"
echo 3. Caricare lo sketch ^(NON modificare^)
echo.
echo ## Uso
echo 1. Avviare TSW6 con -HTTPAPI
echo 2. Collegare Arduino via USB
echo 3. Avviare TSW6_Arduino_Bridge.exe
echo 4. Tab Connessione: connettere TSW6 e Arduino
echo 5. Tab Mappature: configurare quali dati controllano quali LED
echo 6. Premere "Avvia Bridge"
) > "%DIST_DIR%\README.txt"

echo.
echo ========================================
echo  BUILD COMPLETATA!
echo ========================================
echo.
echo Pacchetto creato in: %DIST_DIR%
echo.
dir "%DIST_DIR%"
echo.

pause
