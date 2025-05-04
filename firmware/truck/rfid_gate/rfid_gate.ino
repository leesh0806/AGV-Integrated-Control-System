#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

#define SS_PIN 21    // SDA
#define RST_PIN 22   // RST

MFRC522 rfid(SS_PIN, RST_PIN);

// ==== WiFi 설정 ====
const char* ssid = "olleh_WiFi_ECDF";
const char* password = "0000000567";

// ✅ PC 서버 주소 및 포트
IPAddress serverIP(172, 30, 1, 11);  // ← PC IP로 바꾸세요
const int serverPort = 8001;  // 8000에서 8001로 변경

WiFiClient client;
String incoming_msg = "";

// 등록된 UID 목록
struct UIDEntry {
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  { {0x86, 0x51, 0x0A, 0x05}, "게이트 A" },
  { {0x12, 0x6D, 0x07, 0x05}, "게이트 B" }
};

const int numRegistered = sizeof(registeredCards) / sizeof(registeredCards[0]);

// 트럭 ID 설정
const char* truck_id = "TRUCK_01";  // 설정 가능하도록 변경

void setup() {
  Serial.begin(115200);

  // ✅ WiFi 연결
  WiFi.begin(ssid, password);
  Serial.println("📶 WiFi 연결 중...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi 연결 완료!");

  // ✅ 서버 접속 시도
  reconnectToServer();

  // ✅ RFID 초기화
  SPI.begin(18, 19, 23, 21);  // SCK, MISO, MOSI, SS
  rfid.PCD_Init();
  Serial.println("📡 RC522 RFID 리더기 시작됨!");

  // ✅ 시간 동기화
  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("⏳ 시간 동기화 대기 중...");
  while (time(nullptr) < 100000) {
    delay(100);
    Serial.println("...");
  }
  Serial.println("✅ 시간 동기화 완료!");

  // ✅ 미션 요청 자동 전송
  delay(2000);  // 안정화 대기
  send_assign_mission();
}

void loop() {
  // TCP 서버 접속 확인
  reconnectToServer();

  // RFID 체크
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  Serial.print("UID: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
    Serial.print(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) Serial.print("-");
  }
  Serial.println();

  // UID 확인 및 서버 전송
  checkAndPrintUID(rfid.uid.uidByte);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

// ✅ UID 비교
bool isSameUID(byte *uid1, byte *uid2) {
  for (byte i = 0; i < 4; i++) {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

// ✅ UID 확인 후 메시지 전송
void checkAndPrintUID(byte* uid) {
  for (int i = 0; i < numRegistered; i++) {
    if (isSameUID(uid, registeredCards[i].uid)) {
      const char* desc = registeredCards[i].description;

      Serial.println("✅ 등록된 카드입니다!");
      Serial.print("📌 ");
      Serial.println(desc);

      if (strcmp(desc, "게이트 A") == 0) {
        send_arrive_status("CHECKPOINT_A", "GATE_A");
      } else if (strcmp(desc, "게이트 B") == 0) {
        send_arrive_status("CHECKPOINT_C", "GATE_B");  // CHECKPOINT_B에서 CHECKPOINT_C로 변경
      }

      return;
    }
  }

  Serial.println("❌ 등록되지 않은 카드입니다!");
}

// ✅ 도착 메시지 전송
void send_arrive_status(const char* position, const char* gate_id) {
  StaticJsonDocument<256> doc;

  doc["sender"] = truck_id;  // 하드코딩된 TRUCK_01 대신 truck_id 사용
  doc["receiver"] = "SERVER";
  doc["cmd"] = "ARRIVED";

  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["gate_id"] = gate_id;
  payload["timestamp"] = getISOTime();

  if (client && client.connected()) {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[📤 송신] 도착 정보 전송:");
    serializeJsonPretty(doc, Serial);
    Serial.println();
  } else {
    Serial.println("[❌ 오류] 서버와 연결되지 않음");
  }
}

// ✅ 미션 요청 메시지 전송
void send_assign_mission() {
  StaticJsonDocument<192> doc;

  doc["sender"] = truck_id;  // 하드코딩된 TRUCK_01 대신 truck_id 사용
  doc["receiver"] = "SERVER";
  doc["cmd"] = "ASSIGN_MISSION";
  doc["payload"] = JsonObject();  // 빈 payload

  if (client && client.connected()) {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[📤 송신] 미션 요청:");
    serializeJsonPretty(doc, Serial);
    Serial.println();
  } else {
    Serial.println("[❌ 오류] 서버와 연결되지 않음 (미션 요청 실패)");
  }
}

// ✅ ISO 시간 문자열 생성
String getISOTime() {
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", t);
  return String(buffer);
}

// ✅ 서버 재접속 로직
void reconnectToServer() {
  if (!client.connected()) {
    Serial.print("🌐 서버 접속 시도 중...");
    if (client.connect(serverIP, serverPort)) {
      Serial.println("✅ 접속 성공!");
    } else {
      Serial.println("❌ 접속 실패");
    }
  }
}