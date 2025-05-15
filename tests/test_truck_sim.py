import socket
import time
import sys, os
import requests  # API 요청을 위한 모듈
import struct

# 현재 스크립트 경로를 기준으로 프로젝트 루트 경로를 추가합니다
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.serialio.device_manager import DeviceManager
from backend.tcpio.protocol import TCPProtocol
import threading
import requests

# 서버 설정
HOST = '127.0.0.1'
PORT = 8001
API_PORT = 5001  # Flask API 서버 포트

# 포트 맵: 시리얼 장치 연결에 사용됨 - 서버와 동일한 설정 사용
port_map = {
    "GATE_A": "GATE_A",
    "GATE_B": "GATE_B",
    "BELT": "BELT",
    "DISPENSER": "DISPENSER"  # 디스펜서 추가
}

# 실제 TCP 서버 포트 확인 함수
def get_actual_tcp_port():
    """API 서버에 요청하여 실제 TCP 서버 포트 번호를 확인합니다."""
    try:
        response = requests.get(f"http://{HOST}:{API_PORT}/api/system/tcp/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "status" in data:
                port = data["status"].get("port")
                if port:
                    print(f"[✅ TCP 포트 확인됨] 서버 포트: {port}")
                    return port
        print("[⚠️ TCP 포트 확인 실패] 기본 포트를 사용합니다.")
    except Exception as e:
        print(f"[⚠️ TCP 포트 확인 오류] {e}")
    return PORT  # 기본 포트 반환

# 시리얼 매니저 초기화 - 실제 포트 맵 사용
manager = DeviceManager(port_map=port_map, use_fake=True)

class TruckSimulator:
    def __init__(self):
        self.source = None
        self.client = None
        self.battery_level = 80  # 초기 배터리 레벨을 80%로 설정
        self.charging = False
        self.current_position = "STANDBY"  # 초기 위치를 STANDBY로 설정
        self.run_state = "IDLE"
        self.mission_id = None  # 현재 수행 중인 미션 ID
        self.target_position = None  # 현재 이동 목표 위치
        
        # 미션 요청 관련 변수 추가
        self.last_mission_request_time = 0  # 0으로 설정하여 즉시 미션 요청 가능하게 함
        self.mission_request_interval = 5  # 5초마다 자동으로 미션 요청 (30초에서 변경)
        self.mission_request_in_progress = False  # 미션 요청 중복 방지 플래그
        
        # 명령 추적을 위한 변수
        self.processed_messages = set()  # 처리한 메시지 ID를 추적
        self.last_command = None  # 마지막으로 수신한 명령
        self.last_raw_hex = None  # 마지막으로 수신한 메시지의 원시 헥스 문자열
        
        # 위치 잠금 변수 추가 - 적재작업 중 위치 강제 고정을 위한 변수
        self.position_locked = False
        self.original_position = None
        
        # RUN 명령 수신 플래그 - LOAD_A/LOAD_B에서 CHECKPOINT_C로 이동 시 필요
        self.last_run_command_received = False
        
        # FINISH_LOADING 명령 수신 플래그 추가 - LOAD_A/LOAD_B에서 CHECKPOINT_C로 이동에 필수
        self.loading_finished = False
        
        # 로딩/언로딩 상태 관리
        self.loading_in_progress = False
        self.loading_start_time = 0
        self.unloading_in_progress = False
        self.unloading_start_time = 0
        
        # 실제 TCP 서버 포트 확인
        global PORT
        PORT = get_actual_tcp_port()
        
        # 서버 연결
        if not self.connect():
            print("[⚠️ 초기화 경고] 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
            print("[ℹ️ 도움말] 'python run/run_main_server.py'를 실행하여 서버를 시작하세요.")
            print("[ℹ️ 도움말] 또는 이미 실행 중인 모든 서버 프로세스를 종료하고 다시 시작해보세요.")
        else:
            print("[✅ 초기화 완료] 서버에 성공적으로 연결되었습니다.")
        
        # 상태 업데이트 타이머 시작
        self.updating = True
        self.updater_thread = threading.Thread(target=self.status_update_timer, daemon=True)
        self.updater_thread.start()
        
        # 작업 처리 타이머 시작
        self.task_thread = threading.Thread(target=self.task_timer, daemon=True)
        self.task_thread.start()

    def __del__(self):
        """소멸자 - 자원 정리"""
        self.updating = False
        if self.client:
            try:
                self.client.close()
            except:
                pass

    # TCP 연결
    def connect(self):
        """서버에 연결 (최대 5회 재시도)"""
        # 기존 소켓 정리
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                print(f"[⚠️ 소켓 닫기 실패] {e}")
            self.client = None
        
        # 새 소켓 생성
        max_retries = 5
        retry_count = 0
        retry_delay = 2.0  # 초기 대기 시간
        
        while retry_count < max_retries:
            try:
                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client.settimeout(10.0)  # 연결 시도에 10초 타임아웃 설정
                print(f"[TCP 연결] {HOST}:{PORT} (시도 {retry_count+1}/{max_retries})")
                self.client.connect((HOST, PORT))
                print(f"[TCP 연결 성공] {HOST}:{PORT}")
                
                # TCP 연결 설정 최적화
                self.client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                
                # 플랫폼 따라 TCP Keepalive 설정 (리눅스)
                try:
                    import platform
                    if platform.system() == "Linux":
                        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)  # 60초 비활성 후 keepalive 시작
                        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)  # 10초마다 keepalive 패킷 전송
                        self.client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)     # 5번 실패하면 연결 끊김
                except (ImportError, AttributeError):
                    print("[ℹ️ 정보] TCP Keepalive 세부 설정이 지원되지 않습니다.")
                
                # 연결 성공 후 타임아웃 늘림
                self.client.settimeout(60.0)  # 타임아웃 60초로 설정
                
                # 헬로 메시지 즉시 전송
                self.send("HELLO", {"msg": "register"}, wait=False)
                return True
            except (ConnectionRefusedError, socket.timeout) as e:
                retry_count += 1
                print(f"[⚠️ 연결 실패] {e} - {'재시도 중...' if retry_count < max_retries else '재시도 횟수 초과'}")
                if retry_count < max_retries:
                    # 지수 백오프 - 재시도마다 대기 시간 증가
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10.0)  # 최대 10초까지 증가
                else:
                    print("[❌ 연결 실패] 최대 재시도 횟수를 초과했습니다.")
                    return False
            except Exception as e:
                print(f"[❌ 연결 오류] 예상치 못한 오류가 발생했습니다: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 1.5, 10.0)
                else:
                    return False
                    
        return False

    # 메시지 전송
    def send(self, cmd, payload={}, wait=True):
        """명령을 서버로 전송"""
        if not self.client:
            print("[⚠️ 연결 없음] 메시지 전송 전 연결 시도 중...")
            if not self.connect():
                print("[❌ 전송 실패] 서버에 연결할 수 없어 메시지를 전송할 수 없습니다.")
                return False
                
        # 바이너리 메시지 생성
        message = TCPProtocol.build_message(
            sender="TRUCK_01",
            receiver="SERVER",
            cmd=cmd,
            payload=payload
        )
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.client.sendall(message)
                print(f"[SEND] {cmd} → {payload}")
                if wait:
                    time.sleep(0.5)
                return True
            except (BrokenPipeError, ConnectionResetError, socket.timeout) as e:
                retry_count += 1
                print(f"[⚠️ 전송 오류] {e} - {'재시도 중...' if retry_count < max_retries else '재시도 횟수 초과'}")
                
                if retry_count < max_retries:
                    # 연결 재시도
                    print("[⚠️ 연결 끊김] 서버에 재연결 시도 중...")
                    if not self.connect():
                        print("[❌ 재연결 실패] 메시지 전송을 건너뜁니다.")
                        return False
                    # 연결 재시도 성공 시 바로 재전송 (대기 없음)
                else:
                    print("[❌ 전송 실패] 최대 재시도 횟수를 초과했습니다.")
                    return False
            except Exception as e:
                print(f"[❌ 예상치 못한 오류] {e}")
                retry_count += 1
                if retry_count < max_retries:
                    if not self.connect():
                        return False
                else:
                    return False
                    
        return False
    
    # 통합 상태 업데이트 전송
    def send_status_update(self):
        """통합 상태 업데이트 전송
        
        Returns:
            bool: 전송 성공 여부
        """
        # 배터리 및 위치 정보로 STATUS_UPDATE 페이로드 구성
        status_payload = {
            "battery_level": self.battery_level,
            "position": self.current_position
        }
        
        return self.send("STATUS_UPDATE", status_payload, wait=False)
    
    # 정기적인 상태 업데이트 타이머
    def status_update_timer(self, interval=1):
        """정기적으로 상태 업데이트 전송"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.updating:
            try:
                # 위치 잠금 확인 및 보정 (강제 안전장치)
                if self.position_locked and self.original_position:
                    if self.current_position != self.original_position:
                        print(f"[⚠️ 위치 불일치 감지] 현재 위치({self.current_position})가 잠긴 위치({self.original_position})와 다릅니다.")
                        print(f"[🔧 자동 위치 보정] 위치를 {self.original_position}으로 강제 복원합니다.")
                        # 위치 강제 복원
                        self.current_position = self.original_position
                
                # 배터리 상태 업데이트 (서버 명령에 따라 충전 상태 변경)
                current_level = self.battery_level
                
                if self.charging:
                    # 충전 중일 때 (서버가 START_CHARGING 명령을 보낸 경우)
                    old_level = self.battery_level
                    self.battery_level = min(100, self.battery_level + 20)  # 20%씩 증가 (10%에서 변경)
                    print(f"[DEBUG] 배터리 충전 중: {old_level}% -> {self.battery_level}%")
                    
                    # 배터리가 100%에 도달하면 충전 완료 알림
                    if self.battery_level == 100 and old_level < 100:
                        print(f"[✅ 충전 완료] 배터리가 100%에 도달했습니다. 충전 완료 신호를 보냅니다.")
                        self.charging = False
                        self.send("FINISH_CHARGING", {"battery_level": self.battery_level}, wait=False)
                        
                        # 잠시 대기 후 미션 요청
                        time.sleep(1)
                        print(f"[🔄 충전 후 미션 요청] 배터리 충전 완료 후 새 미션을 요청합니다.")
                        self.last_mission_request_time = time.time()  # 요청 타이머 갱신
                        self.send("ASSIGN_MISSION", {}, wait=False)
                elif self.current_position == "STANDBY":
                    # STANDBY에서는 배터리 유지
                    print(f"[DEBUG] STANDBY 상태: 배터리 유지 {self.battery_level}%")
                    
                    # STANDBY 상태에서 일정 시간(5초) 경과 시 자동으로 미션 요청
                    current_time = time.time()
                    if not self.mission_id and not self.mission_request_in_progress and current_time - self.last_mission_request_time >= self.mission_request_interval:
                        print(f"[🔄 자동 미션 요청] STANDBY 상태에서 {self.mission_request_interval}초 경과, 새 미션을 요청합니다.")
                        self.assign_mission_request()  # 미션 요청
                else:
                    # 이동 중에는 배터리 소모 (3%씩 감소)
                    if self.run_state == "RUNNING":
                        self.battery_level = max(0, self.battery_level - 3)
                        print(f"[DEBUG] 배터리 감소 중: {current_level}% -> {self.battery_level}% (위치: {self.current_position}, 상태: {self.run_state})")
                    else:
                        # 정지 상태에서는 배터리 천천히 감소 (1%씩)
                        self.battery_level = max(0, self.battery_level - 1)
                        print(f"[DEBUG] 배터리 천천히 감소 중: {current_level}% -> {self.battery_level}% (위치: {self.current_position}, 상태: {self.run_state})")
                
                # 통합 상태 업데이트 전송
                if self.send_status_update():
                    # 성공적으로 전송했다면 에러 카운트 초기화
                    consecutive_errors = 0
                else:
                    # 상태 업데이트 전송 실패
                    consecutive_errors += 1
                    print(f"[⚠️ 상태 업데이트 실패] 연속 실패 횟수: {consecutive_errors}/{max_consecutive_errors}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print("[❌ 상태 업데이트 중단] 연속 실패 횟수가 한계를 초과했습니다. 서버 연결 상태를 확인하세요.")
                        break
                
                time.sleep(interval)
            except Exception as e:
                consecutive_errors += 1
                print(f"[ERROR] 상태 업데이트 중 오류 발생: {str(e)}")
                
                if consecutive_errors >= max_consecutive_errors:
                    print("[❌ 상태 업데이트 중단] 연속 오류가 너무 많습니다.")
                    break
                    
                # 짧은 대기 후 재시도
                time.sleep(1)
                
                # 특정 횟수 이상 실패 시 재연결 시도
                if consecutive_errors % 3 == 0:
                    print("[🔄 재연결 시도] 연속 오류가 발생하여 서버에 재연결을 시도합니다.")
                    if not self.connect():
                        print("[⚠️ 재연결 실패] 서버에 연결할 수 없습니다.")
    
    def task_timer(self, interval=0.5):
        """작업 처리 타이머 - 로딩/언로딩 작업 완료 처리"""
        while self.updating:
            try:
                current_time = time.time()
                
                # 로딩 작업 완료 처리 - 자동 FINISH_LOADING 전송 비활성화
                # 서버에서 FINISH_LOADING을 받을 때까지 대기
                # if self.loading_in_progress and (current_time - self.loading_start_time >= 5.0):
                #     if self.current_position in ["LOAD_A", "LOAD_B"]:
                #         print(f"[✅ 적재 완료] 5초 경과 - FINISH_LOADING 자동 전송")
                #         self.send("FINISH_LOADING", {"position": self.current_position}, wait=False)
                #         self.loading_in_progress = False
                #     else:
                #         print(f"[⚠️ 적재 작업 무효화] 현재 위치({self.current_position})가 적재 위치가 아니지만 적재 중 상태임. 상태 초기화")
                #         self.loading_in_progress = False
                
                # 언로딩 작업 완료 처리 (5초 후)
                if self.unloading_in_progress and (current_time - self.unloading_start_time >= 5.0):
                    # 현재 위치 확인 - 하차 위치(BELT)에서만 FINISH_UNLOADING 전송
                    if self.current_position == "BELT":
                        print(f"[✅ 하역 완료] 5초 경과 - FINISH_UNLOADING 자동 전송")
                        self.send("FINISH_UNLOADING", {"position": self.current_position}, wait=False)
                        self.unloading_in_progress = False
                    else:
                        # 하차 위치가 아닌 경우 무효화 (비정상 상태)
                        print(f"[⚠️ 하역 작업 무효화] 현재 위치({self.current_position})가 하차 위치가 아니지만 하역 중 상태임. 상태 초기화")
                        self.unloading_in_progress = False
                
                # 짧은 간격으로 체크
                time.sleep(interval)
            except Exception as e:
                print(f"[⚠️ 작업 타이머 오류] {e}")
                time.sleep(1.0)  # 오류 발생 시 잠시 대기

    def process_server_commands(self, timeout=0.1):  # 타임아웃 더 짧게 설정 (더 자주 체크)
        """서버에서 오는 명령을 처리"""
        self.client.settimeout(timeout)
        try:
            # 헤더(4바이트) 읽기
            header_data = self.client.recv(4)
            if not header_data or len(header_data) < 4:
                if not header_data:
                    print("[❌ 연결 종료] 서버와의 연결이 끊어졌습니다.")
                else:
                    print(f"[⚠️ 불완전한 헤더 수신] 길이: {len(header_data)}")
                self.connect()  # 재연결
                time.sleep(1)  # 재연결 후 잠시 대기
                return False
                
            # 헤더에서 페이로드 길이 추출
            _, _, _, payload_len = header_data[0], header_data[1], header_data[2], header_data[3]
                
            # 페이로드 읽기
            payload_data = b''
            if payload_len > 0:
                try:
                    # 대형 페이로드를 안전하게 읽기 위한 루프
                    remaining = payload_len
                    while remaining > 0:
                        chunk = self.client.recv(remaining)
                        if not chunk:
                            print("[❌ 페이로드 읽기 실패] 서버 연결이 끊겼습니다.")
                            break
                        payload_data += chunk
                        remaining -= len(chunk)
                except socket.timeout:
                    print(f"[⚠️ 페이로드 읽기 타임아웃] 예상: {payload_len}, 수신: {len(payload_data)}")
                    
                if len(payload_data) < payload_len:
                    print(f"[⚠️ 불완전한 페이로드 수신] 예상: {payload_len}, 실제: {len(payload_data)}")
                    return False
            
            # 전체 메시지 파싱
            raw_data = header_data + payload_data
            raw_hex = raw_data.hex()
            print(f"[📩 수신 원문] {raw_hex}")
            
            # 메시지 파싱
            msg = TCPProtocol.parse_message(raw_data)
            if "type" in msg and msg["type"] == "INVALID":
                print(f"[⚠️ 메시지 파싱 실패] {msg.get('error', '알 수 없는 오류')}")
                return False
                
            cmd = msg.get("cmd", "")
            payload = msg.get("payload", {})
            
            # 디버깅: 수신 메시지 바이트 단위 분석 (특히 FINISH_LOADING 관련)
            if raw_hex.startswith("10") and len(raw_hex) >= 10:  # SERVER에서 오는 메시지(sender=0x10)
                cmd_byte = raw_hex[4:6]
                if cmd_byte == "05":  # FINISH_LOADING
                    print(f"[🔍 FINISH_LOADING 명령 감지] raw_hex={raw_hex}, 명령 바이트=0x{cmd_byte}")
                    print(f"[🔍 상세 파싱] sender={msg.get('sender')}, receiver={msg.get('receiver')}, cmd={cmd}, payload={payload}")
            
            # 수신한 명령 저장
            self.last_command = cmd
            
            # RUN 명령 유효성 검증 및 로깅
            if cmd == "RUN":
                # 위치 잠금 확인 - 가장 먼저 체크
                if self.position_locked:
                    print(f"[🔒 이동 거부 - 위치 잠금] 위치가 잠겨 있어 이동할 수 없습니다. 현재 위치: {self.current_position}")
                    print(f"[ℹ️ 안내] FINISH_LOADING 명령을 받아야 위치 잠금이 해제됩니다.")
                    self.send("ACK", {"cmd": "RUN", "status": "POSITION_LOCKED", "error": "POSITION_IS_LOCKED"}, wait=False)
                    return True
                
                # 현재 적재 또는 하역 작업 중인 경우 이동 금지 - 더 강력한 메시지와 함께 확실히 거부
                if self.loading_in_progress:
                    print(f"[🚫 이동 거부 - 강제 보호] 현재 {self.current_position}에서 적재 작업 중입니다.")
                    print(f"[🔒 상태 보호] loading_in_progress={self.loading_in_progress}, 위치={self.current_position}")
                    print(f"[⚠️ 경고] FINISH_LOADING 명령이 필요합니다. RUN 명령은 무시됩니다.")
                    self.send("ACK", {"cmd": "RUN", "status": "LOADING_IN_PROGRESS", "error": "CANNOT_MOVE_WHILE_LOADING"}, wait=False)
                    return True  # 명령 처리 완료로 간주하고 종료
                elif self.unloading_in_progress:
                    print(f"[🚫 이동 거부 - 강제 보호] 현재 {self.current_position}에서 하역 작업 중입니다.")
                    print(f"[⚠️ 경고] FINISH_UNLOADING 명령이 필요합니다. RUN 명령은 무시됩니다.")
                    self.send("ACK", {"cmd": "RUN", "status": "UNLOADING_IN_PROGRESS", "error": "CANNOT_MOVE_WHILE_UNLOADING"}, wait=False)
                    return True  # 명령 처리 완료로 간주하고 종료
                
                # LOAD_A/B에서 이동 시 강제 플래그 설정 - 네트워크 문제로 FINISH_LOADING을 놓친 경우 대비
                if self.current_position in ["LOAD_A", "LOAD_B"]:
                    if not self.loading_finished:
                        print(f"[⚠️ 안전 우회] {self.current_position}에서 RUN 명령을 수신하여 강제로 적재 완료 처리")
                        self.loading_finished = True
                        print(f"[🔑 적재 완료 플래그 강제 설정] loading_finished = True (RUN 명령 기반 강제 설정)")
                
                # RUN 명령 수신 플래그 설정 - 특히 LOAD_A/LOAD_B에서 CHECKPOINT_C로 이동하는 데 필요
                self.last_run_command_received = True
                print(f"[✅ RUN 명령 확인] 서버로부터 이동 명령을 수신했습니다. 다음 위치로 이동 준비 완료")
                print(f"[🔑 이동 플래그 설정] last_run_command_received = True")
                
                # target 파라미터 무시하고 현재 위치에 따라 다음 위치 자동 결정
                next_position = self._get_next_position()
                
                if next_position:
                    print(f"[🚚 자동 이동] 현재 위치({self.current_position})에서 다음 위치({next_position})로 이동합니다.")
                    
                    # 이동 전 상태 업데이트
                    self.run_state = "RUNNING"
                    
                    # 이동 시뮬레이션
                    print(f"[🚛 트럭 이동] {self.current_position} → {next_position} 이동 중...")
                    
                    # 실제 이동 시간 시뮬레이션 (2초)
                    time.sleep(2)
                    
                    # 이동 완료 후 위치 업데이트
                    old_position = self.current_position
                    self.current_position = next_position
                    self.target_position = next_position
                    
                    # 이동 후 상태 업데이트
                    self.run_state = "IDLE"
                    
                    # 도착 알림
                    print(f"[✅ 도착] {old_position} → {next_position} 이동 완료")
                    self.send("ARRIVED", {"position": next_position}, wait=False)
                    
                    # 목적지가 CHECKPOINT인 경우 게이트 ID 추가
                    if next_position.startswith("CHECKPOINT"):
                        gate_id = None
                        if next_position in ["CHECKPOINT_A", "CHECKPOINT_B"]:
                            gate_id = "GATE_A"
                        elif next_position in ["CHECKPOINT_C", "CHECKPOINT_D"]:
                            gate_id = "GATE_B"
                            
                        if gate_id:
                            print(f"[🚧 체크포인트] {next_position}에 도착, 게이트: {gate_id}")
                            # 게이트 관련 추가 메시지
                            self.send("ARRIVED", {"position": next_position, "gate_id": gate_id}, wait=False)
                    
                    # 목적지가 LOAD_A 또는 LOAD_B인 경우 - 자동 로딩 시작하지 않고 서버 명령 대기
                    elif next_position in ["LOAD_A", "LOAD_B"]:
                        print(f"[⏳ 적재 준비] {next_position}에 도착, 서버의 START_LOADING 명령 대기 중...")
                        # 서버의 명시적인 START_LOADING 명령을 기다림 (자동 로딩 시작하지 않음)
                    
                    # 목적지가 BELT인 경우 자동으로 START_UNLOADING 명령 전송
                    elif next_position == "BELT":
                        time.sleep(1)  # 약간의 지연 후 언로딩 시작
                        print(f"[🔄 자동 언로딩 시작] BELT에서 하역 작업 시작")
                        self.send("START_UNLOADING", {"position": next_position}, wait=False)
                        
                        # 언로딩 상태 설정 - 5초 후 자동으로 FINISH_UNLOADING 전송
                        self.unloading_in_progress = True
                        self.unloading_start_time = time.time()

                    # 목적지가 STANDBY인 경우 미션 완료로 간주하고 새 미션 요청
                    elif next_position == "STANDBY":
                        print(f"[✅ 미션 완료] 트럭이 STANDBY 위치에 도착했습니다. 미션 사이클이 완료되었습니다.")
                        # 미션 ID 초기화
                        self.mission_id = None
                        # 배터리 체크
                        if self.battery_level < 30:
                            print(f"[🔋 배터리 부족] 현재 배터리: {self.battery_level}%. 충전이 필요합니다.")
                            # 배터리가 부족하면 충전 요청은 서버에서 할 것이므로 별도 조치 없음
                        else:
                            # 잠시 대기 후 새 미션 요청
                            time.sleep(2)
                            print(f"[🔄 새 미션 요청] STANDBY 위치에서 자동으로 새 미션을 요청합니다.")
                            self.last_mission_request_time = time.time()  # 요청 타이머 갱신
                            self.assign_mission_request()  # 미션 요청
                else:
                    print(f"[⚠️ 경로 오류] 현재 위치({self.current_position})에서 다음 이동할 위치를 결정할 수 없습니다.")
                    print(f"[⚠️ 경고] 현재 위치({self.current_position})에서 다음 이동할 위치를 결정할 수 없습니다.")
            
            # 메시지 중복 처리 방지를 위한 체크
            # 중요 명령(RUN, GATE_OPENED, GATE_CLOSED)은 항상 처리
            important_cmds = ["RUN", "GATE_OPENED", "GATE_CLOSED", "START_LOADING", "FINISH_LOADING", "MISSION_ASSIGNED"]
            
            if cmd not in important_cmds and raw_hex in self.processed_messages:
                print(f"[🚫 중복 메시지] 일반 명령 중복으로 무시: {cmd} ({raw_hex})")
                return True
                
            # 메시지 ID 추적 (최대 20개 메시지만 기억)
            if cmd not in important_cmds:  # 중요 명령은 중복 체크 목록에 추가하지 않음
                self.processed_messages.add(raw_hex)
                if len(self.processed_messages) > 20:
                    self.processed_messages.pop()  # 가장 오래된 ID 제거
                
            # 마지막 메시지 정보 저장
            self.last_raw_hex = raw_hex
            
            print(f"[📩 수신] {cmd} ← {payload}")
            
            # 명령 처리
            if cmd == "HELLO_ACK":
                print("[✅ 서버 연결 확인] 서버에 등록되었습니다.")
                return True
                
            # START_LOADING 명령 처리
            elif cmd == "START_LOADING":
                position = payload.get("position", self.current_position)
                print(f"[✅ 적재 시작 명령 수신] 위치: {position}에서 적재 작업 시작")
                
                # 적재 작업 중 상태 설정 - 적재 중에는 이동 불가
                self.loading_in_progress = True
                self.loading_start_time = time.time()
                
                # 위치 잠금 활성화 - 적재 작업 중에는 위치 변경 불가
                self.position_locked = True
                self.original_position = self.current_position
                print(f"[🔒 위치 잠금 설정] 현재 위치 {self.current_position}를 적재 작업이 완료될 때까지 잠금")
                
                # 적재 시작 ACK 응답 전송
                self.send("ACK", {"cmd": "START_LOADING", "status": "SUCCESS"}, wait=False)
                return True
                
            # FINISH_LOADING 명령 처리
            elif cmd == "FINISH_LOADING":
                position = payload.get("position", self.current_position)
                print(f"[✅ 적재 완료 명령 수신] 위치: {position}에서 적재 작업 완료")
                print(f"[🔍 FINISH_LOADING 디버그] cmd={cmd}, position={position}, raw_hex={raw_hex}")
                print(f"[🔍 상태 정보] loading_in_progress={self.loading_in_progress}, position_locked={self.position_locked}")
                
                # 적재 상태 해제
                self.loading_in_progress = False
                self.loading_finished = True
                print(f"[🔍 상태 변경] loading_in_progress={self.loading_in_progress}, loading_finished={self.loading_finished}")
                
                # 위치 잠금 해제
                if self.position_locked:
                    self.position_locked = False
                    print(f"[🔓 위치 잠금 해제] 위치 잠금이 해제되었습니다. 이제 RUN 명령으로 이동할 수 있습니다.")
                
                # ACK 응답 전송
                self.send("ACK", {"cmd": "FINISH_LOADING", "status": "SUCCESS"}, wait=False)
                return True
                
            # DISPENSER_LOADED 명령 처리
            elif cmd == "DISPENSER_LOADED":
                dispenser_id = payload.get("dispenser_id", "DISPENSER")
                position = payload.get("position", "")
                print(f"[⭐ 디스펜서 적재 완료] 디스펜서 ID: {dispenser_id}, 위치: {position}")
                
                # 디스펜서 적재 완료 감지 시 즉시 FINISH_LOADING 상태로 처리 (자동화)
                if self.loading_in_progress:
                    print(f"[🔄 자동 FINISH_LOADING 처리] 디스펜서 적재 완료 감지, 적재 완료 처리 자동 실행")
                    
                    # 적재 작업 완료 상태로 변경
                    self.loading_in_progress = False
                    self.loading_finished = True
                    
                    # 위치 잠금 해제
                    if self.position_locked:
                        self.position_locked = False
                        print(f"[🔓 위치 잠금 해제] 위치 잠금이 해제되었습니다. 이제 RUN 명령으로 이동할 수 있습니다.")
                    
                    print(f"[🚛 경로 계획] 적재가 완료되었으므로 다음 위치(CHECKPOINT_C)로 이동할 준비가 되었습니다.")
                    print(f"[📝 상태 변경] loading_in_progress = {self.loading_in_progress}, loading_finished = {self.loading_finished}")
                    
                    # ACK 응답 전송
                    self.send("ACK", {"cmd": "FINISH_LOADING", "status": "SUCCESS", "position": position}, wait=False)
                    
                    # 임무 상태 업데이트
                    if self.run_state != "RUNNING":
                        self.run_state = "IDLE"  # 이동 명령을 기다리는 상태로 변경
                    
                    # 서버가 RUN 명령을 보낼 것을 대기
                    print(f"[⏩ 다음 단계 준비] 서버의 RUN 명령을 기다리는 중...")
                else:
                    print(f"[⚠️ 경고] 디스펜서 적재 완료 신호를 받았으나 트럭이 적재 중 상태가 아닙니다.")
                    
            # MISSION_ASSIGNED 처리
            elif cmd == "MISSION_ASSIGNED":
                source = payload.get("source", "")
                mission_id = payload.get("mission_id", "unknown")
                
                print(f"[📦 미션 정보 로깅] 수신 데이터: {payload}")
                
                if not source:
                    source = "LOAD_A"
                    print(f"[⚠️ 경고] 빈 source 값을 수신함 - 기본값 '{source}'을 사용합니다")
                
                # 대문자로 통일
                self.source = source.upper() if source else "LOAD_A"
                self.mission_id = mission_id
                self.run_state = "ASSIGNED"
                
                # 미션 요청 타이머 갱신 및 플래그 초기화
                self.last_mission_request_time = time.time()
                self.mission_request_in_progress = False
                
                print(f"[✅ 미션 수신] → 미션 ID: {mission_id}, source = {self.source}")
                print(f"[📝 미션 할당 확인] 미션 ID가 성공적으로 설정됨: {self.mission_id}, source = {self.source}")
                
                # source 값 확인 및 디버깅
                print(f"[🔍 미션 세부정보] 배정된 source 위치: {self.source} (원본 값: {source})")
                if self.source not in ["LOAD_A", "LOAD_B"]:
                    print(f"[⚠️ source 값 주의] 유효한 source 값이 아닙니다: {self.source}")
                    self.source = "LOAD_A"
                    print(f"[🔀 source 값 수정] 기본값으로 변경: {self.source}")
            
            # STOP 명령 처리
            elif cmd == "STOP":
                print(f"[🛑 정지 명령] 트럭 정지")
                self.run_state = "IDLE"
            
            # START_CHARGING 명령 처리
            elif cmd == "START_CHARGING":
                print("[🔌 충전 시작] 서버로부터 충전 명령을 받았습니다.")
                
                # 이미 100%이면 바로 충전 완료 알림
                if self.battery_level >= 100:
                    print("[✅ 충전 불필요] 배터리가 이미 100%입니다. 바로 충전 완료 신호를 보냅니다.")
                    self.send("FINISH_CHARGING", {"battery_level": self.battery_level}, wait=False)
                    
                    # 잠시 대기 후 미션 요청
                    time.sleep(1)
                    print(f"[🔄 충전 후 미션 요청] 배터리 충전 완료 후 새 미션을 요청합니다.")
                    self.last_mission_request_time = time.time()  # 요청 타이머 갱신
                    self.send("ASSIGN_MISSION", {}, wait=False)
                else:
                    # 충전 시작
                    self.charging = True  # 이 부분이 중요합니다. 무조건 충전 상태로 설정
                    print(f"[🔋 충전 중] 현재 배터리: {self.battery_level}%. 충전이 시작되었습니다.")
                    print(f"[ℹ️ 정보] 충전 완료 후 자동으로 새 미션을 요청합니다.")
                    
                # 명령에 대한 응답 추가
                self.send("ACK", {"cmd": "START_CHARGING", "status": "SUCCESS"}, wait=False)
            
            # NO_MISSION 응답 처리
            elif cmd == "NO_MISSION":
                reason = payload.get("reason", "NO_MISSIONS_AVAILABLE")
                wait_time = payload.get("wait_time", 10)
                print(f"[ℹ️ 미션 없음] 이유: {reason}")
                print(f"[ℹ️ 대기] {wait_time}초 후 다시 미션을 요청합니다.")
                
                # 미션 요청 타이머 갱신 및 플래그 초기화
                self.last_mission_request_time = time.time()
                self.mission_request_in_progress = False
                
                # 대기 시간 동안 하트비트 전송 (연결 유지)
                for i in range(wait_time, 0, -2):
                    print(f"[⏱️ 대기 중...] {i}초 남음")
                    time.sleep(2)
                    # 하트비트 전송
                    self.send("HELLO", {}, wait=False)
                
                # 대기 시간이 지난 후 자동으로 새 미션 요청
                print(f"[🔄 재요청] 대기 시간이 지났습니다. 새 미션을 자동으로 요청합니다.")
                self.assign_mission_request()
            
            # 하트비트 응답 처리
            elif cmd == "HEARTBEAT_ACK" or cmd == "HEARTBEAT_CHECK":
                print(f"[💓 하트비트] 서버와 연결 상태 양호")
                # 하트비트 체크에 응답
                if cmd == "HEARTBEAT_CHECK":
                    self.send("HELLO", {}, wait=False)
            
            # ARRIVED 명령 처리
            elif cmd == "ARRIVED":
                position = payload.get("position", "")
                
                # 위치 잠금 적용 - 위치가 잠긴 경우 ARRIVED 이벤트로 위치가 변경되지 않도록 함
                if self.position_locked and self.original_position:
                    if position != self.original_position:
                        print(f"[🚫 위치 변경 무시] 위치 잠금이 활성화된 상태입니다. ARRIVED 이벤트로 위치를 변경할 수 없습니다.")
                        print(f"[🔒 위치 보존] 현재 위치 {self.original_position}를 유지합니다. (무시된 위치: {position})")
                        # 원래 위치를 유지하기 위해 현재 위치 재설정
                        self.current_position = self.original_position
                        return True  # 이벤트 처리 종료
                
                # 추가 안전장치: LOAD 위치에서 CHECKPOINT_C로 이동하는 경우, FINISH_LOADING + RUN 명령 모두 필요
                if self.current_position in ["LOAD_A", "LOAD_B"] and position == "CHECKPOINT_C":
                    if not self.loading_finished:
                        print(f"[🚫 불법 이동 시도 감지] {self.current_position}에서 {position}로의 이동은 FINISH_LOADING 명령 없이 불가능합니다.")
                        print(f"[🔒 위치 보존] 현재 위치 {self.current_position}를 유지합니다.")
                        return True  # 이벤트 처리 종료
                    
                    if not hasattr(self, 'last_run_command_received') or not self.last_run_command_received:
                        print(f"[🚫 불법 이동 시도 감지] {self.current_position}에서 {position}로의 이동은 RUN 명령 없이 불가능합니다.")
                        print(f"[🔒 위치 보존] 현재 위치 {self.current_position}를 유지합니다.")
                        return True  # 이벤트 처리 종료
                
                # 위치 잠금이 없는 경우 정상적으로 위치 업데이트
                print(f"[📍 위치 변경] {self.current_position} → {position}")
                self.current_position = position
            
            return True
            
        except socket.timeout:
            # 타임아웃은 정상적인 상황
            return True
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            # 연결이 끊어진 경우에만 재연결 시도
            if isinstance(e, (ConnectionResetError, ConnectionRefusedError, ConnectionAbortedError)):
                print("[⚠️ 연결 끊김] 재연결 시도 중...")
                self.connect()  # 재연결
                time.sleep(1)  # 재연결 후 잠시 대기
            return False
        finally:
            self.client.settimeout(None)

    def assign_mission_request(self):
        """미션 할당 요청"""
        # 이미 미션 요청 중이면 중복 요청 방지
        if self.mission_request_in_progress:
            print("[⚠️ 미션 요청 중복] 이미 미션 요청이 진행 중입니다.")
            return False
            
        print("[🔍 미션 요청] 서버에 새로운 미션을 요청합니다...")
        self.mission_request_in_progress = True  # 요청 시작 플래그 설정
        
        if self.send("ASSIGN_MISSION", {}, wait=False):
            self.last_mission_request_time = time.time()  # 요청 타임스탬프 갱신
            # 요청 완료 플래그는 5초 후 자동 해제 (응답 대기 위해)
            threading.Timer(5.0, self._reset_mission_request_flag).start()
            return True
        else:
            print("[❌ 미션 요청 실패] 서버에 미션을 요청할 수 없습니다.")
            self.mission_request_in_progress = False  # 실패 시 즉시 플래그 해제
            return False
            
    def _reset_mission_request_flag(self):
        """미션 요청 중복 방지 플래그 초기화"""
        self.mission_request_in_progress = False
        print("[ℹ️ 미션 요청 상태 초기화] 다음 미션 요청이 가능합니다.")

    def run_simulation(self):
        """서버 명령에 따라 시뮬레이션 실행"""
        try:
            # 서버 연결 확인
            if not self.client:
                print("[⚠️ 서버 연결 없음] 연결을 시도합니다...")
                if not self.connect():
                    print("[❌ 시뮬레이션 취소] 서버에 연결할 수 없습니다.")
                    return False
            
            # 등록 메시지 전송
            if not self.send("HELLO", {}, wait=True):
                print("[❌ 초기화 실패] 서버에 등록할 수 없습니다.")
                return False
            
            # 초기 상태가 STANDBY이면 미션 요청
            if self.current_position == "STANDBY":
                print("[ℹ️ 초기 위치] STANDBY에서 시작")
                # 미션 요청
                print("[🚀 초기화] 미션 요청을 즉시 시작합니다.")
                time.sleep(1)  # 연결 안정화를 위한 짧은 대기
                self.assign_mission_request()
                
                # 서버가 응답할 시간을 주기 위해 잠시 대기
                time.sleep(2)
                
                # 미션을 받지 못했다면 중복 방지 플래그 초기화 (즉시 다시 요청 가능하도록)
                if not self.mission_id:
                    print("[⚠️ 미션 수신 안됨] 미션 요청 플래그를 초기화하여 다시 요청할 수 있도록 합니다.")
                    self.mission_request_in_progress = False
            else:
                # 현재 위치 보고
                print(f"[ℹ️ 현재 위치] {self.current_position}에서 시작")
                self.send("ARRIVED", {"position": self.current_position}, wait=False)
            
            # 무한 루프로 서버 명령 처리
            while True:
                # 서버 명령 처리
                self.process_server_commands()
                
                # 주기적인 하트비트 전송 (여기서는 생략, status_update_timer에서 처리)
                
                # 짧은 대기 후 다시 명령 확인
                time.sleep(0.1)
            
        except Exception as e:
            print(f"[❌ 시뮬레이션 오류] {e}")
            import traceback
            traceback.print_exc()
            return False
        
        return True

    def _get_next_position(self):
        """현재 위치에 따라 다음 위치 자동 결정
        경로 순서: SB → CPA → CPB → LA/LB → CPC → CPD → BLT → SB
        
        Returns:
            str: 다음 이동할 위치. 결정할 수 없으면 None 반환
        """
        position_map = {
            "STANDBY": "CHECKPOINT_A",
            "CHECKPOINT_A": "CHECKPOINT_B",
            "CHECKPOINT_B": self.source if self.source in ["LOAD_A", "LOAD_B"] else "LOAD_A",  # source 값에 따라 LOAD_A 또는 LOAD_B
            "LOAD_A": "CHECKPOINT_C",  # 이 경로는 RUN 명령이 있어야만 사용됨
            "LOAD_B": "CHECKPOINT_C",  # 이 경로는 RUN 명령이 있어야만 사용됨
            "CHECKPOINT_C": "CHECKPOINT_D",
            "CHECKPOINT_D": "BELT",
            "BELT": "STANDBY"
        }
        
        # LOAD_A 또는 LOAD_B에서 이동할 경우 특별 안전 체크
        if self.current_position in ["LOAD_A", "LOAD_B"]:
            # loading_in_progress가 True면 이동 불가
            if self.loading_in_progress:
                print(f"[🚫 자동 이동 금지] {self.current_position}에서 적재 작업이 진행 중입니다. RUN 명령을 받아도 이동할 수 없습니다.")
                print(f"[🔒 이동 보호] 먼저 FINISH_LOADING 명령을 받아야 이동할 수 있습니다.")
                return None
            
            # 위치 잠금이 활성화된 경우 이동 불가
            if self.position_locked:
                print(f"[🚫 이동 금지] {self.current_position} 위치가 잠겨 있어 이동할 수 없습니다.")
                print(f"[🔒 위치 보존] FINISH_LOADING 명령을 받아야 이동이 가능합니다.")
                return None
            
            # FINISH_LOADING 명령 확인 - LOAD_A/B에서 다음 위치로 가려면 반드시 필요
            if not self.loading_finished:
                print(f"[🚫 이동 금지] {self.current_position}에서 적재 완료 명령(FINISH_LOADING)을 받아야 이동 가능합니다.")
                return None
            
            # 마지막으로 받은 명령이 RUN이어야만 다음 위치로 이동
            if not hasattr(self, 'last_run_command_received') or not self.last_run_command_received:
                print(f"[🚫 이동 대기] {self.current_position}에서 다음 위치로 이동하려면 서버의 RUN 명령이 필요합니다.")
                return None
            
            # 안전장치를 통과했으므로 다음 위치로 이동
            print(f"[✅ 이동 허용] {self.current_position}에서 CHECKPOINT_C로 이동합니다.")
            self.last_run_command_received = False  # 사용 후 플래그 초기화
            self.loading_finished = False  # 이동 후 적재 완료 플래그 초기화
        
        # 특수 조건 처리
        if self.current_position in position_map:
            # CHECKPOINT_B에서 LOAD_A 또는 LOAD_B로 가는 경우 특별 처리
            if self.current_position == "CHECKPOINT_B":
                if self.source in ["LOAD_A", "LOAD_B"]:
                    next_pos = self.source
                    print(f"[🔀 경로 결정] 현재 위치 {self.current_position}에서 다음 목적지 → {next_pos} (source: {self.source})")
                else:
                    next_pos = "LOAD_A"  # 기본값
                    print(f"[🔀 경로 결정] 현재 위치 {self.current_position}에서 다음 목적지 → {next_pos} (source 없음, 기본값 사용)")
            else:
                next_pos = position_map[self.current_position]
                print(f"[🔀 경로 결정] 현재 위치 {self.current_position}에서 다음 목적지 → {next_pos}")
            
            # 미션이 없으면 대기장소로 이동 - 무한 반복 방지를 위해 비활성화
            # if not self.mission_id and self.current_position != "STANDBY":
            #     print(f"[🔀 경로 변경] 미션이 없으므로 대기장소(STANDBY)로 이동합니다.")
            #     return "STANDBY"
                
            return next_pos
        else:
            print(f"[⚠️ 경로 오류] 알 수 없는 위치: {self.current_position}")
            # 알 수 없는 위치인 경우 대기장소로 복귀
            return "STANDBY"

if __name__ == "__main__":
    try:
        print(f"[🚚 트럭 시뮬레이터] 서버 {HOST}:{PORT}에 연결을 시도합니다...")
        print(f"[ℹ️ 참고] 서버가 실행 중이 아니라면 먼저 'python run/run_main_server.py'를 실행하세요.")
        
        # 서버 연결 테스트
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(2.0)
        try:
            test_socket.connect((HOST, PORT))
            print(f"[✅ 서버 연결 성공] 서버 {HOST}:{PORT}가 응답합니다.")
            test_socket.close()
        except (ConnectionRefusedError, socket.timeout):
            print(f"[❌ 서버 연결 실패] 서버 {HOST}:{PORT}에 연결할 수 없습니다.")
            print(f"[ℹ️ 해결 방법] 먼저 'python run/run_main_server.py'를 실행하여 서버를 시작하세요.")
            print(f"[ℹ️ 해결 방법] 또는 이미 실행 중인 서버 프로세스를 종료하고 다시 시작해보세요.")
            print(f"[ℹ️ 서버 프로세스 종료 방법] 'pkill -f run_main_server.py' 명령어로 기존 서버를 종료할 수 있습니다.")
            sys.exit(1)
        
        # 시뮬레이터 시작
        simulator = TruckSimulator()
        
        # 초기 상태 설정
        simulator.battery_level = 80
        simulator.current_position = "STANDBY"
        simulator.run_state = "IDLE"
        
        print("[🚚 트럭 시뮬레이터 시작] 초기 배터리: 80%, 위치: STANDBY")
        
        # 시뮬레이션 실행 (무한 루프)
        while True:
            try:
                simulator.run_simulation()
                print("[⚠️ 시뮬레이션 종료] 10초 후 다시 시작합니다...")
                time.sleep(10)
            except KeyboardInterrupt:
                print("\n[👋 종료] 사용자에 의해 시뮬레이터가 종료되었습니다.")
                break
            except Exception as e:
                print(f"[⚠️ 오류 발생] {e}")
                print("[🔄 재시도] 10초 후 다시 시도합니다...")
                time.sleep(10)
                # 연결 재시도
                simulator.connect()
        
    except KeyboardInterrupt:
        print("\n[👋 종료] 사용자에 의해 시뮬레이터가 종료되었습니다.")
    except Exception as e:
        print(f"\n[❌ 오류] 시뮬레이터에서 예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        traceback.print_exc()
