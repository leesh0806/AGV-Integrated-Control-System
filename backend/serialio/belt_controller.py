# backend/serialio/belt_controller.py

import time
import threading

class BeltController:
    def __init__(self, serial_controller):
        self.controller = serial_controller # 아두이노와 시리얼로 연결된 객체
        self.duration = 20 # 벨트 작동 지속 시간
        self.belt_on = False # 현재 벨트 작동 여부
        self.is_full = False # 벨트 위 컨테이너가 가득 찼는지 여부
        self.lock = threading.Lock() # 멀티스레드 환경에서 충돌 방지를 위한 락
        self.timer_thread = None # 벨트 자동 OFF 타이머 스레드
        self.running = True  # 시리얼 수신 루프 제어용 플래그
        self.container_full = False # 컨테이너가 가득 찼는지 여부

    # 로그 출력
    def log(self, msg):
        print(f"[Belt] {msg}")

    # 벨트 상태 보고
    def report_status(self, msg):
        try:
            self.controller.write(msg)
            self.log(f"[보고] {msg}")
        except Exception as e:
            self.log(f"[보고 오류] {e}")

    # GateController와 인터페이스 통일을 위한 send_command 메서드 추가
    def send_command(self, belt_id: str, action: str):
        """GateController와 인터페이스 통일을 위한 메서드"""
        print(f"[BeltController] 명령 전송: {belt_id} → {action}")
        return self.write(action)

    # 외부에서 벨트에 명령을 직접 전송할 때 사용
    def write(self, cmd: str):
        if cmd == "BELT_RUN" and self.container_full:
            print("[⚠️ 벨트 작동 거부] 컨테이너가 가득 찼습니다.")
            return False
            
        print(f"[벨트 명령] {cmd} 전송")
        self.controller.write(cmd)
        return True
    
    # 시리얼 인터페이스와 호환성을 위한 메서드
    def read_response(self, timeout=5):
        """SerialInterface와 호환되는 read_response 메서드"""
        return self.controller.read_response(timeout=timeout)
    
    def close(self):
        """SerialInterface와 호환되는 close 메서드"""
        self.running = False
        if hasattr(self.controller, 'close'):
            self.controller.close()

    # 벨트 장치 또는 중앙 제어로부터 전달된 메시지를 처리
    def handle_message(self, msg):
        msg = msg.strip().upper()
        
        # 벨트 작동 시작
        if msg == "BELT_RUN":
            if self.is_full:
                self.log("무시됨: 컨테이너 A_FULL 상태")
                return
            self.turn_on_belt()

        # 비상 정지
        elif msg == "EMRSTOP":
            self.turn_off_belt()
            self.report_status("BELTOFF")

        # 컨테이너 A가 가득 찼음
        elif msg == "A_FULL":
            self.is_full = True
            self.turn_off_belt()
            self.report_status("ConA_FULL")
            self.report_status("BELTOFF")

        # 벨트 정지
        elif msg == "BELTOFF":
            self.turn_off_belt()
            self.log("상태 수신: 벨트 정지됨")

        # 벨트 작동 중
        elif msg == "BELTON":
            self.log("상태 수신: 벨트 작동 중 (BELTON)")

        # 컨테이너 A가 가득 찼음
        elif msg == "CONA_FULL":
            self.log("상태 수신: 컨테이너 가득 참 (CONA_FULL)")
            
        # 알 수 없는 명령
        else:
            self.log(f"[무시됨] 알 수 없는 명령: {msg}")

    # 벨트 가동 시작
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

    # 벨트 자동 OFF 타이머
    def _auto_off_timer(self):
        time.sleep(self.duration)
        self.turn_off_belt()
        self.report_status("BELTOFF")

    # 벨트 가동 중지
    def turn_off_belt(self):
        with self.lock:
            if not self.belt_on:
                return
            self.belt_on = False
            self.log("모터 OFF → 벨트 정지")

    # 시리얼 수신 대기
    def poll_serial(self):
        self.log("벨트 시리얼 수신 대기 시작")
        try:
            while self.running:
                line = self.controller.read_response()
                if line and isinstance(line, str):
                    self.handle_message(line)
        except Exception as e:
            self.log(f"[시리얼 수신 종료됨] {e}")

    # 벨트 응답 처리
    def handle_response(self, response: str):
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
