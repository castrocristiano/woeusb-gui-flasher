# Interface Contract: Burn Engine (Asynchronous Qt Worker)

**Feature**: WoeUSB GUI Flasher (`001-woeusb-gui`)  
**Interface**: `BurnWorker` (`QThread` / `QObject`)  
**Pattern**: Qt Signals & Slots  

---

## 1. Overview

The `BurnWorker` handles all disk, archive, and command operations in a background worker thread. It communicates with the UI layer exclusively through strongly-typed Qt signals.

---

## 2. Signals & Signatures

```python
from PySide6.QtCore import QObject, Signal


class BurnWorkerSignals(QObject):
    # Emitted when overall progress or stage changes
    # Args: (progress_percent: float, stage_text: str, speed_text: str)
    progress_changed = Signal(float, str, str)

    # Emitted for real-time console/drawer log lines
    # Args: (log_line: str)
    log_line_emitted = Signal(str)

    # Emitted on critical status transition
    # Args: (status_message: str, is_warning: bool)
    status_updated = Signal(str, bool)

    # Emitted upon completion or error
    # Args: (success: bool, final_message: str)
    operation_finished = Signal(bool, str)
```

---

## 3. Public Slots & Methods

### `start_burn(config: BurnConfiguration) -> None`
- Starts the execution pipeline in the worker thread.
- Transitions state from `IDLE` to `VALIDATING`.

### `request_cancel() -> None`
- Sets internal cancellation flag `_abort_requested = True`.
- Sends `SIGTERM` to any active child processes (`7z`, `wimlib-imagex`).
- Triggers cleanup logic: unmounts any temporary filesystem mounts created during the operation.
- Emits `operation_finished(False, "Operação cancelada pelo usuário.")`.

---

## 4. Error Handling Contract

- Any unhandled exception or non-zero subprocess exit code MUST:
  1. Capture stderr/stdout and emit it via `log_line_emitted`.
  2. Attempt safe unmount/cleanup of target drive.
  3. Emit `operation_finished(False, localized_error_explanation)`.
  4. Never crash or leave the GUI in an indeterminate disabled state.

