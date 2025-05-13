// 버튼 매핑
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

unsigned long lastValidCode = 0;
unsigned long lastClicked = 0;
unsigned long timer = 0;
int wait = 100;

void receiveIR() 
{
  unsigned long time = millis();
  timer = time - lastClicked;

  if (IrReceiver.decode()) 
  {
    unsigned long receivedCode = IrReceiver.decodedIRData.decodedRawData;
    
    if (timer > wait)
    {
      if (receivedCode != 0 && receivedCode != 0xFFFFFFFF) // 새로운 신호일때
      { 
        lastValidCode = receivedCode;
        handleButton(receivedCode);
      }
    }
    IrReceiver.resume(); // 다음신호 받을 준비
  }
}

void handleButton(unsigned long code) 
{
  switch(code) // 모든 번호들을 매핑하지는 않았음
  {
    case BTN_PREV:
      if (move == 'L')
      {
        move = 'S';
      }
      else
      {
        move = 'L'; // 왼쪽 이동
      }
      break;
    case BTN_NEXT:
      if (move == 'R')
      {
        move = 'S';
      }
      else
      {
        move = 'R'; // 왼쪽 이동
      }
      break;
    case BTN_PLAY:
      btnServo = 1; // 서보 모터 발동
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
      Serial.println("속도 감속");
      break;
    case BTN_VOLU:
      Serial.println("속도 가속");
      break;
    default:
      Serial.print("알 수 없는 버튼: 0x");
      Serial.println(code, HEX);
      break;
  }
}