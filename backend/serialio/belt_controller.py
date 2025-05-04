# backend/serialio/belt_controller.py

import time
import threading
import serial  # 또는 fake_serial

class BeltController:
    def __init__(self, serial_port):
        self.ser = serial.Serial(serial_port, baudrate=9600, timeout=1)

        # 내부적으로 고정된 동작 시간 (초)
        self.duration = 20

        self.belt_on = False
        self.is_full = False
        self.lock = threading.Lock()
        self.timer_thread = None

    def log(self, msg):
        print(f"[Belt] {msg}")

    def report_status(self, msg):
        """벨트 → HQ 상태 보고"""
        try:
            self.ser.write((msg + '\n').encode())
            self.log(f"[보고] {msg}")
        except Exception as e:
            self.log(f"[보고 오류] {e}")

    def read_from_serial(self):
        try:
            line = self.ser.readline().decode().strip()
            if line:
                self.log(f"[수신] {line}")
            return line
        except Exception as e:
            self.log(f"[읽기 오류] {e}")
            return ""

    def handle_message(self, msg):
        msg = msg.strip()

        if msg == "BELTACT":
            if self.is_full:
                self.log("가동 무시: A_FULL 상태")
                return
            self.turn_on_belt()

        elif msg == "EMRSTOP":
            self.turn_off_belt()
            self.report_status("BELTOFF")

        elif msg == "A_FULL":
            self.is_full = True
            self.turn_off_belt()
            self.report_status("ConA_FULL")
            self.report_status("BELTOFF")

        elif msg == "BELTOFF":  # 수동 정지
            self.turn_off_belt()
            self.report_status("BELTOFF")

    def turn_on_belt(self):
        with self.lock:
            if self.belt_on:
                self.log("벨트 이미 작동 중")
                return

            self.belt_on = True
            self.log("모터 ON → 벨트 가동 시작")
            self.report_status("BELTON")

            # 20초 후 자동 정지 스레드 실행
            self.timer_thread = threading.Thread(target=self._auto_off_timer)
            self.timer_thread.start()

    def _auto_off_timer(self):
        time.sleep(self.duration)
        self.turn_off_belt()
        self.report_status("BELTOFF")

    def turn_off_belt(self):
        with self.lock:
            if not self.belt_on:
                return
            self.belt_on = False
            self.log("모터 OFF → 벨트 정지")

    def run(self):
        self.log("벨트 제어 시작 (시리얼 수신 대기)")
        try:
            while True:
                msg = self.read_from_serial()
                if msg:
                    self.handle_message(msg)
        except KeyboardInterrupt:
            self.ser.close()
            self.log("시리얼 종료됨")
