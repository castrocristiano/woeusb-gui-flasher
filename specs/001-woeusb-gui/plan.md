# Implementation Plan: WoeUSB GUI Flasher (Universal Linux via Flatpak)

**Branch**: `001-woeusb-gui` | **Date**: 2026-10-10 | **Spec**: [specs/001-woeusb-gui/spec.md](spec.md)

**Input**: Feature specification from `/specs/001-woeusb-gui/spec.md`

---

## Summary

O objetivo deste projeto é implementar uma aplicação desktop gráfica moderna em **Python 3** e **PySide6 (Qt 6)** empacotada universalmente via **Flatpak** (`org.woeusb.WoeUsbGui`) para qualquer distribuição Linux. 

A aplicação soluciona o desafio de criar pendrives bootáveis do Windows no Linux (onde imagens ISO com `install.wim` > 4 GB não cabem em FAT32 sem divisão) combinando:
1. **Comunicação D-Bus com `UDisks2`**: Para formatação segura de pendrives autorizada pelo Polkit nativo do sistema sem quebrar o sandbox do Flatpak.
2. **Extração de ISO em Espaço de Usuário (`7z`)**: Copiando os arquivos diretamente para o pendrive montado sem necessidade de `mount -o loop` (bloqueado em containers).
3. **Divisão de WIM (`wimlib-imagex`)**: Integrado no Flatpak para repartir imagens de instalação maiores que 4 GB em arquivos `.swm` compatíveis com FAT32 e inicializáveis via UEFI e Legacy BIOS.
4. **Interface Gráfica Reativa em PySide6**: Com atualização de progresso em tempo real, painel de logs expansível e salvaguarda absoluta contra formatação acidental de discos de sistema.

---

## Technical Context

- **Language/Version**: Python 3.11+
- **GUI Framework**: PySide6 (Qt 6.6+)
- **Packaging/Runtime**: Flatpak (`org.kde.Platform` 6.x ou `org.freedesktop.Platform` 24.08)
- **Primary Dependencies**:
  - `PySide6` (Interface gráfica nativa com suporte a Wayland e X11)
  - `p7zip` / `7z` (Extração rápida de UDF/ISO em espaço de usuário)
  - `wimlib-imagex` (Divisão de arquivos `.wim` em `.swm`)
  - `dbus-python` / `dasbus` / `Gio` (Comunicação com `org.freedesktop.UDisks2`)
  - `udisksctl` / `lsblk`
- **Target Platform**: Qualquer distribuição Linux com Flatpak (BigLinux, Fedora, Ubuntu, Arch, Debian, openSUSE, etc.)
- **Performance Goals**: 60 FPS na interface durante operações de I/O, atualização de progresso suave, inicialização do app em < 1 segundo.
- **Security & Constraints**:
  - Flatpak sandbox compliance (`--system-talk-name=org.freedesktop.UDisks2`, `--filesystem=host`, `--socket=wayland`, `--socket=fallback-x11`).
  - Proteção total contra gravação em discos de sistema (`/`, `/boot`, `/home`, `[SWAP]`, NVMe/SATA internos).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio Constitucional | Status | Justificativa / Validação |
| :--- | :---: | :--- |
| **I. Safety & Non-Destructive Protection** | **PASSED** | O `disk_manager` filtra estritamente por dispositivos removíveis USB (`TRAN=usb` / `RM=true`) e exclui qualquer dispositivo contendo montagens de sistema. Modal de confirmação obrigatório antes de qualquer ação. |
| **II. Universal Linux Execution via Flatpak** | **PASSED** | A arquitetura desacopla a dependência de `mount -o loop` do kernel utilizando extração de ISO via espaço de usuário (`7z`) e formatação mediada por D-Bus `UDisks2`. Manifesto Flatpak oficial incluso. |
| **III. Responsive & Asynchronous Architecture** | **PASSED** | Todo o processo de queima/cópia e escaneamento roda em `QThread` desacoplada da thread principal da GUI (`signals/slots`). |
| **IV. Observability & User Feedback** | **PASSED** | Emissão contínua de sinais de progresso (0 a 100%), etapas descritivas em português e gaveta de logs recolhível com auto-scroll. |
| **V. Native Linux Desktop Integration** | **PASSED** | PySide6 com styling Breeze/Desktop, metainfo AppStream e arquivo `.desktop` com ícone SVG. |

---

## Project Structure

### Documentation (`specs/001-woeusb-gui/`)

```text
specs/001-woeusb-gui/
├── spec.md              # Requisitos da Feature (Fase de Especificação)
├── plan.md              # Este plano de implementação
└── tasks.md             # Tarefas de codificação (Fase 3)
```

### Source Code (`/home/cristiano/Dev/woeusb-gui/`)

```text
woeusb-gui/
├── .specify/
│   ├── memory/
│   │   └── constitution.md
│   └── templates/
├── specs/
│   └── 001-woeusb-gui/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── src/
│   ├── __init__.py
│   ├── models.py            # Dataclasses: StorageDevice, WindowsISO, BurnConfig, BurnState
│   ├── disk_manager.py      # Descoberta de pendrives via UDisks2 e lsblk, filtros de segurança
│   ├── burn_engine.py       # QThread Worker: formatação UDisks2, extração ISO, split WIM, progresso
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py   # Janela principal PySide6, integração Wayland/KDE
│   │   └── components.py    # Widgets reutilizáveis (Card de ISO, Seletor de USB, Console de Logs)
│   └── utils.py             # Formatação de bytes, validação de arquivos, helpers de D-Bus
├── assets/
│   ├── org.woeusb.WoeUsbGui.svg          # Ícone da aplicação
│   ├── org.woeusb.WoeUsbGui.desktop      # Atalho de desktop Linux
│   └── org.woeusb.WoeUsbGui.metainfo.xml # Metadados AppStream para lojas de software
├── org.woeusb.WoeUsbGui.yml # Manifesto Flatpak oficial para flatpak-builder
├── run.sh                   # Script executável de conveniência local
├── SPEC.md -> specs/001-woeusb-gui/spec.md
└── README.md
```

---

## Arquitetura Detalhada & Fluxo de Execução

### 1. Descoberta Segura de Dispositivos (`disk_manager.py`)
```
[Início / Botão Recarregar]
          │
          ▼
   Consulta D-Bus UDisks2 ──(ou lsblk -J -b)──► Lista de todos os dispositivos
          │
          ▼
   Filtro de Segurança:
   ├── TRAN == "usb" ou RM == true?
   ├── Tamanho > 2 GB?
   └── Possui partições montadas em /, /boot, /home, [SWAP]? ──► SE SIM: EXCLUIR SUMARIAMENTE
          │
          ▼
   Lista de Pendrives Seguros para Exibição no ComboBox
```

### 2. Motor de Gravação Universal em Espaço de Usuário (`burn_engine.py`)
```
[Usuário Clica em "Iniciar Gravação" e Confirma]
          │
          ▼
   [Etapa 1: Preparação do Disco via UDisks2]
   ├── Desmontar partições ativas via UDisks2.Filesystem.Unmount()
   ├── Criar tabela de partição MBR (msdos)
   ├── Criar partição primária FAT32 (ou NTFS)
   └── Montar partição via UDisks2.Filesystem.Mount() ──► /run/media/.../Windows USB
          │
          ▼
   [Etapa 2: Extração de Arquivos em User-Space]
   ├── Extrair arquivos da ISO diretamente para a pasta montada usando 7z
   ├── Ignorar temporariamente 'sources/install.wim' se tamanho > 4 GB
   └── Monitorar porcentagem de bytes copiados
          │
          ▼
   [Etapa 3: Divisão da Imagem de Instalação (Split WIM)]
   ├── Executar: wimlib-imagex split <iso_wim> <dest_mount>/sources/install.swm 4000
   └── Monitorar progresso do split
          │
          ▼
   [Etapa 4: Configuração de Boot UEFI & Legacy]
   ├── Garantir que /efi/boot/bootx64.efi existe (copiado da ISO/WIM)
   └── Sincronizar buffers de escrita do kernel (sync)
          │
          ▼
   [Etapa 5: Finalização Segura]
   ├── Desmontar mídia com segurança
   └── Emitir sinal finished(True, "Gravação concluída com sucesso!")
```

---

## Manifesto Flatpak (`org.woeusb.WoeUsbGui.yml`)

O manifesto Flatpak define o empacotamento completo e autossuficiente:

```yaml
app-id: org.woeusb.WoeUsbGui
runtime: org.kde.Platform
runtime-version: '6.6'
sdk: org.kde.Sdk
command: woeusb-gui
finish-args:
  - --share=ipc
  - --socket=fallback-x11
  - --socket=wayland
  - --device=dri
  - --filesystem=host:ro
  - --filesystem=/run/media:rw
  - --system-talk-name=org.freedesktop.UDisks2
  - --talk-name=org.freedesktop.Flatpak

modules:
  - name: wimlib
    buildsystem: autotools
    config-opts:
      - --without-fuse
      - --without-ntfs-3g
    sources:
      - type: archive
        url: https://wimlib.net/downloads/wimlib-1.14.5.tar.gz
        sha256: 84221a3abd5b91228f15f8e6065c335a336237b5738197b75bf419eea561a194

  - name: p7zip
    buildsystem: generic
    # compilação do 7z em espaço de usuário

  - name: woeusb-gui
    buildsystem: simple
    build-commands:
      - install -Dm755 run.sh /app/bin/woeusb-gui
      - cp -r src /app/lib/woeusb-gui/
      - install -Dm644 assets/org.woeusb.WoeUsbGui.desktop /app/share/applications/org.woeusb.WoeUsbGui.desktop
      - install -Dm644 assets/org.woeusb.WoeUsbGui.svg /app/share/icons/hicolor/scalable/apps/org.woeusb.WoeUsbGui.svg
```

---

## Complexity Tracking

| Decisão Arquitetural | Por Que Foi Adotada | Alternativa Mais Simples Rejeitada Porque |
| :--- | :--- | :--- |
| **UDisks2 D-Bus em vez de `pkexec woeusb` direto** | Permite que a aplicação funcione dentro do sandbox do Flatpak em qualquer distro Linux sem exigir root no container. | O comando `woeusb` tradicional usa `mount -o loop`, que é sumariamente bloqueado pelo kernel dentro de sandboxes Flatpak. |
| **Extração com `7z` em user-space** | Lê e extrai a ISO sem necessitar montar dispositivo de loop no sistema operacional. | Montar a ISO com `mount -t udf` exige privilégios de superusuário e acesso a `/dev/loopX`. |
| **Thread `QThread` assíncrona** | Evita travamento da janela ("Aplicação não está respondendo") durante transferências de 5+ GB. | Execução síncrona na thread principal congela a renderização da interface e impede o cancelamento pelo usuário. |

