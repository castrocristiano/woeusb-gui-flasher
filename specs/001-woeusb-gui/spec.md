# Feature Specification: WoeUSB GUI Flasher (Gravador Gráfico de Windows USB)

**Feature Branch**: `001-woeusb-gui`  
**Created**: 2026-10-10  
**Status**: Draft (Updated: Universal Linux via Flatpak)  
**Input**: User description: "baseado nisso, na pasta Dev do meu usuário, quero que crie uma app python que faça esse procedimento, com sdd e baseado em interface gráfica para linux baseado em woe. A aplicação deve rodar em qualquer linux, via flatpak"

---

## Contexto & Visão Geral

O objetivo desta especificação é definir os requisitos funcionais, comportamentais e técnicos para uma aplicação desktop em Python com interface gráfica (PySide6 / Qt6) empacotada universalmente via **Flatpak** (`org.woeusb.WoeUsbGui`), permitindo execução em **qualquer distribuição Linux** (BigLinux, Fedora, Ubuntu, Debian, Arch, openSUSE, Linux Mint, Pop!_OS, etc.) sem depender de ferramentas instaladas manualmente no sistema host.

A aplicação automatiza a criação de pendrives inicializáveis do Windows (Windows 10, Windows 11, Windows 7/8), com particionamento inteligente, split automático de imagens `install.wim` (> 4 GB) para partições FAT32, compatibilidade com firmware UEFI (Secure Boot) e Legacy BIOS, e proteção robusta contra gravação em discos internos e partições de sistema operacional.

Para viabilizar a execução dentro do sandbox restrito do Flatpak, a arquitetura utiliza:
1. **Comunicação D-Bus com `org.freedesktop.UDisks2`**: Para particionamento, formatação e montagem de blocos via permissões nativas do Polkit do host sem requisições inseguras.
2. **Extração de ISO em espaço de usuário (User-Space Extraction)**: Utilizando ferramentas como `7z` ou bibliotecas nativas de ISO para extrair os arquivos da ISO diretamente para o pendrive montado, eliminando a dependência do comando de kernel `mount -o loop` (bloqueado em containers Flatpak).
3. **Divisão de WIM integrada (`wimlib-imagex`)**: Empacotada no Flatpak para dividir `install.wim` em partes `.swm` de até 4 GB em modo user-space.
4. **Fallback com `flatpak-spawn --host`**: Para ambientes onde a execução direta do script `woeusb` no host via `pkexec` seja explicitamente solicitada.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instalação e Execução Universal via Flatpak (Priority: P1)

Como usuário em qualquer distribuição Linux (ex: Fedora Silverblue, Ubuntu, Arch, BigLinux), desejo instalar a aplicação via Flatpak e executá-la diretamente pelo menu de aplicativos do sistema, tendo todas as bibliotecas gráficas (Qt 6) e ferramentas de gravação já embutidas, sem necessidade de compilar ou instalar pacotes de terminal.

**Why this priority**: Garante portabilidade universal ("qualquer linux, via flatpak"), evitando conflitos de dependências do Python no host (como PEP 668) e inconsistências entre distribuições.

**Independent Test**: Pode ser testado gerando o pacote Flatpak (`flatpak-builder`) e executando `flatpak run org.woeusb.WoeUsbGui` em uma distribuição limpa.

**Acceptance Scenarios**:

1. **Given** um sistema Linux com suporte a Flatpak, **When** a aplicação é instalada, **Then** o ícone aparece no lançador de aplicativos e abre a interface gráfica com suporte a Wayland e X11.
2. **Given** que a aplicação está em execução no sandbox Flatpak, **When** solicita a lista de discos, **Then** ela acessa o serviço `org.freedesktop.UDisks2` do sistema host via D-Bus para enumerar os pendrives conectados.

---

### User Story 2 - Gravação de Imagem do Windows em Pendrive USB (Priority: P1)

Como usuário, desejo selecionar uma imagem ISO oficial do Windows (ex: `Win10_21H1_BrazilianPortuguese_x64.iso`), selecionar meu pendrive conectado (ex: `/dev/sdd` - 16 GB), clicar em "Gravar" e obter um pendrive bootável funcional sem precisar executar comandos complexos no terminal.

**Why this priority**: É a funcionalidade central da aplicação.

**Independent Test**: Pode ser testado selecionando uma ISO do Windows 10 e um pendrive de teste, autenticando via Polkit/UDisks2, e verificando se os arquivos foram copiados, divididos e tornados bootáveis.

**Acceptance Scenarios**:

1. **Given** que o usuário abriu a aplicação, **When** seleciona a imagem ISO e escolhe o pendrive `/dev/sdd` e clica em "Iniciar Gravação", **Then** uma tela de confirmação é exibida detalhando o dispositivo de destino e alertando sobre a perda total dos dados contidos nele.
2. **Given** que o usuário confirmou a gravação, **When** o processo é disparado, **Then** o sistema solicita autenticação segura de administrador via Polkit (através do UDisks2) e inicia a preparação da mídia.
3. **Given** que a ISO do Windows contém um `install.wim` maior que 4 GB e o formato alvo é FAT32, **When** os arquivos estão sendo copiados, **Then** a aplicação invoca a divisão automática em arquivos `.swm` via `wimlib-imagex`, mantendo compatibilidade nativa com UEFI e BIOS.
4. **Given** que a gravação finalizou com sucesso, **When** todas as etapas são concluídas, **Then** os pontos de montagem são limpos/sincronizados (`sync`), a barra de progresso atinge 100% e uma notificação de sucesso é exibida informando que o pendrive pode ser removido.

---

### User Story 3 - Detecção Segura e Isolamento de Dispositivos (Priority: P1)

Como usuário, desejo que a aplicação detecte automaticamente apenas unidades removíveis e pendrives USB (ex: `sdd`, `sde`), impedindo que discos rígidos internos, SSDs NVMe e partições do sistema operacional (ex: `/`, `/boot`, `/home`, `[SWAP]`) sejam selecionados acidentalmente.

**Why this priority**: Gravação em blocos (`/dev/sdX`) é uma operação destrutiva e irreversível. A segurança dos dados do usuário é um requisito inegociável.

**Independent Test**: Pode ser testado executando o aplicativo em uma máquina com múltiplos discos e verificando que apenas pendrives USB elegíveis são listados para gravação.

**Acceptance Scenarios**:

1. **Given** que o usuário conecta um novo pendrive USB de 16 GB, **When** clica no botão "Atualizar Dispositivos" (ou na inicialização do app), **Then** o novo dispositivo aparece na lista com caminho (`/dev/sdd`), modelo/marca (`Netac OnlyDisk`), tamanho (`14.5 GB`) e rótulo atual.
2. **Given** um disco interno SATA (`/dev/sda`) ou NVMe (`/dev/nvme0n1`) contendo as partições do sistema, **When** a lista de dispositivos é carregada com o filtro de segurança ativo, **Then** esses discos são categoricamente omitidos da lista de gravação.
3. **Given** um pendrive com partições montadas no sistema (ex: `/run/media/cristiano/Windows USB`), **When** o usuário inicia a gravação, **Then** a aplicação solicita a desmontagem via D-Bus UDisks2 antes de iniciar a formatação.

---

### User Story 4 - Feedback Visual e Observabilidade em Tempo Real (Priority: P2)

Como usuário, desejo acompanhar o progresso exato da gravação (porcentagem de 0 a 100%, etapa atual sendo executada e tempo decorrido) e ter acesso aos logs detalhados caso queira diagnosticar problemas.

**Why this priority**: Gravações de arquivos grandes (5+ GB) em pendrives USB levam vários minutos. Sem feedback em tempo real, o usuário pode acreditar que a aplicação travou.

**Independent Test**: Pode ser testado observando a transição de status durante uma gravação real ou simulada, verificando atualização contínua da barra de progresso e fluxo de texto no painel de logs.

**Acceptance Scenarios**:

1. **Given** que o processo de gravação começou, **When** o processo avança nas etapas, **Then** o rótulo de status exibe descrições amigáveis:
   - "Preparando e formatando partição..."
   - "Extraindo arquivos de boot e estrutura da ISO..."
   - "Copiando e dividindo imagem install.wim..."
   - "Configurando bootloader UEFI..."
   - "Sincronizando dados e finalizando..."
2. **Given** que o processo emite progresso em bytes/porcentagem, **When** os dados são processados, **Then** a barra de progresso é atualizada suavemente.
3. **Given** que o usuário expande o painel de logs, **When** as mensagens são emitidas, **Then** as linhas são exibidas com rolagem automática e botão para copiar logs.

---

### User Story 5 - Cancelamento Seguro e Tratamento de Erros (Priority: P3)

Como usuário, desejo poder cancelar uma operação em andamento com segurança, e receber mensagens de erro claras caso ocorra alguma falha.

**Why this priority**: Evita processos zumbis, pontos de montagem órfãos e dispositivos em estado inconsistente quando o usuário cancela a operação.

**Acceptance Scenarios**:

1. **Given** que a gravação está em andamento, **When** o usuário clica em "Cancelar Operação" e confirma, **Then** a cópia é interrompida, os arquivos temporários são limpos e a interface volta ao estado inicial.
2. **Given** que o usuário cancela o diálogo de autenticação do Polkit, **When** a chamada D-Bus retorna erro de autorização, **Then** a interface informa "Operação cancelada: permissão não concedida" sem travar.

---

## Edge Cases & Flatpak Sandbox Considerations

- **Acesso a arquivos ISO fora do sandbox**: O Flatpak deve utilizar o Portal de Documentos (`xdg-desktop-portal`) e permissões `--filesystem=host` para permitir a leitura de arquivos ISO localizados em qualquer partição ou pasta do usuário (`/run/media/...`, `~/Downloads`, `/home/...`).
- **Sem privilégios de root direto no container**: O Flatpak não executa como root nem permite `mount -o loop`. Toda manipulação de disco de baixo nível é delegada ao `org.freedesktop.UDisks2` e a extração de ISO é feita em espaço de usuário via ferramentas empacotadas no runtime Flatpak.
- **Pendrives desconectados durante a gravação**: O erro de I/O é tratado imediatamente, notificando o usuário e reabilitando a interface.
- **Temas do Sistema**: Compatibilidade automática com os estilos do host (Breeze, Adwaita, temas escuros/claros) fornecida pelos runtimes Flatpak do KDE/Freedesktop.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE ser empacotado como uma aplicação **Flatpak** com ID `org.woeusb.WoeUsbGui`.
- **FR-002**: O manifesto Flatpak DEVE incluir as permissões necessárias:
  - `--socket=wayland` e `--socket=fallback-x11` (Interface gráfica)
  - `--share=ipc`
  - `--device=dri` (Aceleração de renderização gráfica)
  - `--filesystem=host` (Acesso a imagens ISO e pontos de montagem em `/run/media`)
  - `--system-talk-name=org.freedesktop.UDisks2` (Comunicação com o daemon de discos do host)
  - `--talk-name=org.freedesktop.Flatpak` (Para fallback de execução host se necessário)
- **FR-003**: O sistema DEVE permitir a seleção de arquivos de imagem ISO (`*.iso`) através do diálogo nativo do sistema operacional (`QFileDialog` integrado ao XDG Desktop Portal).
- **FR-004**: O sistema DEVE validar o arquivo selecionado, exibindo nome e tamanho formatado (ex: "5.15 GB").
- **FR-005**: O sistema DEVE enumerar os dispositivos de armazenamento através da interface D-Bus `org.freedesktop.UDisks2` ou `lsblk`.
- **FR-006**: O sistema DEVE filtrar e exibir exclusivamente dispositivos removíveis/USB por padrão (`TRAN=usb` ou `RM=true`), ocultando categoricamente partições de sistema (`/`, `/boot`, `/home`, `[SWAP]`, etc.).
- **FR-007**: O sistema DEVE prover botão de atualização ("Recarregar") para atualizar a lista de pendrives conectados.
- **FR-008**: O sistema DEVE oferecer suporte a sistema de arquivos FAT32 (com divisão automática de WIM) e NTFS.
- **FR-009**: O sistema DEVE exibir confirmação explícita antes de qualquer formatação, detalhando caminho, tamanho e nome do pendrive.
- **FR-010**: O sistema DEVE realizar a extração e particionamento em uma thread assíncrona desacoplada (`QThread`), garantindo interface responsiva em 60 FPS.
- **FR-011**: O sistema DEVE emitir atualizações de porcentagem contínua e texto descritivo de cada fase.
- **FR-012**: O sistema DEVE fornecer painel de logs detalhados em tempo real com opção de cópia.
- **FR-013**: O sistema DEVE permitir cancelamento seguro da gravação a qualquer momento.
- **FR-014**: O sistema DEVE incluir manifesto Flatpak (`org.woeusb.WoeUsbGui.yml`) pronto para compilação via `flatpak-builder`.

---

### Key Entities

- **StorageDevice**: Unidade de armazenamento identificada via UDisks2 / lsblk (`name`, `path`, `size_human`, `model`, `vendor`, `is_removable`, `is_system_drive`).
- **WindowsISO**: Imagem de instalação (`file_path`, `file_name`, `file_size_human`, `is_valid`).
- **BurnConfiguration**: Configuração da operação (`iso`, `target_device`, `filesystem`, `boot_mode`).
- **BurnExecutionState**: Estado em tempo real (`status`, `progress_percentage`, `current_stage`, `log_lines`).
- **FlatpakPackageConfig**: Configurações de empacotamento (`app_id`, `runtime`, `sdk`, `finish_args`, `modules`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O aplicativo Flatpak inicia e funciona identicamente em qualquer distribuição Linux moderna (BigLinux, Fedora, Ubuntu, Arch, Debian, openSUSE).
- **SC-002**: 100% de isolamento e proteção contra gravação em unidades de disco de sistema operacional interno.
- **SC-003**: 100% dos pendrives gerados com formato FAT32 devem ser inicializáveis em computadores UEFI com Secure Boot habilitado.
- **SC-004**: A aplicação não congela ou trava durante o processo de gravação de arquivos grandes.
- **SC-005**: O arquivo de manifesto Flatpak compila sem erros via `flatpak-builder`.

---

## Assumptions

- O sistema host possui Flatpak instalado e o serviço `UDisks2` ativo (padrão em 99% das distribuições desktop Linux).
- O usuário possui permissões padrão de usuário desktop para formatar dispositivos de armazenamento removíveis.
