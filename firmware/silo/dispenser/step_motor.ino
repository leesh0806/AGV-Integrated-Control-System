
// 스텝모터 조작 관련
int steps = 0;
unsigned long lastMoved = 0;  
int interval = 3;  

void moveMotor() // 모터를 실제로 움직임
{
  unsigned long time = millis();
  
  // 조이스틱 입력에 따라 방향 설정 및 충분한 시간이 지났을 때만 스텝 실행
  if ((move == 'L') && (time - lastMoved > interval)) 
  {
    direction = -1;  // 왼쪽 방향
    stepper(1);         // 한 스텝 이동
    lastMoved = time;  // 시간 업데이트
  }
  
  if ((move == 'R') && (time - lastMoved > interval)) 
  {
    direction = 1;   // 오른쪽 방향
    stepper(1);         // 한 스텝 이동
    lastMoved = time;  // 시간 업데이트
  }
}

void stepper(int xw) 
{
  for (int x=0;x<xw;x++) 
  {
    switch(steps)
    {
      case 0:  runStep(LOW, LOW, LOW, HIGH);   break; 
      case 1:  runStep(LOW, LOW, HIGH, HIGH);   break; 
      case 2:  runStep(LOW, LOW, HIGH, LOW);   break; 
      case 3:  runStep(LOW, HIGH, HIGH, LOW);   break; 
      case 4:  runStep(LOW, HIGH, LOW, LOW);   break; 
      case 5:  runStep(HIGH, HIGH, LOW, LOW);   break; 
      case 6:  runStep(HIGH, LOW, LOW, LOW);   break; 
      case 7:  runStep(HIGH, LOW, LOW, HIGH);   break;     
      default:  runStep(LOW, LOW, LOW, LOW);   break; 
    }
    SetDirection();
  }
}

void runStep(int value1, int value2, int value3, int value4)
{
  digitalWrite(IN1, value1); 
  digitalWrite(IN2, value2);
  digitalWrite(IN3, value3);
  digitalWrite(IN4, value4);  
}

void SetDirection()
{
  if(direction == 1)  steps++; 
  if(direction == -1)  steps--; 
  if(steps > 7)  steps = 0; 
  if(steps < 0)  steps = 7; 
}

void debug() // 현재 상황 Serial 로 표시
{
  unsigned long time = millis();
  if (time % 1000 == 0) {  // 100ms마다 출력
    Serial.print(x);
    Serial.print(", ");
    Serial.print(y);
    Serial.print("\t");
    Serial.println(steps);
  }
}

void checkServButton()
{
  int servbtn = digitalRead(SERBTN);
  
  if (servbtn == HIGH)
  {
    btnServo = HIGH;
  }

  if (btnServo == HIGH)
  {
    if (open == false)
    {
      open = true;
    }
    else
    {
      open = false;
    }
  }

  btnServo = 0; // 초기화
}

void dispense()
{
  if (open)
  {
    servo.write(10);
  }
  else
  {
    servo.write(100);
  }
}