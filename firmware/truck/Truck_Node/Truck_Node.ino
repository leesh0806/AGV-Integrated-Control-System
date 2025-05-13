#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

/*--------------------------------WiFi 설정--------------------------------*/

const char* ssid = "addinedu_class_2 (2.4G)";
const char* password = "addinedu1";

/*--------------------------------PC 서버 주소 및 포트--------------------------------*/

IPAddress serverIP(192, 168, 0, 166);  // ← PC IP로 바꾸세요
const int serverPort = 8001;  
WiFiClient client;
String incoming_msg = "";

/*--------------------------------프로토콜 정의--------------------------------*/

// 트럭 → PC 명령어
#define CMD_ARRIVED 0x01
#define CMD_OBSTACLE 0x02
#define CMD_STATUS_UPDATE 0x03
#define CMD_START_LOADING 0x04
#define CMD_FINISH_LOADING 0x05
#define CMD_START_UNLOADING 0x06
#define CMD_FINISH_UNLOADING 0x07
#define CMD_ASSIGN_MISSION 0x08
#define CMD_ACK_GATE_OPENED 0x09
#define CMD_FINISH_CHARGING 0x0A
#define CMD_BATTERY 0x0B  // 추가: 배터리 상태 전용 명령어

// PC → 트럭 명령어
#define CMD_MISSION_ASSIGNED 0x10
#define CMD_NO_MISSION 0x11
#define CMD_RUN 0x12
#define CMD_STOP 0x13
#define CMD_GATE_OPENED 0x14
#define CMD_START_CHARGING 0x15
#define CMD_CANCEL_MISSION 0x16  // 추가: 미션 취소 명령어

// 시스템 명령어
#define CMD_HELLO 0xF0
#define CMD_HEARTBEAT_ACK 0xF1
#define CMD_HEARTBEAT_CHECK 0xF2

// sender/receiver IDs
#define ID_SERVER 0x10
#define ID_TRUCK_01 0x01
#define ID_TRUCK_02 0x02
#define ID_TRUCK_03 0x03
#define ID_GUI 0x04

// position 코드
#define POS_CHECKPOINT_A 0x01
#define POS_CHECKPOINT_B 0x02
#define POS_CHECKPOINT_C 0x03
#define POS_CHECKPOINT_D 0x04
#define POS_LOAD_A 0x05
#define POS_LOAD_B 0x06
#define POS_BELT 0x07
#define POS_STANDBY 0x08
#define POS_GATE_A 0xA1
#define POS_GATE_B 0xA2
#define POS_UNKNOWN 0x00

// 상태 코드
#define STATE_NORMAL 0x00
#define STATE_EMERGENCY 0x01
#define STATE_LOW_BATTERY 0x02
#define STATE_CHARGING 0x03
#define STATE_FULLY_CHARGED 0x04

/*--------------------------------등록된 UID 목록--------------------------------*/

struct UIDEntry 
{
  byte uid[4];
  const char* description;
};

UIDEntry registeredCards[] = {
  // { {0x8B, 0xEE, 0xC9, 0x01}, "CHARGE_LOCATION" },
  { {0x86, 0x51, 0x0A, 0x05}, "CHECKPOINT_A" },
  { {0x12, 0x6D, 0x07, 0x05}, "CHECKPOINT_B" },
  { {0xD9, 0x3F, 0x09, 0x05}, "load_A" },
  { {0xA3, 0x8F, 0x09, 0x05}, "load_B" },
  { {0x9C, 0x84, 0x0B, 0x05}, "CHECKPOINT_C" },
  { {0x83, 0x58, 0xAE, 0x1A}, "BELT" },
  { {0x63, 0x9D, 0x9F, 0x35}, "CHECKPOINT_D" },
  { {0xF3, 0x16, 0x63, 0x1B}, "STANDBY" },
  
};
const int numRegistered = sizeof(registeredCards) / sizeof(registeredCards[0]);

unsigned long last_rfid_check = 0;
const unsigned long RFID_CHECK_INTERVAL = 300;  // 0.3초마다 RFID 체크

/*--------------------------------트럭 ID 설정--------------------------------*/

char* truck_id = "TRUCK_01";
byte truck_id_byte = ID_TRUCK_01;  // 바이트 형식 ID

/*-------------------------상태 로직 변환 및 기타 변수들--------------------------------*/

bool run_command = false;
bool obstacle_block = false;   //지금 멈춰야 하나?(실시간 결정용)
bool prev_obstacle_state = false;
float last_distance_cm = 0;

String current_position = "UNKNOWN";
String last_cmd = "";
String mission_target = "";
unsigned long last_mission_check = 0;    // 마지막 미션 체크 시간
const unsigned long MISSION_CHECK_INTERVAL = 5000;  // 5초마다 체크

/*-------------------------loading 변수들--------------------------------*/

bool wait_start_loading = false;
unsigned long wait_start_loading_time = 0;

bool loading_in_progress = false;
unsigned long loading_start_time = 0;

/*-------------------------unloading 변수들--------------------------------*/
bool wait_start_unloading = false;
unsigned long wait_start_unloading_time = 0;

bool unloading_in_progress = false;
unsigned long unloading_start_time = 0;

unsigned long unloading_stage_time = 0;
int unloading_stage = 0;

// 서보모터 제어 관련 전역 변수
Servo unloading_servo;
const int SERVO_PIN = 17;
const int SERVO_INIT_ANGLE = 170;
const int SERVO_DROP_ANGLE = 90;

/*--------------------------------가상 배터리 잔량 체크--------------------------------*/

int battery_level = 100;

unsigned long last_battery_drop = 0;
const unsigned long BATTERY_DROP_INTERVAL = 5000; //5초 마다 배터리 감소 

unsigned long last_battery_report = 0;
const unsigned long BATTERY_REPORT_INTERVAL = 5000; // 5초마다 배터리 상태 서버에 전송
bool battery_empty = false;  // 배터리 0% 상태 플래그

unsigned long last_heartbeat = 0;
const unsigned long HEARTBEAT_INTERVAL = 30000;  // 30초마다 하트비트 전송

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

double Kp = 0.1020;
double Kd = 0.2;
double Ki = 0.0001;       
double integral = 0.0;  // 누적 적분값
double PID_control;
int last_error = 0;
int derivative;
int L_PWM, R_PWM;
int error;
int l_sensor_val;
int r_sensor_val;
int avg_PWM = 150;
int max_pwm = 75;

/*--------------------------------rfid 객체 생성--------------------------------*/

MFRC522 rfid(SS_PIN, RST_PIN);

/*--------------------------------함수 선언--------------------------------*/

void receive_binary(const uint8_t* data, size_t len);
void send_binary(uint8_t cmd_id, const char* position = nullptr, const char* gate_id = nullptr);
uint8_t get_position_code(const char* position);
const char* get_position_str(uint8_t code);
uint8_t get_cmd_code(const char* cmd);
const char* get_cmd_str(uint8_t code);
uint8_t get_truck_state();

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

  //서보모터 초기 설정
  unloading_servo.attach(SERVO_PIN);
  unloading_servo.write(SERVO_INIT_ANGLE);  // 초기 위치

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
    // 헤더 4바이트 읽기
    uint8_t header[4];
    int read_size = client.read(header, 4);
    
    if (read_size == 4) {
      uint8_t sender_id = header[0];
      uint8_t receiver_id = header[1];
      uint8_t cmd_id = header[2];
      uint8_t payload_len = header[3];
      
      // 페이로드 읽기
      uint8_t payload[32] = {0}; // 최대 32바이트 페이로드 가정
      if (payload_len > 0) {
        read_size = client.read(payload, payload_len);
        if (read_size != payload_len) {
          Serial.println("[⚠️ 오류] 페이로드 데이터 불완전");
          return;
        }
      }
      
      // 전체 메시지
      uint8_t full_msg[36]; // 헤더 4바이트 + 최대 32바이트 페이로드
      memcpy(full_msg, header, 4);
      if (payload_len > 0) {
        memcpy(full_msg + 4, payload, payload_len);
      }
      
      Serial.println("========== 📩 [서버 메시지 수신] ==========");
      Serial.print("명령 코드: 0x");
      Serial.println(cmd_id, HEX);
      Serial.println("===========================================");
      
      receive_binary(full_msg, 4 + payload_len);
    }
  }

  // ✅ 현재 시간 갱신
  unsigned long current_time = millis();

  // ✅ 주기적인 미션 체크
  if (current_time - last_mission_check >= MISSION_CHECK_INTERVAL) 
  {
    last_mission_check = current_time;
    if (current_position == "UNKNOWN" || current_position == "STANDBY") 
    {
      Serial.println("[🔄 미션 체크] 새로운 미션 확인 중...");
      send_assign_mission();
    }
  }

    // ✅ 주행 제어
  obstacle_block = obstacle_detected();
  if (run_command && !obstacle_block && !battery_empty)
  {
    //Serial.println("run");
    line_trace();
    send_obstacle(last_distance_cm, false, current_position.c_str());
  }
  else if (obstacle_block) 
  {
    Serial.println("stop");
    //Serial.print("Distance: ");
    //Serial.print(distance_cm);
    //Serial.println(" cm");
    stop_motors();
    send_obstacle(last_distance_cm, true, current_position.c_str());
  }
  //적재 시작 지연 처리
  if (wait_start_loading && (current_time - wait_start_loading_time >= 2000)) 
  {
    Serial.println("🕒 적재 시작 메시지 전송 (2초 지연 후)");
    send_start_loading();
    loading_in_progress = true;
    loading_start_time = current_time;
    wait_start_loading = false;
  }
  // 적재 완료 로직 추가 (5초 뒤 자동 전송)
  if (loading_in_progress && (current_time - loading_start_time >= 5000)) 
  {
    Serial.println("✅ 적재 완료 메시지 전송 (5초 경과)");
    send_finish_loading();
    loading_in_progress = false;
  }

  // 언로딩 시작 지연 처리
  if (wait_start_unloading && (current_time - wait_start_unloading_time >= 2000)) 
  {
    start_unloading();
    wait_start_unloading = false;
  }

  // 언로딩 FSM 처리
  handle_unloading(current_time);
    
  // RFID 체크
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) 
  {
    return;
  }

  // Serial.print("UID: ");
  // for (byte i = 0; i < rfid.uid.size; i++) {
  //   if (rfid.uid.uidByte[i] < 0x10) Serial.print("0");
  //   Serial.print(rfid.uid.uidByte[i], HEX);
  //   if (i < rfid.uid.size - 1) Serial.print("-");
  // }
  // Serial.println();

  // UID 확인 및 서버 전송
  checkAndPrintUID(rfid.uid.uidByte);

  // 🪫 10초마다 배터리 감소
  if (current_time - last_battery_drop >= BATTERY_DROP_INTERVAL) {
    last_battery_drop = current_time;

    if (battery_level > 0) {
      battery_level -= 5;
      if (battery_level <= 0) {
        battery_level = 0;
        battery_empty = true;
        run_command = false;
        stop_motors();
        Serial.println("❌ 배터리 소진 → 트럭 정지");
      }

      Serial.print("🪫 배터리 감소됨: ");
      Serial.print(battery_level);
      Serial.println("%");
    }
  }

  // 📤 5초마다 서버에 배터리 상태 전송
  if (current_time - last_battery_report >= BATTERY_REPORT_INTERVAL) {
    last_battery_report = current_time;
    send_battery_status();
  }

  // ✅ 주기적인 하트비트 전송
  if (current_time - last_heartbeat >= HEARTBEAT_INTERVAL) {
    last_heartbeat = current_time;
    send_heartbeat();
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

}

/*------------------------------- 수신 처리--------------------------------*/

void receive_binary(const uint8_t* data, size_t len) {
  if (len < 4) {
    Serial.println("[⚠️ 오류] 메시지 길이 불충분");
    return;
  }
  
  uint8_t sender_id = data[0];
  uint8_t receiver_id = data[1];
  uint8_t cmd_id = data[2];
  uint8_t payload_len = data[3];
  
  // 페이로드 길이 검증
  if (len != 4 + payload_len) {
    Serial.println("[⚠️ 오류] 페이로드 길이 불일치");
    return;
  }
  
  Serial.println("📩 [디버깅] 바이너리 메시지 수신됨");
  Serial.print("  - 송신자: 0x");
  Serial.println(sender_id, HEX);
  Serial.print("  - 수신자: 0x");
  Serial.println(receiver_id, HEX);
  Serial.print("  - 명령어: 0x");
  Serial.println(cmd_id, HEX);
  Serial.print("  - 페이로드 길이: ");
  Serial.println(payload_len);
  
  // 중복 명령 확인
  if (last_cmd == String(cmd_id)) {
    Serial.print("[⏭️ 중복 명령 무시] 이미 처리한 명령: 0x");
    Serial.println(cmd_id, HEX);
    return;
  }
  
  last_cmd = String(cmd_id);
  
  // 명령 처리
  switch (cmd_id) {
    case CMD_RUN:
      Serial.println("[✅ 디버깅] RUN 명령 수신됨!");
      run_command = true;
      break;
      
    case CMD_STOP:
      Serial.println("[⛔ 디버깅] STOP 명령 수신됨!");
      run_command = false;
      stop_motors();
      break;
      
    case CMD_GATE_OPENED:
      if (payload_len >= 1) {
        uint8_t gate_code = data[4]; // 첫 번째 페이로드 바이트
        const char* gate_id = get_position_str(gate_code);
        Serial.print("[🚪 게이트 열림 감지] : ");
        Serial.println(gate_id);
        send_gateopen_message(gate_id);  // 응답 전송
        run_command = true;
      }
      break;
      
    case CMD_MISSION_ASSIGNED:
      if (payload_len >= 1) {
        // 단순화된 형식: source 코드만 포함
        uint8_t source_code = data[4]; // 첫 번째 페이로드 바이트
        const char* source = get_position_str(source_code);
        mission_target = String(source);
        Serial.print("[📦 미션 할당됨] 목표 위치: ");
        Serial.println(mission_target);
        run_command = true;
      }
      break;
      
    case CMD_NO_MISSION:
      Serial.println("📭 [서버 응답] 미션 없음 → 대기 상태 유지");
      run_command = false;
      mission_target = "";
      break;
      
    case CMD_HEARTBEAT_ACK:
      Serial.println("[💓 하트비트 응답] 서버로부터 하트비트 응답 수신");
      break;
      
    case CMD_HEARTBEAT_CHECK:
      Serial.println("[💓 하트비트 요청] 서버에서 생존 확인 요청");
      send_heartbeat();
      break;
      
    case CMD_CANCEL_MISSION:
      // 미션 취소 처리
      if (payload_len >= 1) {
        uint8_t reason_len = data[4];
        String reason = "UNKNOWN";
        
        if (payload_len >= 1 + reason_len) {
          char reason_buf[33] = {0}; // 최대 32바이트 + NULL 종료
          memcpy(reason_buf, &data[5], min(reason_len, 32));
          reason = String(reason_buf);
        }
        
        Serial.print("[❌ 미션 취소] 사유: ");
        Serial.println(reason);
        
        // 주행 정지 및 미션 초기화
        run_command = false;
        mission_target = "";
        stop_motors();
      }
      break;
      
    case CMD_START_CHARGING:
      Serial.println("[🔋 충전 시작] 서버에서 충전 명령 수신");
      
      // 충전 상태로 변경 및 주행 정지
      run_command = false;
      stop_motors();
      
      // 필요한 경우 추가 충전 관련 처리
      
      break;
      
    default:
      Serial.print("[ℹ️ 디버깅] 알 수 없는 명령: 0x");
      Serial.println(cmd_id, HEX);
  }
}

/*-------------------------------- 송신 처리 --------------------------------*/

// 바이너리 송신 함수
void send_binary(uint8_t cmd_id, const char* position = nullptr, const char* gate_id = nullptr) {
  uint8_t payload[32] = {0};  // 최대 32바이트 페이로드
  uint8_t payload_len = 0;
  
  // 페이로드 구성 (명령어별로 다름)
  if (cmd_id == CMD_ARRIVED && position != nullptr) {
    // ARRIVED 명령의 경우 위치 정보 포함
    payload[0] = get_position_code(position);
    if (gate_id != nullptr) {
      payload[1] = get_position_code(gate_id);
      payload_len = 2;
    } else {
      payload_len = 1;
    }
  }
  else if (cmd_id == CMD_OBSTACLE) {
    // 장애물 감지 명령의 경우 위치와 감지 여부 및 거리 포함
    if (position != nullptr) {
      payload[0] = get_position_code(position);
      payload[1] = prev_obstacle_state ? 0x01 : 0x00;  // 장애물 감지 여부
      
      // 거리 정보 (2바이트 빅 엔디안 부호 없는 정수)
      uint16_t distance = (uint16_t)last_distance_cm;
      payload[2] = (distance >> 8) & 0xFF;  // 상위 바이트
      payload[3] = distance & 0xFF;         // 하위 바이트
      
      payload_len = 4;
    }
  }
  else if (cmd_id == CMD_ACK_GATE_OPENED && gate_id != nullptr) {
    // 게이트 열림 응답의 경우 게이트 ID 포함
    payload[0] = get_position_code(gate_id);
    if (position != nullptr) {
      payload[1] = get_position_code(position);
      payload_len = 2;
    } else {
      payload_len = 1;
    }
  }
  else if (cmd_id == CMD_STATUS_UPDATE) {
    // 단순화: battery_level(1) + position_code(1)만 포함
    uint8_t battery_level_byte = (uint8_t)battery_level;
    uint8_t position_code = position != nullptr ? get_position_code(position) : get_position_code(current_position.c_str());
    
    // 바이너리 구성: battery_level(1) + position_code(1)
    payload[0] = battery_level_byte;
    payload[1] = position_code;
    payload_len = 2;
  }
  else if (cmd_id == CMD_BATTERY) {
    // 배터리 상태만 전용으로 전송
    uint8_t battery_level_byte = (uint8_t)battery_level;
    uint8_t is_charging = 0;  // 현재는 충전 상태 추적 안함
    uint8_t battery_state = battery_level <= 20 ? STATE_LOW_BATTERY : STATE_NORMAL;
    
    payload[0] = battery_level_byte;
    payload[1] = is_charging;
    payload[2] = battery_state;
    payload_len = 3;
  }
  else if (cmd_id == CMD_START_LOADING || 
           cmd_id == CMD_FINISH_LOADING || 
           cmd_id == CMD_START_UNLOADING || 
           cmd_id == CMD_FINISH_UNLOADING) {
    // 위치 정보 포함하는 기타 명령
    if (position != nullptr) {
      payload[0] = get_position_code(position);
      payload_len = 1;
    }
  }
  
  // 헤더 구성 (4바이트)
  uint8_t header[4] = {
    truck_id_byte,         // sender_id
    ID_SERVER,             // receiver_id
    cmd_id,                // cmd_id
    payload_len            // payload_len
  };
  
  // 서버 연결 확인 후 메시지 전송
  if (client && client.connected()) {
    // 헤더 전송
    client.write(header, 4);
    
    // 페이로드가 있으면 전송
    if (payload_len > 0) {
      client.write(payload, payload_len);
    }
    
    Serial.println("[📤 송신] 바이너리 메시지 전송:");
    Serial.print("  - 명령어: 0x");
    Serial.println(cmd_id, HEX);
    Serial.print("  - 페이로드 길이: ");
    Serial.println(payload_len);
  }
  else {
    Serial.println("[❌ 오류] 서버와 연결되지 않음 (메시지 전송 실패)");
  }
}

// 위치 코드 변환 함수
uint8_t get_position_code(const char* position) {
  if (strcmp(position, "CHECKPOINT_A") == 0) return POS_CHECKPOINT_A;
  if (strcmp(position, "CHECKPOINT_B") == 0) return POS_CHECKPOINT_B;
  if (strcmp(position, "CHECKPOINT_C") == 0) return POS_CHECKPOINT_C;
  if (strcmp(position, "CHECKPOINT_D") == 0) return POS_CHECKPOINT_D;
  if (strcmp(position, "LOAD_A") == 0) return POS_LOAD_A;
  if (strcmp(position, "load_A") == 0) return POS_LOAD_A;  // 호환성
  if (strcmp(position, "LOAD_B") == 0) return POS_LOAD_B;
  if (strcmp(position, "load_B") == 0) return POS_LOAD_B;  // 호환성
  if (strcmp(position, "BELT") == 0) return POS_BELT;
  if (strcmp(position, "STANDBY") == 0) return POS_STANDBY;
  if (strcmp(position, "GATE_A") == 0) return POS_GATE_A;
  if (strcmp(position, "GATE_B") == 0) return POS_GATE_B;
  return POS_UNKNOWN;  // 알 수 없는 위치
}

// 위치 문자열 변환 함수
const char* get_position_str(uint8_t code) {
  switch (code) {
    case POS_CHECKPOINT_A: return "CHECKPOINT_A";
    case POS_CHECKPOINT_B: return "CHECKPOINT_B";
    case POS_CHECKPOINT_C: return "CHECKPOINT_C";
    case POS_CHECKPOINT_D: return "CHECKPOINT_D";
    case POS_LOAD_A: return "LOAD_A";
    case POS_LOAD_B: return "LOAD_B";
    case POS_BELT: return "BELT";
    case POS_STANDBY: return "STANDBY";
    case POS_GATE_A: return "GATE_A";
    case POS_GATE_B: return "GATE_B";
    default: return "UNKNOWN";
  }
}

// 명령 코드 변환 함수
uint8_t get_cmd_code(const char* cmd) {
  if (strcmp(cmd, "ARRIVED") == 0) return CMD_ARRIVED;
  if (strcmp(cmd, "OBSTACLE") == 0) return CMD_OBSTACLE;
  if (strcmp(cmd, "STATUS_UPDATE") == 0) return CMD_STATUS_UPDATE;
  if (strcmp(cmd, "START_LOADING") == 0) return CMD_START_LOADING;
  if (strcmp(cmd, "FINISH_LOADING") == 0) return CMD_FINISH_LOADING;
  if (strcmp(cmd, "START_UNLOADING") == 0) return CMD_START_UNLOADING;
  if (strcmp(cmd, "FINISH_UNLOADING") == 0) return CMD_FINISH_UNLOADING;
  if (strcmp(cmd, "ASSIGN_MISSION") == 0) return CMD_ASSIGN_MISSION;
  if (strcmp(cmd, "ACK_GATE_OPENED") == 0) return CMD_ACK_GATE_OPENED;
  if (strcmp(cmd, "FINISH_CHARGING") == 0) return CMD_FINISH_CHARGING;
  return 0;  // 알 수 없는 명령
}

// 명령 문자열 변환 함수
const char* get_cmd_str(uint8_t code) {
  switch (code) {
    case CMD_ARRIVED: return "ARRIVED";
    case CMD_OBSTACLE: return "OBSTACLE";
    case CMD_STATUS_UPDATE: return "STATUS_UPDATE";
    case CMD_START_LOADING: return "START_LOADING";
    case CMD_FINISH_LOADING: return "FINISH_LOADING";
    case CMD_START_UNLOADING: return "START_UNLOADING";
    case CMD_FINISH_UNLOADING: return "FINISH_UNLOADING";
    case CMD_ASSIGN_MISSION: return "ASSIGN_MISSION";
    case CMD_ACK_GATE_OPENED: return "ACK_GATE_OPENED";
    case CMD_FINISH_CHARGING: return "FINISH_CHARGING";
    case CMD_MISSION_ASSIGNED: return "MISSION_ASSIGNED";
    case CMD_NO_MISSION: return "NO_MISSION";
    case CMD_RUN: return "RUN";
    case CMD_STOP: return "STOP";
    case CMD_GATE_OPENED: return "GATE_OPENED";
    case CMD_START_CHARGING: return "START_CHARGING";
    case CMD_CANCEL_MISSION: return "CANCEL_MISSION";
    default: return "UNKNOWN";
  }
}

// 미션 요청 메시지 (ASSIGN_MISSION)
void send_assign_mission() {
  send_binary(CMD_ASSIGN_MISSION);
}

// 게이트 열림 확인 메시지
void send_gateopen_message(const char* gate_id) {
  send_binary(CMD_ACK_GATE_OPENED, current_position.c_str(), gate_id);
}

// 도착 메시지 (ARRIVED)
void send_arrived(const char* position, const char* gate_id) {
  send_binary(CMD_ARRIVED, position, gate_id);
}

// 장애물 감지 메시지 (OBSTACLE)
void send_obstacle(float distance_cm, bool detected, const char* position) {
  if (detected == prev_obstacle_state) return;
  prev_obstacle_state = detected;
  send_binary(CMD_OBSTACLE, position);
}

// 로딩 시작 메세지
void send_start_loading() {
  send_binary(CMD_START_LOADING, current_position.c_str());
}

void send_finish_loading() 
{
  send_binary(CMD_FINISH_LOADING, current_position.c_str());
}

// 언로딩 시작 메세지
void send_start_unloading() {
  send_binary(CMD_START_UNLOADING, current_position.c_str());
  unloading_in_progress = true;
  unloading_stage = 1;
  unloading_stage_time = millis();
}

void send_finish_unloading() {
  send_binary(CMD_FINISH_UNLOADING, current_position.c_str());
  unloading_in_progress = false;
  unloading_stage = 0;
}

void send_battery_status() {
  send_binary(CMD_BATTERY);
}

/*--------------------------------라인트레이서 제어--------------------------------*/

void line_trace() {
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);

  Serial.print("L: "); Serial.print(l_sensor_val);
  Serial.print(" R: "); Serial.println(r_sensor_val);

  error = l_sensor_val - r_sensor_val;

  // ⬇ PID 제어 계산
  integral += error;
  derivative = error - last_error;
  PID_control = Kp * error + Ki * integral + Kd * derivative;

  last_error = error;

  R_PWM = speed_limit(avg_PWM - PID_control, 0, max_pwm);
  L_PWM = speed_limit(avg_PWM + PID_control, 0, max_pwm);

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
    //Serial.println("Hello");
    return false;  // 실패했으면 장애물 없음
  }
  
  distance_cm = duration * 0.034 / 2.0;  // 거리 계산
  last_distance_cm = distance_cm;  // 전역 변수 업데이트

  return distance_cm < 12.0;  // 10cm 이내면 true
}

/*--------------------------------언로딩 처리 함수--------------------------------*/

void start_unloading() {
  Serial.println("🕒 언로딩 시작 메시지 전송 (2초 지연 후)");
  send_start_unloading();
  unloading_in_progress = true;
  unloading_stage = 1;
  unloading_stage_time = millis();
}

void handle_unloading(unsigned long current_time) {
  if (!unloading_in_progress) return;

  if (unloading_stage == 1 && current_time - unloading_stage_time >= 0) {
    Serial.println("✅ 언로딩 서보모터 → 90도 (내리기)");
    unloading_servo.write(SERVO_DROP_ANGLE);
    unloading_stage_time = current_time;
    unloading_stage = 2;
  }
  else if (unloading_stage == 2 && current_time - unloading_stage_time >= 2000) {
    Serial.println("✅ 언로딩 서보모터 → 170도 (올리기)");
    unloading_servo.write(SERVO_INIT_ANGLE);
    unloading_stage_time = current_time;
    unloading_stage = 3;
  }
  else if (unloading_stage == 3 && current_time - unloading_stage_time >= 1000) {
    Serial.println("✅ 언로딩 완료 메시지 전송");
    send_finish_unloading();
    unloading_in_progress = false;
    unloading_stage = 0;
  }
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

      // 위치 갱신 및 도착 메시지 전송
      current_position = String(desc);

      if (strcmp(desc, "CHECKPOINT_A") == 0) 
      {
        send_arrived("CHECKPOINT_A", "GATE_A");
        run_command = false;
      } 
      else if (strcmp(desc, "CHECKPOINT_B") == 0) 
      {
        send_arrived("CHECKPOINT_B", "GATE_A");
      } 
      else if (strcmp(desc, "CHECKPOINT_C") == 0) 
      {
        send_arrived("CHECKPOINT_C", "GATE_B");
        run_command = false;
      } 
      else if (strcmp(desc, "CHECKPOINT_D") == 0) 
      {
        send_arrived("CHECKPOINT_D", "GATE_B");
      }
      else if (strcmp(desc, "load_A") == 0)                        //load_A
      {
        send_arrived("load_A", "LOAD_A");
        // 현재 목적지가 load_A인 경우에만 적재 시작 대기
        if ((mission_target == "LOAD_A")or(mission_target == "load_A")) 
        {
          Serial.println(mission_target);
          Serial.println("Debug1");
          wait_start_loading = true;
          wait_start_loading_time = millis();
        }
      }
      else if (strcmp(desc, "load_B") == 0)                       //load_B
      {
        send_arrived("load_B", "LOAD_B");

        if ((mission_target == "load_B") or (mission_target == "LOAD_B")) 
        {
          wait_start_loading = true;
          wait_start_loading_time = millis();
        }
      }
      else if (strcmp(desc, "BELT") == 0) 
      {
        send_arrived("BELT", "BELT");
        wait_start_unloading = true;
        wait_start_unloading_time = millis();
        
      }
      else if (strcmp(desc, "STANDBY") == 0) 
      {
        send_arrived("STANDBY", "STANDBY");
        run_command = false;
        stop_motors();
        send_assign_mission(); 
      } 

      // 🎯 목적지에 도달한 경우 멈춤
      if (mission_target != "" && mission_target == String(desc)) {
        Serial.println("🎯 [도착 확인] 목적지 도달 → 주행 중지");
        run_command = false;
        stop_motors();
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

// 하트비트 메시지 전송
void send_heartbeat() {
  if (client && client.connected()) {
    uint8_t header[4] = {
      truck_id_byte,   // sender_id
      ID_SERVER,       // receiver_id
      CMD_HELLO,       // cmd_id
      0                // payload_len (페이로드 없음)
    };
    
    client.write(header, 4);
    Serial.println("[💓 하트비트] 서버에 하트비트 메시지 전송");
  }
}

// 트럭 상태 가져오기
uint8_t get_truck_state() {
  if (battery_empty)
    return STATE_LOW_BATTERY;
  else
    return STATE_NORMAL;
}
