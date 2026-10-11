# Tasks: WoeUSB GUI Flasher (Universal Linux via Flatpak)

**Input**: Design documents from `/specs/001-woeusb-gui/`  
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [research.md](research.md), [contracts/](contracts/)  
**Status**: Ready for Implementation  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory structure, Flatpak manifest, and desktop assets.

- [X] T001 Create project package structure and `__init__.py` in `src/woeusb_gui_flasher/` and `tests/`
- [X] T002 [P] Create Flatpak builder manifest `org.woeusb.WoeUsbGui.yml` configured for `org.kde.Platform` 6.6 with permissions `--system-talk-name=org.freedesktop.UDisks2`, `--filesystem=host:ro`, `--filesystem=/run/media:rw`, `--socket=wayland`, `--socket=fallback-x11`
- [X] T003 [P] Create application icon `assets/org.woeusb.WoeUsbGui.svg` and desktop shortcut entry `assets/org.woeusb.WoeUsbGui.desktop`
- [X] T004 [P] Create AppStream metadata `assets/org.woeusb.WoeUsbGui.metainfo.xml` for Linux app stores (Flathub, Discover, GNOME Software)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core domain entities, data models, state machine enums, and utility helpers required by all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 [P] Implement domain models and enums in `src/woeusb_gui_flasher/models.py`:
  - `StorageDevice`: `name: str`, `path: str`, `size_bytes: int` (constraint: `> 2,000,000,000` / 2 GB), `size_human: str`, `vendor: str`, `model: str`, `is_removable: bool` (constraint: `TRAN == "usb"` or `RM == true`), `is_system_drive: bool` (constraint: `True` if mounts `/`, `/boot`, `/home`, etc.), `mount_points: list[str]`, `partitions: list[str]`
  - `WindowsISO`: `file_path: Path`, `file_name: str`, `size_bytes: int`, `size_human: str`, `has_install_wim: bool`, `has_install_esd: bool`, `install_image_size: int`, `requires_split: bool` (constraint: `True` if `install_image_size > 4,294,967,295` and FAT32), `is_valid: bool`
  - `FileSystemType` enum (`FAT32`, `NTFS`), `BootMode` enum (`UEFI_AND_LEGACY`, `UEFI_ONLY`)
  - `BurnConfiguration`: `iso: WindowsISO`, `target_device: StorageDevice`, `filesystem: FileSystemType`, `boot_mode: BootMode`, `label: str = "WININSTALL"`
  - `BurnStage` enum (`IDLE`, `VALIDATING`, `UNMOUNTING`, `PARTITIONING`, `FORMATTING`, `MOUNTING`, `EXTRACTING_ISO`, `SPLITTING_WIM`, `CONFIGURING_BOOT`, `FINALIZING`, `COMPLETED`, `ERROR`, `CANCELLED`)
  - `BurnOperationState`: `stage: BurnStage`, `stage_description: str`, `progress_percent: float`, `bytes_written: int`, `total_bytes: int`, `transfer_speed: str`, `elapsed_seconds: int`, `is_running: bool`, `error_message: str | None`
- [X] T006 [P] Implement utility functions in `src/woeusb_gui_flasher/utils.py` for byte formatting (`format_bytes`), subprocess execution with streaming output, and path sanitization
- [X] T007 Implement unit tests for domain models and utility helpers in `tests/test_models.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Instalação e Execução Universal via Flatpak (Priority: P1)

**Goal**: Permitir a execução universal em qualquer distribuição Linux via Flatpak sem dependências manuais, com suporte a Wayland e X11.

**Independent Test**: Executar `python -m woeusb_gui_flasher` ou `./run.sh` e verificar que a aplicação inicializa sem erros de importação e valida o manifesto Flatpak.

- [X] T008 [P] [US1] Contract test for Flatpak manifest compliance in `tests/test_flatpak_contract.py` validating permissions (`--system-talk-name=org.freedesktop.UDisks2`, `--filesystem=host:ro`, `--filesystem=/run/media:rw`, `--socket=wayland`)
- [X] T009 [US1] Implement application entry point in `src/woeusb_gui_flasher/main.py` with `QApplication` initialization, Wayland/X11 display handling, and styling
- [X] T010 [US1] Implement package execution entry point in `src/woeusb_gui_flasher/__main__.py` allowing `python -m woeusb_gui_flasher`
- [X] T011 [US1] Create standalone convenience executable script `run.sh` with execution permissions (`chmod +x run.sh`)

**Checkpoint**: User Story 1 pronta e testável de forma independente.

---

## Phase 4: User Story 3 - Detecção Segura e Isolamento de Dispositivos (Priority: P1)

**Goal**: Descobrir pendrives USB conectados (`/dev/sdX`), aplicar filtro inegociável de segurança para excluir discos de sistema (`/`, `/boot`, `/home`, `[SWAP]`, NVMe/SATA internos), e suportar desmontagem de partições ativas.

**Independent Test**: Conectar pendrive USB de teste e executar `disk_manager.get_removable_devices()`, verificando que apenas pendrives USB elegíveis são retornados e que discos internos são 100% omitidos.

- [X] T012 [P] [US3] Contract test for UDisks2 enumeration and safety filter invariants in `tests/test_udisks2_contract.py` verifying that system mount points and non-USB drives are never classified as eligible
- [X] T013 [US3] Implement `DiskManager` in `src/woeusb_gui_flasher/disk_manager.py` using D-Bus `org.freedesktop.UDisks2.ObjectManager.GetManagedObjects()` with `lsblk -J -b` fallback
- [X] T014 [US3] Implement non-destructive filtering logic in `src/woeusb_gui_flasher/disk_manager.py` ensuring `TRAN == "usb"` or `RM == true` and excluding any drive mounting core system paths
- [X] T015 [US3] Implement partition unmount routine in `src/woeusb_gui_flasher/disk_manager.py` using `org.freedesktop.UDisks2.Filesystem.Unmount()` or `udisksctl unmount`
- [X] T016 [US3] Implement unit and integration tests for disk detection and filtering in `tests/test_disk_manager.py`

**Checkpoint**: User Story 3 pronta e testável de forma independente.

---

## Phase 5: User Story 2 - Gravação de Imagem do Windows em Pendrive USB (Priority: P1) 🎯 MVP

**Goal**: Executar o fluxo completo de gravação: validação da ISO, formatação via UDisks2, extração em espaço de usuário (`7z`), divisão de `install.wim` (> 4 GB) para FAT32 com `wimlib-imagex`, e configuração de bootloader UEFI/BIOS.

**Independent Test**: Executar uma queima com imagem ISO válida (ou mock) para dispositivo de teste e validar que todas as fases (`FORMATTING` -> `EXTRACTING_ISO` -> `SPLITTING_WIM` -> `CONFIGURING_BOOT` -> `FINALIZING`) completam com sucesso.

- [X] T017 [P] [US2] Contract test for burn engine signals in `tests/test_burn_engine_contract.py` verifying `progress_changed`, `log_line_emitted`, `status_updated`, and `operation_finished`
- [X] T018 [US2] Implement `BurnWorker` (`QThread` / `QObject`) in `src/woeusb_gui_flasher/burn_engine.py` with Qt signals and execution state transitions
- [X] T019 [US2] Implement partition creation and formatting (MBR + FAT32/NTFS) in `src/woeusb_gui_flasher/burn_engine.py` via `UDisks2.Block.Format()` or `mkfs.vfat`/`mkfs.ntfs`
- [X] T020 [US2] Implement user-space ISO extraction in `src/woeusb_gui_flasher/burn_engine.py` using `7z x -bso0 -bsp1 -bd` into the mounted drive path
- [X] T021 [US2] Implement automatic `install.wim` split in `src/woeusb_gui_flasher/burn_engine.py` via `wimlib-imagex split <wim_path> <dest_swm_path> 3800` when target is FAT32 and file > 4 GB
- [X] T022 [US2] Implement UEFI and Legacy BIOS bootloader configuration and `sync` buffer flush in `src/woeusb_gui_flasher/burn_engine.py`
- [X] T023 [US2] Implement unit tests for `BurnWorker` execution flow with mocked subprocesses in `tests/test_burn_engine.py`

**Checkpoint**: User Story 2 (MVP) completa e funcional.

---

## Phase 6: User Story 4 - Feedback Visual e Observabilidade em Tempo Real (Priority: P2)

**Goal**: Interface gráfica moderna em PySide6 / Qt 6 com seleção de ISO, seletor de pendrive seguro, barra de progresso suave, gaveta de logs expansível e diálogo de confirmação de segurança.

**Independent Test**: Abrir a janela da aplicação, selecionar uma ISO de teste, verificar atualização da UI em 60 FPS e validar que o diálogo modal de confirmação exige clique explícito do usuário.

- [X] T024 [P] [US4] Implement reusable UI components in `src/woeusb_gui_flasher/ui/components.py` (`IsoSelectorCard`, `DriveSelectorCard`, `OptionsCard`, `ProgressCard`, `LogConsoleDrawer`)
- [X] T025 [US4] Implement main window layout and signal wiring in `src/woeusb_gui_flasher/ui/main_window.py` connecting `DiskManager` and `BurnWorker` to the UI controls
- [X] T026 [US4] Implement explicit destructive operation confirmation modal dialog in `src/woeusb_gui_flasher/ui/main_window.py` displaying target device path, vendor/model, size, and data loss warning
- [X] T027 [US4] Implement UI integration tests with `pytest-qt` in `tests/test_ui.py`

**Checkpoint**: User Story 4 completa e integrada ao motor de gravação.

---

## Phase 7: User Story 5 - Cancelamento Seguro e Tratamento de Erros (Priority: P3)

**Goal**: Permitir o cancelamento seguro da gravação a qualquer momento com encerramento de subprocessos (`SIGTERM`) e limpeza de pontos de montagem, exibindo erros de Polkit/IO com clareza.

**Independent Test**: Iniciar uma gravação de teste, acionar "Cancelar Operação", verificar emissão de `SIGTERM`, limpeza de arquivos temporários e retorno imediato da UI ao estado `IDLE`.

- [X] T028 [US5] Implement `request_cancel()` method in `src/woeusb_gui_flasher/burn_engine.py` terminating active subprocesses (`7z`, `wimlib-imagex`) and cleaning up temporary files
- [X] T029 [US5] Implement cancellation handler and error banner displays in `src/woeusb_gui_flasher/ui/main_window.py`
- [X] T030 [US5] Implement cancellation and error recovery tests in `tests/test_cancellation.py`

**Checkpoint**: User Story 5 completa e protegida contra processos zumbis.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verificação de estilo, documentação e validação ponta a ponta.

- [X] T031 [P] Verify code formatting and linting with `ruff check` and `ruff format` across `src/` and `tests/`
- [X] T032 [P] Update project documentation and usage examples in `README.md`
- [X] T033 Execute complete dry-run validation following `specs/001-woeusb-gui/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ➔ Phase 2 (Foundational) ➔ Phase 3 (US1 Flatpak Run)
                                        ➔ Phase 4 (US3 Safe Disk)
                                        ➔ Phase 5 (US2 Burn Engine MVP) ➔ Phase 6 (US4 UI Feedback) ➔ Phase 7 (US5 Cancel) ➔ Phase 8 (Polish)
```

- **Setup (Phase 1)**: Não possui dependências - pode iniciar imediatamente.
- **Foundational (Phase 2)**: Depende de Setup - **BLOQUEIA** todas as histórias de usuário.
- **User Story 1 (Phase 3)**: Depende da Fase 2.
- **User Story 3 (Phase 4)**: Depende da Fase 2.
- **User Story 2 (Phase 5 - MVP)**: Depende da Fase 2 e integra com US3.
- **User Story 4 (Phase 6)**: Depende de US1, US2 e US3 para conectar a interface ao motor.
- **User Story 5 (Phase 7)**: Depende de US2 e US4 para orquestrar cancelamento da thread e UI.
- **Polish (Phase 8)**: Depende da conclusão de todas as histórias desejadas.

---

## Parallel Opportunities

- **Setup**: T002, T003, T004 podem ser executadas em paralelo.
- **Foundational**: T005 e T006 podem ser executadas em paralelo.
- **Contract Tests**: T008, T012, T017 podem ser escritas em paralelo assim que a Fase 2 for concluída.
- **UI Components & Polish**: T024, T031, T032 podem ser executadas em paralelo.

---

## Implementation Strategy

### MVP First (User Stories 1, 2 e 3)
1. Completar Fase 1 (Setup) e Fase 2 (Foundational).
2. Completar Fase 3 (US1) e Fase 4 (US3 - Descoberta Segura de Disco).
3. Completar Fase 5 (US2 - Motor de Gravação Universal).
4. **Validar MVP**: Executar o motor via script/CLI com sucesso.
5. Avançar para Fase 6 (UI) e Fase 7 (Cancelamento Seguro).
