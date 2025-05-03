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

WiFiServer server(8000);
WiFiClient client;

String incoming_msg = "";

// 등록된 UID 목록
byte checkpoint_A[4]  = {0x86, 0x51, 0x0A, 0x05};
byte checkpoint_B[4] = {0x12, 0x6D, 0x07, 0x05};
// byte load_B[4] = {0x12, 0x6D, 0x07, 0x05};
// byte load_A[4] = {0x12, 0x6D, 0x07, 0x05};
// byte checkpoint_C[4] = {0x12, 0x6D, 0x07, 0x05};
// byte checkpoint_D[4] = {0x12, 0x6D, 0x07, 0x05};
// byte belt[4] = {0x12, 0x6D, 0x07, 0x05};
// byte standby[4] = {0x12, 0x6D, 0x07, 0x05};

struct UIDEntry  //클래스로 알고 있기
{
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  { {0x86, 0x51, 0x0A, 0x05}, "게이트 A" },
  { {0x12, 0x6D, 0x07, 0x05}, "게이트 B" }
  // { {0xDE, 0xAD, 0xBE, 0xEF}, "로드 B" },
  // { {0xDE, 0xAD, 0xBE, 0xEF}, "로드 A" },
  // { {0xDE, 0xAD, 0xBE, 0xEF}, "게이트 C" },
  // { {0xDE, 0xAD, 0xBE, 0xEF}, "게이트 D" },
  // { {0xDE, 0xAD, 0xBE, 0xEF}, "벨트" },
  // { {0xDE, 0xAD, 0xBE, 0xEF}, "스탠바이 "}
};

const int numRegistered = sizeof(registeredCards) / sizeof(registeredCards[0]);

void setup() 
{
  Serial.begin(115200);
/////////////////////////////////wifi begin//////////////////////////////////////////////////////////////
  // 1. WiFi 연결
  WiFi.begin(ssid, password);
  Serial.println("📶 WiFi 연결 중...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ Wi-Fi 연결 완료!");
///////////////////////////////////////////////////////rfid//////////////////////////////////////////////
  SPI.begin(18, 19, 23, 21);  // SCK, MISO, MOSI, SS
  rfid.PCD_Init();
  Serial.println("📡 RC522 RFID 리더기 시작됨!");
/////////////////////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////시간: 2025/00/00 으로 설정 //////////////////////////////////
  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");  // 한국: UTC+9
  Serial.println("⏳ 시간 동기화 대기 중...");
  while (time(nullptr) < 100000) 
  {
    delay(100);
    Serial.println("hello");
  }
  Serial.println("✅ 시간 동기화 완료!");
  /////////////////////////////////////////////////////////////////////////////////////////////////////////
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) 
  {
    return;
  }

  // UID 포맷 출력
  Serial.print("UID: ");
  for (byte i = 0; i < rfid.uid.size; i++) 
  {
    if (rfid.uid.uidByte[i] < 0x10) 
    {
      Serial.print("0");
    }
    Serial.print(rfid.uid.uidByte[i], HEX);

    if (i < rfid.uid.size - 1) 
    {
      Serial.print("-");
    }
  }
  Serial.println();

  // 체크 + 출력 + 전송 통합
  checkAndPrintUID(rfid.uid.uidByte);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

// UID 비교 함수
bool isSameUID(byte *uid1, byte *uid2) {
  for (byte i = 0; i < 4; i++) {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

void checkAndPrintUID(byte* uid) 
{
  for (int i = 0; i < numRegistered; i++) 
  {
    if (isSameUID(uid, registeredCards[i].uid)) 
    {
      const char* desc = registeredCards[i].description;

      Serial.println("✅ 등록된 카드입니다!");
      Serial.print("📌 ");
      Serial.println(desc);

      // 설명에 따라 서버 전송
      if (strcmp(desc, "게이트 A") == 0) {
        send_arrive_status("CHECKPOINT_A", "GATE_A");
      }
      // 다른 경우 추가 가능
      // else if (strcmp(desc, "게이트 B") == 0) {
      //   send_arrive_status("CHECKPOINT_B", "GATE_B");
      // }

      return;
    }
  }

  Serial.println("❌ 등록되지 않은 카드입니다!");
}

void send_arrive_status(const char* position, const char* gate_id) 
{
  StaticJsonDocument<256> doc;

  doc["sender"] = "TRUCK";
  doc["receiver"] = "SERVER";
  doc["cmd"] = "ARRIVED";

  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["gate_id"] = gate_id;
  payload["timestamp"] = getISOTime();  // ISO 시간 추가

  if (client && client.connected()) 
  {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[송신] 도착 정보 전송:");
    serializeJsonPretty(doc, Serial);  // 콘솔에도 보기 좋게 출력
    Serial.println();
  } 
  else 
  {
    Serial.println("[오류] 서버와 연결되지 않음");
  }
}
////////////////////////////////////////////////////////////현재 시간 문자열 생성 함수//////////////////////////////////////////////////
String getISOTime() 
{
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", t);
  return String(buffer);
}
////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

