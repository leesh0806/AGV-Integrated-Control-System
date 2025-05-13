#include <Servo.h>

#define GATE_A 9
#define GATE_B 8

Servo gateServo_A;
Servo gateServo_B;

bool AisOpen = false;
bool BisOpen = false;


void openGate_A() 
{
  Serial.println("ACK:GATE_A_OPEN:OK");  // 먼저 ACK를 보내고 작업 수행
  gateServo_A.write(90);  // 열림 위치
  delay(700);  // 게이트가 열리는데 필요한 시간 (700ms)
  Serial.println("STATUS:GATE_A:OPENED");
  Serial.println("ACK:GATE_A_OPENED");  // 형식 통일: _OPENED
  AisOpen = true;
}

void closeGate_A() 
{
  Serial.println("ACK:GATE_A_CLOSE:OK");  // 먼저 ACK를 보내고 작업 수행
  gateServo_A.write(5);  // 닫힘 위치
  delay(700);  // 게이트가 닫히는데 필요한 시간 (700ms)
  Serial.println("STATUS:GATE_A:CLOSED");
  Serial.println("ACK:GATE_A_CLOSED");  // 형식 통일: _CLOSED
  AisOpen = false;
}

void openGate_B() 
{
  Serial.println("ACK:GATE_B_OPEN:OK");  // 먼저 ACK를 보내고 작업 수행
  gateServo_B.write(90);  // 열림 위치
  delay(700);  // 게이트가 열리는데 필요한 시간 (700ms)
  Serial.println("STATUS:GATE_B:OPENED");
  Serial.println("ACK:GATE_B_OPENED");  // 형식 통일: _OPENED
  BisOpen = true;
}

void closeGate_B() 
{
  Serial.println("ACK:GATE_B_CLOSE:OK");  // 먼저 ACK를 보내고 작업 수행
  gateServo_B.write(5);  // 닫힘 위치
  delay(700);  // 게이트가 닫히는데 필요한 시간 (700ms)
  Serial.println("STATUS:GATE_B:CLOSED");
  Serial.println("ACK:GATE_B_CLOSED");  // 형식 통일: _CLOSED
  BisOpen = false;
}


void setup() 
{
  Serial.begin(9600);
  gateServo_A.attach(GATE_A);
  gateServo_B.attach(GATE_B);
  
  // 초기화 지연
  delay(1000);  // 초기화 대기 1초
  
  closeGate_A();  // 초기 상태 닫힘
  closeGate_B();  // 초기 상태 닫힘
  
  Serial.println("STATUS:SYSTEM:READY");
  
  // 초기 게이트 상태 알림
  Serial.println("STATUS:GATE_A:CLOSED");
  Serial.println("STATUS:GATE_B:CLOSED");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // 메인 명령 처리
    if (cmd == "GATE_A_OPEN") {
      openGate_A();
    } else if (cmd == "GATE_A_CLOSE") {
      closeGate_A();
    } else if (cmd == "GATE_B_OPEN") {
      openGate_B();
    } else if (cmd == "GATE_B_CLOSE") {
      closeGate_B();
    } else if (cmd == "STATUS") {
      // 현재 게이트 상태 보고
      Serial.print("STATUS:GATE_A:");
      Serial.println(AisOpen ? "OPENED" : "CLOSED");
      Serial.print("STATUS:GATE_B:");
      Serial.println(BisOpen ? "OPENED" : "CLOSED");
    } else {
      Serial.print("ACK:");
      Serial.print(cmd);
      Serial.println(":ERROR");
    }
  }
  
  // 주기적인 상태 업데이트 (1초마다)
  static unsigned long lastStatusTime = 0;
  if (millis() - lastStatusTime > 10000) {  // 10초마다 상태 보고
    lastStatusTime = millis();
    
    // 현재 게이트 상태 주기적 보고
    Serial.print("STATUS:GATE_A:");
    Serial.println(AisOpen ? "OPENED" : "CLOSED");
    Serial.print("STATUS:GATE_B:");
    Serial.println(BisOpen ? "OPENED" : "CLOSED");
  }
}