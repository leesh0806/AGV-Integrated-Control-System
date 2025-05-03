import socket
import json
import time

HOST = '127.0.0.1'
PORT = 8000

truck_id = "TRUCK_001"
source = None  # load_A 또는 load_B

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))
print(f"[TCP 연결] {HOST}:{PORT}")

def send(cmd, payload=None, wait=True):
    msg = {
        "sender": truck_id,
        "receiver": "SERVER",
        "cmd": cmd,
        "payload": payload or {}
    }
    client.send((json.dumps(msg) + "\n").encode('utf-8'))
    print(f"[TCP Send] {json.dumps(msg)}")
    print(f"[SEND] {cmd} → {msg['payload']}")
    if wait:
        input("▶ 엔터를 누르면 계속 진행합니다...")

def wait_for_mission_response(timeout=3.0):
    global source
    client.settimeout(timeout)
    try:
        while True:
            data = client.recv(4096)
            raw = data.decode('utf-8').strip()
            for line in raw.splitlines():
                print(f"[📩 수신 원문] {line}")
                if not line.startswith("{"):
                    print("[ℹ️ 비JSON 메시지 무시]")
                    continue

                msg = json.loads(line)
                if msg.get("cmd") == "MISSION_ASSIGNED":
                    source = msg["payload"]["source"].upper()
                    print(f"[✅ 미션 수신] → source = {source}")
                    return True
                else:
                    print("[⚠️ 예상치 못한 응답]", msg)
        return False
    except socket.timeout:
        print("[⏰ 타임아웃] MISSION_ASSIGNED 수신 실패")
        return False
    except Exception as e:
        print(f"[❌ JSON 파싱 오류] → {e}")
        return False
    finally:
        client.settimeout(None)

def run_full_mission():
    # ✅ 트럭 등록
    send("HELLO", {"msg": "register"}, wait=False)
    time.sleep(0.1)

    # ✅ 상태 초기화 (IDLE로 리셋)
    send("RESET", wait=False)
    time.sleep(0.1)

    # ✅ 미션 요청
    send("ASSIGN_MISSION", wait=False)
    if not wait_for_mission_response():
        return

    # ✅ 전체 미션 수행
    send("ARRIVED", {"position": "CHECKPOINT_A", "gate_id": "GATE_A"})
    send("ACK_GATE_OPENED")
    send("ARRIVED", {"position": source})  # load_A or load_B
    send("START_LOADING")
    send("FINISH_LOADING")
    send("ARRIVED", {"position": "CHECKPOINT_C", "gate_id": "GATE_B"})
    send("ACK_GATE_OPENED")
    send("ARRIVED", {"position": "BELT"})
    send("START_UNLOADING")
    send("FINISH_UNLOADING")
    send("ARRIVED", {"position": "STANDBY"})

    print("\n✅ 테스트 완료: 정상 시나리오 흐름 종료")

if __name__ == "__main__":
    run_full_mission()
