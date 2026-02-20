#include "FS.h"
#include "SD.h"
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_BMP280.h>
#include <RTClib.h>
#include "esp_sleep.h"

// ---------- SD ----------
#define SD_CS 5

// ---------- LED ----------
#define LED_PIN 25

// ---------- Sensores ----------
Adafruit_AHTX0 aht;
Adafruit_BMP280 bmp;
RTC_DS3231 rtc;

// ---------- DEEP SLEEP ----------
RTC_DATA_ATTR int readingID = 0;

// 30 minutos = 1800 segundos
const uint64_t TIME_TO_SLEEP = 1800;

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println("Iniciando sistema...");

  // LED
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // I2C
  Wire.begin(21, 22);

  // BMP280
  if (!bmp.begin(0x77)) {
    Serial.println("ERROR: No se encuentra BMP280");
    while (1);
  }

  // AHT20
  if (!aht.begin()) {
    Serial.println("ERROR: No se encuentra AHT20");
    while (1);
  }

  // RTC
  if (!rtc.begin()) {
    Serial.println("ERROR: No se encuentra DS3231");
    while (1);
  }

  // SD
  if (!SD.begin(SD_CS)) {
    Serial.println("ERROR: SD mount failed");
    while (1);
  }

  // Crear archivo si no existe
  if (!SD.exists("/clim28033.txt")) {
    writeFile(SD, "/clim28033.txt",
      "Date,Time,Temperature_AHT20,Humidity_AHT20,Pressure_BMP280\r\n");
  }

  // Guardar lectura
  logSDCard();

  readingID++;

  Serial.println("Entrando en deep sleep...");
  Serial.flush();

  esp_sleep_enable_timer_wakeup(TIME_TO_SLEEP * 1000000ULL);
  delay(300);
  esp_deep_sleep_start();
}

void loop() {
}

// ---------------- FUNCIONES ----------------

void logSDCard() {

  sensors_event_t humidityEvent, tempEvent;
  aht.getEvent(&humidityEvent, &tempEvent);

  float temperatureAHT = tempEvent.temperature;
  float humidityAHT = humidityEvent.relative_humidity;
  float pressureBMP = bmp.readPressure() / 100.0F;

  DateTime now = rtc.now();

  String dateStr = String(now.year()) + "-" +
                   String(now.month()) + "-" +
                   String(now.day());

  String timeStr = String(now.hour()) + ":" +
                   String(now.minute()) + ":" +
                   String(now.second());

  String dataMessage = dateStr + "," +
                       timeStr + "," +
                       String(temperatureAHT, 2) + "," +
                       String(humidityAHT, 2) + "," +
                       String(pressureBMP, 2) + "\r\n";

  Serial.print("Guardando: ");
  Serial.println(dataMessage);

  appendFile(SD, "/clim28033.txt", dataMessage.c_str());

  // Encender LED 5 segundos
  digitalWrite(LED_PIN, HIGH);
  delay(5000);
  digitalWrite(LED_PIN, LOW);
}

void writeFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_WRITE);
  if (!file) {
    Serial.println("ERROR: writeFile failed");
    return;
  }
  file.print(message);
  file.close();
}

void appendFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_APPEND);
  if (!file) {
    Serial.println("ERROR: appendFile failed");
    return;
  }
  file.print(message);
  file.close();
}