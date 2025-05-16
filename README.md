![배너](https://github.com/jinhyuk2me/iot-dust/blob/main/assets/images/banner.png?raw=true)

---

## 📚 목차

1. [프로젝트 개요](#1-프로젝트-개요)  
2. [기술 스택](#2-기술-스택)  
3. [프로젝트 목적 / 필요성](#3-프로젝트-목적--필요성)  
4. [시스템 아키텍처](#4-시스템-아키텍처)  
5. [요구사항 정의 (UR / SR)](#5-요구사항-정의)  
6. [데이터베이스 구성 및 출처](#6-데이터베이스-구성-및-출처)  
7. [기능 설명](#7-기능-설명)  
8. [한계점](#8-한계점)  
9. [디렉토리 구조](#9-디렉토리-구조)

---

# 🚚 IoT 기반 운송로봇 관제 시스템

## 📦 1. 프로젝트 개요

<p align="center">
  <img src="https://github.com/jinhyuk2me/iot-dust/blob/main/assets/images/gui/main_monitoring_1.gif?raw=true" width="45%" style="margin-right:10px;">
  <img src="https://github.com/jinhyuk2me/iot-dust/blob/main/assets/images/truck/truck_1.gif?raw=true" width="45%">
</p>

> ⏰ **프로젝트 기간**: 2025.05.12 ~ 2025.05.15

**D.U.S.T. (Dynamic Unified Smart Transport)** 는 소형 운송 로봇을 기반으로, **센서 입력 → 서버 제어 → 트럭 주행 → 설비 제어 → GUI 반영**까지 운송 시스템의 제어 흐름 전체를 통합하여 구현한 **IoT 기반 관제 시스템**입니다.

트럭은 RFID 태그를 인식하며 지정된 경로를 따라 주행하고, 서버는 FSM 로직을 통해 상태에 따른 제어 명령을 전송합니다. 관제자는 GUI를 통해 전체 상태를 확인하고, 필요한 시설 및 트럭 제어를 직접 수행할 수 있습니다.

---

## 🛠️ 2. 기술 스택

| 분류 | 기술 구성 | 배지 |
|------|-----------|------|
| **MCU 및 펌웨어** | ESP32-WROOM, Arduino IDE | ![ESP32](https://img.shields.io/badge/ESP32-WROOM-E7352C?style=for-the-badge&logo=espressif&logoColor=white) ![Arduino](https://img.shields.io/badge/Arduino-00979D?style=for-the-badge&logo=arduino&logoColor=white) |
| **센서** | RFID, 초음파 센서, IR 라인트레이서 | ![RFID](https://img.shields.io/badge/RFID-0052CC?style=for-the-badge) ![Ultrasonic](https://img.shields.io/badge/Ultrasonic-8E44AD?style=for-the-badge) ![Infrared](https://img.shields.io/badge/IR%20Sensor-E67E22?style=for-the-badge) |
| **통신** | TCP 소켓 통신 (JSON / Byte 프로토콜) | ![TCP](https://img.shields.io/badge/TCP%20Socket-0052CC?style=for-the-badge&logo=protocols&logoColor=white) ![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white) |
| **제어 로직** | 상태기반 FSM (Finite State Machine) | ![FSM](https://img.shields.io/badge/FSM%20Control-008080?style=for-the-badge) |
| **프로그래밍 언어** | Python 3.12 | ![Python](https://img.shields.io/badge/python-3776AB?style=for-the-badge&logo=python&logoColor=white) |
| **관제 UI** | PyQt6 (QTabWidget 기반) | ![PyQt6](https://img.shields.io/badge/PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white) |
| **DB 연동** | MySQL, PyMySQL | ![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white) ![PyMySQL](https://img.shields.io/badge/PyMySQL-3776AB?style=for-the-badge&logo=python&logoColor=white) |
| **버전 관리** | Git, GitHub | ![Git](https://img.shields.io/badge/git-F05032?style=for-the-badge&logo=git&logoColor=white) ![GitHub](https://img.shields.io/badge/github-181717?style=for-the-badge&logo=github&logoColor=white) |

---

## 🎯 3. 프로젝트 목적 / 필요성

본 프로젝트는 **경로 기반 운송 로봇을 제어하고 전체 시스템 흐름을 일관되게 구성하는 데 중점**을 두었습니다. 단순한 주행 제어나 UI가 아닌, **센서 입력부터 서버 FSM 처리, 설비 제어, GUI 반영까지 전 영역을 아우르는 구현**을 목표로 했습니다.

### 🔍 추진 배경

- 물류 현장에는 **일정한 경로를 반복 이동하며 상호작용하는 소형 로봇 시스템**의 수요가 많으며, 이를 실제로 구현하려면 **센서, 통신, 판단, 제어, UI**가 모두 유기적으로 연결되어야 합니다.
- 본 시스템은 이러한 연결 구조를 **단일 통합 흐름으로 구성**하였고, 복잡하지 않지만 명확하게 작동하는 시스템을 직접 설계/개발했습니다.

---

### ⚙️ 구현 범위

- **FSM 기반 상태 전이 제어 시스템** 구축 (서버 측 상태 판단 및 명령 송신)
- **ESP32 기반 트럭 제어 및 센서 통합 (RFID + 초음파 등)**
- **TCP 기반 메시지 송수신 구조 설계 및 바이트 프로토콜 구현**
- **PyQt 기반 관제 UI 구성 (지도 시각화 + 제어 패널 통합)**
- **MySQL 기반 미션/상태/로그 관리 연동**

> 본 시스템은 각 요소가 독립적으로 기능하는 것이 아닌, **서버와 로봇, 설비와 GUI가 실시간으로 연결되어 동작하는 구조**에 초점을 맞췄습니다.

---

## 🧾 4. 요구사항 정의 (UR / SR)

본 시스템의 기능은 사용자 관점에서의 요구사항(**User Requirement, UR**)과  이를 만족시키기 위한 시스템 관점의 요구사항(**System Requirement, SR**)으로 나뉘며, 각 항목은 구현된 기능 기준으로 우선순위(Priority)를 함께 정의하였습니다.

### ✅ User Requirement (UR)

| ID | 요구사항 내용 | 우선순위 |
|----|----------------|---------|
| UR_01 | 차량은 특정 장소로 이동할 수 있어야 한다. | R |
| UR_02 | 이동에 사용되는 차량은 무인 주행이 가능해야 한다. | O |
| UR_03 | 권한 있는 사용자만 시스템에 접속할 수 있어야 한다. | R |
| UR_04 | 차량 이동 단계별 상태를 실시간으로 모니터링할 수 있어야 한다. | R |
| UR_05 | 차량의 상태 기록을 저장하고 조회할 수 있어야 한다. | R |
| UR_06 | 각 시설의 상태를 모니터링할 수 있어야 한다. | R |
| UR_07 | 차량 출입은 허가된 차량에 한해 이루어져야 한다. | R |
| UR_08 | 자동화된 적재 시설이 존재해야 한다. | R |
| UR_09 | 적재 시설은 수동 제어도 가능해야 한다. | O |
| UR_10 | 차량은 자동으로 화물을 적하할 수 있어야 한다. | R |
| UR_11 | 화물 저장소가 자동화되어 있어야 한다. | R |
| UR_12 | 저장소는 가용성을 고려해 자동으로 선택되어야 한다. | O |
| UR_13 | 저장소는 상황에 따라 동작을 정지할 수 있어야 한다. | R |

### ✅ System Requirement (SR)

| ID | 기능명 | 설명 |
|-----|--------|------|
| SR_01 | 차량 모니터링 기능 | 트럭의 위치, 상태, 미션 진행 상황을 실시간 확인 |
| SR_02 | 시설 모니터링 기능 | 게이트, 벨트, 적재소 등 주요 시설 상태 시각화 |
| SR_03 | 사용자 권한 관리 기능 | 로그인, 접근 권한 설정 및 사용자 정보 관리 |
| SR_04 | 작업 관리 기능 | 미션 등록, 실행, 로그 기록 및 조회 기능 |
| SR_05 | 중앙 통제 기능 | 트럭과 시설을 통합 제어하는 FSM 기반 중앙 서버 |
| SR_06 | 차량 자동 주행 기능 | 지정 경로에 따라 무인 주행 및 장애물 정지 |
| SR_07 | 적하 기능 | 적재 완료 후 화물을 자동으로 하역 |
| SR_08 | 위치 인식 기능 | RFID 기반으로 트럭 위치 판단 및 상태 연동 |
| SR_09 | 상태 보고 기능 | 미션, 위치, 배터리 등의 상태를 서버에 실시간 송신 |
| SR_10 | 출입 제어 기능 | 차량 출입 여부를 게이트에서 확인 및 제한 |
| SR_11 | 게이트 자동 제어 기능 | 차량 통과 여부에 따라 자동 개폐 수행 |
| SR_12 | 적재소 차량 감지 기능 | 트럭 도착 여부 인식 및 응답 처리 |
| SR_13 | 적재소 자동 제어 기능 | 서버 명령에 따라 화물 적하 자동 제어 |
| SR_14 | 적재소 수동 제어 기능 | 수동으로 자원 투하 명령 가능 (GUI에서 제어 가능) |
| SR_15 | 벨트 이송 제어 기능 | 중앙 서버 명령에 따라 벨트 작동 및 정지 |
| SR_16 | 저장소 적재량 감지 기능 | 컨테이너의 실시간 적재 상태 모니터링 |
| SR_17 | 저장소 선택 자동화 기능 | 저장소 가용성에 따라 자동으로 저장 대상 결정 |
| SR_18 | 자동 정지 기능 | 중앙 명령 또는 저장소 포화 시 운반 시스템 정지 |
| SR_19 | 충전소 기능 | 배터리 상태에 따라 자동 충전 및 대기 전환 |

> 우선순위(R: Required / O: Optional)는 개발 당시의 시스템 구조 설계 기준이며,  
> 대부분의 필수 요구사항은 이번 구현에 포함되어 있으며, 일부 선택 항목도 기본 동작 구조 내 포함되어 있습니다.


---

## 🧩 4. 시스템 아키텍처

본 프로젝트는 **트럭 디바이스, 관제 서버, 설비 컨트롤러, 사용자 인터페이스**로 구성된  
IoT 기반 분산 제어 시스템입니다. 각 구성요소는 다음과 같은 통신 구조로 연결됩니다:

- **TCP 통신**: 트럭 ↔ 중앙 서버 간 양방향 명령/상태 전송
- **시리얼 통신**: 서버 ↔ 설비 컨트롤러(벨트, 게이트, 디스펜서) 간 유선 명령 전송
- **HTTP 통신**: 관제 UI ↔ 서버 내 서비스 레이어 간 RESTful API 호출

<p align="center">
  <img src="https://github.com/jinhyuk2me/iot-dust/blob/main/assets/images/system%20architecture/system.png?raw=true" width="85%">
</p>

---

### 🧠 서버 중심 구조 및 소프트웨어 계층

서버는 FSM 기반 제어 흐름을 중심으로, 다음과 같은 구성 요소로 설계되어 있습니다:

- **Main Controller**: 트럭 및 설비를 제어하는 중앙 FSM / 명령 관리자
- **TruckFSM**: 트럭 상태 전이 및 이벤트 처리 로직
- **FacilityManager**: Gate, Belt, Dispenser 제어 라우팅
- **StatusManager**: 각 장치의 상태를 실시간 수집 및 DB 반영
- **MissionManager**: 미션 등록, 상태 변경, 로그 기록 처리

<p align="center">
  <img src="https://github.com/jinhyuk2me/iot-dust/blob/main/assets/images/system%20architecture/sw.png?raw=true" width="70%">
</p>

---

### 🏗 하드웨어 구성 및 연결 구조

각 요소는 물리적으로 다음과 같은 장치 및 통신 방식으로 구성되어 있습니다:

- **트럭**: ESP32 기반 주행 제어, RFID/초음파 센서 장착, DC 모터 구동
- **시설**: Arduino 기반 컨트롤러 (게이트/벨트/적재소), Servo 및 Step Motor 제어
- **충전소**: 배터리 상태 감지 및 충전 명령 응답

<p align="center">
  <img src="https://github.com/jinhyuk2me/iot-dust/blob/main/assets/images/system%20architecture/hw.png?raw=true" width="70%">
</p>

> 이와 같은 아키텍처 구성은 **현실 환경의 제어 흐름을 소형화·모듈화**한 구조로,  
> 각 장치 간 통신 및 상태 연계를 실제 작동 가능한 수준까지 구현하였습니다.

