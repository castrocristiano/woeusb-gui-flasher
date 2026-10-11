# WoeUSB-GUI (Windows USB Flasher)

Aplicação desktop moderna em Python (**PySide6 / Qt 6**) para criação de pendrives inicializáveis do Windows no Linux (BigLinux, Arch Linux, Manjaro, Ubuntu, Debian, Fedora), empacotada universalmente via **Flatpak** (`org.woeusb.WoeUsbGui`).

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python: >=3.11](https://img.shields.io/badge/Python->=3.11-green.svg)
![Qt: 6 (PySide6)](https://img.shields.io/badge/Qt-6-green.svg)
![Flatpak: Ready](https://img.shields.io/badge/Flatpak-Flathub%20Ready-orange.svg)

---

## ✨ Principais Funcionalidades

- **Segurança Absoluta contra Destruição de Dados**:
  - Detecção rigorosa de dispositivos via D-Bus `UDisks2` e `lsblk`.
  - Exibição **estrita** de dispositivos USB removíveis com $\ge$ 2 GB de capacidade.
  - Bloqueio e ocultação incondicional de partições e discos de sistema (`/`, `/boot`, `/home`, etc.).
  - Diálogo modal de confirmação explícito detalhando modelo, caminho e aviso de perda de dados.
- **Extração Segura em Espaço de Usuário**:
  - Extração direta dos arquivos da ISO do Windows utilizando `7z` (p7zip), eliminando a necessidade de comandos inseguros de root (`mount -o loop`).
- **Suporte Automático a UEFI Secure Boot (FAT32)**:
  - Divisão automática de arquivos `install.wim` maiores que 4 GB em volumes `.swm` via `wimlib-imagex split`.
  - Configuração automática de bootloader UEFI (`/efi/boot/bootx64.efi`).
- **Interface Gráfica Moderna e Responsiva**:
  - Motor assíncrono em thread dedicada (`QThread`) para manter a UI sempre fluida (60 FPS).
  - Barra de progresso suave, cálculo de velocidade estimada e etapas em tempo real.
  - Gaveta expansível de logs detalhados com opção de cópia para a área de transferência.
  - Cancelamento seguro a qualquer momento com encerramento de subprocessos e desmontagem limpa.

---

## 🚀 Como Executar

### 1. Executando Localmente (Desenvolvimento)

Requisitos:
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (ou `venv` + `pip`)
- Dependências de sistema: `p7zip` (`7z`), `wimlib`, `dosfstools` (`mkfs.vfat`), `ntfs-3g`, `udisks2`

```bash
# Clonar o repositório
git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
cd woeusb-gui-flasher

# Sincronizar o ambiente com uv
uv sync

# Iniciar a aplicação
uv run woeusb-gui
# ou pelo script auxiliar:
./run.sh
```

### 2. Construindo e Testando com Flatpak

O aplicativo foi projetado e validado em conformidade total com as diretrizes do **Flathub Quality Guidelines**:

```bash
# Instalar runtime e SDK do GNOME 47
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47

# Compilar o pacote Flatpak
flatpak-builder --force-clean --user --install build-dir org.woeusb.WoeUsbGui.yml

# Executar o Flatpak instalado
flatpak run org.woeusb.WoeUsbGui
```

---

## 🧪 Testes Automatizados

O projeto conta com uma suíte abrangente de testes unitários, testes de contrato e integração de interface gráfica (`pytest`, `pytest-qt`):

```bash
# Executar todos os testes em modo headless (offscreen)
uv run pytest

# Executar com relatório de cobertura
uv run pytest --cov=woeusb_gui_flasher
```

---

## 📁 Estrutura do Repositório

```
woeusb-gui-flasher/
├── assets/
│   ├── org.woeusb.WoeUsbGui.desktop    # Integração de lançador desktop
│   ├── org.woeusb.WoeUsbGui.metainfo.xml# Metadados AppStream / Flathub
│   └── org.woeusb.WoeUsbGui.svg        # Ícone vetorial da aplicação
├── org.woeusb.WoeUsbGui.yml            # Manifesto Flatpak
├── pyproject.toml                      # Metadados do pacote Python e dependências
├── run.sh                              # Launcher shell
├── specs/
│   └── 001-woeusb-gui/                 # Artefatos Spec-Driven Development
│       ├── spec.md                     # Especificação funcional
│       ├── plan.md                     # Arquitetura técnica e contratos
│       ├── tasks.md                    # Plano de implementação executável
│       └── quickstart.md               # Guia de validação rápida
├── src/
│   └── woeusb_gui_flasher/
│       ├── __init__.py
│       ├── __main__.py
│       ├── main.py                     # Entry point da aplicação
│       ├── models.py                   # Entidades de domínio e dataclasses
│       ├── utils.py                    # Formatação de bytes e helpers de subprocesso
│       ├── disk_manager.py             # Descoberta segura de discos (UDisks2/lsblk)
│       ├── burn_engine.py              # Motor assíncrono de gravação (BurnWorker QThread)
│       └── ui/
│           ├── __init__.py
│           ├── components.py           # Componentes visuais e cards reutilizáveis
│           └── main_window.py          # Janela principal e diálogo de confirmação
└── tests/                              # Suíte completa de testes unitários e de contrato
```

---

## 📜 Licença

Distribuído sob a licença **GPL-3.0-or-later**. Consulte o arquivo de licença para mais informações.
