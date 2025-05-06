#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

// ==== WiFi 설정 ====
const char* ssid = "olleh_WiFi_ECDF";
const char* password = "0000000567";

// ==== ✅ PC 서버 주소 및 포트 ==== /////////////////////////////////////////////////
IPAddress serverIP(172, 30, 1, 11);  // ← PC IP로 바꾸세요
const int serverPort = 8001;  
WiFiClient client;
String incoming_msg = "";
////////////////////////////////////////////////////////////////////////////////////

//////////////////////////==== 등록된 UID 목록 ==== //////////////////////////////////
struct UIDEntry 
{
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  { {0x86, 0x51, 0x0A, 0x05}, "게이트 A" },
  { {0x12, 0x6D, 0x07, 0x05}, "게이트 B" }
  /////////////더 추가 해야함 ////////////////
};
const int numRegistered = sizeof(registeredCards) / sizeof(registeredCards[0]);
/////////////////////////////////////////////////////////////////////////////////////


// ==== 트럭 ID 설정 ====/////////////////////////////////////////////////////////////
const char* truck_id = "TRUCK_01";  // 설정 가능하도록 변경
////////////////////////////////////////////////////////////////////////////////////

//////////////////////// ==== 상태 로직 변환 및 기타 변수들 ==== ////////////////////////
bool run_command = false;  // PC 명령으로 주행 여부 결정
bool obstacle_block = false;
float last_distance_cm = 0;
String current_position = "UNKNOWN";     // 현재 위치 동적으로 관리
///////////////////////////////////////////////////////////////////////////////////

// ==== 모터 제어 핀 및 PWM ====
#define MOTOR12_EN 27    // PWM 채널 0
#define MOTOR34_EN 13    // PWM 채널 1
#define MOTOR1_IN1 26
#define MOTOR1_IN2 25
#define MOTOR2_IN3 12
#define MOTOR2_IN4 14

#define PWM_FREQ 1000
#define PWM_RESOLUTION 8
#define PWM_CHANNEL_LEFT 0
#define PWM_CHANNEL_RIGHT 1

// ==== 초음파 센서 핀 ====
#define TRIG_PIN 33
#define ECHO_PIN 32
// ==== rfid 센서 핀 ====
#define SS_PIN 21    // SDA
#define RST_PIN 22   // RST
// ==== 적외선 센서 핀 ====
#define LEFT_SENSOR 34
#define RIGHT_SENSOR 35

// ==== PID 제어 변수 ====
double Kp = 0.1025;
double Kd = 0.2;
double PD_control;
int last_error = 0;
int derivative;
int L_PWM, R_PWM;
int error;
int l_sensor_val;
int r_sensor_val;
int avg_PWM = 150;

int max_pwm = 70;  // 기본값, 이후 PyQt6에서 조정

// ==== rfid 객체 생성 ====
MFRC522 rfid(SS_PIN, RST_PIN);


// ==== 초기화 ====
void setup() 
{
  Serial.begin(115200);

  // ==== 모터 핀 설정 ====
  pinMode(MOTOR1_IN1, OUTPUT);
  pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT);
  pinMode(MOTOR2_IN4, OUTPUT);

  ledcSetup(PWM_CHANNEL_LEFT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR12_EN, PWM_CHANNEL_LEFT);

  ledcSetup(PWM_CHANNEL_RIGHT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR34_EN, PWM_CHANNEL_RIGHT);
  
  // ==== 초음파센서 핀 설정 ====
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // ==== 📶 WiFi 연결 ====
  WiFi.begin(ssid, password);
  Serial.println("WiFi 연결 중...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅Wi-Fi 연결 완료!");

  // ==== 📡 서버 접속 시도 ====
  reconnectToServer();

  // ==== 💳 RFID 초기화 ====
  SPI.begin(18, 19, 23, 21);  // SCK, MISO, MOSI, SS
  rfid.PCD_Init();
  Serial.println("✅RC522 RFID 리더기 시작됨!");

  // ==== ⏱️ 시간 동기화 ====
  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("⏳ 시간 동기화 대기 중...");
  while (time(nullptr) < 100000) 
  {
    delay(100);
    Serial.println("...");
  }
  Serial.println("✅시간 동기화 완료!");

  // ==== ✅ 미션 요청 자동 전송 ====
  delay(2000);  // 안정화 대기
  send_assign_mission();

}

// ==== 메인 루프 ====
void loop() 
{//////////////////////////////////////////==== server ====//////////////////////////////////////////

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


  // 클라이언트로부터 명령 수신
  if (client && client.available()) 
  {
    incoming_msg = client.readStringUntil('\n');
    incoming_msg.trim();
    incoming_msg.toUpperCase();

    Serial.print("[TCP 수신] ");
    Serial.println(incoming_msg);

    ///////////////////====모터속도 업데이팅====///////////////////////////
    handleIncomingJsonMessage(incoming_msg);

    ///명령어 처리
    if (incoming_msg == "RUN") 
    {
      run_command = true;
      line_trace();
    } 
    else if (incoming_msg == "STOP") 
    {
      run_command = false;
      stop_motors();
    }
  }

/////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////// 주행////////////////////////////////////////////
  if (checkAndPrintUID(rfid.uid.uidByte)) 
  {
    stop_motors();        
    run_command = false;  // 등록된 카드일 때만 정지 및 대기
  }

  obstacle_block = obstacle_detected();
  Serial.println(obstacle_block);
  if(!obstacle_block)
  {
    line_trace();
    send_obstacle_status(last_distance_cm, false, current_position.c_str());
  }
  else
  {
    stop_motors();
    send_obstacle_status(last_distance_cm, true, current_position.c_str());
  }
}
////////////////////////////////////////////////////////////////////////////////////////

///////////////////////////// ==== 여기서 부터는 사용자 함수 ==== ///////////////////////////
///////////////////////////// ==== 라인트레이서 제어 ==== ///////////////////////////////////
void line_trace() {
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);

  Serial.print("L: "); Serial.print(l_sensor_val);
  Serial.print(" R: "); Serial.println(r_sensor_val);

  error = l_sensor_val - r_sensor_val;
  PD_control = error * Kp;
  derivative = error - last_error;
  PD_control += Kd * derivative;
  last_error = error;

  R_PWM = speed_limit(avg_PWM - PD_control, 0, max_pwm);
  L_PWM = speed_limit(avg_PWM + PD_control, 0, max_pwm);

  left_motor_f(L_PWM);
  right_motor_f(R_PWM);
}

void stop_motors() {
  ledcWrite(PWM_CHANNEL_LEFT, 0);
  ledcWrite(PWM_CHANNEL_RIGHT, 0);
}

void left_motor_f(int pwm_val) {
  digitalWrite(MOTOR1_IN1, LOW);
  digitalWrite(MOTOR1_IN2, HIGH);
  ledcWrite(PWM_CHANNEL_LEFT, pwm_val);
}

void right_motor_f(int pwm_val) {
  digitalWrite(MOTOR2_IN3, LOW);
  digitalWrite(MOTOR2_IN4, HIGH);
  ledcWrite(PWM_CHANNEL_RIGHT, pwm_val);
}

int speed_limit(int val, int minVal, int maxVal) {
  if (val < minVal) return minVal;
  if (val > maxVal) return maxVal;
  return val;
}
/////////////////////////////////////////////////////////////////////////////////////////////////////////

//////////////////////////////////////// 초음파 기반 장애물 감지 함수//////////////////////////////////////////
bool obstacle_detected() {
  long duration;
  float distance_cm;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH); 
  if (duration == 0)
  {
    Serial.println("Hello");
    return false;  // 실패했으면 장애물 없음
  }
  

  distance_cm = duration * 0.034 / 2.0;  // 거리 계산
  last_distance_cm = distance_cm;  // 전역 변수 업데이트

  Serial.print("Distance: ");
  Serial.print(distance_cm);
  Serial.println(" cm");

  return distance_cm < 10.0;  // 10cm 이내면 true
}
////////////////////////////////////////////////////////////////////////////////////////////////////////

/////////////////////////////////====전송 함수 만들기====//////////////////////////////////////////////////////
void send_obstacle_status(float distance_cm, bool detected, const char* position) 
{
  StaticJsonDocument<256> doc;

  doc["sender"] = truck_id;
  doc["receiver"] = "SERVER";
  doc["cmd"] = "OBSTACLE";

  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["distance_cm"] = distance_cm;

  // 간단한 timestamp
  payload["timestamp"] = getISOTime();

  // 감지 여부: true/false → "DETECTED"/"CLEARED"
  payload["detected"] = detected ? "DETECTED" : "CLEARED";

  if (client && client.connected()) {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[송신] 장애물 상태 전송됨");
  }
}

///////////////////////////////////////////////////////////////////////////////////////////////////

// ✅ UID 비교
bool isSameUID(byte *uid1, byte *uid2) 
{
  for (byte i = 0; i < 4; i++) 
  {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

// ✅ UID 확인 후 메시지 전송
bool checkAndPrintUID(byte* uid) 
{
  for (int i = 0; i < numRegistered; i++) {
    if (isSameUID(uid, registeredCards[i].uid)) {
      const char* desc = registeredCards[i].description;

      Serial.println("✅ 등록된 카드입니다!");
      Serial.print("📌 ");
      Serial.println(desc);

      if (strcmp(desc, "게이트 A") == 0) 
      {
        current_position = "CHECKPOINT_A";
        send_arrive_status("CHECKPOINT_A", "GATE_A");
      } 
      else if (strcmp(desc, "게이트 B") == 0) 
      {
        current_position = "CHECKPOINT_B";
        send_arrive_status("CHECKPOINT_B", "GATE_B");
      }


      return true;  // 등록된 카드
    }
  }

  Serial.println("❌ 등록되지 않은 카드입니다!");
  return false;  // 등록되지 않음
}

// ✅ 도착 메시지 전송
void send_arrive_status(const char* position, const char* gate_id) 
{
  StaticJsonDocument<256> doc;

  doc["sender"] = truck_id;  // 하드코딩된 TRUCK_01 대신 truck_id 사용
  doc["receiver"] = "SERVER";
  doc["cmd"] = "ARRIVED";

  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["gate_id"] = gate_id;
  payload["timestamp"] = getISOTime();

  if (client && client.connected()) 
  {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[📤 송신] 도착 정보 전송:");
    serializeJsonPretty(doc, Serial);
    Serial.println();
  } 
  else 
  {
    Serial.println("[❌ 오류] 서버와 연결되지 않음");
  }
}

// ✅ 미션 요청 메시지 전송
void send_assign_mission() 
{
  StaticJsonDocument<192> doc;

  doc["sender"] = truck_id;  // 하드코딩된 TRUCK_01 대신 truck_id 사용
  doc["receiver"] = "SERVER";
  doc["cmd"] = "ASSIGN_MISSION";
  doc["payload"] = JsonObject();  // 빈 payload

  if (client && client.connected()) 
  {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[📤 송신] 미션 요청:");
    serializeJsonPretty(doc, Serial);
    Serial.println();
  } 
  else 
  {
    Serial.println("[❌ 오류] 서버와 연결되지 않음 (미션 요청 실패)");
  }
}

// ✅ ISO 시간 문자열 생성
String getISOTime() 
{
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", t);
  return String(buffer);
}

// ✅ 서버 재접속 로직
void reconnectToServer() 
{
  if (!client.connected()) 
  {
    Serial.print("🌐 서버 접속 시도 중...");
    if (client.connect(serverIP, serverPort)) 
    {
      Serial.println("✅ 접속 성공!");
    } 
    else 
    {
      Serial.println("❌ 접속 실패");
    }
  }
}
//////////////////////////////////////////==== 속도 조절 명령 수신 ==== /////////////
void handleIncomingJsonMessage(const String& msg) {
  StaticJsonDocument<128> doc;
  DeserializationError err = deserializeJson(doc, msg);
  if (err) {
    Serial.println("[⚠️ JSON 파싱 실패]");
    return;
  }

  const char* cmd = doc["cmd"];
  if (strcmp(cmd, "SET_SPEED") == 0) {
    int new_speed = doc["payload"]["max_pwm"];
    if (new_speed >= 0 && new_speed <= 255) {
      max_pwm = new_speed;
      Serial.print("🌀 속도 변경됨: ");
      Serial.println(max_pwm);
    } else {
      Serial.println("[❌ 오류] PWM 범위 초과");
    }
  } else {
    Serial.print("[ℹ️ 기타 명령어 무시] ");
    Serial.println(cmd);
  }
}

