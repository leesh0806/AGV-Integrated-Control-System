// // #include <Servo.h>

// // const int MOTOR_PIN_A = 4;
// // const int MOTOR_PIN_B = 5;
// // const int MOTOR_PIN_PWM = 6;
// // const int SERVO_PIN = 9;
// // const int SENSOR_PIN_A = A0;
// // const int SENSOR_PIN_B = A1;

// // const int CDS_THRESHOLD_LOW = 90;
// // const int CDS_THRESHOLD_HIGH = 110;
// // const int MOTOR_SPEED = 90;

// // #define ROUTE_A 0
// // #define ROUTE_B 1
// // #define ROUTE_NONE 2

// // int currentRoute = ROUTE_A;
// // int routeLock = ROUTE_NONE;

// // unsigned long motorStartTime = 0;
// // unsigned long motorEndTime = 0;
// // unsigned long remainingTime = 0;
// // const unsigned long MOTOR_DURATION = 20000;
// // bool motorRunning = false;

// // Servo conveyorServo;

// // // 전역 상태 변수 (히스테리시스 적용된 결과 저장)
// // bool fullA_state = false;
// // bool fullB_state = false;

// // void setup() {
// //   pinMode(MOTOR_PIN_A, OUTPUT);
// //   pinMode(MOTOR_PIN_B, OUTPUT);
// //   pinMode(MOTOR_PIN_PWM, OUTPUT);
// //   Serial.begin(9600);
// //   conveyorServo.attach(SERVO_PIN);
// //   conveyorServo.write(50);
// //   Serial.println("BELT_ROUTE_A");
// // }

// // void loop() {
// //   reportStatus();

// //   if (Serial.available() > 0) {
// //     String command = Serial.readStringUntil('\n');
// //     command.trim();

// //     if (command == "R" && !motorRunning) {
// //       if (decideRoute()) {
// //         startMotor(MOTOR_DURATION);
// //       }
// //     } else if (command == "E") {
// //       stopMotor();
// //     }
// //   }

// //   if (motorRunning) {
// //     if (millis() >= motorEndTime) {
// //       stopMotor();
// //     }

// //     if (isWarehouseFullStable(currentRoute)) {
// //       unsigned long elapsed = millis() - motorStartTime;
// //       stopMotor();
// //       remainingTime = motorEndTime - millis();

// //       if (currentRoute == ROUTE_A && !isWarehouseFullStable(ROUTE_B)) {
// //         currentRoute = ROUTE_B;
// //         routeLock = ROUTE_B;
// //         conveyorServo.write(130);
// //         Serial.println("BELT_ROUTE_B");
// //       } else if (currentRoute == ROUTE_B && !isWarehouseFullStable(ROUTE_A)) {
// //         currentRoute = ROUTE_A;
// //         routeLock = ROUTE_A;
// //         conveyorServo.write(50);
// //         Serial.println("BELT_ROUTE_A");
// //       } else {
// //         Serial.println("BELT_ALL_FULL while Running");
// //         return;
// //       }

// //       delay(1000);
// //       startMotor(remainingTime);
// //       Serial.println(remainingTime);
// //     }
// //   }
// // }

// // bool decideRoute() {
// //   if (routeLock != ROUTE_NONE) {
// //     currentRoute = routeLock;
// //     return true;
// //   }

// //   bool fullA = isWarehouseFullStable(ROUTE_A);
// //   bool fullB = isWarehouseFullStable(ROUTE_B);

// //   if (!fullA) {
// //     currentRoute = ROUTE_A;
// //     routeLock = ROUTE_A;
// //   } else if (!fullB) {
// //     currentRoute = ROUTE_B;
// //     routeLock = ROUTE_B;
// //   } else {
// //     Serial.println("BELT_ALL_FULL at beginning");
// //     return false;
// //   }

// //   if (currentRoute == ROUTE_A) {
// //     conveyorServo.write(50);
// //     Serial.println("BELT_ROUTE_A");
// //   } else {
// //     conveyorServo.write(130);
// //     Serial.println("BELT_ROUTE_B");
// //     delay(800);
// //   }

// //   return true;
// // }

// // void startMotor(unsigned long duration) {
// //   digitalWrite(MOTOR_PIN_A, HIGH);
// //   digitalWrite(MOTOR_PIN_B, LOW);
// //   analogWrite(MOTOR_PIN_PWM, MOTOR_SPEED);
// //   motorStartTime = millis();
// //   motorEndTime = motorStartTime + duration;
// //   motorRunning = true;
// //   Serial.print(duration);
// //   Serial.println("BELT_RUNNING");
// // }

// // void stopMotor() {
// //   digitalWrite(MOTOR_PIN_A, LOW);
// //   digitalWrite(MOTOR_PIN_B, LOW);
// //   analogWrite(MOTOR_PIN_PWM, 0);
// //   motorRunning = false;
// //   Serial.println("BELT_STOPPED");
// // }

// // // 히스테리시스 적용된 센서 안정화
// // bool isWarehouseFullStable(int route) {
// //   int value = 0;
// //   if (route == ROUTE_A) {
// //     value = analogRead(SENSOR_PIN_A);
// //     if (value < CDS_THRESHOLD_LOW) fullA_state = true;
// //     else if (value > CDS_THRESHOLD_HIGH) fullA_state = false;
// //     return fullA_state;
// //   } else {
// //     value = analogRead(SENSOR_PIN_B);
// //     if (value < CDS_THRESHOLD_LOW) fullB_state = true;
// //     else if (value > CDS_THRESHOLD_HIGH) fullB_state = false;
// //     return fullB_state;
// //   }
// // }

// // // 상태 출력 (요동 방지)
// // unsigned long lastReportTime = 0;
// // const unsigned long REPORT_INTERVAL = 300;

// // void reportStatus() {
// //   static bool lastAState = false;
// //   static bool lastBState = false;

// //   if (millis() - lastReportTime < REPORT_INTERVAL) return;

// //   bool aNow = isWarehouseFullStable(ROUTE_A);
// //   bool bNow = isWarehouseFullStable(ROUTE_B);

// //   if (aNow != lastAState || bNow != lastBState) {
// //     if (aNow != lastAState)
// //       Serial.println(aNow ? "BELT_A_FULL" : "BELT_A_EMPTY");
// //     if (bNow != lastBState)
// //       Serial.println(bNow ? "BELT_B_FULL" : "BELT_B_EMPTY");

// //     lastAState = aNow;
// //     lastBState = bNow;
// //     lastReportTime = millis();
// //   }
// // }




// #include <Servo.h>

// const int MOTOR_PIN_A = 4;
// const int MOTOR_PIN_B = 5;
// const int MOTOR_PIN_PWM = 6;
// const int SERVO_PIN = 9;
// const int SENSOR_PIN_A = A0;
// const int SENSOR_PIN_B = A1;

// const int CDS_THRESHOLD_LOW = 90;
// const int CDS_THRESHOLD_HIGH = 110;
// const int MOTOR_SPEED = 90;

// #define ROUTE_A 0
// #define ROUTE_B 1
// #define ROUTE_NONE 2

// int currentRoute = ROUTE_A;
// int routeLock = ROUTE_NONE;

// unsigned long motorStartTime = 0;
// unsigned long motorEndTime = 0;
// unsigned long remainingTime = 0;
// const unsigned long MOTOR_DURATION = 20000;
// bool motorRunning = false;

// Servo conveyorServo;

// // 센서 상태 관리 변수
// bool fullA_state = false;
// bool fullB_state = false;
// int fullACounter = 0;
// int fullBCounter = 0;
// const int STABLE_COUNT = 5;

// void setup() {
//   pinMode(MOTOR_PIN_A, OUTPUT);
//   pinMode(MOTOR_PIN_B, OUTPUT);
//   pinMode(MOTOR_PIN_PWM, OUTPUT);
//   Serial.begin(9600);
//   conveyorServo.attach(SERVO_PIN);
//   conveyorServo.write(50);
//   Serial.println("BELT_ROUTE_A");
// }

// void loop() {
//   reportStatus();

//   if (Serial.available() > 0) {
//     String command = Serial.readStringUntil('\n');
//     command.trim();

//     if (command == "R" && !motorRunning) {
//       if (decideRoute()) {
//         startMotor(MOTOR_DURATION);
//       }
//     } else if (command == "E") {
//       stopMotor();
//     }
//   }

//   if (motorRunning) {
//     if (millis() >= motorEndTime) {
//       stopMotor();
//     }

//     if (isWarehouseFullStable(currentRoute)) {
//       unsigned long elapsed = millis() - motorStartTime;
//       stopMotor();
//       remainingTime = motorEndTime - millis();

//       if (currentRoute == ROUTE_A && !isWarehouseFullStable(ROUTE_B)) {
//         currentRoute = ROUTE_B;
//         routeLock = ROUTE_B;
//         conveyorServo.write(130);
//         Serial.println("BELT_ROUTE_B");
//       } else if (currentRoute == ROUTE_B && !isWarehouseFullStable(ROUTE_A)) {
//         currentRoute = ROUTE_A;
//         routeLock = ROUTE_A;
//         conveyorServo.write(50);
//         Serial.println("BELT_ROUTE_A");
//       } else {
//         Serial.println("BELT_ALL_FULL while Running");
//         return;
//       }

//       delay(1000);
//       startMotor(remainingTime);
//       Serial.println(remainingTime);
//     }
//   }
// }

// bool decideRoute() {
//   if (routeLock != ROUTE_NONE) {
//     currentRoute = routeLock;
//     return true;
//   }

//   bool fullA = isWarehouseFullStable(ROUTE_A);
//   bool fullB = isWarehouseFullStable(ROUTE_B);

//   if (!fullA) {
//     currentRoute = ROUTE_A;
//     routeLock = ROUTE_A;
//   } else if (!fullB) {
//     currentRoute = ROUTE_B;
//     routeLock = ROUTE_B;
//   } else {
//     Serial.println("BELT_ALL_FULL at beginning");
//     return false;
//   }

//   if (currentRoute == ROUTE_A) {
//     conveyorServo.write(50);
//     Serial.println("BELT_ROUTE_A");
//   } else {
//     conveyorServo.write(130);
//     Serial.println("BELT_ROUTE_B");
//     delay(800);
//   }

//   return true;
// }

// void startMotor(unsigned long duration) {
//   digitalWrite(MOTOR_PIN_A, HIGH);
//   digitalWrite(MOTOR_PIN_B, LOW);
//   analogWrite(MOTOR_PIN_PWM, MOTOR_SPEED);
//   motorStartTime = millis();
//   motorEndTime = motorStartTime + duration;
//   motorRunning = true;
//   Serial.print(duration);
//   Serial.println("BELT_RUNNING");
// }

// void stopMotor() {
//   digitalWrite(MOTOR_PIN_A, LOW);
//   digitalWrite(MOTOR_PIN_B, LOW);
//   analogWrite(MOTOR_PIN_PWM, 0);
//   motorRunning = false;
//   Serial.println("BELT_STOPPED");
// }

// bool isWarehouseFullStable(int route) {
//   int value = 0;
//   if (route == ROUTE_A) {
//     value = analogRead(SENSOR_PIN_A);
//     if (value < CDS_THRESHOLD_LOW) {
//       if (fullACounter < STABLE_COUNT) fullACounter++;
//     } else if (value > CDS_THRESHOLD_HIGH) {
//       if (fullACounter > 0) fullACounter--;
//     }
//     fullA_state = (fullACounter >= STABLE_COUNT);
//     return fullA_state;
//   } else {
//     value = analogRead(SENSOR_PIN_B);
//     if (value < CDS_THRESHOLD_LOW) {
//       if (fullBCounter < STABLE_COUNT) fullBCounter++;
//     } else if (value > CDS_THRESHOLD_HIGH) {
//       if (fullBCounter > 0) fullBCounter--;
//     }
//     fullB_state = (fullBCounter >= STABLE_COUNT);
//     return fullB_state;
//   }
// }

// unsigned long lastReportTime = 0;
// const unsigned long REPORT_INTERVAL = 300;

// void reportStatus() {
//   static bool lastAState = false;
//   static bool lastBState = false;

//   if (millis() - lastReportTime < REPORT_INTERVAL) return;

//   bool aNow = isWarehouseFullStable(ROUTE_A);
//   bool bNow = isWarehouseFullStable(ROUTE_B);

//   if (aNow != lastAState || bNow != lastBState) {
//     if (aNow != lastAState)
//       Serial.println(aNow ? "BELT_A_FULL" : "BELT_A_EMPTY");
//     if (bNow != lastBState)
//       Serial.println(bNow ? "BELT_B_FULL" : "BELT_B_EMPTY");

//     lastAState = aNow;
//     lastBState = bNow;
//     lastReportTime = millis();
//   }
// }



// #include <Servo.h>

// const int MOTOR_PIN_A = 4;
// const int MOTOR_PIN_B = 5;
// const int MOTOR_PIN_PWM = 6;
// const int SERVO_PIN = 9;
// const int SENSOR_PIN_A = A0;
// const int SENSOR_PIN_B = A1;

// const int CDS_THRESHOLD_LOW = 90;
// const int CDS_THRESHOLD_HIGH = 110;
// const int MOTOR_SPEED = 90;

// #define ROUTE_A 0
// #define ROUTE_B 1
// #define ROUTE_NONE 2

// int currentRoute = ROUTE_A;
// int routeLock = ROUTE_NONE;

// unsigned long motorStartTime = 0;
// unsigned long motorEndTime = 0;
// unsigned long remainingTime = 0;
// const unsigned long MOTOR_DURATION = 20000;
// bool motorRunning = false;

// Servo conveyorServo;

// bool fullA_state = false;
// bool fullB_state = false;
// int fullACounter = 0;
// int fullBCounter = 0;
// const int STABLE_COUNT = 5;

// void setup() {
//   pinMode(MOTOR_PIN_A, OUTPUT);
//   pinMode(MOTOR_PIN_B, OUTPUT);
//   pinMode(MOTOR_PIN_PWM, OUTPUT);
//   Serial.begin(9600);
//   conveyorServo.attach(SERVO_PIN);
//   conveyorServo.write(50);
//   Serial.println("BELT_ROUTE_A");
// }

// void loop() {
//   // !!! 센서 raw 값 직접 출력
//   int rawA = getAveragedSensor(SENSOR_PIN_A);
//   int rawB = getAveragedSensor(SENSOR_PIN_B);
//   // Serial.print("!!! RAW_A: ");
//   // Serial.print(rawA);
//   // Serial.print(" | RAW_B: ");
//   // Serial.println(rawB);

//   reportStatus();

//   if (Serial.available() > 0) {
//     String command = Serial.readStringUntil('\n');
//     command.trim();

//     if (command == "R" && !motorRunning) {
//       if (decideRoute()) {
//         startMotor(MOTOR_DURATION);
//       }
//     } else if (command == "E") {
//       stopMotor();
//     }
//   }

//   if (motorRunning) {
//     if (millis() >= motorEndTime) {
//       stopMotor();
//     }

//     if (isWarehouseFullStable(currentRoute)) {
//       unsigned long elapsed = millis() - motorStartTime;
//       stopMotor();
//       remainingTime = motorEndTime - millis();

//       if (currentRoute == ROUTE_A && !isWarehouseFullStable(ROUTE_B)) {
//         currentRoute = ROUTE_B;
//         routeLock = ROUTE_B;
//         conveyorServo.write(130);
//         Serial.println("BELT_ROUTE_B");
//       } else if (currentRoute == ROUTE_B && !isWarehouseFullStable(ROUTE_A)) {
//         currentRoute = ROUTE_A;
//         routeLock = ROUTE_A;
//         conveyorServo.write(50);
//         Serial.println("BELT_ROUTE_A");
//       } else {
//         Serial.println("BELT_ALL_FULL while Running");
//         return;
//       }

//       delay(1000);
//       startMotor(remainingTime);
//       Serial.println(remainingTime);
//     }
//   }

//   delay(200); // !!! 센서 로그 확인을 위해 추가 (너무 빠르게 쌓이지 않게)
// }

// bool decideRoute() {
//   if (routeLock != ROUTE_NONE) {
//     currentRoute = routeLock;
//     return true;
//   }

//   bool fullA = isWarehouseFullStable(ROUTE_A);
//   bool fullB = isWarehouseFullStable(ROUTE_B);

//   if (!fullA) {
//     currentRoute = ROUTE_A;
//     routeLock = ROUTE_A;
//   } else if (!fullB) {
//     currentRoute = ROUTE_B;
//     routeLock = ROUTE_B;
//   } else {
//     Serial.println("BELT_ALL_FULL at beginning");
//     return false;
//   }

//   if (currentRoute == ROUTE_A) {
//     conveyorServo.write(50);
//     Serial.println("BELT_ROUTE_A");
//   } else {
//     conveyorServo.write(130);
//     Serial.println("BELT_ROUTE_B");
//     delay(800);
//   }

//   return true;
// }

// void startMotor(unsigned long duration) {
//   digitalWrite(MOTOR_PIN_A, HIGH);
//   digitalWrite(MOTOR_PIN_B, LOW);
//   analogWrite(MOTOR_PIN_PWM, MOTOR_SPEED);
//   motorStartTime = millis();
//   motorEndTime = motorStartTime + duration;
//   motorRunning = true;
//   Serial.print(duration);
//   Serial.println("BELT_RUNNING");
// }

// void stopMotor() {
//   digitalWrite(MOTOR_PIN_A, LOW);
//   digitalWrite(MOTOR_PIN_B, LOW);
//   analogWrite(MOTOR_PIN_PWM, 0);
//   motorRunning = false;
//   Serial.println("BELT_STOPPED");
// }

// bool isWarehouseFullStable(int route) {
//   int value = 0;
//   if (route == ROUTE_A) {
//     value = getAveragedSensor(SENSOR_PIN_A);
//     // !!! A센서 측정 로그 출력
//     // Serial.print("!!! [A] CDS = ");
//     // Serial.print(value);
//     // Serial.print(" | Counter = ");
//     // Serial.println(fullACounter);

//     if (value < CDS_THRESHOLD_LOW) {
//       if (fullACounter < STABLE_COUNT) fullACounter++;
//     } else if (value > CDS_THRESHOLD_HIGH) {
//       if (fullACounter > 0) fullACounter--;
//     }
//     fullA_state = (fullACounter >= STABLE_COUNT);
//     return fullA_state;

//   } else {
//     value = getAveragedSensor(SENSOR_PIN_B);
//     // !!! B센서 측정 로그 출력
//     // Serial.print("!!! [B] CDS = ");
//     // Serial.print(value);
//     // Serial.print(" | Counter = ");
//     // Serial.println(fullBCounter);

//     if (value < CDS_THRESHOLD_LOW) {
//       if (fullBCounter < STABLE_COUNT) fullBCounter++;
//     } else if (value > CDS_THRESHOLD_HIGH) {
//       if (fullBCounter > 0) fullBCounter--;
//     }
//     fullB_state = (fullBCounter >= STABLE_COUNT);
//     return fullB_state;
//   }
// }

// unsigned long lastReportTime = 0;
// const unsigned long REPORT_INTERVAL = 300;

// void reportStatus() {
//   static bool lastAState = false;
//   static bool lastBState = false;

//   if (millis() - lastReportTime < REPORT_INTERVAL) return;

//   bool aNow = isWarehouseFullStable(ROUTE_A);
//   bool bNow = isWarehouseFullStable(ROUTE_B);

//   if (aNow != lastAState || bNow != lastBState) {
//     if (aNow != lastAState)
//       Serial.println(aNow ? "BELT_A_FULL" : "BELT_A_EMPTY");
//     if (bNow != lastBState)
//       Serial.println(bNow ? "BELT_B_FULL" : "BELT_B_EMPTY");

//     lastAState = aNow;
//     lastBState = bNow;
//     lastReportTime = millis();
//   }
// }


// int getAveragedSensor(int pin) {
//   long sum = 0;
//   for (int i = 0; i < 10; i++) {
//     sum += analogRead(pin);
//     delay(2); // 총 20ms 대기, 실시간성 유지됨
//   }
//   return sum / 10;
// }

#include <Servo.h>

const int MOTOR_PIN_A = 4;
const int MOTOR_PIN_B = 5;
const int MOTOR_PIN_PWM = 6;
const int SERVO_PIN = 9;
const int SENSOR_PIN_A = A0;
const int SENSOR_PIN_B = A1;

const int CDS_THRESHOLD_LOW = 90;
const int CDS_THRESHOLD_HIGH = 110;
const int MOTOR_SPEED =254;

#define ROUTE_A 0
#define ROUTE_B 1
#define ROUTE_NONE 2

int currentRoute = ROUTE_A;
int routeLock = ROUTE_NONE;

unsigned long motorStartTime = 0;
unsigned long motorEndTime = 0;
unsigned long remainingTime = 0;
const unsigned long MOTOR_DURATION = 20000;
bool motorRunning = false;

Servo conveyorServo;

bool fullA_state = false;
bool fullB_state = false;
int fullACounter = 0;
int fullBCounter = 0;
const int STABLE_COUNT = 5;

void setup() {
  pinMode(MOTOR_PIN_A, OUTPUT);
  pinMode(MOTOR_PIN_B, OUTPUT);
  pinMode(MOTOR_PIN_PWM, OUTPUT);
  Serial.begin(9600);
  conveyorServo.attach(SERVO_PIN);
  conveyorServo.write(50);
  Serial.println("BELT_ROUTE_A");
}

void loop() {
  
  reportStatus();

  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "BELT_RUN" && !motorRunning) {
      if (decideRoute()) {
        startMotor(MOTOR_DURATION);
      }
    } else if (command == "E") {
      stopMotor();
    }
  }

  if (motorRunning) {
    if (millis() >= motorEndTime) {
      stopMotor();
    }

    if (isWarehouseFullStable(currentRoute)) {
      unsigned long elapsed = millis() - motorStartTime;
      stopMotor();
      remainingTime = motorEndTime - millis();

      if (currentRoute == ROUTE_A && !isWarehouseFullStable(ROUTE_B)) {
        currentRoute = ROUTE_B;
        routeLock = ROUTE_B;
        conveyorServo.write(130);
        Serial.println("BELT_ROUTE_B");
      } 
      else if (currentRoute == ROUTE_B && !isWarehouseFullStable(ROUTE_A)) {
        currentRoute = ROUTE_A;
        routeLock = ROUTE_A;
        conveyorServo.write(50);
        Serial.println("BELT_ROUTE_A");
      } 
      else {
        Serial.println("BELT_ALL_FULL while Running");
        return;
      }

      delay(1000);
      startMotor(remainingTime);
      Serial.println(remainingTime);
    }
  }
}

bool decideRoute() {
  if (routeLock != ROUTE_NONE) {
    currentRoute = routeLock;
    return true;
  }

  bool fullA = isWarehouseFullStable(ROUTE_A);
  bool fullB = isWarehouseFullStable(ROUTE_B);

  if (!fullA) {
    currentRoute = ROUTE_A;
    routeLock = ROUTE_A;
  } else if (!fullB) {
    currentRoute = ROUTE_B;
    routeLock = ROUTE_B;
  } else {
    Serial.println("BELT_ALL_FULL at beginning");
    return false;
  }

  if (currentRoute == ROUTE_A) {
    conveyorServo.write(50);
    Serial.println("BELT_ROUTE_A");
  } else {
    conveyorServo.write(130);
    Serial.println("BELT_ROUTE_B");
    delay(800);
  }

  return true;
}

void startMotor(unsigned long duration) {
  digitalWrite(MOTOR_PIN_A, HIGH);
  digitalWrite(MOTOR_PIN_B, LOW);
  analogWrite(MOTOR_PIN_PWM, MOTOR_SPEED);
  motorStartTime = millis();
  motorEndTime = motorStartTime + duration;
  motorRunning = true;
  Serial.print(duration);
  Serial.println("BELT_RUNNING");
}

void stopMotor() {
  digitalWrite(MOTOR_PIN_A, LOW);
  digitalWrite(MOTOR_PIN_B, LOW);
  analogWrite(MOTOR_PIN_PWM, 0);
  motorRunning = false;
  Serial.println("BELT_STOPPED");
}

int getAveragedSensor(int pin) {
  long sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(pin);
    delay(2);
  }
  return sum / 10;
}

bool isWarehouseFullStable(int route) {
  int value = 0;
  if (route == ROUTE_A) {
    value = getAveragedSensor(SENSOR_PIN_A);
    if (value < CDS_THRESHOLD_LOW) {
      if (fullACounter < STABLE_COUNT) fullACounter++;
    } else if (value > CDS_THRESHOLD_HIGH) {
      if (fullACounter > 0) fullACounter--;
    }
    fullA_state = (fullACounter >= STABLE_COUNT);
    return fullA_state;
  } else {
    value = getAveragedSensor(SENSOR_PIN_B);
    if (value < CDS_THRESHOLD_LOW) {
      if (fullBCounter < STABLE_COUNT) fullBCounter++;
    } else if (value > CDS_THRESHOLD_HIGH) {
      if (fullBCounter > 0) fullBCounter--;
    }
    fullB_state = (fullBCounter >= STABLE_COUNT);
    return fullB_state;
  }
}

unsigned long lastReportTime = 0;
const unsigned long REPORT_INTERVAL = 300;

void reportStatus() {
  static bool lastAState = false;
  static bool lastBState = false;


  

  if (millis() - lastReportTime < REPORT_INTERVAL) return;

  

  bool aNow = isWarehouseFullStable(ROUTE_A);
  bool bNow = isWarehouseFullStable(ROUTE_B);

  if (aNow != lastAState || bNow != lastBState) {
    
    if (aNow != lastAState)
      Serial.println(aNow ? "BELT_A_FULL" : "BELT_A_EMPTY");
    if (bNow != lastBState)
      Serial.println(bNow ? "BELT_B_FULL" : "BELT_B_EMPTY");

    lastAState = aNow;
    lastBState = bNow;
    lastReportTime = millis();
  }
}

