# Research & Technical Decisions: Filtro de Dispositivos Grandes e Prevenção de Conflito de Disco

**Feature**: `002-device-safety-filters`  
**Date**: 2026-10-10  
**Status**: Completed  

---

## 1. Filtragem de Dispositivos de Grande Porte (Large Drive Filtering)

### Contexto & Problema
Atualmente, o `DiskManager` filtra unidades removíveis USB (`TRAN=usb` ou `RM=true`) com tamanho $\ge$ 2 GB e que não possuam pontos de montagem do sistema (`/`, `/home`, etc.). No entanto, unidades de backup externas (ex.: HDs de 1 TB ou 2 TB como o Seagate Expansion) são marcadas pelo kernel como dispositivos USB removíveis e aparecem no dropdown. Usuários podem selecionar acidentalmente um HD com backups inteiros, além de que a escrita de instaladores do Windows em unidades lentas ou de grande porte frequentemente satura o barramento USB causando timeouts de UAS.

### Pesquisa & Decisões

#### Decisão 1: Limiar de Capacidade para "Dispositivos Grandes"
- **Decisão**: Adotar $64\text{ GiB}$ ($68.719.476.736\text{ bytes}$) como o ponto de corte do filtro. Mídias com capacidade reportada em bytes superior a $68{,}7\text{ GB}$ são consideradas unidades de grande porte.
- **Racional**:
  - Pendrives comerciais de 64 GB rotulados pelos fabricantes costumam reportar entre $58\text{ GiB}$ e $64{,}5\text{ GB}$ no sistema operacional devido à convenção decimal ($1\text{ GB} = 10^9\text{ bytes}$).
  - Definir o corte em $68{,}7\text{ GB}$ ($64\text{ GiB}$) garante que pendrives convencionais de 8 GB, 16 GB, 32 GB e 64 GB permaneçam 100% visíveis no filtro padrão.
  - Discos de 128 GB, 256 GB, 500 GB, 1 TB e superiores serão ocultados quando o filtro estiver ativo.
- **Alternativas descartadas**:
  - *Corte em 32 GB*: Excluiria pendrives legítimos de 64 GB muito usados hoje em dia para mídias de instalação com ISOs de Windows 11 atualizadas.
  - *Corte estrito em 64.000.000.000 bytes*: Poderia ocultar pendrives de 64 GB cuja contagem de blocos exceda ligeiramente a marca por conta de partições ou cabeçalhos.

#### Decisão 2: Controle na Interface e Estado Padrão
- **Decisão**: Adicionar um `QCheckBox` estilizado no `DriveSelectorCard` com o rótulo `"Ocultar discos grandes (> 64 GB)"` e estado padrão marcado (`setChecked(True)`).
- **Racional**:
  - Cumpre diretamente o requisito do usuário ("com default ativo para não listar dispositivos grandes").
  - Oferece um botão/toggle visual discreto ao lado ou abaixo do seletor de discos, permitindo que usuários que intencionalmente precisem gravar em discos maiores desmarquem a opção com apenas um clique.
  - Conectar o evento `toggled` para recalcular dinamicamente os itens exibidos no `QComboBox` sem requerer nova consulta D-Bus ou I/O pesado de disco.

---

## 2. Detecção Preventiva de Origem e Destino no Mesmo Disco Físico (Same-Disk Collision Check)

### Contexto & Problema
Se o usuário selecionar um arquivo ISO (`/run/media/cristiano/Dados/Win10.iso`) que está localizado em uma partição de um disco externo (ex.: `/dev/sdc2`), e selecionar como destino de gravação o disco `/dev/sdc`, a formatação ou particionamento do disco destruirá a própria ISO de origem durante o processo. Além disso, leituras massivas e escritas no mesmo barramento USB causam contenção e travamentos de I/O.

### Pesquisa & Decisões

#### Decisão 1: Mecanismo de Resolução do Disco Físico Subjacente
- **Decisão**: Utilizar uma estratégia multinível compatível com Flatpak sandbox e Linux host:
  1. **Resolução do caminho canônico**: `iso_path.resolve()` para tratar symlinks.
  2. **Identificação do ponto de montagem e dispositivo de bloco da ISO**:
     - Através de `/proc/self/mountinfo` (sempre legível no sandbox Linux) e `os.stat(iso_path).st_dev`.
     - Comparar o `st_dev` do arquivo da ISO com os pontos de montagem conhecidos para identificar a partição (ex.: `/dev/sdc2` ou `/dev/nvme0n1p3`).
  3. **Identificação do Parent Disk (Disco Físico Raiz)**:
     - Função utilitária canônica `get_parent_disk_name(device_name_or_path: str) -> str`:
       - Para discos SCSI/SATA/USB (`/dev/sdX[0-9]*`): remove os dígitos finais da partição $\to$ `/dev/sdX` (ex.: `/dev/sdc2` $\to$ `/dev/sdc`).
       - Para NVMe (`/dev/nvmeXnYpZ`): remove o sufixo `p[0-9]+` $\to$ `/dev/nvmeXnY` (ex.: `/dev/nvme0n1p2` $\to$ `/dev/nvme0n1`).
       - Para MMC/eMMC (`/dev/mmcblkXpY`): remove o sufixo `p[0-9]+` $\to$ `/dev/mmcblkX` (ex.: `/dev/mmcblk0p1` $\to$ `/dev/mmcblk0`).
       - Fallback via `lsblk -no PKNAME` e D-Bus `UDisks2` quando disponível.
- **Racional**:
  - Funciona de forma ultrarrápida ($< 5\text{ ms}$), determinística e sem dependência de privilégios de `root`.
  - É 100% tolerante a ambientes Flatpak, onde `/proc/self/mountinfo` reflete os pontos de montagem do sistema e dispositivos expostos.

#### Decisão 2: Tratamento e Feedback na Interface do Usuário
- **Decisão**: 
  1. No `MainWindow._update_burn_button_state()`: invocar `check_same_disk_collision(iso, drive)`.
  2. Se houver colisão:
     - Desabilitar o botão `Iniciar Gravação`.
     - Exibir mensagem de alerta destacada em vermelho no card de seleção ou abaixo dos botões de ação:
       `"Aviso: O arquivo ISO de origem está armazenado no mesmo disco físico selecionado como destino. Selecione outro pendrive ou transfira a ISO para outro disco."`
  3. No `BurnConfiguration.validate()`: adicionar validação preventiva mandatória antes de qualquer ação do `BurnWorker`.
- **Racional**:
  - Evita qualquer chance de o usuário prosseguir por engano.
  - Oferece orientação imediata e clara sem mensagens de erro crípticas de terminal.

---

## 3. Resumo de Decisões Arquiteturais

| Questão | Decisão Técnica | Racional |
|---------|-----------------|----------|
| Padrão de corte de tamanho | $68{,}7\text{ GB}$ ($64\text{ GiB}$) | Cobre pendrives típicos de até 64 GB comerciais sem descartá-los acidentalmente. |
| Reatividade da UI | Sinal `filter_toggled` no `DriveSelectorCard` | Filtra dispositivos em memória sem refazer requisições de barramento desnecessárias. |
| Identificação de disco de origem | `os.stat` + `/proc/self/mountinfo` + normalização de parent block | Compatível com Flatpak, instantâneo e sem necessidade de elevação de privilégios. |
| Ponto de validação de colisão | Dupla checagem: reativa na UI e mandatória no `BurnConfiguration.validate()` | Garante segurança visual para o usuário e proteção de dados rigorosa no motor. |

