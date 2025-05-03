
# D.U.S.T. - IoT기반 자율 운송관제 시스템

**D.U.S.T. (Dynamic Unified Smart Transport)** 는 희토류 및 광물 자원의 자동 운송을 목표로 하는 IoT 기반 자율 운송 관제 시스템입니다.  
RFID, 시리얼, TCP 통신을 기반으로 차량 위치 파악, 게이트 제어, 벨트 운송 등 복합 제어를 통합 관리합니다.

---

## 🗂️ 디렉터리 구조

```bash
.
├── backend/       # 제어 서버, TCP/시리얼 통신, 미션 관리
├── frontend/      # PyQt 기반 GUI 인터페이스
├── firmware/      # 트럭, 게이트, 벨트용 ESP/Arduino 펌웨어
├── documents/     # 발표자료, 설계 문서, UML 다이어그램
├── tests/         # 가상 시리얼 장치 테스트 코드
```

---

## 🚀 실행 방법

### 1. TCP 서버 실행
```bash
python3 backend/run_tcp_server.py
```

---

## 🧠 주요 기능

| 기능 항목         | 설명 |
|------------------|------|
| 차량 위치 추적   | RFID 센서 → 중앙서버 위치 보고 |
| 게이트 제어       | TCP 명령 → 시리얼 명령 전환 → 아두이노 제어 |
| 벨트 컨트롤       | 트럭 도착 시 자동 컨베이어 작동 |
| 미션 관리         | 미션 DB, 상태 관리 FSM 기반 처리 |
| GUI 인터페이스    | 운송 현황, 시설 상태 모니터링 (PyQt6 기반) |

---

## 🛠 기술 스택

- **Python 3.12**: 전체 서버 로직
- **PyQt6**: GUI 프론트엔드
- **Socket**: TCP 통신 (트럭 ↔ 서버)
- **pyserial**: 시리얼 통신 (서버 ↔ MCU)
- **ESP32/Arduino**: 트럭/게이트/벨트 제어용 펌웨어
- **draw.io**: UML 다이어그램

---

## 🧾 문서 및 설계자료

- 📊 발표자료: `documents/DUST_ IoT기반 자율 운송관제 시스템.pptx`
- 🧭 상태도: `documents/uml/state_diagram_for_truck.drawio`
- 💡 초기 설계안: `documents/IoT 프로젝트 초안.pptx`
