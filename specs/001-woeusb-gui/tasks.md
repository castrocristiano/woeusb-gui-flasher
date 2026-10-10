# Tasks: WoeUSB GUI Flasher (Universal Linux via Flatpak)

**Input**: Design documents from `/specs/001-woeusb-gui/`  
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md)  
**Status**: Ready for Implementation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estrutura base de pastas, arquivos de empacotamento e assets visuais.

- [ ] **T001**: Criar estrutura de diretórios do projeto (`src/`, `src/ui/`, `assets/`, `tests/`) em `/home/cristiano/Dev/woeusb-gui`.
- [ ] **T002**: Criar o manifesto de empacotamento Flatpak [`org.woeusb.WoeUsbGui.yml`](org.woeusb.WoeUsbGui.yml) configurando runtime KDE 6, permissões UDisks2 e módulos `wimlib`/`p7zip`.
- [ ] **T003** [P]: Criar ícone visual SVG em [`assets/org.woeusb.WoeUsbGui.svg`](assets/org.woeusb.WoeUsbGui.svg) e arquivo de lançador de aplicativo em [`assets/org.woeusb.WoeUsbGui.desktop`](assets/org.woeusb.WoeUsbGui.desktop).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Modelos de dados e infraestrutura essencial que bloqueiam a implementação das histórias de usuário.

- [ ] **T004**: Implementar dataclasses de dados em [`src/models.py`](src/models.py):
  - `StorageDevice`: informações do pendrive, tamanho legível, rótulo, flag de segurança `is_system_drive`.
  - `WindowsISO`: caminho, validação, tamanho e existência do arquivo ISO.
  - `BurnConfig`: opções de partição (FAT32 vs NTFS), flag BIOS e rótulo de volume.
  - `BurnState`: estados da queima (IDLE, PREPARING, EXTRACTING, SPLITTING, BOOTLOADER, FINISHED, ERROR, CANCELED).
- [ ] **T005** [P]: Implementar utilitários auxiliares em [`src/utils.py`](src/utils.py) para formatação de bytes (`format_size`), busca de comandos no PATH e helpers de comunicação D-Bus.
- [ ] **T006**: Criar script executável local de conveniência [`run.sh`](run.sh) com permissões `chmod +x`.

---

## Phase 3: User Story 3 - Detecção Segura e Isolamento de Dispositivos (Priority: P1)

**Goal**: Descobrir pendrives USB conectados (`/dev/sdd`), filtrar e proibir categoricamente discos internos do sistema operacional (`/`, `/boot`, `/home`, `[SWAP]`), e desmontar partições ativas com segurança.

- [ ] **T007** [US3]: Implementar módulo [`src/disk_manager.py`](src/disk_manager.py):
  - Consulta estruturada a dispositivos via `lsblk -J -b` e D-Bus `org.freedesktop.UDisks2`.
  - Filtro restrito: apenas unidades removíveis (`TRAN == "usb"` ou `RM == true`) com capacidade > 2 GB.
  - **Trava de segurança:** Excluir sumariamente qualquer disco contendo montagens críticas do sistema host.
- [ ] **T008** [US3]: Implementar rotina de desmontagem de partições ativas via `udisksctl unmount` ou D-Bus `UDisks2.Filesystem.Unmount()` em [`src/disk_manager.py`](src/disk_manager.py).
- [ ] **T009** [P] [US3]: Criar testes de validação do filtro de discos em [`tests/test_disk_manager.py`](tests/test_disk_manager.py) garantindo que discos internos nunca apareçam na lista.

---

## Phase 4: User Story 2 - Motor de Gravação Universal (Priority: P1 MVP)

**Goal**: Implementar a lógica assíncrona (`QThread`) de particionamento, extração de ISO em espaço de usuário, divisão de `install.wim` (> 4 GB) para FAT32 e configuração de bootloader UEFI/BIOS.

- [ ] **T010** [US2]: Criar classe trabalhadora `BurnWorker(QThread)` em [`src/burn_engine.py`](src/burn_engine.py) com definição de sinais Qt:
  - `progress_changed(int)` (0 a 100)
  - `status_changed(str)` (descrição da etapa atual)
  - `log_received(str)` (linha de log em tempo real)
  - `finished(bool, str)` (sucesso/falha e mensagem)
- [ ] **T011** [US2]: Implementar preparação e formatação de partição (MBR + FAT32/NTFS) via D-Bus UDisks2 ou fallback `woeusb` em [`src/burn_engine.py`](src/burn_engine.py).
- [ ] **T012** [US2]: Implementar extração de arquivos da ISO em espaço de usuário (`7z x`) diretamente para a mídia montada em [`src/burn_engine.py`](src/burn_engine.py).
- [ ] **T013** [US2]: Implementar rotina de split de `install.wim` (> 4 GB) em arquivos `.swm` de 4000 MB via `wimlib-imagex split` em [`src/burn_engine.py`](src/burn_engine.py).
- [ ] **T014** [US2]: Implementar cálculo de progresso contínuo e sincronização de buffers (`sync`) antes da desmontagem final em [`src/burn_engine.py`](src/burn_engine.py).

---

## Phase 5: User Stories 4 & 5 - Interface Gráfica, Feedback e Cancelamento (Priority: P2 & P3)

**Goal**: Criar interface visual moderna em PySide6 / Qt 6 integrada ao KDE Plasma (Wayland/X11), com feedback visual instantâneo, confirmação modal de segurança e suporte a cancelamento.

- [ ] **T015** [P] [US4]: Criar componentes visuais customizados em [`src/ui/components.py`](src/ui/components.py):
  - `IsoSelectorCard`: Exibição do caminho da ISO, tamanho e botão "Escolher ISO...".
  - `DriveSelectorCard`: ComboBox de pendrives detectados com botão de recarregar e detalhes de capacidade.
  - `OptionsCard`: Rádios para FAT32 / NTFS e checkbox de flag de boot legado.
  - `ProgressCard`: Barra de progresso animada, rótulo de etapa e percentual numérico.
  - `LogConsole`: Painel recolhível com rolagem automática e botão "Copiar Logs".
- [ ] **T016** [US4]: Implementar a janela principal em [`src/ui/main_window.py`](src/ui/main_window.py), conectando os componentes visuais ao `disk_manager` e ao `burn_engine`.
- [ ] **T017** [US4]: Implementar diálogo modal de confirmação de segurança com aviso em destaque sobre perda irreversível de dados antes do início da gravação.
- [ ] **T018** [US5]: Implementar rotina de cancelamento seguro com envio de sinal SIGTERM/SIGINT ao subprocesso e limpeza de recursos temporários.

---

## Phase 6: Ponto de Entrada, Integração e Metadados Flatpak

**Purpose**: Unificar os módulos no ponto de entrada e garantir conformidade de empacotamento.

- [ ] **T019**: Implementar arquivo principal de inicialização [`src/main.py`](src/main.py) com configuração de `QApplication`, metadados de janela e estilo nativo Qt 6.
- [ ] **T020**: Criar arquivo AppStream Metainfo em [`assets/org.woeusb.WoeUsbGui.metainfo.xml`](assets/org.woeusb.WoeUsbGui.metainfo.xml) para integração com lojas de software (Discover / GNOME Software).
- [ ] **T021**: Validar execução nativa executando `./run.sh` no ambiente gráfico atual.
- [ ] **T022**: Validar sintaxe e integridade do manifesto Flatpak [`org.woeusb.WoeUsbGui.yml`](org.woeusb.WoeUsbGui.yml).

---

## Dependencies & Execution Order

```
Phase 1 (Setup) ➔ Phase 2 (Foundational) ➔ Phase 3 (US3 Disk Safety) ➔ Phase 4 (US2 Burn Engine) ➔ Phase 5 (UI & Progress) ➔ Phase 6 (Integration)
```

- **T001, T002, T003** executados primeiro.
- **T004, T005, T006** desbloqueiam o desenvolvimento dos módulos de lógica.
- **T007, T008** fornecem a lista segura de pendrives para o motor e UI.
- **T010 - T014** implementam o core de gravação.
- **T015 - T018** conectam a interface gráfica ao core.
- **T019 - T022** fecham a aplicação e validam o Flatpak.

