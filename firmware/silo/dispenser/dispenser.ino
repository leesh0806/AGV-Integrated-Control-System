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
char lastmove= 'S';

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
  if (Serial.available()) 
  {
    readCommand();
  }

  receiveIR();
  moveLeftRight();

  checkServButton();
  dispense();

  //debug(); // 1초에 한번씩 출력
}

void readCommand()
{
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();

  if (cmd == "A" || cmd == "DI_LEFT_TURN") 
  {
    move = 'L';
    Serial.println("ACK:DI_LEFT_TURN:OK");
  } 

  else if (cmd == "D" || cmd == "DI_RIGHT_TURN") 
  {
    move = 'R';
    Serial.println("ACK:DI_RIGHT_TURN:OK");
  } 

  else if (cmd == "S" || cmd == "DI_STOP_TURN") 
  {
    move = 'S';
    Serial.println("ACK:DI_STOP_TURN:OK");
  } 

  else if (cmd == "V" || cmd == "DI_LOC_ROUTE_A")
  {
    if (lastmove != 'A')
    {
      move = 'A';
    }
    Serial.println("ACK:DI_LOC_A:OK");
  }
  
  else if (cmd == "B" || cmd == "DI_LOC_ROUTE_B")
  {
    if (lastmove != 'B')
    {
      move = 'B';
    }
    Serial.println("ACK:DI_LOC_B:OK");
  }

  else if (cmd == "W") 
  {
    if (open == false)
    {
      open = true;
      Serial.println("ACK:DI_OPENED");
    }
    else
    {
      open = false;
      Serial.println("ACK:DI_CLOSED");
    }
  }

  else if (cmd == "DI_OPEN")
  {
    open = true;
    Serial.println("ACK:DI_OPENED");
  }
  else if (cmd == "DI_CLOSE")
  {
    open = false;
    Serial.println("ACK:DI_CLOSED");
  }

}