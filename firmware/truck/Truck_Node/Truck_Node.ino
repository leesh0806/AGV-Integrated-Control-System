#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

/*--------------------------------WiFi 설정--------------------------------*/

const char* ssid = "addinedu_class_1(2.4G)";
const char* password = "addinedu1";

/*--------------------------------PC 서버 주소 및 포트--------------------------------*/

IPAddress serverIP(192, 168, 2, 23);  // ← PC IP로 바꾸세요
const int serverPort = 8001;  
WiFiClient client;
String incoming_msg = "";

/*--------------------------------등록된 UID 목록--------------------------------*/

struct UIDEntry 
{
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  { {0x86, 0x51, 0x0A, 0x05}, "CHECKPOINT_A" },
  { {0x12, 0x6D, 0x07, 0x05}, "CHECKPOINT_B" },
  { {0x12, 0x6D, 0x07, 0x05}, "CHECKPOINT_C" },
  { {0x12, 0x6D, 0x07, 0x05}, "CHECKPOINT_D" },
};
const int numRegistered = sizeof(registeredCards) / sizeof(registeredCards[0]);

/*--------------------------------트럭 ID 설정--------------------------------*/

char* truck_id = "TRUCK_01";

/*-------------------------상태 로직 변환 및 기타 변수들--------------------------------*/

bool run_command = false;
bool obstacle_block = false;   //지금 멈춰야 하나?(실시간 결정용)
bool prev_obstacle_state = false;
float last_distance_cm = 0;
String current_position = "UNKNOWN";
String last_cmd = "";
unsigned long last_mission_check = 0;    // 마지막 미션 체크 시간
const unsigned long MISSION_CHECK_INTERVAL = 5000;  // 5초마다 체크

/*--------------------------------모터 제어 핀 및 PWM--------------------------------*/

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

/*--------------------------------초음파 센서 핀--------------------------------*/

#define TRIG_PIN 33
#define ECHO_PIN 32

/*--------------------------------rfid 센서 핀--------------------------------*/

#define SS_PIN 21    // SDA
#define RST_PIN 22   // RST

/*--------------------------------적외선 센서 핀--------------------------------*/
#define LEFT_SENSOR 34
#define RIGHT_SENSOR 35

/*--------------------------------PID 제어 변수--------------------------------*/

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
int max_pwm = 70;

/*--------------------------------rfid 객체 생성--------------------------------*/

MFRC522 rfid(SS_PIN, RST_PIN);

/*--------------------------------함수 선언--------------------------------*/

void receive_json(const String& msg);
void send_obstacle(float distance_cm, bool detected, const char* position);
void send_arrived(const char* position, const char* gate_id);
bool isSameUID(byte* uid1, byte* uid2);
bool checkAndPrintUID(byte* uid);

/*--------------------------------------------------------------------------------*/

void setup() 
{
  Serial.begin(115200);

  // 모터 핀 설정
  pinMode(MOTOR1_IN1, OUTPUT);
  pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT);
  pinMode(MOTOR2_IN4, OUTPUT);

  ledcSetup(PWM_CHANNEL_LEFT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR12_EN, PWM_CHANNEL_LEFT);
  ledcSetup(PWM_CHANNEL_RIGHT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR34_EN, PWM_CHANNEL_RIGHT);
  
  // 초음파센서 핀 설정
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // WiFi 연결
  WiFi.begin(ssid, password);
  Serial.println("WiFi 연결 중...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅Wi-Fi 연결 완료!");

  // 서버 접속 시도
  reconnectToServer();

  // RFID 초기화
  SPI.begin(18, 19, 23, 21);  // SCK, MISO, MOSI, SS
  rfid.PCD_Init();
  Serial.println("✅RC522 RFID 리더기 시작됨!");

  // 시간 동기화
  configTime(9 * 3600, 0, "pool.ntp.org", "time.nist.gov");
  Serial.println("⏳ 시간 동기화 대기 중...");
  while (time(nullptr) < 100000) 
  {
    delay(100);
    Serial.println("...");
  }
  Serial.println("✅시간 동기화 완료!");

  // 미션 요청 자동 전송
  delay(2000);  // 안정화 대기
  send_assign_mission();

}

void loop() 
{
  reconnectToServer();

  // ✅ 수신 메시지 처리
  if (client && client.available()) {
    incoming_msg = client.readStringUntil('\n');
    incoming_msg.trim();

    Serial.println("========== 📩 [서버 메시지 수신] ==========");
    Serial.println(incoming_msg);
    Serial.println("===========================================");

    receive_json(incoming_msg);
  }

  // ✅ 주기적인 미션 체크
  unsigned long current_time = millis();
  if (current_time - last_mission_check >= MISSION_CHECK_INTERVAL) {
    last_mission_check = current_time;
    if (current_position == "UNKNOWN" || current_position == "STANDBY") {
      Serial.println("[🔄 미션 체크] 새로운 미션 확인 중...");
      send_assign_mission();
    }
  }

  // ✅ 주행 제어
  obstacle_block = obstacle_detected();
  if (run_command && !obstacle_block) 
  {
    line_trace();
    send_obstacle(last_distance_cm, false, current_position.c_str());
  }
  else if (obstacle_block) 
  {
    stop_motors();
    send_obstacle(last_distance_cm, true, current_position.c_str());
  }
}

/*------------------------------- 수신 처리--------------------------------*/

// JSON 수신 함수
void receive_json(const String& msg)
{
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, msg);

  // JSON 파싱 오류 처리
  if (err)
  {
    Serial.println("[⚠️ JSON 파싱 실패]");
    Serial.println(msg);
    return;
  }

  const char* cmd = doc["cmd"];
  Serial.print("📩 [디버깅] 파싱된 명령어: ");
  Serial.println(cmd);

  // 중복 명령 처리 방지
  if (last_cmd == String(cmd))
  {
    Serial.print("[⏭️ 중복 명령 무시] 이미 처리한 명령: ");  
    Serial.println(cmd);
    return;
  }

  // 명령 처리
  last_cmd = String(cmd);
  if (strcmp(cmd, "SET_SPEED") == 0) {
    Serial.println("[디버깅] SET_SPEED 명령 처리 시작");
  } 
  else if (strcmp(cmd, "RUN") == 0) {
    Serial.println("[✅ 디버깅] RUN 명령 수신됨!");
    run_command = true;
  } 
  else if (strcmp(cmd, "STOP") == 0) {
    Serial.println("[⛔ 디버깅] STOP 명령 수신됨!");
    run_command = false;
    stop_motors();
  } 
  else {
    Serial.print("[ℹ️ 디버깅] 알 수 없는 명령: ");
    Serial.println(cmd);
  }
}

/*-------------------------------- 송신 처리 --------------------------------*/

// JSON 송신 함수
void send_json(const char* cmd, JsonObject payload)
{
  StaticJsonDocument<256> doc;

  // 공통 메시지 구조
  doc["sender"] = truck_id;
  doc["receiver"] = "SERVER";
  doc["cmd"] = cmd;
  doc["payload"] = payload;
  
  // 서버 연결 확인 후 메시지 전송
  if (client && client.connected())
  {
    serializeJson(doc, client);
    client.print("\n");
    Serial.println("[📤 송신] 메시지 전송:");
    serializeJsonPretty(doc, Serial);
    Serial.println();
  }
  else
  {
    Serial.println("[❌ 오류] 서버와 연결되지 않음 (메시지 전송 실패)");
  }
}

// 미션 요청 메시지 (ASSIGN_MISSION)
void send_assign_mission() 
{
  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");
  send_json("ASSIGN_MISSION", payload);
}

// 도착 메시지 (ARRIVED)
void send_arrived(const char* position, const char* gate_id) 
{
  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["gate_id"] = gate_id;
  payload["timestamp"] = getISOTime();
  send_json("ARRIVED", payload);
}

// 장애물 감지 메시지 (OBSTACLE)
void send_obstacle(float distance_cm, bool detected, const char* position) 
{

  if (detected == prev_obstacle_state) return;

  prev_obstacle_state = detected;

  StaticJsonDocument<256> doc;
  JsonObject payload = doc.createNestedObject("payload");

  payload["position"] = position;
  payload["distance_cm"] = distance_cm;
  payload["timestamp"] = getISOTime();
  payload["detected"] = detected ? "DETECTED" : "CLEARED";
  
  send_json("OBSTACLE", payload);
}

/*--------------------------------라인트레이서 제어--------------------------------*/

void line_trace() {
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);

  //Serial.print("L: "); Serial.print(l_sensor_val);
  //Serial.print(" R: "); Serial.println(r_sensor_val);

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

/*--------------------------------초음파 기반 장애물 감지--------------------------------*/

// 장애물 감지 여부
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

/*--------------------------------UID 관련 함수--------------------------------*/

bool isSameUID(byte *uid1, byte *uid2) 
{
  for (byte i = 0; i < 4; i++) 
  {
    if (uid1[i] != uid2[i]) return false;
  }
  return true;
}

bool checkAndPrintUID(byte* uid) 
{
  for (int i = 0; i < numRegistered; i++) {
    if (isSameUID(uid, registeredCards[i].uid)) {
      const char* desc = registeredCards[i].description;

      Serial.println("✅ 등록된 카드입니다!");
      Serial.print("📌 ");
      Serial.println(desc);

      if (strcmp(desc, "CHECKPOINT_A") == 0) 
      {
        current_position = "CHECKPOINT_A";
        send_arrived("CHECKPOINT_A", "GATE_A");
      } 
      else if (strcmp(desc, "CHECKPOINT_B") == 0) 
      {
        current_position = "CHECKPOINT_B";
        send_arrived("CHECKPOINT_B", "GATE_B");
      }
      else if (strcmp(desc, "CHECKPOINT_C") == 0) 
      {
        current_position = "CHECKPOINT_C";
        send_arrived("CHECKPOINT_C", "GATE_C");
      }
      else if (strcmp(desc, "CHECKPOINT_D") == 0)
      {
        current_position = "CHECKPOINT_D";
        send_arrived("CHECKPOINT_D", "GATE_D");
      }
      return true;
    }
  }

  Serial.println("❌ 등록되지 않은 카드입니다!");
  return false;  // 등록되지 않음
}

/*-------------------------------유틸 함수--------------------------------*/

String getISOTime() 
{
  time_t now = time(nullptr);
  struct tm* t = localtime(&now);
  char buffer[25];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", t);
  return String(buffer);
}

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
