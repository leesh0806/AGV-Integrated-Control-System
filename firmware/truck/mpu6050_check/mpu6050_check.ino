#include <Wire.h>
#include <MPU6050.h>

MPU6050 mpu;

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);  // SDA = GPIO21, SCL = GPIO22

  Serial.println("MPU6050 초기화 중...");
  mpu.initialize();

  if (mpu.testConnection()) {
    Serial.println("MPU6050 연결 성공!");
  } else {
    Serial.println("MPU6050 연결 실패!");
    while (1);
  }
}

void loop() {
  int16_t ax, ay, az;
  int16_t gx, gy, gz;

  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  Serial.print("Accel X: "); Serial.print(ax);
  Serial.print(" | Y: "); Serial.print(ay);
  Serial.print(" | Z: "); Serial.println(az);

  Serial.print("Gyro  X: "); Serial.print(gx);
  Serial.print(" | Y: "); Serial.print(gy);
  Serial.print(" | Z: "); Serial.println(gz);

}