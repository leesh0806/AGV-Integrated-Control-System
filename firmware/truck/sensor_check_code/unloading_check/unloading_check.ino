#include <ESP32Servo.h>

Servo myServo;
int servoPin = 5;
int currentAngle = 0;  // 초기 서보 위치를 90도로 설정

void setup() {
  Serial.begin(115200);
  myServo.attach(servoPin);
  myServo.write(currentAngle);  // 초기 위치 설정
  Serial.println("서보 제어 시작 (0~180 입력)");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.length() > 0) {
      int targetAngle = input.toInt();

      if (targetAngle >= 0 && targetAngle <= 180) {
        Serial.print("서보 각도 이동: ");
        Serial.print(currentAngle);
        Serial.print(" → ");
        Serial.println(targetAngle);

        // 10도씩 천천히 이동
        while (currentAngle != targetAngle) {
          if (currentAngle < targetAngle) {
            currentAngle += 10;
            if (currentAngle > targetAngle) currentAngle = targetAngle;
          } else {
            currentAngle -= 10;
            if (currentAngle < targetAngle) currentAngle = targetAngle;
          }

          myServo.write(currentAngle);
          delay(10);  // 이동 속도 조절 (200ms 간격)
        }

        Serial.println("✅ 이동 완료");
      } else {
        Serial.println("⚠️ 유효한 각도를 입력하세요 (0~180)");
      }
    }
  }
}
