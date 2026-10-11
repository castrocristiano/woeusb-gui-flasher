# Implementation Plan: WoeUSB GUI Flasher (Universal Linux via Flatpak)

**Branch**: `001-woeusb-gui` | **Date**: 2026-10-10 | **Spec**: [specs/001-woeusb-gui/spec.md](spec.md)

**Input**: Feature specification from `/specs/001-woeusb-gui/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

---

## Summary

O objetivo deste projeto é implementar uma aplicação desktop gráfica moderna em **Python 3** e **PySide6 (Qt 6)** empacotada universalmente via **Flatpak** (`org.woeusb.WoeUsbGui`) para qualquer distribuição Linux.

A aplicação soluciona o desafio de criar pendrives inicializáveis do Windows no Linux (onde imagens ISO com `install.wim` > 4 GB não cabem em partições FAT32 sem divisão) através de:
1. **Comunicação D-Bus com `UDisks2`**: Para particionamento e formatação segura autorizada pelo Polkit do host sem violar o isolamento do sandbox Flatpak.
2. **Extração de ISO em Espaço de Usuário (`7z`)**: Copiando os arquivos diretamente para o ponto de montagem do pendrive sem requerer privilégios de kernel para `mount -o loop`.
3. **Divisão de WIM (`wimlib-imagex`)**: Integrada no Flatpak para repartir imagens maiores que 4 GB em arquivos `.swm`, mantendo compatibilidade nativa com UEFI Secure Boot e Legacy BIOS.
4. **Interface Gráfica Reativa em PySide6**: Com atualização de progresso contínua (0 a 100%), painel de logs expansível e salvaguarda absoluta contra formatação acidental de discos de sistema.

---

## Technical Context

- **Language/Version**: Python 3.11+ (Python 3.12 padrão do ambiente)
- **GUI Framework**: PySide6 (Qt 6.6+) com suporte a Wayland e X11
- **Packaging/Runtime**: Flatpak (`org.kde.Platform` 6.x ou `org.freedesktop.Platform` 24.08)
- **Primary Dependencies**:
  - `PySide6` (Interface gráfica nativa com estilos Breeze/Desktop)
  - `p7zip` / `7z` (Extração em espaço de usuário de imagens UDF/ISO)
  - `wimlib-imagex` (Divisão de arquivos `.wim` em `.swm`)
  - `dasbus` / `Gio` / `dbus-python` (Comunicação com `org.freedesktop.UDisks2`)
- **Storage / Devices**: Dispositivos de bloco removíveis USB via `UDisks2`
- **Testing**: `pytest`, `pytest-cov`, `pytest-qt` (para componentes gráficos)
- **Target Platform**: Qualquer distribuição Linux com Flatpak (BigLinux, Fedora, Ubuntu, Arch, Debian, openSUSE, etc.)
- **Project Type**: Desktop Application (PySide6 / Qt 6)
- **Performance Goals**: Interface fluida em 60 FPS durante operações intensivas de I/O, atualização de progresso suave, inicialização do aplicativo em < 1 segundo.
- **Constraints**:
  - Conformidade estrita com o sandbox Flatpak (`--system-talk-name=org.freedesktop.UDisks2`, `--filesystem=host:ro`, `--filesystem=/run/media:rw`, `--device=dri`).
  - Proteção inegociável contra gravação em discos internos e partições de sistema (`/`, `/boot`, `/home`, `[SWAP]`).
- **Scale/Scope**: Ferramenta desktop autossuficiente focada em gravação confiável de instaladores Windows 7/8/10/11.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio Constitucional | Status | Justificativa / Validação |
| :--- | :---: | :--- |
| **I. Safety & Non-Destructive Protection (NON-NEGOTIABLE)** | **PASSED** | Apenas unidades removíveis USB (`TRAN=usb` / `RM=true`) são elegíveis. Unidades de sistema são categoricamente omitidas. Confirmação modal obrigatória detalhando caminho, tamanho e modelo antes de qualquer operação destrutiva. |
| **II. Universal Linux Execution via Flatpak** | **PASSED** | Desacoplamento total de `mount -o loop` usando extração user-space com `7z`. Particionamento mediado por D-Bus `UDisks2` com autenticação Polkit do host. Manifesto Flatpak oficial incluso. |
| **III. Responsive & Asynchronous Architecture** | **PASSED** | Todas as operações de I/O, extração e escaneamento rodam em `QThread` assíncrona (`BurnWorker`) desacoplada da thread principal de renderização da GUI via signals/slots. Cancelamento limpo com `SIGTERM` e desalocação de recursos. |
| **IV. Observability & User Feedback** | **PASSED** | Sinais em tempo real de porcentagem (`0-100%`), estágio atual textual descritivo, velocidade de gravação e gaveta de logs integrada com auto-scroll e botão de cópia. |
| **V. Native Linux Desktop Integration** | **PASSED** | Construído em Python 3 + PySide6 (Qt 6), manifesto Flatpak com permissões Wayland e X11, arquivo `.desktop` padronizado e ícone SVG em conformidade com XDG. |

---

## Project Structure

### Documentation (this feature)

```text
specs/001-woeusb-gui/
├── spec.md                              # Requisitos e cenários de aceitação
├── plan.md                              # Este plano de implementação técnica
├── research.md                          # Fase 0: Decisões técnicas e justificativas arquiteturais
├── data-model.md                        # Fase 1: Entidades de domínio, enums e máquina de estados
├── quickstart.md                        # Fase 1: Guia prático de execução e cenários de validação
├── contracts/                           # Fase 1: Especificação formal de contratos
│   ├── udisks2-contract.md              # Contrato D-Bus com o daemon de discos UDisks2
│   ├── burn-engine-contract.md          # Contrato de sinais e slots da thread trabalhadora
│   └── flatpak-contract.md              # Contrato de sandbox e permissões Flatpak
└── tasks.md                             # Fase 2: Mapeamento ordenado de tarefas
```

### Source Code (repository root)

```text
src/
└── woeusb_gui_flasher/
    ├── __init__.py                      # Package entry point e versão
    ├── __main__.py                      # CLI / GUI runner (python -m woeusb_gui_flasher)
    ├── models.py                        # Dataclasses: StorageDevice, WindowsISO, BurnConfiguration, BurnState
    ├── disk_manager.py                  # Descoberta segura via UDisks2 / lsblk com filtros estritos
    ├── burn_engine.py                   # QThread assíncrona: orquestração de formatação, 7z e wimlib
    ├── ui/
    │   ├── __init__.py
    │   ├── main_window.py               # Janela principal PySide6, layout reativo e eventos
    │   └── components.py                # Widgets: Seletor de ISO, Seletor de USB, Barra e Drawer de Logs
    └── utils.py                         # Validações, conversão de unidades e helpers de subprocesso

tests/
├── __init__.py
├── test_spec.py                         # Validação de integridade dos artefatos da especificação
├── test_models.py                       # Testes unitários para modelos de dados e validações
├── test_disk_manager.py                 # Testes unitários para filtros de segurança e UDisks2
├── test_burn_engine.py                  # Testes do motor de gravação com subprocessos simulados
└── test_ui.py                           # Testes de integração de interface via pytest-qt

assets/
├── org.woeusb.WoeUsbGui.svg             # Ícone SVG vetorial do aplicativo
├── org.woeusb.WoeUsbGui.desktop         # Entrada para menu de aplicativos do Linux
└── org.woeusb.WoeUsbGui.metainfo.xml    # Metadados AppStream para Flathub / GNOME Software / Discover

org.woeusb.WoeUsbGui.yml                 # Manifesto oficial de compilação via flatpak-builder
pyproject.toml                           # Configuração do projeto Python (uv / hatchling)
README.md                                # Documentação geral do repositório
```

**Structure Decision**:
Projeto estruturado no modelo de pacote Python padronizado (`src/woeusb_gui_flasher/`) gerenciado com `uv` e `pyproject.toml`, com camada gráfica encapsulada em `ui/`, motor desacoplado em `burn_engine.py`, ativos de desktop em `assets/` e manifesto de empacotamento Flatpak na raiz.

---

## Complexity Tracking

> Todas as diretrizes da Constituição foram atendidas integralmente. Nenhuma exceção ou violação foi necessária.

| Item | Status | Justificativa |
| :--- | :---: | :--- |
| Ausência de `mount -o loop` | Conforme | Substituído por `7z` em espaço de usuário para compatibilidade com Flatpak. |
| Formatação via D-Bus UDisks2 | Conforme | Garante autenticação nativa sem requisições de root desnecessárias. |
| Divisão de WIM automática | Conforme | Garante inicialização em hardware UEFI com Secure Boot sem quebras. |
