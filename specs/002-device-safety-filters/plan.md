# Implementation Plan: Filtro de Dispositivos Grandes e Prevenção de Conflito de Disco

**Branch**: `002-device-safety-filters` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-device-safety-filters/spec.md`

---

## Summary

Esta feature adiciona duas salvaguardas essenciais ao WoeUSB-GUI:
1. **Filtro de Dispositivos de Grande Porte**: Um controle visual selecionável na interface (`QCheckBox`) com estado padrão ativo (`True`) que oculta da lista de destinos qualquer unidade USB de capacidade superior a 64 GiB ($68.7\text{ GB}$), prevenindo a seleção acidental de HDs/SSDs externos de backup de 1 TB ou maiores, enquanto permite sua exibição sob demanda com um único clique.
2. **Prevenção Preventiva de Conflito de Mesmo Disco**: Mecanismo de resolução física do parent block device que compara a partição de armazenamento do arquivo ISO de origem com o dispositivo alvo de destino. Detectada a coincidência (mesmo disco físico ou partição do mesmo disco), a aplicação bloqueia preventivamente o botão de gravação na interface com alerta visual explícito e aborta o início no motor de gravação, prevenindo corrupção e destruição de dados.

---

## Technical Context

**Language/Version**: Python 3.11+ (compatível com runtime Flatpak Freedesktop 24.08 e Python 3.12/3.14)  
**Primary Dependencies**: PySide6 (Qt 6.7+), `gdbus`, `UDisks2` D-Bus  
**Storage**: N/A (aplicação stateless sem banco de dados local)  
**Testing**: `pytest` com plugin `pytest-cov`, executado em modo headless via `QT_QPA_PLATFORM=offscreen`  
**Target Platform**: Linux Desktop universal empacotado em Flatpak (`org.woeusb.WoeUsbGui`)  
**Project Type**: Desktop GUI Application (PySide6 / Flatpak)  
**Performance Goals**: Alternância de filtro instantânea ($< 50\text{ ms}$ em memória); resolução de mesmo disco $< 10\text{ ms}$ via `/proc/self/mountinfo`  
**Constraints**: Execução dentro do sandbox sem privilégios de root direto; conformidade estrita com a Constituição do projeto  
**Scale/Scope**: Módulo `disk_manager.py`, componentes de UI em `ui/components.py`, `ui/main_window.py` e validação em `models.py`  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio Constitucional | Status | Avaliação |
|--------------------------|--------|-----------|
| **I. Safety & Non-Destructive Protection (NON-NEGOTIABLE)** | **PASS** | Reforça a proteção central: salvaguarda discos de backup de 1 TB+ contra formatação acidental e bloqueia 100% dos cenários de sobrescrita destrutiva da própria ISO de origem. |
| **II. Universal Linux Execution via Flatpak** | **PASS** | A resolução do disco físico da ISO utiliza `/proc/self/mountinfo` e D-Bus `UDisks2`, plenamente funcionais no container sandbox do Flatpak. |
| **III. Responsive & Asynchronous Architecture** | **PASS** | A filtragem de tamanho opera em memória e a resolução de parent device não bloqueia a interface gráfica. |
| **IV. Observability & User Feedback** | **PASS** | Alertas visuais claros em caso de colisão e tooltips explicativos para o filtro de 64 GB. |
| **V. Native Linux Desktop Integration** | **PASS** | Componentes estilizados nativamente em Qt 6 / PySide6, respeitando o tema do sistema. |

---

## Project Structure

### Documentation (this feature)

```text
specs/002-device-safety-filters/
├── spec.md              # Especificação de requisitos da feature
├── checklists/
│   └── requirements.md  # Checklist de qualidade da especificação
├── plan.md              # Este plano de implementação
├── research.md          # Decisões técnicas e pesquisa arquitetural (Fase 0)
├── data-model.md        # Modelo de dados e entidades atualizadas (Fase 1)
├── quickstart.md        # Guia de validação e cenários de teste (Fase 1)
├── contracts/           # Contratos de interfaces e UI (Fase 1)
│   ├── disk-manager-contract.md
│   └── ui-safety-contract.md
└── tasks.md             # Decomposição de tarefas (Fase 2 - gerado via /speckit-tasks)
```

### Source Code (repository layout)

```text
src/woeusb_gui_flasher/
├── models.py            # StorageDevice (is_large_drive), DiskCollisionCheckResult, BurnConfiguration.validate()
├── disk_manager.py      # get_removable_devices(hide_large_drives), get_parent_disk_name(), check_same_disk_collision()
├── burn_engine.py       # Validação pré-execução antes de unmount/format
└── ui/
    ├── components.py    # DriveSelectorCard: QCheckBox ("Ocultar discos grandes"), filtro reativo
    └── main_window.py   # MainWindow: alerta visual de colisão, bloqueio do btn_burn

tests/
├── test_device_safety_filters.py   # Testes unitários de filtragem e detecção de mesmo disco
└── test_ui_safety_filters.py       # Testes de integração de UI para o checkbox e avisos
```

**Structure Decision**: Aplicação desktop modular em pacote único `woeusb_gui_flasher`, estendendo o domínio e os componentes existentes sem quebra de compatibilidade.

---

## Complexity Tracking

*Nenhuma violação aos princípios constitucionais. Nenhuma complexidade injustificada adicionada.*
