# backend/serialio/belt_controller.py

import time
import threading

class BeltController:
    def __init__(self, serial_controller):
        self.controller = serial_controller
        self.duration = 20
        self.belt_on = False
        self.is_full = False
        self.lock = threading.Lock()
        self.timer_thread = None
        self.running = True  # ✅ 스레드 종료 flag
        self.container_full = False

    def log(self, msg):
        print(f"[Belt] {msg}")

    def report_status(self, msg):
        try:
            self.controller.write(msg)
            self.log(f"[보고] {msg}")
        except Exception as e:
            self.log(f"[보고 오류] {e}")

    def send_command(self, cmd: str):
        """
        벨트 명령 전송
        - BELTACT: 벨트 작동 시작 (벨트에서 20초 타이머 관리)
        - EMRSTOP: 비상 정지
        """
        if cmd == "BELTACT" and self.container_full:
            print("[⚠️ 벨트 작동 거부] 컨테이너가 가득 찼습니다.")
            return False
            
        print(f"[벨트 명령] {cmd} 전송")
        self.controller.write(cmd)
        return True

    def handle_message(self, msg):
        msg = msg.strip().upper()

        if msg == "BELTACT":
            if self.is_full:
                self.log("무시됨: 컨테이너 A_FULL 상태")
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

        elif msg == "BELTOFF":
            self.turn_off_belt()
            self.log("상태 수신: 벨트 정지됨")

        elif msg == "BELTON":
            self.log("상태 수신: 벨트 작동 중 (BELTON)")

        elif msg == "CONA_FULL":
            self.log("상태 수신: 컨테이너 가득 참 (CONA_FULL)")
            
        else:
            self.log(f"[무시됨] 알 수 없는 명령: {msg}")

    def turn_on_belt(self):
        with self.lock:
            if self.belt_on:
                self.log("이미 가동 중")
                return

            self.belt_on = True
            self.log("모터 ON → 벨트 가동 시작")
            self.report_status("BELTON")

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

    def poll_serial(self):
        self.log("벨트 시리얼 수신 대기 시작")
        try:
            while self.running:
                line = self.controller.read_response()
                if line and isinstance(line, str):
                    self.handle_message(line)
        except Exception as e:
            self.log(f"[시리얼 수신 종료됨] {e}")

    def handle_response(self, response: str):
        """
        벨트 응답 처리
        - BELTON: 벨트 작동 시작
        - BELTOFF: 벨트 정지
        - ConA_FULL: 컨테이너 가득 참
        """
        if response == "ConA_FULL":
            self.container_full = True
            print("[⚠️ 컨테이너 상태] 가득 참")
            return True
            
        elif response == "BELTOFF":
            print("[ℹ️ 벨트 상태] 정지")
            return True
            
        elif response == "BELTON":
            print("[ℹ️ 벨트 상태] 작동 중")
            return True
            
        return False
