g#include <Servo.h>

#define GATE_SERVO_PIN 9

Servo gateServo;
bool isOpen = false;

void setup() {
  Serial.begin(9600);
  gateServo.attach(GATE_SERVO_PIN);
  closeGate();  // 초기 상태 닫힘
  Serial.println("🚦 Gate Controller Ready (Test Mode)");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "GATE_A_OPEN") {
      openGate();
      Serial.println("GATE_A_OPENED");
    } else if (cmd == "GATE_A_CLOSE") {
      closeGate();
      Serial.println("GATE_A_CLOSED");
    } else if (cmd == "GATE_B_OPEN") {
      openGate();
      Serial.println("GATE_B_OPENED");
    } else if (cmd == "GATE_B_CLOSE") {
      closeGate();
      Serial.println("GATE_B_CLOSED");
    } else {
      Serial.print("❓ Unknown Command: ");
      Serial.println(cmd);
    }
  }
}

void openGate() {
  gateServo.write(90);  // 열림 위치
  Serial.println("🔓 게이트 열림");
  isOpen = true;
}

void closeGate() {
  gateServo.write(0);  // 닫힘 위치
  Serial.println("🔒 게이트 닫힘");
  isOpen = false;
}
