/*
 * 디스펜서 제어 통합 시스템
 * 
 * 기능:
 * 1. 서보모터를 이용한 디스펜서 개폐 제어
 * 2. 스테퍼모터를 이용한 방향 회전 제어
 * 3. 시리얼 통신을 통한 명령 수신 및 응답
 * 4. IR 리모컨을 통한 수동 제어
 * 5. 조이스틱 및 버튼을 통한 수동 제어
 * 
 * 명령 프로토콜:
 * - OPEN, DI_OPEN 또는 DISPENSER_DI_OPEN: 디스펜서 열기
 * - CLOSE, DI_CLOSE 또는 DISPENSER_DI_CLOSE: 디스펜서 닫기
 * - LEFT_TURN, DI_LEFT_TURN 또는 DISPENSER_DI_LEFT_TURN: 왼쪽으로 회전
 * - RIGHT_TURN, DI_RIGHT_TURN 또는 DISPENSER_DI_RIGHT_TURN: 오른쪽으로 회전
 * - STOP_TURN, DI_STOP_TURN 또는 DISPENSER_DI_STOP_TURN: 회전 정지
 * - LOC_ROUTE_A, DI_LOC_ROUTE_A 또는 DISPENSER_DI_LOC_ROUTE_A: A 경로로 이동
 * - LOC_ROUTE_B, DI_LOC_ROUTE_B 또는 DISPENSER_DI_LOC_ROUTE_B: B 경로로 이동
 * 
 * 응답 프로토콜:
 * - ACK:DI_OPENED:OK - 디스펜서 열림 명령 응답
 * - ACK:DI_CLOSED:OK - 디스펜서 닫힘 명령 응답
 * - STATUS:DISPENSER:LOADED - 적재 완료 상태 (백엔드 연동용)
 */

#include <IRremote.h>
#include <Servo.h>

//============================= 핀 정의 =============================

// 원래 코드 기준 핀 번호 복원
#define SERVO_PIN 6       // 서보모터 핀
#define IR_PIN 7          // IR 리모컨 수신기 핀
#define IN1 8             // 스텝모터 1
#define IN2 9             // 스텝모터 2 
#define IN3 10            // 스텝모터 3
#define IN4 11            // 스텝모터 4
#define SERVO_BTN 4       // 서보 버튼 
#define X_AXIS A0         // 조이스틱 X
#define Y_AXIS A1         // 조이스틱 Y
#define JOY_CLICK 2       // 조이스틱 클릭

//============================= 상수 정의 =============================

// 서보 위치 설정
#define SERVO_OPEN 10      // 디스펜서 열림 위치
#define SERVO_CLOSED 100   // 디스펜서 닫힘 위치

// 자동 닫힘 타이머 (ms)
#define AUTO_CLOSE_TIMEOUT 30000  // 30초
#define LOADING_DELAY 5000       // 적재 시뮬레이션 시간 (5초로 단축)

// IR 리모컨 버튼 코드
const unsigned long BTN_CHAD =  0xBA45FF00;
const unsigned long BTN_CHAU =  0xB847FF00;
const unsigned long BTN_CHA =   0xB946FF00;
const unsigned long BTN_PREV =  0xBB44FF00;
const unsigned long BTN_NEXT =  0xBF40FF00;
const unsigned long BTN_PLAY =  0xBC43FF00;
const unsigned long BTN_VOLD =  0xF807FF00;
const unsigned long BTN_VOLU =  0xEA15FF00;
const unsigned long BTN_EQ =    0xF609FF00;
const unsigned long BTN_ZERO =  0xE916FF00;
const unsigned long BTN_OHUND = 0xE619FF00;
const unsigned long BTN_THUND = 0xF20DFF00;
const unsigned long BTN_ONE =   0xF30CFF00;
const unsigned long BTN_TWO =   0xE718FF00;
const unsigned long BTN_THREE = 0xA15EFF00;
const unsigned long BTN_FOUR =  0xF708FF00;
const unsigned long BTN_FIVE =  0xE31CFF00;
const unsigned long BTN_SIX =   0xA55AFF00;
const unsigned long BTN_SEVEN = 0xBD42FF00;
const unsigned long BTN_EIGHT = 0xAD52FF00;
const unsigned long BTN_NINE =  0xB54AFF00;

//============================= 상태 변수 =============================

// 서보 모터 인스턴스
Servo dispenseServo;

// 디스펜서 상태 변수 (원래 코드와 호환)
int pos = 0;              // 서보 위치
int x = 0;                // 조이스틱 X 값
int y = 0;                // 조이스틱 Y 값
bool c = false;           // 조이스틱 클릭
bool open = false;        // 디스펜서 열림 상태
int btnServo = 0;         // 서보 버튼 상태
char move = 'S';          // 모터 회전 방향 (S=정지, L=왼쪽, R=오른쪽, A=A위치, B=B위치)
char lastmove = 'S';      // 마지막 이동 방향

// 스텝모터 관련 변수
int steps = 0;            // 현재 스텝 
int direction = 0;        // 모터 방향 (-1=왼쪽, 0=정지, 1=오른쪽)
unsigned long lastMoved = 0; // 마지막 이동 시간
int interval = 3;         // 스텝 간격 (ms)

// IR 리모컨 관련 변수
unsigned long lastValidCode = 0;
unsigned long lastClicked = 0;
unsigned long timer = 0;
int wait = 100;           // IR 디바운스 시간

// 명령 처리 관련
String commandBuffer = "";
boolean commandComplete = false;

// 상태 추적 및 타임스탬프
unsigned long lastCommandTime = 0;
unsigned long loadingStartTime = 0;  // 적재 시작 시간
bool isLoadingInProgress = false;    // 적재 진행 중 상태

//============================= 초기화 =============================

void setup() {
  // 시리얼 통신 초기화
  Serial.begin(9600);
  
  // 핀 모드 설정
  pinMode(SERVO_BTN, INPUT);
  pinMode(IN1, OUTPUT); 
  pinMode(IN2, OUTPUT); 
  pinMode(IN3, OUTPUT); 
  pinMode(IN4, OUTPUT); 
  pinMode(JOY_CLICK, INPUT_PULLUP);
  
  // 서보모터 초기화
  dispenseServo.attach(SERVO_PIN);
  dispenseServo.write(SERVO_CLOSED);  // 시작 시 닫힘 상태로
  
  // IR 리모컨 초기화
  IrReceiver.begin(IR_PIN, ENABLE_LED_FEEDBACK);
  Serial.println("IR 수신기 시작");
  
  // 시작 메시지
  Serial.println("STATUS:DISPENSER:READY");
  delay(1000);
}

//============================= 메인 루프 =============================

void loop() { 
  // 시리얼 명령 처리
  if (Serial.available() > 0) {
    readSerialCommand();
  }

  // 명령이 완료되었으면 처리
  if (commandComplete) {
    processCommand();
  }
  
  // 조이스틱 입력 처리
  readJoystick();

  // IR 리모컨 처리
  receiveIR();
  
  // 실제 모터 이동 처리
  moveLeftRight();
  
  // 버튼 체크 및 서보 제어
  checkServButton();
  dispense();
  
  // 적재 완료 타이머 체크 (중요: 우선적으로 처리)
  checkLoadingComplete();
  
  // 일정 시간 이후 자동 닫기 (안전장치)
  autoCloseCheck();
}

//============================= 시리얼 통신 함수 =============================

// 시리얼 명령 읽기
void readSerialCommand() {
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    
    if (inChar == '\n' || inChar == '\r') {
      if (commandBuffer.length() > 0) {
        commandComplete = true;
        return;
      }
    } else {
      commandBuffer += inChar;
    }
  }
}

// 명령 처리
void processCommand() {
  String command = commandBuffer;
  command.trim();
  
  lastCommandTime = millis();
  
  // 명령어 처리 - 모든 형태의 명령어 호환성 지원
  String cmd = command;
  
  // 1. "DISPENSER_DI_" 접두사 제거 (예: DISPENSER_DI_OPEN -> OPEN)
  if (cmd.startsWith("DISPENSER_DI_")) {
    cmd = cmd.substring(13);
  }
  // 2. "DISPENSER_" 접두사 제거 (예: DISPENSER_OPEN -> OPEN)
  else if (cmd.startsWith("DISPENSER_")) {
    cmd = cmd.substring(10);
  }
  // 3. "DI_" 접두사 제거 (예: DI_OPEN -> OPEN)
  else if (cmd.startsWith("DI_")) {
    cmd = cmd.substring(3);
  }
  
  // 명령어 대문자로 변환하여 일관성 유지
  cmd.toUpperCase();
  
  // 단축명령어 변환 (원래 코드 호환성)
  if (cmd == "A") cmd = "LEFT_TURN";
  else if (cmd == "D") cmd = "RIGHT_TURN";
  else if (cmd == "S") cmd = "STOP_TURN";
  else if (cmd == "V") cmd = "LOC_ROUTE_A";
  else if (cmd == "B") cmd = "LOC_ROUTE_B";
  else if (cmd == "W") {
    // W명령은 토글이었음
    if (open) {
      cmd = "CLOSE";
    } else {
      cmd = "OPEN";
    }
  }
  
  // 표준화된 명령어 처리
  if (cmd == "OPEN") {
    open = true;
    Serial.println("ACK:DI_OPENED:OK");
    
    // 적재 완료 프로세스 시작
    simulateLoading();
  } 
  else if (cmd == "CLOSE") {
    open = false;
    Serial.println("ACK:DI_CLOSED:OK");
  }
  else if (cmd == "LEFT_TURN") {
    move = 'L';
    Serial.println("ACK:DI_LEFT_TURN:OK");
  }
  else if (cmd == "RIGHT_TURN") {
    move = 'R';
    Serial.println("ACK:DI_RIGHT_TURN:OK");
  }
  else if (cmd == "STOP_TURN") {
    move = 'S';
    Serial.println("ACK:DI_STOP_TURN:OK");
  }
  else if (cmd == "LOC_ROUTE_A") {
    if (lastmove != 'A') {
      move = 'A';
    }
    Serial.println("ACK:DI_LOC_A:OK");
  }
  else if (cmd == "LOC_ROUTE_B") {
    if (lastmove != 'B') {
      move = 'B';
    }
    Serial.println("ACK:DI_LOC_B:OK");
  }
  else {
    Serial.println("ACK:UNKNOWN_COMMAND:ERROR");
  }
  
  // 처리 완료 후 버퍼 초기화
  commandBuffer = "";
  commandComplete = false;
}

// 적재 시뮬레이션 함수
void simulateLoading() {
  // 적재 완료 메시지 전송 프로세스 - 서버가 확인할 수 있도록 로그 추가
  Serial.println("STATUS:DISPENSER:OPENING_COMPLETE");
  Serial.println("STATUS:DISPENSER:WAITING_FOR_LOADED");
  
  // 적재 시작 시간 기록 및 상태 설정
  loadingStartTime = millis();
  isLoadingInProgress = true;
  
  // 즉시 상태 메시지 전송
  Serial.println("STATUS:DISPENSER:LOADING_STARTED");
}

// 적재 완료 체크 - 더 안정적인 메시지 전송
void checkLoadingComplete() {
  if (isLoadingInProgress) {
    unsigned long currentTime = millis();
    unsigned long elapsedTime = currentTime - loadingStartTime;
    
    // 적재 완료 시간이 되면
    if (elapsedTime >= LOADING_DELAY) {
      // 적재 완료 메시지 전송 (확실하게 전송되도록 여러 번 전송)
      Serial.println("\n"); // 버퍼 정리
      
      // 10번 반복하여 메시지 전송 신뢰성 향상
      for (int i = 0; i < 10; i++) {
        Serial.println("STATUS:DISPENSER:LOADED");
        Serial.println("STATUS:DISPENSER:LOADED_CONFIRMED");
        delay(100); // 간격 증가
      }
      
      // 적재 완료 상태로 변경
      isLoadingInProgress = false;
      Serial.println("STATUS:DISPENSER:LOADED");
      
      // 추가 백업 메시지
      delay(500);
      Serial.println("STATUS:DISPENSER:LOADED");
    }
  }
}

// 자동 닫기 전에 LOADED 메시지 한 번 더 전송
void autoCloseCheck() {
  // 열려있고, 마지막 명령 이후 설정된 시간이 지났을 때 자동으로 닫기
  if (open && (millis() - lastCommandTime > AUTO_CLOSE_TIMEOUT)) {
    // 닫기 전 한 번 더 LOADED 메시지 전송
    if (isLoadingInProgress) {
      Serial.println("STATUS:DISPENSER:LOADED");
      Serial.println("STATUS:DISPENSER:FORCE_LOADED");
      isLoadingInProgress = false;
    }
    
    open = false;
    Serial.println("STATUS:DISPENSER:AUTO_CLOSED");
  }
}

//============================= 조이스틱 제어 함수 =============================

void readJoystick() {
  // 조이스틱 읽기
  x = analogRead(X_AXIS);
  y = analogRead(Y_AXIS);
  c = !digitalRead(JOY_CLICK);  // 풀업이므로 반전
  
  // 조이스틱으로 모터 방향 제어 (필요시 활성화)
  /*
  if (x < 300) {
    move = 'L';  // 왼쪽
  } 
  else if (x > 700) {
    move = 'R';  // 오른쪽
  }
  else if (y < 300) {
    // 위 동작 (필요시 구현)
  }
  else if (y > 700) {
    // 아래 동작 (필요시 구현)
  }
  else if (400 < x && x < 600 && 400 < y && y < 600) {
    // 중앙 위치일 때
    //move = 'S';  // 정지 (필요시 활성화)
  }
  
  // 클릭 처리
  if (c) {
    // 디스펜서 열림/닫힘 토글 (필요시 활성화)
    //btnServo = 1;
  }
  */
}

//============================= IR 리모컨 함수 =============================

// IR 리모컨 수신 처리
void receiveIR() {
  unsigned long time = millis();
  timer = time - lastClicked;

  if (IrReceiver.decode()) {
    unsigned long receivedCode = IrReceiver.decodedIRData.decodedRawData;
    
    if (timer > wait) {
      if (receivedCode != 0 && receivedCode != 0xFFFFFFFF) { // 새로운 신호일 때
        lastValidCode = receivedCode;
        handleButton(receivedCode);
        lastClicked = time;
      }
    }
    IrReceiver.resume(); // 다음 신호 받을 준비
  }
}

// IR 버튼 처리
void handleButton(unsigned long code) {
  switch(code) {
    case BTN_PREV:
      if (move == 'L') {
        move = 'S';
      } else {
        move = 'L';  // 왼쪽 이동
      }
      break;
    case BTN_NEXT:
      if (move == 'R') {
        move = 'S';
      } else {
        move = 'R';  // 오른쪽 이동
      }
      break;
    case BTN_PLAY:
      btnServo = 1;  // 서보 모터 발동
      break;
    case BTN_CHAD:
      Serial.println("채널 아래로");
      break;
    case BTN_CHAU:
      Serial.println("채널 위로");
      break;
    case BTN_CHA:
      Serial.println("현재 채널");
      break;
    case BTN_VOLD:
      move = 'A';
      Serial.println("A");
      break;
    case BTN_VOLU:
      move = 'B';
      Serial.println("B");
      break;
    default:
      Serial.print("알 수 없는 버튼: 0x");
      Serial.println(code, HEX);
      break;
  }
}

//============================= 모터 제어 함수 =============================

// 좌우 이동 처리
void moveLeftRight() {
  unsigned long time = millis();
  
  // 조이스틱 입력에 따라 방향 설정 및 충분한 시간이 지났을 때만 스텝 실행
  if ((move == 'L') && (time - lastMoved > interval)) {
    direction = -1;  // 왼쪽 방향
    stepper(1);      // 한 스텝 이동
    lastMoved = time;  // 시간 업데이트
  }
  
  if ((move == 'R') && (time - lastMoved > interval)) {
    direction = 1;   // 오른쪽 방향
    stepper(1);      // 한 스텝 이동
    lastMoved = time;  // 시간 업데이트
  }

  if (move == 'A') {
    if (lastmove != 'A') {
      for(int i = 0; i < 1200; i++) {
        direction = -1;   // 왼쪽 방향
        stepper(1);       // 한 스텝 이동
        lastMoved = time; // 시간 업데이트
        delay(3);
      }
      lastmove = 'A';
      Serial.println("STATUS:DISPENSER:AT_ROUTE_A");
    }
  }

  if (move == 'B') {
    if (lastmove != 'B') {
      for(int i = 0; i < 1200; i++) {
        direction = 1;    // 오른쪽 방향
        stepper(1);       // 한 스텝 이동
        lastMoved = time; // 시간 업데이트
        delay(3);
      }
      lastmove = 'B';
      Serial.println("STATUS:DISPENSER:AT_ROUTE_B");
    }
  }
}

// 스텝모터 제어
void stepper(int xw) {
  for (int x=0; x<xw; x++) {
    switch(steps) {
      case 0:  runStep(LOW, LOW, LOW, HIGH);    break; 
      case 1:  runStep(LOW, LOW, HIGH, HIGH);   break; 
      case 2:  runStep(LOW, LOW, HIGH, LOW);    break; 
      case 3:  runStep(LOW, HIGH, HIGH, LOW);   break; 
      case 4:  runStep(LOW, HIGH, LOW, LOW);    break; 
      case 5:  runStep(HIGH, HIGH, LOW, LOW);   break; 
      case 6:  runStep(HIGH, LOW, LOW, LOW);    break; 
      case 7:  runStep(HIGH, LOW, LOW, HIGH);   break;     
      default: runStep(LOW, LOW, LOW, LOW);     break; 
    }
    SetDirection();
  }
}

// 스텝모터 핀 제어
void runStep(int value1, int value2, int value3, int value4) {
  digitalWrite(IN1, value1); 
  digitalWrite(IN2, value2);
  digitalWrite(IN3, value3);
  digitalWrite(IN4, value4);  
}

// 방향에 따른 스텝 변경
void SetDirection() {
  if(direction == 1)  steps++; 
  if(direction == -1) steps--; 
  if(steps > 7) steps = 0; 
  if(steps < 0) steps = 7; 
}

//============================= 서보 제어 함수 =============================

// 서보 버튼 체크
void checkServButton() {
  int servbtn = digitalRead(SERVO_BTN);
  
  if (servbtn == HIGH) {
    btnServo = HIGH;
  }

  if (btnServo == HIGH) {
    if (open == false) {
      open = true;
      // 적재 완료 프로세스 시작 (버튼으로 열었을 때도)
      simulateLoading();
    } else {
      open = false;
    }
    btnServo = 0; // 초기화
  }
}

// 디스펜서 개폐 제어
void dispense() {
  if (open) {
    dispenseServo.write(SERVO_OPEN);
  } else {
    dispenseServo.write(SERVO_CLOSED);
  }
}