# Tasks: Filtro de Dispositivos Grandes e Prevenção de Conflito de Disco

**Feature**: `002-device-safety-filters`  
**Input**: Design artifacts from `specs/002-device-safety-filters/` (`spec.md`, `plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`)  
**Status**: Completed  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Preparação de arquivos de teste e fixtures compartilhadas

- [X] T001 [P] Create initial test suite structure in tests/test_device_safety_filters.py
- [X] T002 [P] Create UI safety test suite structure in tests/test_ui_safety_filters.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura de domínio e utilitários que bloqueiam as histórias de usuário

**⚠️ CRITICAL**: Nenhuma história de usuário pode ser concluída sem estes modelos e utilitários base

- [X] T003 Define `MAX_TYPICAL_PENDRIVE_BYTES = 68_719_476_736` and `is_large_drive` property on `StorageDevice` in src/woeusb_gui_flasher/models.py
- [X] T004 [P] Implement `DiskCollisionCheckResult` dataclass in src/woeusb_gui_flasher/models.py
- [X] T005 Implement `get_parent_disk_name(device_or_partition: str | Path) -> str` utility in src/woeusb_gui_flasher/disk_manager.py

**Checkpoint**: Modelos e funções de base disponíveis para as histórias de usuário

---

## Phase 3: User Story 1 - Filtragem de Dispositivos de Grande Porte (Priority: P1) 🎯 MVP

**Goal**: Dispositivos USB com capacidade superior a 64 GiB ($68.7\text{ GB}$) são omitidos por padrão da listagem, mas podem ser exibidos mediante desmarcação do filtro na interface.

**Independent Test**: Conectar ou simular pendrive de 16 GB e HD externo de 1 TB; apenas o pendrive aparece no seletor com o filtro ativo. Desmarcar o controle torna o disco de 1 TB visível imediatamente.

### Tests for User Story 1
- [X] T006 [P] [US1] Unit test for `StorageDevice.is_large_drive` and `DiskManager.get_removable_devices(hide_large_drives=...)` in tests/test_device_safety_filters.py
- [X] T007 [P] [US1] Integration test for large drive filter toggle in tests/test_ui_safety_filters.py

### Implementation for User Story 1
- [X] T008 [US1] Update `filter_safe_device` and `get_removable_devices` in src/woeusb_gui_flasher/disk_manager.py to accept `hide_large_drives: bool = True`
- [X] T009 [US1] Add `QCheckBox` "Ocultar discos grandes (> 64 GB)" with default `True` and `filter_toggled` signal in src/woeusb_gui_flasher/ui/components.py
- [X] T010 [US1] Connect `DriveSelectorCard.filter_toggled` in src/woeusb_gui_flasher/ui/main_window.py to re-filter and update the devices dropdown

**Checkpoint**: User Story 1 funcional e testável de forma autônoma.

---

## Phase 4: User Story 2 - Prevenção Preventiva de Conflito de Origem e Destino no Mesmo Disco (Priority: P1)

**Goal**: Identificar quando o arquivo ISO e o dispositivo alvo pertencem ao mesmo disco físico, bloqueando preventivamente a gravação para evitar corrupção e destruição de dados.

**Independent Test**: Selecionar uma ISO localizada em uma partição de um disco externo (ex.: `/dev/sdc2`) e selecionar esse mesmo disco (`/dev/sdc` ou `/dev/sdc1`) como destino; a gravação é bloqueada e `BurnConfiguration.validate()` rejeita com `ValueError`.

### Tests for User Story 2
- [X] T011 [P] [US2] Unit test for `resolve_file_source_block_device` and `check_same_disk_collision` in tests/test_device_safety_filters.py
- [X] T012 [P] [US2] Unit test for `BurnConfiguration.validate()` same-disk rejection in tests/test_device_safety_filters.py

### Implementation for User Story 2
- [X] T013 [US2] Implement `resolve_file_source_block_device(file_path: Path) -> str | None` using `/proc/self/mountinfo` and `os.stat` in src/woeusb_gui_flasher/disk_manager.py
- [X] T014 [US2] Implement `check_same_disk_collision(iso_path: Path | str, target_device: StorageDevice) -> DiskCollisionCheckResult` in src/woeusb_gui_flasher/disk_manager.py
- [X] T015 [US2] Update `BurnConfiguration.validate()` in src/woeusb_gui_flasher/models.py to verify same-disk collision and raise `ValueError`
- [X] T016 [US2] Add defensive check in `BurnWorker.run()` in src/woeusb_gui_flasher/burn_engine.py to abort before unmounting or formatting if same disk is detected

**Checkpoint**: User Stories 1 e 2 operacionais e protegendo contra gravação no mesmo disco.

---

## Phase 5: User Story 3 - Feedback Amigável e Clareza nas Validações de Disco (Priority: P2)

**Goal**: Exibir avisos visuais destacados, textos de orientação contextuais e mensagens amigáveis em caso de colisão ou listagem vazia.

**Independent Test**: Verificar que ao selecionar disco com colisão, um banner estilizado em vermelho aparece acima dos botões com mensagem explicativa e o botão "Iniciar Gravação" permanece desabilitado.

### Tests for User Story 3
- [X] T017 [P] [US3] UI test for collision warning label and tooltip visibility in tests/test_ui_safety_filters.py

### Implementation for User Story 3
- [X] T018 [US3] Add tooltip to the large drive filter checkbox explaining the 64 GB threshold in src/woeusb_gui_flasher/ui/components.py
- [X] T019 [US3] Add styled `lbl_collision_warning` and connect collision check in `MainWindow._update_burn_button_state` in src/woeusb_gui_flasher/ui/main_window.py
- [X] T020 [US3] Update empty-state message in `DriveSelectorCard.populate_devices` in src/woeusb_gui_flasher/ui/components.py advising to uncheck filter if using large disk

**Checkpoint**: Todas as histórias de usuário integradas com feedback visual completo.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificação global, qualidade de testes e conformidade

- [X] T021 [P] Run full test suite with coverage via `QT_QPA_PLATFORM=offscreen PYTHONPATH=src:.venv/lib/python3.12/site-packages python3 -m pytest tests/`
- [X] T022 [P] Verify Flatpak manifest compliance in org.woeusb.WoeUsbGui.yml
- [X] T023 Execute end-to-end validation scenarios documented in specs/002-device-safety-filters/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências - pode iniciar imediatamente.
- **Foundational (Phase 2)**: Depende da Fase 1 - BLOQUEIA todas as histórias de usuário.
- **User Story 1 (Phase 3)**: Depende da Fase 2.
- **User Story 2 (Phase 4)**: Depende da Fase 2. Pode ser desenvolvida em paralelo ou logo após a História 1.
- **User Story 3 (Phase 5)**: Depende das Fases 3 e 4 (aprimora o feedback visual da filtragem e colisão).
- **Polish (Phase 6)**: Depende de todas as fases anteriores completadas.

### Within Each User Story

- Testes unitários/integração preparados antes da implementação.
- Modelo de dados e lógica de serviço (`disk_manager.py`) antes dos componentes visuais (`components.py`, `main_window.py`).
- Validação no motor (`burn_engine.py`) garantindo tolerância a falhas.

---

## Parallel Opportunities

```bash
# Execução paralela de Setup:
Task T001: tests/test_device_safety_filters.py
Task T002: tests/test_ui_safety_filters.py

# Execução paralela na Fase Foundational:
Task T004: src/woeusb_gui_flasher/models.py
Task T005: src/woeusb_gui_flasher/disk_manager.py

# Execução paralela de Testes na História 1:
Task T006: tests/test_device_safety_filters.py
Task T007: tests/test_ui_safety_filters.py

# Execução paralela de Testes na História 2:
Task T011: tests/test_device_safety_filters.py
Task T012: tests/test_device_safety_filters.py
```

---

## Implementation Strategy

### MVP First (User Story 1)
1. Completar Setup (Fase 1) e Foundational (Fase 2).
2. Implementar User Story 1 (Fase 3): Filtragem de discos grandes com default ativo.
3. **Validar MVP**: Discos $> 64\text{ GiB}$ são ocultados por padrão.

### Entrega Incremental
1. Adicionar User Story 2 (Fase 4): Prevenção de gravação no mesmo disco.
2. Adicionar User Story 3 (Fase 5): Banner de alerta visual e mensagens contextuais.
3. Executar Polish (Fase 6): Suíte de testes completa e validação no Flatpak.
