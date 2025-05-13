#include <IRremote.h>
#include <Servo.h>

#define SERBTN  4  // 서보버튼
#define IR   7  // IR리모컨
#define IN1  8  // 스텝모터
#define IN2  9  // 스텝모터
#define IN3  10 // 스텝모터
#define IN4  11 // 스텝모터
#define X_AX A0 // 조이스틱
#define Y_AX A1 // 조이스틱
#define CLK  2  // 조이스틱(클릭)

Servo servo;

int pos = 0;
int x = 0;
int y = 0;
bool c = false;
bool open = false;
int btnServo = 0;
char move = 'S'; // 회전 방향을 결정함

int direction = 0; // 스텝모터 내부 로직의 왼쪽 = -1 | 정지 = 0 | 오른쪽 = 1 

void setup()
{
  Serial.begin(9600);
  pinMode(SERBTN, INPUT);
  pinMode(IN1, OUTPUT); 
  pinMode(IN2, OUTPUT); 
  pinMode(IN3, OUTPUT); 
  pinMode(IN4, OUTPUT); 
  pinMode(CLK, INPUT_PULLUP);
  servo.attach(6);

  IrReceiver.begin(IR, ENABLE_LED_FEEDBACK); // LED 피드백 활성화
  Serial.println("IR 수신기 시작");
}

void loop()
{ 
  receiveIR();
  moveMotor();

  checkServButton();
  dispense();

  if (Serial.available()) 
  {
    readCommand();
  }
  debug(); // 1초에 한번씩 출력
}

void readCommand()
{
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd == "A") 
  {
    move = 'L';
  } 

  else if (cmd == "D") 
  {
    move = 'R';
  } 

  else if (cmd == "S") 
  {
    move = 'S';
  } 

  else if (cmd == "W") 
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
}