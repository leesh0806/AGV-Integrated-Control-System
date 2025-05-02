// 모터 제어 핀 정의 및 PWM 채널 설정
#define MOTOR12_EN 27    // PWM 채널 0
#define MOTOR34_EN 13    // PWM 채널 1
#define MOTOR1_IN1 26
#define MOTOR1_IN2 25
#define MOTOR2_IN3 12
#define MOTOR2_IN4 14

// 적외선 센서 핀
#define LEFT_SENSOR 34
#define RIGHT_SENSOR 35

// PWM 설정
#define PWM_FREQ 1000
#define PWM_RESOLUTION 8  // 8bit → 0~255
#define PWM_CHANNEL_LEFT 0
#define PWM_CHANNEL_RIGHT 1

// PID 계수 및 변수
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

bool run = true;


void setup() {
  Serial.begin(115200);

  // 모터 방향 핀 설정
  pinMode(MOTOR1_IN1, OUTPUT);
  pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT);
  pinMode(MOTOR2_IN4, OUTPUT);

  // PWM 채널 설정
  ledcSetup(PWM_CHANNEL_LEFT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR12_EN, PWM_CHANNEL_LEFT);

  ledcSetup(PWM_CHANNEL_RIGHT, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(MOTOR34_EN, PWM_CHANNEL_RIGHT);

  delay(5000);  // 초기 지연
}

void loop() {
  if (run)
  {
    line_trace();
  }
  else
  {
    stop();
  }


  line_trace();  // 주행 함수 호출
  




  // 이후 여기에 다양한 이벤트 조건 추가 가능
  // if (obstacle_detected()) { stop(); }
  // if (rfid_detected()) { handle_rfid(); }
}

// 라인트레이서 주행 함수
void line_trace() {
  // 적외선 센서 읽기
  l_sensor_val = analogRead(LEFT_SENSOR);
  r_sensor_val = analogRead(RIGHT_SENSOR);

  Serial.print("L: ");
  Serial.print(l_sensor_val);
  Serial.print(" R: ");
  Serial.println(r_sensor_val);

  // PID 계산
  error = l_sensor_val - r_sensor_val;
  PD_control = error * Kp;

  derivative = error - last_error;
  PD_control += Kd * derivative;
  last_error = error;

  R_PWM = speed_limit(avg_PWM - PD_control, 0, 70);
  L_PWM = speed_limit(avg_PWM + PD_control, 0, 70);

  // 모터 실행
  left_motor_f(L_PWM);
  right_motor_f(R_PWM);
}

// 기타 함수 그대로 유지
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
