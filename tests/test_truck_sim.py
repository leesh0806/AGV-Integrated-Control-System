import socket
import json
import time
import sys, os
import requests  # API 요청을 위한 모듈

# 현재 스크립트 경로를 기준으로 프로젝트 루트 경로를 추가합니다
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from backend.serialio.device_manager import DeviceManager
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
    "BELT": "BELT"
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
                
        msg = {
            "sender": "TRUCK_01",
            "receiver": "SERVER",
            "cmd": cmd,
            "payload": payload
        }
        data = json.dumps(msg) + "\n"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self.client.send(data.encode())
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
        timestamp = time.time()
        
        status_payload = {
            "timestamp": timestamp,
            "battery": {
                "level": self.battery_level,
                "is_charging": self.charging
            },
            "position": {
                "current": self.current_position,
                "run_state": self.run_state
            }
        }
        
        # 미션 정보가 있으면 추가
        if self.mission_id:
            status_payload["mission"] = {
                "mission_id": self.mission_id,
                "target": self.target_position
            }
        
        return self.send("STATUS_UPDATE", status_payload, wait=False)
    
    # 정기적인 상태 업데이트 타이머
    def status_update_timer(self, interval=3):
        """정기적으로 상태 업데이트 전송"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.updating:
            try:
                # 배터리 상태 업데이트 (서버 명령에 따라 충전 상태 변경)
                current_level = self.battery_level
                
                if self.charging:
                    # 충전 중일 때 (서버가 START_CHARGING 명령을 보낸 경우)
                    old_level = self.battery_level
                    self.battery_level = min(100, self.battery_level + 10)  # 10%씩 증가
                    print(f"[DEBUG] 배터리 충전 중: {old_level}% -> {self.battery_level}%")
                    
                    # 배터리가 100%에 도달하면 충전 완료 알림
                    if self.battery_level == 100 and old_level < 100:
                        print(f"[✅ 충전 완료] 배터리가 100%에 도달했습니다. 충전 완료 신호를 보냅니다.")
                        self.charging = False
                        self.send("FINISH_CHARGING", {"battery_level": self.battery_level}, wait=False)
                        
                        # 잠시 대기 후 미션 요청
                        time.sleep(1)
                        print(f"[🔍 충전 후 미션 요청] 배터리 충전 완료 후 새 미션을 요청합니다.")
                        self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                elif self.current_position == "STANDBY":
                    # STANDBY에서는 배터리 유지
                    print(f"[DEBUG] STANDBY 상태: 배터리 유지 {self.battery_level}%")
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
                
                # 로딩 작업 완료 처리 (5초 후)
                if self.loading_in_progress and (current_time - self.loading_start_time >= 5.0):
                    print(f"[✅ 적재 완료] 5초 경과 - FINISH_LOADING 자동 전송")
                    self.send("FINISH_LOADING", {}, wait=False)
                    self.loading_in_progress = False
                
                # 언로딩 작업 완료 처리 (5초 후)
                if self.unloading_in_progress and (current_time - self.unloading_start_time >= 5.0):
                    print(f"[✅ 하역 완료] 5초 경과 - FINISH_UNLOADING 자동 전송")
                    self.send("FINISH_UNLOADING", {}, wait=False)
                    self.unloading_in_progress = False
                
                # 짧은 간격으로 체크
                time.sleep(interval)
            except Exception as e:
                print(f"[⚠️ 작업 타이머 오류] {e}")
                time.sleep(1.0)  # 오류 발생 시 잠시 대기

    def process_server_commands(self, timeout=5.0):
        """서버에서 오는 명령을 처리"""
        self.client.settimeout(timeout)
        try:
            data = self.client.recv(4096)
            if not data:
                print("[❌ 연결 종료] 서버와의 연결이 끊어졌습니다.")
                self.connect()  # 재연결
                time.sleep(1)  # 재연결 후 잠시 대기
                return False
                
            raw = data.decode('utf-8').strip()
            for line in raw.splitlines():
                print(f"[📩 수신] {line}")
                try:
                    msg = json.loads(line)
                    cmd = msg.get("cmd", "")
                    payload = msg.get("payload", {})
                    
                    # MISSION_ASSIGNED 처리
                    if cmd == "MISSION_ASSIGNED":
                        source = payload.get("source", "")
                        mission_id = payload.get("mission_id", "unknown")
                        
                        if not source:
                            source = "LOAD_A"
                            print(f"[⚠️ 경고] 빈 source 값을 수신함 - 기본값 '{source}'을 사용합니다")
                        
                        self.source = source.upper()
                        self.mission_id = mission_id
                        self.run_state = "ASSIGNED"
                        print(f"[✅ 미션 수신] → 미션 ID: {mission_id}, source = {self.source}")
                    
                    # RUN 명령 처리
                    elif cmd == "RUN":
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
                            
                            # 목적지가 LOAD_A 또는 LOAD_B인 경우 자동으로 START_LOADING 명령 전송
                            elif next_position in ["LOAD_A", "LOAD_B"]:
                                time.sleep(1)  # 약간의 지연 후 로딩 시작
                                print(f"[🔄 자동 로딩 시작] {next_position}에서 적재 작업 시작")
                                self.send("START_LOADING", {}, wait=False)
                                
                                 # 로딩 상태 설정 - 5초 후 자동으로 FINISH_LOADING 전송
                                self.loading_in_progress = True
                                self.loading_start_time = time.time()
                            
                            # 목적지가 BELT인 경우 자동으로 START_UNLOADING 명령 전송
                            elif next_position == "BELT":
                                time.sleep(1)  # 약간의 지연 후 언로딩 시작
                                print(f"[🔄 자동 언로딩 시작] BELT에서 하역 작업 시작")
                                self.send("START_UNLOADING", {}, wait=False)
                                
                                # 언로딩 상태 설정 - 5초 후 자동으로 FINISH_UNLOADING 전송
                                self.unloading_in_progress = True
                                self.unloading_start_time = time.time()
                            
                            # 대기 위치(STANDBY)에 도착한 경우 미션 완료 및 새 미션 요청
                            elif next_position == "STANDBY":
                                # 현재 미션이 있으면 완료 처리
                                if self.mission_id:
                                    print(f"[✅ 미션 완료] 미션 ID: {self.mission_id} 완료 (STANDBY 도착)")
                                      # 미션 정보 초기화
                                    old_mission_id = self.mission_id
                                    self.mission_id = None
                                    self.target_position = None
                                    
                                    # 잠시 대기 후 새 미션 요청
                                    time.sleep(2)
                                
                                    # 새로운 미션 요청
                                    print(f"[🔍 새 미션 요청] STANDBY 위치에서 새로운 미션을 요청합니다.")
                                    self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                        else:
                            print(f"[⚠️ 경고] 현재 위치({self.current_position})에서 다음 이동할 위치를 결정할 수 없습니다.")
                    
                    # STOP 명령 처리
                    elif cmd == "STOP":
                        print(f"[🛑 정지 명령] 트럭 정지")
                        self.run_state = "IDLE"
                    
                    # GATE_OPENED 명령 처리
                    elif cmd == "GATE_OPENED":
                        gate_id = payload.get("gate_id")
                        print(f"[🚧 게이트 열림] {gate_id}가 열렸습니다.")
                        # ACK 응답
                        self.send("ACK_GATE_OPENED", {"gate_id": gate_id}, wait=False)
                        
                        # 게이트 열림 후 자동으로 이동하지 않음 (서버가 명시적으로 RUN 명령을 보낼 때만 이동)
                        # 서버에서 보낸 RUN 명령만 처리하도록 대기
                    
                    # GATE_CLOSED 명령 처리
                    elif cmd == "GATE_CLOSED":
                        gate_id = payload.get("gate_id")
                        print(f"[🚧 게이트 닫힘] {gate_id}가 닫혔습니다.")
                        
                        # 게이트가 닫히면 자동으로 다음 위치로 이동
                        # 다음 목적지 결정
                        next_target = None
                        
                        # 현재 위치에 따라 다음 위치 자동 결정
                        if self.current_position == "CHECKPOINT_B" and gate_id == "GATE_A":
                            if self.mission_id:  # 미션이 있을 때만
                                # 로딩 위치로 이동 (source 값에 따라 LOAD_A 또는 LOAD_B로)
                                next_target = self.source if self.source in ["LOAD_A", "LOAD_B"] else "LOAD_A"
                                print(f"[🚚 자동 이동] {self.current_position} → {next_target} (게이트 닫힘 후)")
                                
                                # 서버에 RUN 명령 요청하지 않고 직접 이동 시작
                                self.run_state = "RUNNING"
                                print(f"[🚛 트럭 이동] {self.current_position} → {next_target} 이동 중...")
                                
                                # 실제 이동 시간 시뮬레이션 (2초)
                                time.sleep(2)
                                
                                # 이동 완료 후 위치 업데이트
                                old_position = self.current_position
                                self.current_position = next_target
                                self.target_position = next_target
                                
                                # 이동 후 상태 업데이트
                                self.run_state = "IDLE"
                                
                                # 도착 알림
                                print(f"[✅ 도착] {old_position} → {next_target} 이동 완료")
                                self.send("ARRIVED", {"position": next_target}, wait=False)
                                
                                # LOAD_A/LOAD_B에 도착한 경우 자동 로딩 시작
                                if next_target in ["LOAD_A", "LOAD_B"]:
                                    time.sleep(1)  # 약간의 지연 후 로딩 시작
                                    print(f"[🔄 자동 로딩 시작] {next_target}에서 적재 작업 시작")
                                    self.send("START_LOADING", {}, wait=False)
                                    
                                    # 로딩 상태 설정 - 5초 후 자동으로 FINISH_LOADING 전송
                                    self.loading_in_progress = True
                                    self.loading_start_time = time.time()
                        
                        elif self.current_position == "CHECKPOINT_D" and gate_id == "GATE_B":
                            # CHECKPOINT_D에서 게이트가 닫히면 BELT로 이동
                            next_target = "BELT"
                            print(f"[🚚 자동 이동] {self.current_position} → {next_target} (게이트 닫힘 후)")
                            
                            # 서버에 RUN 명령 요청하지 않고 직접 이동 시작
                            self.run_state = "RUNNING"
                            print(f"[🚛 트럭 이동] {self.current_position} → {next_target} 이동 중...")
                            
                            # 실제 이동 시간 시뮬레이션 (2초)
                            time.sleep(2)
                            
                            # 이동 완료 후 위치 업데이트
                            old_position = self.current_position
                            self.current_position = next_target
                            self.target_position = next_target
                            
                            # 이동 후 상태 업데이트
                            self.run_state = "IDLE"
                            
                            # 도착 알림
                            print(f"[✅ 도착] {old_position} → {next_target} 이동 완료")
                            self.send("ARRIVED", {"position": next_target}, wait=False)
                            
                            # BELT에 도착한 경우 자동 언로딩 시작
                            time.sleep(1)  # 약간의 지연 후 언로딩 시작
                            print(f"[🔄 자동 언로딩 시작] BELT에서 하역 작업 시작")
                            self.send("START_UNLOADING", {}, wait=False)
                            
                            # 언로딩 상태 설정 - 5초 후 자동으로 FINISH_UNLOADING 전송
                            self.unloading_in_progress = True
                            self.unloading_start_time = time.time()
                    
                    # START_CHARGING 명령 처리
                    elif cmd == "START_CHARGING":
                        print("[🔌 충전 시작] 서버로부터 충전 명령을 받았습니다.")
                        
                        # 이미 100%이면 바로 충전 완료 알림
                        if self.battery_level >= 100:
                            print("[✅ 충전 불필요] 배터리가 이미 100%입니다. 바로 충전 완료 신호를 보냅니다.")
                            self.send("FINISH_CHARGING", {"battery_level": self.battery_level}, wait=False)
                            
                            # 잠시 대기 후 미션 요청
                            time.sleep(1)
                            print(f"[🔍 충전 후 미션 요청] 배터리 충전 완료 후 새 미션을 요청합니다.")
                            self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                        else:
                            # 충전 시작
                            self.charging = True
                            # 충전 시작 응답
                            self.send("ACK_CHARGING", {"status": "started"}, wait=False)
                    
                    # STOP_CHARGING 명령 처리
                    elif cmd == "STOP_CHARGING":
                        print("[🔌 충전 중지] 서버로부터 충전 중지 명령을 받았습니다.")
                        self.charging = False
                        # 충전 중지 응답
                        self.send("ACK_CHARGING", {"status": "stopped", "battery_level": self.battery_level}, wait=False)
                    
                    # CHARGING_COMPLETED 명령 처리
                    elif cmd == "CHARGING_COMPLETED":
                        print("[✅ 충전 완료 확인] 서버가 충전 완료를 확인했습니다.")
                        self.charging = False
                    
                    # NO_MISSION 응답 처리
                    elif cmd == "NO_MISSION":
                        reason = payload.get("reason", "NO_MISSIONS_AVAILABLE")
                        wait_time = payload.get("wait_time", 10)
                        print(f"[ℹ️ 미션 없음] 이유: {reason}")
                        print(f"[ℹ️ 대기] {wait_time}초 후 다시 미션을 요청합니다.")
                        
                        # 대기 시간 동안 하트비트 전송 (연결 유지)
                        for i in range(wait_time, 0, -2):
                            print(f"[⏱️ 대기 중...] {i}초 남음")
                            time.sleep(2)
                            # 하트비트 전송
                            self.send("HELLO", {"msg": "heartbeat"}, wait=False)
                        
                        # 대기 후 미션 재요청
                        print("[🔍 미션 재요청] 서버에 미션을 다시 요청합니다.")
                        self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                    
                    # 하트비트 응답 처리
                    elif cmd == "HEARTBEAT_ACK" or cmd == "HEARTBEAT_CHECK":
                        print(f"[💓 하트비트] 서버와 연결 상태 양호")
                        # 하트비트 체크에 응답
                        if cmd == "HEARTBEAT_CHECK":
                            self.send("HELLO", {"msg": "heartbeat"}, wait=False)
                    
                    # START_LOADING 명령 처리
                    elif cmd == "START_LOADING":
                        print(f"[🔄 로딩 시작] 서버로부터 START_LOADING 명령 수신")
                        # 로딩 상태 설정 - 5초 후 자동으로 FINISH_LOADING 전송
                        self.loading_in_progress = True
                        self.loading_start_time = time.time()
                    
                    # START_UNLOADING 명령 처리
                    elif cmd == "START_UNLOADING":
                        print(f"[🔄 언로딩 시작] 서버로부터 START_UNLOADING 명령 수신")
                        # 언로딩 상태 설정 - 5초 후 자동으로 FINISH_UNLOADING 전송
                        self.unloading_in_progress = True
                        self.unloading_start_time = time.time()
                    
                    # FINISH_LOADING 명령 처리
                    elif cmd == "FINISH_LOADING":
                        print(f"[✅ 로딩 완료] 서버로부터 FINISH_LOADING 명령 수신")
                        self.loading_in_progress = False
                    
                    # FINISH_UNLOADING 명령 처리
                    elif cmd == "FINISH_UNLOADING":
                        print(f"[✅ 언로딩 완료] 서버로부터 FINISH_UNLOADING 명령 수신")
                        self.unloading_in_progress = False
                    
                    # 기타 메시지
                    else:
                        print(f"[ℹ️ 기타 메시지] {msg}")
                
                except json.JSONDecodeError:
                    print("[ℹ️ 비JSON 메시지 무시]")
                    continue
            
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
        print("[🔍 미션 요청] 서버에 새로운 미션을 요청합니다...")
        if self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False):
            return True
        else:
            print("[❌ 미션 요청 실패] 서버에 미션을 요청할 수 없습니다.")
            return False

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
            if not self.send("HELLO", {"msg": "register"}, wait=True):
                print("[❌ 초기화 실패] 서버에 등록할 수 없습니다.")
                return False
            
            # 초기 상태가 STANDBY이면 미션 요청
            if self.current_position == "STANDBY":
                print("[ℹ️ 초기 위치] STANDBY에서 시작")
                # 미션 요청
                self.assign_mission_request()
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
            "LOAD_A": "CHECKPOINT_C",
            "LOAD_B": "CHECKPOINT_C",
            "CHECKPOINT_C": "CHECKPOINT_D",
            "CHECKPOINT_D": "BELT",
            "BELT": "STANDBY"
        }
        
        # 특수 조건 처리
        if self.current_position in position_map:
            next_pos = position_map[self.current_position]
            print(f"[🔀 경로 결정] 현재 위치 {self.current_position}에서 다음 목적지 → {next_pos}")
            
            # 미션이 없으면 대기장소로 이동
            if not self.mission_id and self.current_position != "STANDBY":
                print(f"[🔀 경로 변경] 미션이 없으므로 대기장소(STANDBY)로 이동합니다.")
                return "STANDBY"
                
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
