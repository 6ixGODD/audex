# Service Layer Usage Examples

This document provides examples of how to use the domain services in the audex system.

## Overview

The service layer is organized by domain:

- **DoctorService**: Handles doctor authentication and voiceprint management
- **SessionService**: Manages conversation session lifecycle
- **ExportService**: Exports session data to USB or other storage

All services inherit from `BaseService` which provides logging capabilities.

## Doctor Service

### Registration

```python
from audex.service.doctor import DoctorService
from audex.lib.database.sqlite import SQLite
from audex.lib.vpr.xfyun import XFYunVPR
from audex.lib.store.localfile import LocalFileStore

# Initialize dependencies
sqlite = SQLite("path/to/database.db")
vpr = XFYunVPR(config)
store = LocalFileStore(config)

# Create service
doctor_service = DoctorService(sqlite, vpr, store)

# Register new doctor
doctor = await doctor_service.register(
    username="dr_zhang",
    password="secure_password",
    name="张医生",
    employee_number="H12345",
    department="内科",
    hospital_name="市人民医院",
)
print(f"Doctor registered: {doctor.id}")
```

### Login

```python
# Login existing doctor
doctor = await doctor_service.login(
    username="dr_zhang",
    password="secure_password",
)
print(f"Welcome {doctor.name}!")
```

### Voiceprint Registration

```python
# Register voiceprint (first-time or re-registration)
with open("voiceprint.wav", "rb") as f:
    audio_data = f.read()

registration = await doctor_service.register_voiceprint(
    doctor_id=doctor.id,
    audio_data=audio_data,
    sample_rate=16000,
    vp_text="请朗读以下内容进行声纹注册：零一二三四五六七八九",
    vpr_group_id="hospital_001",
    vpr_system="xfyun",
)
print(f"Voiceprint registered: {registration.vp_id}")
```

## Session Service

### Creating a Session

```python
from audex.service.session import SessionService

# Initialize service
session_service = SessionService(sqlite)

# Create new session with clinical information
session = await session_service.create_session(
    doctor_id=doctor.id,
    patient_name="李女士",
    outpatient_number="2024112301",
    medical_record_number="MR-987654",
    notes="初诊，主诉头痛",
)
print(f"Session created: {session.id}")
```

### Starting and Managing Session

```python
# Start the session (begin recording)
session = await session_service.start_session(session.id)
print(f"Session status: {session.status}")  # SessionStatus.IN_PROGRESS

# ... recording happens here ...

# Complete the session
session = await session_service.complete_session(session.id)
print(f"Session status: {session.status}")  # SessionStatus.COMPLETED
```

### Updating Session Information

```python
# Update clinical information during or after session
session = await session_service.update_session_info(
    session_id=session.id,
    notes="患者诉说头痛持续3天，伴有恶心",
)
```

## Export Service

### Exporting Session Data

```python
from audex.service.export import ExportService

# Initialize service
export_service = ExportService(sqlite, store)

# Export session to local directory
export_stats = await export_service.export_session(
    session_id=session.id,
    export_path="/tmp/exports",
    include_audio=True,
)

print(f"Exported to: {export_stats['export_path']}")
print(f"Conversation JSON: {export_stats['conversation_file']}")
print(f"Audio files: {export_stats['audio_count']}")
```

### Exporting to USB Device

```python
# Export directly to USB device
try:
    export_stats = await export_service.export_to_usb(
        session_id=session.id,
        usb_mount_point="/media/usb",
    )
    print(f"Exported to USB: {export_stats['export_path']}")
except IOError as e:
    print(f"USB export failed: {e}")
```

## Export File Structure

When exporting a session, the following directory structure is created:

```
{export_path}/{session_id}/
├── conversation.json
└── audio/
    ├── segment-001.wav
    ├── segment-002.wav
    └── segment-003.wav
```

### Conversation JSON Format

```json
{
  "session_id": "session-abc123",
  "doctor_id": "doctor-xyz789",
  "patient_name": "李女士",
  "outpatient_number": "2024112301",
  "medical_record_number": "MR-987654",
  "status": "completed",
  "started_at": "2024-11-23T12:30:00+00:00",
  "ended_at": "2024-11-23T12:45:00+00:00",
  "notes": "初诊，主诉头痛",
  "created_at": "2024-11-23T12:29:00+00:00",
  "utterances": [
    {
      "sequence": 1,
      "speaker": "doctor",
      "text": "您好，今天哪里不舒服？",
      "confidence": 0.95,
      "start_time_ms": 1000,
      "end_time_ms": 3500,
      "duration_ms": 2500,
      "timestamp": "2024-11-23T12:30:01+00:00"
    },
    {
      "sequence": 2,
      "speaker": "patient",
      "text": "医生，我最近总是头疼。",
      "confidence": 0.88,
      "start_time_ms": 4000,
      "end_time_ms": 6800,
      "duration_ms": 2800,
      "timestamp": "2024-11-23T12:30:04+00:00"
    }
  ]
}
```

## Complete Workflow Example

```python
import asyncio
from audex.service.doctor import DoctorService
from audex.service.session import SessionService
from audex.service.export import ExportService

async def complete_workflow():
    # 1. Doctor Registration
    doctor_service = DoctorService(sqlite, vpr, store)
    doctor = await doctor_service.register(
        username="dr_wang",
        password="password123",
        name="王医生",
        employee_number="H67890",
        department="外科",
        hospital_name="市人民医院",
    )
    
    # 2. Voiceprint Registration
    with open("voiceprint.wav", "rb") as f:
        audio_data = f.read()
    
    await doctor_service.register_voiceprint(
        doctor_id=doctor.id,
        audio_data=audio_data,
        sample_rate=16000,
        vp_text="声纹注册文本",
        vpr_group_id="hospital_001",
        vpr_system="xfyun",
    )
    
    # 3. Create and Start Session
    session_service = SessionService(sqlite)
    session = await session_service.create_session(
        doctor_id=doctor.id,
        patient_name="张先生",
        outpatient_number="2024112302",
        medical_record_number="MR-123456",
    )
    
    await session_service.start_session(session.id)
    
    # ... Recording and conversation processing ...
    
    # 4. Complete Session
    await session_service.complete_session(session.id)
    
    # 5. Export to USB
    export_service = ExportService(sqlite, store)
    export_stats = await export_service.export_to_usb(
        session_id=session.id,
        usb_mount_point="/media/usb",
    )
    
    print(f"Workflow completed! Exported to: {export_stats['export_path']}")

# Run the workflow
asyncio.run(complete_workflow())
```

## Error Handling

All services raise appropriate exceptions:

```python
from audex.service.doctor import DoctorService

try:
    # Try to register duplicate username
    doctor = await doctor_service.register(
        username="existing_user",
        password="password",
        name="Test",
    )
except ValueError as e:
    print(f"Registration failed: {e}")

try:
    # Try to login with wrong password
    doctor = await doctor_service.login(
        username="dr_zhang",
        password="wrong_password",
    )
except ValueError as e:
    print(f"Login failed: {e}")
```
