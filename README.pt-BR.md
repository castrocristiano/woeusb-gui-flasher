# WoeUSB-GUI (Windows USB Flasher)

Aplicação desktop moderna em Python (**PySide6 / Qt 6**) para criação de pendrives inicializáveis do Windows no Linux (BigLinux, Arch Linux, Manjaro, Ubuntu, Debian, Fedora), empacotada universalmente via **Flatpak** (`org.woeusb.WoeUsbGui`).

[![Flathub](https://img.shields.io/badge/Flathub-org.woeusb.WoeUsbGui-blue?logo=flathub)](https://flathub.org/apps/org.woeusb.WoeUsbGui)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Python: >=3.11](https://img.shields.io/badge/Python->=3.11-green.svg)
![Qt: 6 (PySide6)](https://img.shields.io/badge/Qt-6-green.svg)
![AppStream: Validated](https://img.shields.io/badge/AppStream-Validated-brightgreen.svg)

🌐 **Idioma**: [English](README.md) | **Português (Brasil)**

---

## 📸 Interface

![Interface do WoeUSB-GUI](assets/screenshots/main-window.png)

---

## ✨ Principais Funcionalidades

- **Segurança Absoluta contra Destruição de Dados**:
  - Detecção rigorosa de dispositivos via D-Bus `UDisks2` e `lsblk`.
  - Exibição **estrita** de dispositivos USB removíveis com capacidade $\ge$ 2 GB.
  - Bloqueio e ocultação incondicional de discos internos e partições de sistema (`/`, `/boot`, `/home`, swap).
  - Diálogo modal de confirmação explícito detalhando fabricante, modelo, capacidade e caminho do dispositivo.
- **Extração Segura em Espaço de Usuário**:
  - Extração direta dos arquivos da ISO do Windows utilizando `7z` (`p7zip`), eliminando a necessidade de comandos inseguros de root (`mount -o loop`).
- **Suporte Automático a UEFI Secure Boot (FAT32)**:
  - Formatação em partição FAT32 com estrutura de inicialização UEFI padrão (`/efi/boot/bootx64.efi`).
  - Divisão automática de arquivos `install.wim` maiores que 4 GB em volumes `.swm` via `wimlib-imagex split`, superando o limite de tamanho de arquivo do FAT32.
- **Interface Gráfica Moderna e Responsiva (Qt 6)**:
  - Motor assíncrono em thread dedicada (`QThread`) mantendo a interface fluida a 60 FPS.
  - Barra de progresso suave, cálculo de velocidade estimada e etapas em tempo real.
  - Gaveta expansível de logs detalhados com opção de cópia para a área de transferência.
  - Cancelamento seguro a qualquer momento com encerramento limpo de subprocessos e desmontagem.
- **Conformidade com Diretrizes do Flathub**:
  - Sandbox estrito e metadados AppStream validados segundo os padrões de qualidade do Flathub.

---

## 🚀 Como Executar

### 1. Instalar via Flathub (Recomendado)

Assim que publicado no Flathub, o aplicativo pode ser instalado e executado diretamente com:

```bash
# Instalar do Flathub
flatpak install flathub org.woeusb.WoeUsbGui

# Executar a aplicação
flatpak run org.woeusb.WoeUsbGui
```

### 2. Construindo e Testando com Flatpak Localmente

O WoeUSB-GUI utiliza o runtime KDE 6.6 (`org.kde.Platform`), que oferece suporte nativo completo ao PySide6 e Qt 6:

```bash
# 1. Instalar runtime e SDK do KDE 6.6
flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6

# 2. Compilar o pacote Flatpak
flatpak-builder --force-clean --user --install build-dir org.woeusb.WoeUsbGui.yml

# 3. Executar o Flatpak instalado
flatpak run org.woeusb.WoeUsbGui
```

### 3. Executando Localmente a partir do Código-Fonte (Desenvolvimento)

#### Requisitos:
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (ou `venv` + `pip`)
- Dependências de sistema: `p7zip` (`7z`), `wimlib`, `dosfstools` (`mkfs.vfat`), `udisks2`

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

---

## 🔒 Permissões do Sandbox Flatpak

Para operar com segurança dentro do sandbox Flatpak gerenciando discos USB, o aplicativo requer as seguintes permissões declaradas:

| Permissão | Justificativa |
| :--- | :--- |
| `--system-talk-name=org.freedesktop.UDisks2` | Permite enumerar pendrives, formatar partições e gerenciar pontos de montagem via serviço UDisks2 do sistema sem privilégios de root. |
| `--filesystem=/run/media:rw` | Permite gravar os arquivos da instalação do Windows nos pontos de montagem do pendrive criados pelo UDisks2. |
| `--filesystem=host:ro` | Permite ao usuário selecionar imagens `.iso` do Windows localizadas na pasta pessoal, Downloads ou discos secundários. |
| `--socket=wayland` / `--socket=fallback-x11` | Suporte nativo a sessões Wayland e compatibilidade com X11. |
| `--device=dri` | Aceleração gráfica por hardware para a interface Qt 6. |

Para detalhes aprofundados sobre empacotamento, consulte [docs/FLATHUB.md](docs/FLATHUB.md).

---

## 🧪 Testes Automatizados e Validação

### Suíte de Testes

O projeto conta com testes unitários, de contrato e de interface gráfica (`pytest`, `pytest-qt`):

```bash
# Executar todos os testes em modo headless (offscreen)
uv run pytest

# Executar com relatório de cobertura
uv run pytest --cov=woeusb_gui_flasher
```

### Validação de Metadados AppStream e Desktop

Validação com as ferramentas de conformidade do Flathub:

```bash
# Validar arquivo desktop
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop

# Validar metadados AppStream (modo pedante)
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

---

## 📁 Estrutura do Repositório

```
woeusb-gui-flasher/
├── assets/
│   ├── org.woeusb.WoeUsbGui.desktop     # Integração de lançador desktop
│   ├── org.woeusb.WoeUsbGui.metainfo.xml # Metadados AppStream / Flathub
│   ├── org.woeusb.WoeUsbGui.svg         # Ícone vetorial da aplicação
│   └── screenshots/
│       └── main-window.png              # Captura de tela para Flathub e AppStream
├── docs/
│   └── FLATHUB.md                       # Guia detalhado de empacotamento Flathub
├── specs/
│   └── 001-woeusb-gui/                  # Artefatos Spec-Driven Development
├── src/
│   └── woeusb_gui_flasher/
│       ├── main.py                      # Entry point da aplicação
│       ├── models.py                    # Entidades de domínio e dataclasses
│       ├── utils.py                     # Formatação de bytes e helpers de subprocesso
│       ├── disk_manager.py              # Descoberta segura de discos (UDisks2/lsblk)
│       ├── burn_engine.py               # Motor assíncrono de gravação (BurnWorker QThread)
│       └── ui/
│           ├── components.py            # Componentes visuais e cards reutilizáveis
│           └── main_window.py           # Janela principal e diálogo de confirmação
├── tests/                               # Suíte completa de testes unitários e de contrato
├── CONTRIBUTING.md                      # Diretrizes de contribuição
├── org.woeusb.WoeUsbGui.yml             # Manifesto Flatpak
└── pyproject.toml                       # Metadados do pacote Python e dependências
```

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Consulte o arquivo [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes sobre estilo de código, testes e processo de pull requests.

---

## 🤖 Declaração sobre Uso de IA Generativa

Em total conformidade com a [Política de IA Generativa do Flathub](https://docs.flathub.org/docs/for-app-authors/requirements/):

- **Código da Aplicação e Documentação**: Partes da base de código, suíte de testes e documentação foram desenvolvidas com o auxílio de ferramentas de IA Generativa (assistentes de código LLM) sob supervisão direta, arquitetura e revisão humana.
- **Verificação Humana e Segurança**: Toda a lógica crítica — especialmente os filtros de segurança de detecção de discos USB, comunicação com o UDisks2 e rotinas de divisão de WIM — foi auditada, testada e validada pelo mantenedor.
- **Manifesto e Empacotamento Flatpak**: O manifesto Flatpak (`org.woeusb.WoeUsbGui.yml`) é mantido, revisado e testado localmente por desenvolvedor humano. Conforme as regras do Flathub, todas as submissões de pull requests, mensagens de commit e respostas aos revisores são conduzidas manualmente pelo mantenedor sem automações de agentes de IA.

---

## 📜 Licença

Distribuído sob a licença **GPL-3.0-or-later**. Consulte o arquivo [LICENSE](LICENSE) para mais informações. Os metadados AppStream são licenciados sob **CC0-1.0**.

