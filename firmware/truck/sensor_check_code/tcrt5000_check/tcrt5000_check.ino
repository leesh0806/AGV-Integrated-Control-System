const int sensorPin0 = 36;    // 왼쪽 끝 센서
const int sensorPin1 = 34;   // 왼쪽 중간 센서
const int sensorPin2 = 35;   // 오른쪽 중간 센서
const int sensorPin3 = 4;    // 오른쪽 끝 센서

const int ledPin = 2;        // 상태 확인용 LED

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(115200);
}

void loop() {
  int val0 = analogRead(sensorPin0);  // 왼쪽 끝
  int val1 = analogRead(sensorPin1);  // 왼쪽 중간
  int val2 = analogRead(sensorPin2);  // 오른쪽 중간
  int val3 = analogRead(sensorPin3);  // 오른쪽 끝

  Serial.print("S0: "); Serial.print(val0);
  Serial.print(" | S1: "); Serial.print(val1);
  Serial.print(" | S2: "); Serial.print(val2);
  Serial.print(" | S3: "); Serial.println(val3);

  // 어떤 센서라도 검은색 라인을 감지하면 LED ON
  if (val0 < 500 || val1 < 500 || val2 < 500 || val3 < 500) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }

  // delay(100); // 필요시 활성화
}
