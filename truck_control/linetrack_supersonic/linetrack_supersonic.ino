#include <WiFi.h>
#include <ESP32Servo.h>
#include <Arduino.h>
#include <ArduinoJson.h>

// ==== WiFi 설정 ====
const char* ssid = "leesh0806";
const char* password = "1234567890!";

WiFiServer server(8000);
WiFiClient client;

String incoming_msg = "";
bool run_command = false;  // PC 명령으로 주행 여부 결정
bool obstacle_block = false;
float last_distance_cm = 0;

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

#define TRIG_PIN 33
#define ECHO_PIN 32

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

// ==== 초기화 ====
void setup() {
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

  // Wi-Fi 연결
  WiFi.begin(ssid, password);
  Serial.print("WiFi 연결 중");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] 연결됨!");
  Serial.print("[IP] ");
  Serial.println(WiFi.localIP());

  server.begin();
}

// ==== 메인 루프 ====
void loop() 
{//////////////////////////////////////////Wifi///////////////////////////////////
  Serial.println(WiFi.localIP());
  // 클라이언트 연결 처리
  if (!client || !client.connected()) {
    client = server.available();
  }

  // 클라이언트로부터 명령 수신
  if (client && client.available()) {
    incoming_msg = client.readStringUntil('\n');
    incoming_msg.trim();
    incoming_msg.toUpperCase();

    Serial.print("[TCP 수신] ");
    Serial.println(incoming_msg);

    if (incoming_msg == "RUN") {
      run_command = true;
    } else if (incoming_msg == "STOP") {
      run_command = false;
      stop_motors();
    }
  }
/////////////////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////// 주행////////////////////////////////////////////

  obstacle_block = obstacle_detected();

  if(run_command && !obstacle_block)
  {
    line_trace();
  }
  else
  {
    stop_motors();
  }
  
  if (obstacle_block) 
  {
    send_obstacle_status(last_distance_cm, true, "sectorA");
  }

  else 
  {
    send_obstacle_status(last_distance_cm, false, "sectorA");
  }
}
////////////////////////////////////////////////////////////////////////////////////////

///////////////////////////// ==== 라인트레이서 제어 ====///////////////////////////////////
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

  R_PWM = speed_limit(avg_PWM - PD_control, 0, 70);
  L_PWM = speed_limit(avg_PWM + PD_control, 0, 70);

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
////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////// 초음파 기반 장애물 감지 함수//////////////////////////////////////////
bool obstacle_detected() {
  long duration;
  float distance_cm;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH, 20000); // timeout 20ms
  if (duration == 0) return false;  // 실패했으면 장애물 없음

  distance_cm = duration * 0.034 / 2.0;  // 거리 계산
  last_distance_cm = distance_cm;  // 전역 변수 업데이트

  Serial.print("Distance: ");
  Serial.print(distance_cm);
  Serial.println(" cm");

  return distance_cm < 10.0;  // 10cm 이내면 true
}
/////////////////////////////////////////////////////////////////////////////////////////////////////

///////////////////////==전송 함수 만들기==/////////////////////////////////////////////////////////////
void send_obstacle_status(float distance_cm, bool detected, const char* position) {
  // JSON 문서 생성
  StaticJsonDocument<256> doc;

  doc["sender"] = "truck";
  doc["receiver"] = "server";
  doc["cmd"] = "obstacle";

  JsonObject payload = doc.createNestedObject("payload");
  payload["position"] = position;
  payload["distance_cm"] = distance_cm;
  payload["timestamp"] = millis();  // 또는 현재 시간
  payload["detected"] = detected;

  // JSON 직렬화 후 전송
  if (client && client.connected()) {
    serializeJson(doc, client);
    client.print("\n");  // 메시지 구분용 줄바꿈
    Serial.println("[송신] 장애물 상태 전송됨");
  }
}
///////////////////////////////////////////////////////////////////////////////////////////////////



