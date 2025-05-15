#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <time.h>

//트럭 - > server 명령어
#define ARRIVED          0x01
#define OBSTACLE         0x02
#define STATUS_UPDATE    0x03
#define START_LOADING    0x04
#define FINISH_LOADING   0x05
#define START_UNLOADING  0x06
#define FINISH_UNLOADING 0x07
#define ASSIGN_MISSION   0x08
#define ACK_GATE_OPENED  0x09
#define FINISH_CHARGING  0x0A

//SERVER → 트럭 명령어
#define MISSION_ASSIGNED  0x10
#define NO_MISSION        0x11
#define RUN               0x12
#define STOP              0x13
#define GATE_OPENED       0x14
#define START_CHARGING    0x15

//상수 정의 
#define SERVER   0x10
#define TRUCK_01 0x01
#define TRUCK_02 0x02
#define TRUCK_03 0x03

//position
#define CHECKPOINT_A 0x01
#define CHECKPOINT_B 0x02
#define CHECKPOINT_C 0x03
#define CHECKPOINT_D 0x04
#define LOAD_A       0x05
#define LOAD_B       0x06
#define BELT         0x07
#define STANDBY      0x08

// 게이트 ID
#define GATE_A       0xA1
#define GATE_B       0xA2

/*--------------------------------WiFi 설정--------------------------------*/

const char* ssid = "addinedu_class_2 (2.4G)";
//const char* ssid = "base";
const char* password = "addinedu1";
//const char* password = "base6666";

/*--------------------------------PC 서버 주소 및 포트--------------------------------*/

IPAddress serverIP(192, 168, 0, 166);  // ← PC IP로 바꾸세요
const int serverPort = 8001;  
WiFiClient client;

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
  { {0xD9, 0x3F, 0x09, 0x05}, "LOAD_A" },
  { {0xA3, 0x8F, 0x09, 0x05}, "LOAD_B" },
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

uint8_t get_sender_id_from_truck_id(const char* id) {
  if (strcmp(id, "TRUCK_01") == 0) return 0x01;
  if (strcmp(id, "TRUCK_02") == 0) return 0x02;
  if (strcmp(id, "TRUCK_03") == 0) return 0x03;
  return 0xFF;  // 알 수 없는 경우
}

/*-------------------------상태 로직 변환 및 기타 변수들--------------------------------*/

bool run_command = false;
bool obstacle_block = false;   //지금 멈춰야 하나?(실시간 결정용)
bool prev_obstacle_state = false;
float last_distance_cm = 0;

String current_position = "UNKNOWN";
uint8_t current_position_id = 0xFF;  // UNKNOWN
String last_cmd = "";
uint8_t mission_target = 0xFF;  // 0xFF = 미할당 상태
bool mission_requested = false;
unsigned long last_mission_check = 0;    // 마지막 미션 체크 시간
const unsigned long MISSION_CHECK_INTERVAL = 2000;  // 5초마다 체크


bool initial_delay_done = false;  //초기 출발
unsigned long system_start_time = 0; //초기 출발

uint8_t get_position_id(const String& desc) 
{
  if (desc == "CHECKPOINT_A") return CHECKPOINT_A;
  if (desc == "CHECKPOINT_B") return CHECKPOINT_B;
  if (desc == "CHECKPOINT_C") return CHECKPOINT_C;
  if (desc == "CHECKPOINT_D") return CHECKPOINT_D;
  if (desc == "LOAD_A") return LOAD_A;
  if (desc == "LOAD_B") return LOAD_B;
  if (desc == "BELT") return BELT;
  if (desc == "STANDBY") return STANDBY;
  return 0xFF;
}

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
const int SERVO_PIN = 5;
const int SERVO_INIT_ANGLE = 0;
const int SERVO_DROP_ANGLE = 70;

unsigned long belt_arrival_time = 0;
bool belt_waiting_to_unload = false;

/*--------------------------------가상 배터리 잔량 체크--------------------------------*/

int battery_level = 100;

unsigned long last_battery_drop = 0;
const unsigned long BATTERY_DROP_INTERVAL = 5000; //5초 마다 배터리 감소 

unsigned long last_battery_report = 0;
const unsigned long STATUS_REPORT_INTERVAL = 10000; // 10초마다 배터리 상태 서버에 전송
bool battery_empty = false;  // 배터리 0% 상태 플래그


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
#define LLEFT_SENSOR 36
#define RRIGHT_SENSOR 4

/*--------------------------------PID 제어 변수--------------------------------*/

double Kp = 0.1025;
double Kd = 0.2;
//double Ki = 0.00005;       
//double integral = 0.0;  // 누적 적분값
//const double integral_max = 500.0;
double PID_control;
int last_error = 0;
int derivative;
int L_PWM, R_PWM;
int prev_l_pwm, prev_r_pwm;
int error;
int l_sensor_val;
int r_sensor_val;
int ll_sensor_val;
int rr_sensor_val;
int avg_PWM = 170;
int max_pwm = 220;


/*--------------------------------rfid 객체 생성--------------------------------*/

MFRC522 rfid(SS_PIN, RST_PIN);

/*--------------------------------함수 선언--------------------------------*/

void send_obstacle(uint8_t position_id, bool detected, uint16_t distance_cm); 
void send_arrived(uint8_t position_id, uint8_t gate_id);
bool isSameUID(byte* uid1, byte* uid2);
bool checkAndPrintUID(byte* uid);

/*--------------------------------------------------------------------------------*/

bool resume_with_prev_pwm = false;
unsigned long resume_start_time = 0;
const unsigned long RESUME_DURATION = 500;

/*-------------------------------------------------------------------------------*/

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
  while (WiFi.status() != WL_CONNECTED) 
  {
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


  // 미션 요청 자동 전송
  delay(2000);  // 안정화 대기
  send_assign_mission();
  // ✅ 시작 위치를 STANDBY로 설정
  current_position = "STANDBY";
  current_position_id = STANDBY;
  Serial.println("🟢 초기 위치 상태: STANDBY");
  system_start_time = millis();  // 시스템 부팅 기준 시각 저장

}

void loop() 
{
  reconnectToServer();
  // ✅ 서버로부터 수신 메시지 처리
  if (client && client.available() >= 4) 
  {
    static uint8_t buffer[16];
    int len = client.readBytes(buffer, sizeof(buffer));  // 프레임 길이 기준 수신
    if (len >= 4) 
    {
      receive_binary(buffer, len);
    }
  }
  // ✅ 현재 시간 갱신
  unsigned long current_time = millis();

  // ✅ 주기적인 미션 체크
  if (current_time - last_mission_check >= 2000) 
  {
    last_mission_check = current_time;
    if (!mission_requested && (mission_target == 0x00 || mission_target == 0xFF) && (current_position_id == 0x00 || current_position_id == STANDBY) )  
    {
      // Serial.println("[🔄 미션 체크] 새로운 미션 확인 중...");
      send_assign_mission();
      mission_requested = false;  // ✅ 중복 요청 방지
    }
  }

  // ✅ 최초 1회 지연 처리 (1초)
  if (!initial_delay_done && (current_time - system_start_time < 1000)) 
  {
    // Serial.printf("⏳ 시스템 부팅 후 대기 중... %.0fms 남음\n", 1000.0 - (current_time - system_start_time));
    return;  // 아직 1초 안 지났으므로 아무 작업도 하지 않음
  }
  initial_delay_done = true;  // 이후부터는 바로 동작

  // ✅ 주행 제어
  obstacle_block = obstacle_detected();
  if (run_command && !obstacle_block && !battery_empty)
  {
    if (resume_with_prev_pwm) {
      if (current_time - resume_start_time < RESUME_DURATION) {
        // Serial.println("↩️ [RFID 인식] 이전 PWM 값으로 주행 중...");
        left_motor_f(prev_l_pwm);
        right_motor_f(prev_r_pwm);
      } else {
        resume_with_prev_pwm = false;
        line_trace();
      }
    } else {
      line_trace();
    }
  }
  else if (obstacle_block) 
  {
    // Serial.println("🛑 장애물 감지로 정지");
    stop_motors();
    send_obstacle(current_position_id, true, (uint16_t)last_distance_cm);
    //integral = 0;
  }
    // ✅RFID 체크 (쿨타임 1초 적용)
  if (current_time - last_rfid_check >= 1000)  // 1초 쿨타임
  {
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) 
    {
      if (checkAndPrintUID(rfid.uid.uidByte)) {
        last_rfid_check = current_time;  // 인식 성공 시만 갱신
      }
      rfid.PICC_HaltA();
      rfid.PCD_StopCrypto1();
    }
  }
  // ✅ 배터리 감소 처리 (STANDBY에서는 감소 안 함)
  if (current_time - last_battery_drop >= BATTERY_DROP_INTERVAL) 
  {
    last_battery_drop = current_time;

    // STANDBY일 때는 배터리 유지
    if (current_position_id != STANDBY && battery_level > 0) 
    {
      battery_level -= 5;
      if (battery_level <= 0) 
      {
        battery_level = 0;
        battery_empty = true;
        run_command = false;
        prev_l_pwm = L_PWM;
        prev_r_pwm = R_PWM;
        stop_motors();
        // Serial.println("❌ 배터리 소진 → 트럭 정지");
      }
      // Serial.print("🪫 배터리 감소됨: ");
      // Serial.print(battery_level);
      // Serial.println("%");
    }
  }

  // ✅ 상태 전송 (STATUS_UPDATE)
  if (current_time - last_battery_report >= STATUS_REPORT_INTERVAL) 
  {
    last_battery_report = current_time;
    send_status_update(battery_level, current_position_id);
  }

}

/*------------------------------- 수신 처리--------------------------------*/

void receive_binary(const uint8_t* buffer, uint8_t len) {
  if (len < 4) return;  // 최소한의 헤더 길이 확인

  uint8_t sender_id = buffer[0];
  uint8_t receiver_id = buffer[1];
  uint8_t cmd_id = buffer[2];
  uint8_t payload_len = buffer[3];
  const uint8_t* payload = &buffer[4];

  if (receiver_id != get_sender_id_from_truck_id(truck_id)) {
    // Serial.println("[❌ 수신 무시] 나에게 온 메시지가 아님");
    return;
  }
  switch (cmd_id) {
    case MISSION_ASSIGNED:
      if (payload_len >= 1) {
        uint8_t new_mission = payload[0];

        if (battery_level <= 30) 
        {
          // Serial.printf("⚡ [배터리 부족: %d%%] 미션 거절하고 충전 시작\n", battery_level);
          mission_target = 0;
          run_command = false;
          prev_l_pwm = L_PWM;
          prev_r_pwm = R_PWM;
        } else 
        {
          mission_target = new_mission;
          run_command = true;
          mission_requested = true;
          // Serial.printf("📝 [미션 수락] 목표 위치 ID: 0x%02X\n", mission_target);
        }
      }
      break;

    case NO_MISSION:
      mission_target = 0;
      run_command = false;
      prev_l_pwm = L_PWM;
      prev_r_pwm = R_PWM;
      // Serial.println("📭 [미션 없음] 대기 상태 유지");
      break;

    case RUN:
      run_command = true;
      // Serial.println("🏃‍♂️ [명령] 주행 시작");
      break;

    case STOP:
      run_command = false;
      prev_l_pwm = L_PWM;
      prev_r_pwm = R_PWM;
      stop_motors();
      // Serial.println("🛑 [명령] 주행 정지");
      break;

    case GATE_OPENED:
      if (payload_len >= 1) {
        uint8_t gate_id = payload[0];
        //Serial.printf("🚪 [게이트 열림 감지] gate_id: %02X\n", gate_id);
        run_command = true;
      }
      break;

    case START_LOADING:
      if (current_position_id == LOAD_A || current_position_id == LOAD_B) 
      {
        Serial.println("📥 loading");
        // 아무 행동 안 함
      }
      break;
    
    case FINISH_LOADING:
      if (current_position_id == LOAD_A || current_position_id == LOAD_B) {
        Serial.println("📥 [서버 명령] FINISH_LOADING 수신 → 주행 재개");
        if (mission_target == current_position_id) {
          mission_target = 0;
        }
        run_command = true;

      }
      break;

    case START_CHARGING:
      battery_level = 100;
      battery_empty = false;
      // Serial.println("🔋 [충전 완료] 배터리 100% 복구");
      send_finish_charging(battery_level);
      //delay(500); // 약간의 간격 후 미션 요청
      //Serial.println("📨 [충전 완료 후] 미션 재요청");
      //send_assign_mission();
      mission_target = 0;
      mission_requested = false;
      break;

    default:
      // Serial.printf("⚠️ [알 수 없는 명령] cmd_id: %02X\n", cmd_id);
      break;
  }
}

/*-------------------------------- 송신 처리 --------------------------------*/
//공통 바이너리 송신 함수
void send_binary(uint8_t cmd_id, const uint8_t* payload, uint8_t payload_len) 
{
  uint8_t buffer[16];
  uint8_t sender_id = get_sender_id_from_truck_id(truck_id);  // 예: TRUCK_01 → 0x01
  const uint8_t receiver_id = SERVER;  // 0x10

  buffer[0] = sender_id;
  buffer[1] = receiver_id;
  buffer[2] = cmd_id;
  buffer[3] = payload_len;

  for (uint8_t i = 0; i < payload_len; ++i) 
  {
    buffer[4 + i] = payload[i];
  }

  if (client && client.connected()) 
  {
    client.write(buffer, 4 + payload_len);
    // Serial.printf("[📤 Binary] CMD %02X → SERVER: ", cmd_id);
    for (int i = 0; i < 4 + payload_len; i++)
    {
      // Serial.printf("%02X ", buffer[i]);
    }
    // Serial.println();
  }
}
//도착 메시지 (ARRIVED)
void send_arrived(uint8_t position_id, uint8_t gate_id) 
{
  uint8_t payload[2] = { position_id, gate_id };
  send_binary(ARRIVED, payload, 2);
}

//장애물 메시지 (OBSTACLE)
void send_obstacle(uint8_t position_id, bool detected, uint16_t distance_cm) 
{
  if (detected == prev_obstacle_state) return;
  prev_obstacle_state = detected;

  uint8_t payload[4] = 
  {
    position_id,
    detected ? 0x01 : 0x00,
    (distance_cm >> 8) & 0xFF,
    distance_cm & 0xFF
  };
  send_binary(OBSTACLE, payload, 4);
}

//상태 메시지 (STATUS_UPDATE: 배터리 + 위치)
void send_status_update(uint8_t battery_level, uint8_t position_id) 
{
  uint8_t payload[2] = { battery_level, position_id };
  send_binary(STATUS_UPDATE, payload, 2);
}

//언로딩 메시지
void send_start_unloading(uint8_t position_id) 
{
  uint8_t payload[1] = { position_id };
  send_binary(START_UNLOADING, payload, 1);
}

void send_finish_unloading(uint8_t position_id) 
{
  uint8_t payload[1] = { position_id };
  send_binary(FINISH_UNLOADING, payload, 1);
}

//미션 요청 (ASSIGN_MISSION)
void send_assign_mission() 
{
  send_binary(ASSIGN_MISSION, nullptr, 0);  // payload 없음
}

//게이트 열림 응답 (ACK_GATE_OPENED)
void send_gate_opened_ack(uint8_t gate_id, uint8_t position_id) 
{
  uint8_t payload[2] = { gate_id, position_id };
  send_binary(ACK_GATE_OPENED, payload, 2);
}

//충전 완료 보고 (FINISH_CHARGING)
void send_finish_charging(uint8_t battery_level) 
{
  uint8_t payload[1] = { battery_level };
  send_binary(FINISH_CHARGING, payload, 1);
}

/*--------------------------------라인트레이서 제어--------------------------------*/

void line_trace() {
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);
  ll_sensor_val = analogRead(LLEFT_SENSOR);
  rr_sensor_val = analogRead(RRIGHT_SENSOR);

  //Serial.print("L: "); Serial.print(l_sensor_val);
  //Serial.print(" R: "); Serial.println(r_sensor_val);

  error = (4 * ll_sensor_val) + (1 * l_sensor_val) + (-1 * r_sensor_val) + (-4 * rr_sensor_val);
  // ⬇ PID 제어 계산
  derivative = error - last_error;
  PID_control = Kp * error + Kd * derivative;

  last_error = error;

  R_PWM = speed_limit(avg_PWM - PID_control, 0, max_pwm);
  L_PWM = speed_limit(avg_PWM + PID_control, 0, max_pwm);

  left_motor_f(L_PWM);
  right_motor_f(R_PWM);
}

void stop_motors() 
{
  ledcWrite(PWM_CHANNEL_LEFT, 0);
  ledcWrite(PWM_CHANNEL_RIGHT, 0);
}
void left_motor_f(int pwm_val) 
{
  digitalWrite(MOTOR1_IN1, LOW);
  digitalWrite(MOTOR1_IN2, HIGH);
  ledcWrite(PWM_CHANNEL_LEFT, pwm_val);
}
void right_motor_f(int pwm_val) 
{
  digitalWrite(MOTOR2_IN3, LOW);
  digitalWrite(MOTOR2_IN4, HIGH);
  ledcWrite(PWM_CHANNEL_RIGHT, pwm_val);
}
int speed_limit(int val, int minVal, int maxVal) 
{
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

  return distance_cm < 12.0;  // 12cm 이내면 true
}
/*--------------------------------언로딩 처리 함수--------------------------------*/

void start_unloading() 
{
  Serial.println("🕒 언로딩 시작 메시지 전송 및 동작 시작");
  send_start_unloading(current_position_id);
  unloading_in_progress = true;
  unloading_stage = 1;
  unloading_stage_time = millis();
}

// void handle_unloading(unsigned long current_time) 
// {
//   if (!unloading_in_progress) return;

//   if (unloading_stage == 1 && current_time - unloading_stage_time >= 0) 
//   {
//     Serial.println("✅ 언로딩 서보모터 → 70도 (내리기)");
//     unloading_servo.write(SERVO_DROP_ANGLE);
//     unloading_stage_time = current_time;
//     unloading_stage = 2;
//     Serial.println("servo_error1");
//   } 
//   else if (unloading_stage == 2 && current_time - unloading_stage_time >= 2000) 
//   {
//     Serial.println("✅ 언로딩 서보모터 → 0도 (올리기)");
//     unloading_servo.write(SERVO_INIT_ANGLE);
//     unloading_stage_time = current_time;
//     unloading_stage = 3;
//     Serial.println("servo_error2");
//   } 
//   else if (unloading_stage == 3 && current_time - unloading_stage_time >= 1000) 
//   {
//     Serial.println("✅ 언로딩 완료 메시지 전송");
//     send_finish_unloading(current_position_id);
//     unloading_in_progress = false;
//     unloading_stage = 0;
//     Serial.println("servo_error3");
//   }
//   else
//   {
//     Serial.println("servo_error4");
//   }
// }

void handle_unloading() 
{
  unsigned long current_time = millis();

  Serial.println("🕒 언로딩 시작");

  // ✅ 1. 언로딩 시작 메시지 전송
  send_start_unloading(current_position_id);
  delay(100);  // 약간의 네트워크 전송 안정화 대기 (선택적)

  // ✅ 2. 서보모터 70도 내리기
  Serial.println("✅ 언로딩 서보모터 → 70도 (내리기)");
  unloading_servo.write(SERVO_DROP_ANGLE);
  delay(2000);  // 2초 기다림

  // ✅ 3. 서보모터 0도 올리기
  Serial.println("✅ 언로딩 서보모터 → 0도 (올리기)");
  unloading_servo.write(SERVO_INIT_ANGLE);
  delay(1000);  // 1초 기다림

  // ✅ 4. 언로딩 완료 메시지 전송
  Serial.println("✅ 언로딩 완료 메시지 전송");
  send_finish_unloading(current_position_id);

  Serial.println("✅ 언로딩 종료");
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

// ⬇ checkAndPrintUID 내부 수정
bool checkAndPrintUID(byte* uid) {
  for (int i = 0; i < numRegistered; i++) {
    if (isSameUID(uid, registeredCards[i].uid)) {
      const char* desc = registeredCards[i].description;
      Serial.println("✅ 등록된 카드입니다!");
      Serial.print("📌 ");
      Serial.println(desc);

      current_position = String(desc);
      uint8_t pos_id = get_position_id(desc);
      current_position_id = pos_id;

      // ✅ RFID 인식 시 PID 제어 임시 보류
      prev_l_pwm = L_PWM;
      prev_r_pwm = R_PWM;
      resume_with_prev_pwm = true;
      resume_start_time = millis();

      if (pos_id == CHECKPOINT_A) 
      {
        send_arrived(CHECKPOINT_A, GATE_A);
        run_command = false;
      } 
      else if (pos_id == CHECKPOINT_B) 
      {
        send_arrived(CHECKPOINT_B, GATE_A);
      } 
      else if (pos_id == CHECKPOINT_C) 
      {
        send_arrived(CHECKPOINT_C, GATE_B);
        run_command = false;
      } 
      else if (pos_id == CHECKPOINT_D) 
      {
        send_arrived(CHECKPOINT_D, GATE_B);
      } 
      else if (pos_id == LOAD_A) 
      {
        send_arrived(LOAD_A, GATE_A);
        if (mission_target == pos_id) 
        {
          run_command = false;
          stop_motors();  // 도착지일 경우에만 멈춤
        }
      }
      else if (pos_id == LOAD_B) 
      {
        send_arrived(LOAD_B, GATE_B);
        if (mission_target == pos_id) 
        {
          run_command = false;
          stop_motors();
        }
      }
      else if (pos_id == BELT) 
      {
        send_arrived(BELT, 0x00);
        handle_unloading();  // 한 번에 언로딩 전체 수행
      }
      else if (pos_id == STANDBY) 
      {
        send_arrived(STANDBY, 0x00);
        run_command = false;
        stop_motors();
        if (mission_target == 0 || mission_target == 0xFF) 
        {
          // Serial.println("📨 [STANDBY] 미션 없음 → 요청");
          send_assign_mission();
        }
      }
      if (mission_target == pos_id) {
        // Serial.println("🎯 [도착 확인] 목적지 도달 → 주행 정지");
        run_command = false;
        stop_motors();
      }

      return true;
    }
  }
  // Serial.println("❌ 등록되지 않은 카드입니다!");
  return false;
}

/*-------------------------------유틸 함수--------------------------------*/

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