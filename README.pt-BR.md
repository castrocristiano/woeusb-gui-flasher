# WoeUSB-GUI (Gravador de Pendrive Bootável do Windows)

Aplicação desktop para Linux em Python e **PySide6 / Qt 6** que cria pendrives de instalação do Windows a partir de imagens ISO oficiais. Funciona nas principais distribuições (Arch Linux, Fedora, Ubuntu, Debian, BigLinux, Manjaro) e é empacotada como **Flatpak** (`org.woeusb.WoeUsbGui`).

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
![Python: >=3.11](https://img.shields.io/badge/Python->=3.11-green.svg)
![Qt: 6 (PySide6)](https://img.shields.io/badge/Qt-6-green.svg)
![Flathub: ainda não publicado](https://img.shields.io/badge/Flathub-ainda%20n%C3%A3o%20publicado-lightgrey?logo=flathub)

🌐 **Idioma**: [English](README.md) | **Português (Brasil)**

> [!NOTE]
> O WoeUSB-GUI **ainda não está no Flathub**. Veja em [docs/FLATHUB.md](docs/FLATHUB.md) o status da submissão e as pendências que precisam ser resolvidas antes.

---

## 📸 Interface

![Janela principal do WoeUSB-GUI](assets/screenshots/main-window.png)

---

## ✨ Funcionalidades

### Segurança dos discos
- Descoberta de dispositivos pelo serviço **UDisks2** do sistema (D-Bus), com `lsblk` como alternativa.
- Só lista **pendrives USB removíveis ≥ 2 GB**. Discos internos, swap e qualquer disco com ponto de montagem do sistema (`/`, `/boot`, `/home`, …) nunca aparecem.
- **Filtro de discos grandes**: a opção *"Ocultar discos grandes (> 64 GB)"* vem **ativada por padrão** e esconde unidades acima de 64 GiB (68,7 GB), para que HDs/SSDs externos de backup não sejam oferecidos por engano. Desmarque para exibi-los.
- **Verificação de mesmo disco**: se a ISO escolhida estiver no mesmo disco físico do destino (em qualquer partição, com symlinks resolvidos), o botão *Iniciar* fica desabilitado com a explicação. A verificação é repetida logo antes de qualquer desmontagem ou formatação.
- Diálogo de confirmação com fabricante, modelo, capacidade e caminho do dispositivo antes de apagar qualquer coisa.

### Gravação
- Extração da ISO em espaço de usuário com `7z` (p7zip), sem `mount -o loop` e sem root.
- Destino em FAT32 com a estrutura UEFI padrão (`/efi/boot/bootx64.efi`).
- `install.wim` maior que 4 GB é dividido em partes `.swm` com `wimlib-imagex split`, mantendo o pendrive compatível com FAT32 / UEFI Secure Boot.

### Interface
- Toda operação longa roda em um `QThread` dedicado; a interface continua responsiva.
- Barra de progresso, etapa atual, estimativa de velocidade e painel de log expansível com cópia para a área de transferência.
- Cancelamento seguro: subprocessos são encerrados e o pendrive é desmontado corretamente.

---

## 🚀 Instalação e Uso

### 1. Compilar e executar o Flatpak localmente

O manifesto usa o runtime KDE 6.6 e empacota as wheels do PySide6 6.6.3 (x86_64).

```bash
# Runtime e SDK do KDE 6.6
flatpak install flathub org.kde.Platform//6.6 org.kde.Sdk//6.6

# Compilar e instalar na instalação do usuário
flatpak-builder --force-clean --user --install build-dir org.woeusb.WoeUsbGui.yml

# Executar
flatpak run org.woeusb.WoeUsbGui
```

> [!TIP]
> Se o build falhar com `fuse: mount failed` (containers, ambientes restritos), acrescente `--disable-rofiles-fuse`.

### 2. Executar a partir do código-fonte (desenvolvimento)

Requisitos:
- Python 3.11+ e `venv` + `pip` (ou [uv](https://docs.astral.sh/uv/))
- Ferramentas do sistema: `p7zip` (`7z`), `wimlib`, `dosfstools` (`mkfs.vfat`), `udisks2`

#### Opção A: `venv` padrão do Python + `pip`

```bash
git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
cd woeusb-gui-flasher

# Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar o projeto em modo editável e as dependências de desenvolvimento
pip install -e . --group dev

# Executar a aplicação
woeusb-gui               # ou: ./run.sh
```

#### Opção B: Usando `uv`

```bash
git clone https://github.com/castrocristiano/woeusb-gui-flasher.git
cd woeusb-gui-flasher
uv sync
uv run woeusb-gui        # ou: ./run.sh
```

---

## 🔒 Permissões do Sandbox Flatpak

| Permissão | Justificativa |
| :--- | :--- |
| `--system-talk-name=org.freedesktop.UDisks2` | Listar pendrives, formatar, montar e desmontar pelo UDisks2 do sistema, sem root. |
| `--filesystem=/run/media:rw` | Gravar os arquivos do Windows no ponto de montagem criado pelo UDisks2. |
| `--filesystem=host:ro` | Ler a `.iso` de qualquer lugar do sistema e descobrir em qual disco físico ela está (verificação de mesmo disco). |
| `--socket=wayland` / `--socket=fallback-x11` | Exibição em Wayland, com X11 como alternativa. |
| `--share=ipc` / `--device=dri` | Memória compartilhada do X11 e renderização acelerada por GPU. |
| `--talk-name=org.freedesktop.Flatpak` | ⚠️ Está no manifesto mas **não é usada pelo código**; será removida antes da submissão (ver [docs/FLATHUB.md](docs/FLATHUB.md#7-open-items-before-flathub-submission)). |

---

## 🧪 Testes e Qualidade

Com o `.venv` ativado (ou prefixando os comandos com `uv run`):

```bash
# Lint e verificação de formatação (igual ao CI)
ruff check .
ruff format --check .

# Testes (headless) com cobertura
QT_QPA_PLATFORM=offscreen pytest -v --cov=src --cov-report=xml:coverage.xml

# Arquivo desktop e metadados AppStream
desktop-file-validate assets/org.woeusb.WoeUsbGui.desktop
appstreamcli validate --no-net --pedantic assets/org.woeusb.WoeUsbGui.metainfo.xml
```

A suíte cobre modelos, disk manager, filtros de segurança, motor de gravação, cancelamento, interface e os contratos UDisks2 / Flatpak / burn engine.

### SonarQube (opcional, local)

Servidor e scanner SonarQube locais estão definidos em [docker-compose.yml](docker-compose.yml) (Docker ou Podman):

```bash
docker compose up -d sonarqube                       # ou: podman-compose up -d sonarqube
docker compose --profile scan run --rm sonar-scanner # rodar depois de gerar o coverage.xml
docker compose down
```

### Integração Contínua

O [.github/workflows/ci.yml](.github/workflows/ci.yml) roda em pushes para `feature/**`, `phase/**`, `develop`, `main` e em PRs:

1. **Build & Test**: `uv sync`, `ruff check`, `ruff format --check`, `pytest` com cobertura.
2. **SonarQube**: análise + Quality Gate em um SonarQube efêmero.
3. **Auto PR**: no `develop`, abre/atualiza o PR `develop → main`.
4. **Release**: no `main`, cria uma GitHub Release com a versão do `pyproject.toml`.

> [!IMPORTANT]
> Essa automação vale **só para este repositório**. Nada no CI interage com `flathub/flathub`; veja a seção de política de IA em [docs/FLATHUB.md](docs/FLATHUB.md#6-flathub-generative-ai-policy-compliance).

---

## 📁 Estrutura do Repositório

```
woeusb-gui-flasher/
├── .github/workflows/ci.yml             # CI: lint, testes, SonarQube, auto PR, release
├── assets/
│   ├── org.woeusb.WoeUsbGui.desktop     # Entrada desktop
│   ├── org.woeusb.WoeUsbGui.metainfo.xml# Metadados AppStream
│   ├── org.woeusb.WoeUsbGui.svg         # Ícone
│   └── screenshots/main-window.png      # Captura usada no AppStream / README
├── docs/FLATHUB.md                      # Empacotamento, permissões, política de IA, pendências
├── specs/                               # Artefatos de Spec-Driven Development
│   ├── 001-woeusb-gui/                  #   aplicação principal
│   └── 002-device-safety-filters/       #   filtro de discos grandes + verificação de mesmo disco
├── src/woeusb_gui_flasher/
│   ├── main.py                          # Ponto de entrada
│   ├── models.py                        # Dataclasses e limiares (mín. 2 GB, "grande" > 64 GiB)
│   ├── utils.py                         # Formatação de bytes, helpers de subprocesso
│   ├── disk_manager.py                  # Descoberta, filtros de segurança, colisão, desmontagem
│   ├── burn_engine.py                   # BurnWorker (QThread): formata, extrai, divide WIM
│   └── ui/
│       ├── components.py                # Widgets reutilizáveis
│       └── main_window.py               # Janela principal e diálogo de confirmação
├── tests/                               # Testes unitários, de contrato e de interface
├── CONTRIBUTING.md
├── docker-compose.yml                   # SonarQube + scanner locais
├── org.woeusb.WoeUsbGui.yml             # Manifesto Flatpak
├── pyproject.toml
└── run.sh                               # Launcher auxiliar
```

---

## 🤝 Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🤖 Declaração de Uso de IA Generativa

Conforme os [requisitos e a política de IA Generativa do Flathub](https://docs.flathub.org/docs/for-app-authors/requirements):

- **Código, testes e documentação** (incluindo este README, o `CONTRIBUTING.md` e o `docs/FLATHUB.md`) foram produzidos com auxílio substancial de assistentes de código com IA Generativa, sob direção e revisão do mantenedor humano.
- **Lógica crítica de segurança** (filtro de discos, detecção de mesmo disco, chamadas ao UDisks2, formatação e divisão do WIM) é revisada e testada pelo mantenedor e coberta por testes automatizados.
- **Manifesto Flatpak**: o Flathub não aceita manifestos gerados ou assistidos por IA, mesmo com declaração. O manifesto submetido ao Flathub será escrito e mantido pelo mantenedor humano.
- **Submissão ao Flathub**: o pull request, as mensagens de commit e todas as respostas aos revisores do Flathub são escritos manualmente pelo mantenedor, sem agentes de IA.

---

## 📜 Licença

**GPL-3.0-or-later**: veja [LICENSE](LICENSE). Os metadados AppStream são licenciados sob **CC0-1.0**.
