void setup() {
  pinMode(2, OUTPUT);  // 보드에 따라 2번이 내장 LED일 수 있음
}

void loop() {
  digitalWrite(2, HIGH);
  delay(500);
  digitalWrite(2, LOW);
  delay(500);
}