import socket
import json
import time
import sys, os

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

# 포트 맵: 시리얼 장치 연결에 사용됨 - 서버와 동일한 설정 사용
port_map = {
    "GATE_A": "GATE_A",
    "GATE_B": "GATE_B",
    "BELT": "BELT"
}

# 시리얼 매니저 초기화 - 실제 포트 맵 사용
manager = DeviceManager(port_map=port_map, use_fake=True)

class TruckSimulator:
    def __init__(self):
        self.source = None
        self.client = None
        self.battery_level = 100
        self.charging = False
        self.current_position = "STANDBY"
        self.run_state = "IDLE"
        self.connect()
        
        # 상태 업데이트 타이머 시작
        self.updater_thread = threading.Thread(target=self.status_update_timer, daemon=True)
        self.updater_thread.start()

    # TCP 연결
    def connect(self):
        if self.client:
            try:
                self.client.close()
            except:
                pass
        
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"[TCP 연결] {HOST}:{PORT}")
        self.client.connect((HOST, PORT))

    # 메시지 전송
    def send(self, cmd, payload={}, wait=True):
        msg = {
            "sender": "TRUCK_01",
            "receiver": "SERVER",
            "cmd": cmd,
            "payload": payload
        }
        data = json.dumps(msg) + "\n"
        try:
            self.client.send(data.encode())
            print(f"[SEND] {cmd} → {payload}")
            if wait:
                time.sleep(0.5)
        except (BrokenPipeError, ConnectionResetError):
            print("[⚠️ 연결 끊김] 서버에 재연결 시도 중...")
            self.connect()
            self.send(cmd, payload, wait)  # 재시도
    
    # 통합 상태 업데이트 전송
    def send_status_update(self):
        """통합 상태 업데이트 전송"""
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
        
        self.send("STATUS_UPDATE", status_payload, wait=False)
    
    # 정기적인 상태 업데이트 타이머
    def status_update_timer(self, interval=3):
        """정기적으로 상태 업데이트 전송"""
        while True:
            try:
                # 배터리 상태 업데이트
                current_level = self.battery_level
                
                if self.charging:
                    self.battery_level = min(100, self.battery_level + 5)
                    print(f"[DEBUG] 배터리 충전 중: {current_level}% -> {self.battery_level}%")
                elif self.current_position == "STANDBY":
                    # STANDBY에서는 배터리 유지
                    print(f"[DEBUG] STANDBY 상태: 배터리 유지 {self.battery_level}%")
                else:
                    self.battery_level = max(0, self.battery_level - 5)
                    print(f"[DEBUG] 배터리 감소 중: {current_level}% -> {self.battery_level}% (위치: {self.current_position})")
                
                # 통합 상태 업데이트 전송
                self.send_status_update()
                
                time.sleep(interval)
            except Exception as e:
                print(f"[ERROR] 상태 업데이트 중 오류 발생: {str(e)}")
                time.sleep(1)
                continue

    # 미션 수신 대기
    def wait_for_mission_response(self, timeout=5.0):
        self.client.settimeout(timeout)
        try:
            while True:
                # 데이터 수신
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
                        if msg.get("cmd") == "MISSION_ASSIGNED":
                            source = msg["payload"]["source"]
                            # source가 비어있는 경우 기본값 설정
                            if not source:
                                source = "LOAD_A"
                                print(f"[⚠️ 경고] 빈 source 값을 수신함 - 기본값 '{source}'을 사용합니다")
                            
                            self.source = source.upper()
                            print(f"[✅ 미션 수신] → source = {self.source}")
                            return True
                        elif msg.get("cmd") == "NO_MISSION":
                            reason = msg.get("payload", {}).get("reason", "")
                            if reason == "BATTERY_LOW" or reason == "CHARGING":
                                print(f"[🔋 충전 필요] {reason}")
                                self.charging = True  # 충전 상태로 설정
                                self.run_state = "CHARGING"
                                # 충전이 완료될 때까지 대기
                                while True:
                                    time.sleep(5)  # 5초마다 배터리 상태 확인
                                    if self.battery_level >= 100:
                                        print("[🔋 충전 완료] 충전 완료 메시지 전송")
                                        self.charging = False
                                        self.run_state = "IDLE"
                                        self.send("FINISH_CHARGING", wait=False)
                                        return self.wait_for_mission_response()
                            else:
                                print("[ℹ️ 미션 없음] 서버에서 미션이 없다고 응답함. 3초 후 재요청.")
                                time.sleep(3)
                                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                                # 재귀적으로 다시 대기
                                return self.wait_for_mission_response()
                        elif msg.get("cmd") == "START_CHARGING":
                            print("[🔋 충전 시작] 서버로부터 충전 명령 수신")
                            self.charging = True
                            self.run_state = "CHARGING"
                            # 충전이 완료될 때까지 대기
                            while self.battery_level < 100:
                                time.sleep(1)
                            print("[🔋 충전 완료] 100% 도달")
                            self.charging = False
                            self.run_state = "IDLE"
                            self.send("FINISH_CHARGING", wait=False)
                            return self.wait_for_mission_response()
                        elif msg.get("cmd") == "CHARGING_COMPLETED":
                            print("[🔋 충전 완료 메시지 수신]")
                            self.charging = False
                            self.run_state = "IDLE"
                            # 배터리가 30% 이하일 때만 다시 충전 요청
                            if self.battery_level <= 30:
                                print(f"[🔋 배터리 부족] {self.battery_level}% - 충전 요청")
                                self.charging = True
                                self.run_state = "CHARGING"
                                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                            else:
                                print(f"[🔋 배터리 충분] {self.battery_level}% - 미션 요청")
                                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                            return self.wait_for_mission_response()
                        elif msg.get("cmd") == "RUN":
                            print("[ℹ️ RUN 명령 수신]")
                            self.run_state = "RUNNING"
                            continue
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
            return False
        except socket.timeout:
            print("[⏰ 타임아웃] MISSION_ASSIGNED 수신 실패")
            self.connect()  # 재연결
            time.sleep(1)  # 재연결 후 잠시 대기
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            self.connect()  # 재연결
            time.sleep(1)  # 재연결 후 잠시 대기
            return False
        finally:
            self.client.settimeout(None)

    def wait_for_gate_response(self, timeout=15.0):
        """
        게이트 열림 명령을 기다립니다.
        게이트가 열리면 ACK_GATE_OPENED를 보내야 합니다.
        """
        self.client.settimeout(timeout)
        received_gate_open = False
        
        try:
            # 게이트 응답 대기 (최대 timeout 초)
            start_time = time.time()
            while time.time() - start_time < timeout:
                # 소켓에서 데이터를 읽음
                try:
                    raw = self.client.recv(4096).decode()
                    if not raw:
                        time.sleep(0.1)
                        continue
                except socket.timeout:
                    continue
                
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        cmd = msg.get("cmd", "")
                        
                        # GATE_OPENED 명령을 받으면 성공
                        if cmd == "GATE_OPENED":
                            print("[✅ 게이트 열림 확인]")
                            received_gate_open = True
                        
                        # RUN 명령 처리
                        elif cmd == "RUN":
                            print("[ℹ️ RUN 명령 수신]")
                            self.run_state = "RUNNING"
                        
                        # GATE_CLOSED는 이전 게이트에 대한 것이므로 무시
                        elif cmd == "GATE_CLOSED":
                            continue
                            
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                            
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
                
                # GATE_OPENED를 받았으면 루프 종료
                if received_gate_open:
                    return True
                
        except socket.timeout:
            print("[⏰ 타임아웃] GATE_OPENED 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)
        
        return received_gate_open

    def wait_for_run_command(self, timeout=5.0):
        """
        RUN 명령을 기다립니다.
        """
        self.client.settimeout(timeout)
        received_run = False
        
        try:
            print("[🔄 RUN 명령 대기 중...]")
            # RUN 명령 대기 (최대 timeout 초)
            start_time = time.time()
            while time.time() - start_time < timeout:
                # 소켓에서 데이터를 읽음
                try:
                    raw = self.client.recv(4096).decode()
                    if not raw:
                        time.sleep(0.1)
                        continue
                except socket.timeout:
                    continue
                
                for line in raw.splitlines():
                    print(f"[📩 수신] {line}")
                    try:
                        msg = json.loads(line)
                        cmd = msg.get("cmd", "")
                        
                        # RUN 명령을 받으면 성공
                        if cmd == "RUN":
                            print("[✅ RUN 명령 수신 - 이동 시작]")
                            self.run_state = "RUNNING"
                            received_run = True
                            break
                        else:
                            print(f"[ℹ️ 기타 메시지] {msg}")
                            
                    except json.JSONDecodeError:
                        print("[ℹ️ 비JSON 메시지 무시]")
                        continue
                
                # RUN을 받았으면 루프 종료
                if received_run:
                    return True
            
        except socket.timeout:
            print("[⏰ 타임아웃] RUN 명령 수신 실패")
            return False
        except Exception as e:
            print(f"[❌ 오류] → {e}")
            return False
        finally:
            self.client.settimeout(None)
        
        return received_run

    def run_full_mission(self):
        # 최초 1회만 등록 및 초기화
        self.send("HELLO", {"msg": "register"}, wait=False)
        time.sleep(0.1)
        
        # 첫 미션 요청
        self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
        mission_received = self.wait_for_mission_response()
        if not mission_received:
            print("[ℹ️ 미션 없음] 3초 후 다시 시도합니다.")
            time.sleep(3)
            self.run_full_mission()  # 재귀 호출로 다시 시작
            return

        while True:
            try:
                # ✅ 전체 미션 수행
                print("\n[🚛 트럭 이동] CHECKPOINT_A로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.current_position = "CHECKPOINT_A"
                self.charging = False
                
                # 도착 알림
                self.send("ARRIVED", {"position": "CHECKPOINT_A", "gate_id": "GATE_A"})
                
                if self.wait_for_gate_response():
                    self.send("ACK_GATE_OPENED")
                    # RUN 명령을 기다린 후 이동
                    if self.wait_for_run_command():
                        print("\n[🚛 트럭 이동] CHECKPOINT_B로 이동 중...")
                    else:
                        print("[❌ 오류] RUN 명령을 받지 못했습니다.")
                        return
                else:
                    print("[❌ 오류] GATE_A가 열리지 않았습니다.")
                    return

                time.sleep(2)  # 이동 시간
                self.current_position = "CHECKPOINT_B"
                self.send("ARRIVED", {"position": "CHECKPOINT_B", "gate_id": "GATE_A"})

                print(f"\n[🚛 트럭 이동] {self.source}로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.current_position = self.source
                self.send("ARRIVED", {"position": self.source})  # load_A or load_B

                print("\n[📦 적재 시작]")
                time.sleep(1)  # 적재 준비 시간
                self.run_state = "LOADING"
                self.send("START_LOADING")
                time.sleep(3)  # 적재 시간
                self.send("FINISH_LOADING")
                self.run_state = "IDLE"
                
                print("\n[🚛 트럭 이동] CHECKPOINT_C로 이동 중...")
                time.sleep(2)
                self.current_position = "CHECKPOINT_C"
                self.send("ARRIVED", {"position": "CHECKPOINT_C", "gate_id": "GATE_B"})
                
                if self.wait_for_gate_response():
                    self.send("ACK_GATE_OPENED")
                    # RUN 명령을 기다린 후 이동
                    if self.wait_for_run_command():
                        print("\n[🚛 트럭 이동] CHECKPOINT_D로 이동 중...")
                    else:
                        print("[❌ 오류] RUN 명령을 받지 못했습니다.")
                        return
                else:
                    print("[❌ 오류] GATE_B가 열리지 않았습니다.")
                    return

                time.sleep(2)  # 이동 시간
                self.current_position = "CHECKPOINT_D"
                self.send("ARRIVED", {"position": "CHECKPOINT_D", "gate_id": "GATE_B"})

                print("\n[🚛 트럭 이동] BELT로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.current_position = "BELT"
                self.send("ARRIVED", {"position": "BELT"})

                print("\n[📦 하차 시작]")
                time.sleep(1)  # 하차 준비 시간
                self.run_state = "UNLOADING"
                self.send("START_UNLOADING")
                time.sleep(3)  # 하차 시간
                self.send("FINISH_UNLOADING")
                self.run_state = "IDLE"

                print("\n[🚛 트럭 이동] STANDBY로 이동 중...")
                time.sleep(2)  # 이동 시간
                self.current_position = "STANDBY"
                self.send("ARRIVED", {"position": "STANDBY"})
                
                print("\n✅ 한 턴 완료. 다음 미션을 기다립니다.")
                time.sleep(2)
                
                # STANDBY에 도착한 후에만 새 미션 요청
                self.send("ASSIGN_MISSION", {"battery_level": self.battery_level}, wait=False)
                mission_received = self.wait_for_mission_response()
                if not mission_received:
                    print("[ℹ️ 미션 없음] 3초 후 다시 시도합니다.")
                    time.sleep(3)
                    continue
            except Exception as e:
                print(f"\n❌ 테스트 실패: {e}")
                break

if __name__ == "__main__":
    simulator = TruckSimulator()
    simulator.run_full_mission()
