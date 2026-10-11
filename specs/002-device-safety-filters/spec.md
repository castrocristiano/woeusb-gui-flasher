# Feature Specification: Filtro de Dispositivos Grandes e Prevenção de Conflito de Disco

**Feature Branch**: `002-device-safety-filters`  
**Created**: 2026-10-10  
**Status**: Ready for Planning  
**Input**: User description: "adicione um botão com default ativo para não listar dispositivos grandes. Verificar se a origem e destino não são ou estão no mesmo disco."

---

## Contexto & Visão Geral

Ao preparar mídias de instalação do Windows em sistemas Linux, os usuários conectam frequentemente dispositivos USB variados, que vão desde pendrives convencionais de 8 GB a 64 GB até discos rígidos externos (HDs) e SSDs portáteis de grande capacidade (500 GB, 1 TB ou mais), utilizados para armazenamento pessoal ou backups.

A gravação de uma imagem de inicialização é um procedimento destrutivo e intensivo em entrada/saída (I/O). Dois riscos críticos foram identificados na experiência do usuário:
1. **Risco de seleção acidental de discos de backup de grande porte**: Discos externos de 1 TB ou superiores podem ser listados como dispositivos USB elegíveis, aumentando o risco de formatação catastrófica de mídias de armazenamento primárias ou lentidão extrema no barramento USB.
2. **Conflito físico entre mídia de origem e destino**: Se o arquivo ISO do Windows estiver localizado em uma partição do mesmo disco rígido ou pendrive selecionado como destino da gravação, iniciar a operação causará a destruição da própria imagem de origem durante a formatação, corrupção de dados ou travamentos críticos de I/O decorrentes de leituras e gravações concorrentes no mesmo dispositivo físico.

Esta funcionalidade introduz salvaguardas adicionais para a interface e fluxo de gravação:
- Um controle visual na interface (marcado por padrão) que filtra mídias removíveis com capacidade superior a 64 GB, exibindo apenas pendrives típicos de instalação, mas permitindo que usuários avançados exibam discos grandes quando desejado.
- Uma validação preventiva determinística que analisa o disco de armazenamento da imagem ISO selecionada e o disco de destino, bloqueando preventivamente a operação se ambos residirem no mesmo disco físico.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filtragem de Dispositivos de Grande Porte com Estado Padrão Ativo (Priority: P1)

Como usuário que possui múltiplos dispositivos USB conectados (incluindo discos de backup externos de grande capacidade e pendrives comuns), desejo que o aplicativo oculte automaticamente unidades grandes por padrão, para que a lista exiba apenas pendrives convencionais de instalação e reduza a zero o risco de sobrescrever acidentalmente um HD/SSD externo de trabalho.

**Why this priority**: Previne destruição acidental de dados em mídias de grande capacidade e evita contenção de I/O em unidades não recomendadas para instaladores portáteis.

**Independent Test**: Pode ser testado conectando simultaneamente um pendrive de 16 GB e um disco externo de 1 TB; ao abrir o aplicativo, apenas o pendrive de 16 GB deve aparecer no seletor de dispositivos. Ao desmarcar o filtro, o disco de 1 TB deve se tornar visível.

**Acceptance Scenarios**:

1. **Given** que o aplicativo foi iniciado com o estado padrão, **When** a lista de dispositivos é carregada, **Then** o controle de filtro "Ocultar discos grandes (> 64 GB)" é exibido com estado marcado (ativo) por padrão.
2. **Given** que o filtro está ativo e existem dispositivos USB conectados de 16 GB e de 1 TB, **When** a listagem de dispositivos de destino é gerada, **Then** apenas o dispositivo de 16 GB é apresentado na lista de seleção.
3. **Given** que o usuário deseja gravar intencionalmente em um disco de grande capacidade, **When** o usuário desmarca a opção "Ocultar discos grandes (> 64 GB)", **Then** a lista de dispositivos é atualizada imediatamente, exibindo tanto o pendrive quanto o disco de 1 TB.
4. **Given** que o usuário marca novamente o controle de filtro, **When** a lista é recalculada, **Then** os dispositivos com capacidade superior a 64 GB são imediatamente removidos da listagem de seleção.
5. **Given** que nenhum pendrive menor que 64 GB está conectado e o filtro está ativo, **When** o usuário visualiza a lista de destinos vazia, **Then** uma mensagem informativa amigável orienta o usuário a conectar um pendrive ou desmarcar o filtro para exibir discos maiores.

---

### User Story 2 - Prevenção Preventiva de Conflito de Origem e Destino no Mesmo Disco (Priority: P1)

Como usuário, desejo ser alertado e impedido de iniciar a gravação se o arquivo ISO que selecionei estiver localizado no mesmo disco físico selecionado como destino, para evitar a perda da imagem ISO durante a formatação e falhas graves de leitura e gravação simultânea.

**Why this priority**: Operações de formatação em um disco destroem as partições existentes. Se a ISO de origem estiver nesse mesmo disco, a operação resultará em perda de dados irreversível e falha catastrófica no processo de gravação.

**Independent Test**: Pode ser testado selecionando uma imagem ISO armazenada em uma partição de um disco externo (ex.: partição 1 de um disco) e tentando selecionar esse mesmo disco físico como destino da gravação; o aplicativo deve exibir alerta claro e desabilitar o botão de início.

**Acceptance Scenarios**:

1. **Given** que o usuário selecionou uma imagem ISO localizada em uma partição de um disco físico específico, **When** o usuário seleciona como dispositivo de destino esse mesmo disco físico (ou qualquer partição contida nele), **Then** o aplicativo detecta a colisão de disco físico imediatamente.
2. **Given** que a colisão entre origem e destino foi detectada, **When** o usuário observa a interface, **Then** o botão "Iniciar Gravação" é desabilitado e uma mensagem de alerta visível informa claramente que o arquivo ISO está armazenado no mesmo disco selecionado como destino.
3. **Given** um estado de colisão detectado, **When** o usuário altera a seleção para outro dispositivo de destino localizado em disco físico distinto (ou escolhe uma ISO em outro disco), **Then** o estado de bloqueio é desfeito e o botão "Iniciar Gravação" volta a ficar disponível (caso os demais requisitos estejam válidos).
4. **Given** que o usuário tente acionar a gravação por atalhos ou eventos assíncronos, **When** a validação final pré-gravação é executada, **Then** o sistema verifica novamente se origem e destino pertencem ao mesmo disco físico e aborta o início antes de qualquer operação destrutiva (desmontagem ou formatação).

---

### User Story 3 - Feedback Amigável e Clareza nas Validações de Disco (Priority: P2)

Como usuário, desejo receber orientações contextuais claras sobre os critérios de filtragem e as razões de bloqueio de gravação, para que eu compreenda rapidamente como resolver pendências operacionais sem recorrer a suporte técnico.

**Why this priority**: Assegura que o usuário compreenda o motivo pelo qual um disco não aparece na lista ou por que o botão de gravação está inativo, proporcionando uma experiência de uso transparente e sem frustrações.

**Independent Test**: Pode ser testado ativando/desativando o filtro e simulando cenários de colisão para inspecionar os textos de aviso e tooltips da interface gráfica.

**Acceptance Scenarios**:

1. **Given** o controle de filtro na tela, **When** o usuário passa o cursor sobre ele, **Then** um texto descritivo (tooltip) detalha que mídias com capacidade superior a 64 GB são ocultadas por segurança para evitar seleção de discos de backup.
2. **Given** a detecção de colisão entre origem e destino, **When** a mensagem de erro é apresentada, **Then** ela orienta o usuário de forma prescritiva (exemplo: "Mova o arquivo ISO para um disco interno ou selecione outro pendrive").

---

### Edge Cases

- **Múltiplas partições no mesmo disco físico**: A imagem ISO está na partição 2 (`/dev/sdb2`) e o destino selecionado é a partição 1 (`/dev/sdb1`) ou o disco raiz (`/dev/sdb`). O sistema deve identificar que o dispositivo pai de bloco é idêntico e bloquear a operação.
- **Links simbólicos na rota da ISO**: O caminho da ISO selecionada aponta para um symlink cujo alvo final reside no disco de destino. O sistema deve resolver o caminho canônico do arquivo antes de determinar o disco físico subjacente.
- **Dispositivo removido ou desconectado durante a validação**: Se o dispositivo alvo for desconectado antes do início da gravação, a validação de colisão e a listagem devem ser invalidadas com segurança sem congelar a aplicação.
- **Dispositivo com tamanho limítrofe (exato limiar de 64 GB)**: Unidades de 64 GB comerciais (que reportam entre 58 GiB e 64.5 GB) devem ser tratadas adequadamente como pendrives típicos e permanecer visíveis sob o filtro padrão. O limiar de corte deve considerar mídias que excedam a capacidade nominal de 64 GB (ex.: corte acima de 65 GB ou 68.7 GB / 64 GiB).
- **ISO em sistema de arquivos de rede ou virtual**: Se a ISO estiver em um sistema de arquivos virtual (ex.: tmpfs, nfs ou montagem sem dispositivo de bloco direto), o sistema deve identificar a ausência de colisão física e permitir a gravação normalmente.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE incluir um controle de filtro selecionável na interface gráfica com o rótulo "Ocultar discos grandes (> 64 GB)" (ou equivalente claro).
- **FR-002**: O sistema DEVE inicializar o controle de filtro de discos grandes em estado **ativo** (marcado) por padrão.
- **FR-003**: Quando o filtro estiver ativo, o sistema DEVE omitir da listagem de dispositivos de gravação qualquer unidade cuja capacidade nominal seja superior a 64 GB.
- **FR-004**: Quando o filtro for desmarcado pelo usuário, o sistema DEVE atualizar imediatamente a lista de dispositivos de gravação para exibir todas as mídias removíveis elegíveis, independentemente do tamanho.
- **FR-005**: Ao marcar novamente o filtro, o sistema DEVE atualizar dinamicamente a listagem de dispositivos, removendo as mídias grandes que excedam o limite.
- **FR-006**: Se o dispositivo atualmente selecionado for um disco grande e o usuário reativar o filtro, o sistema DEVE limpar a seleção atual e solicitar nova escolha.
- **FR-007**: O sistema DEVE inspecionar o dispositivo de armazenamento físico pai (parent physical block device) onde reside o arquivo ISO selecionado.
- **FR-008**: O sistema DEVE inspecionar o dispositivo de armazenamento físico pai selecionado como alvo de gravação.
- **FR-009**: O sistema DEVE comparar a identidade física do disco que armazena a ISO com a do disco de destino antes de permitir a operação.
- **FR-010**: Se o disco de armazenamento da ISO e o disco de destino coincidirem (mesmo dispositivo físico ou partições do mesmo disco), o sistema DEVE bloquear o acionamento da gravação.
- **FR-011**: Em caso de colisão detectada entre origem e destino, o sistema DEVE exibir um alerta visual claro informando ao usuário que a ISO está localizada no mesmo disco físico selecionado para gravação.
- **FR-012**: O sistema DEVE revalidar a colisão de disco físico sempre que o usuário alterar o caminho da ISO ou mudar o dispositivo de destino selecionado.
- **FR-013**: O sistema DEVE realizar uma validação final de colisão física imediatamente antes de iniciar qualquer etapa destrutiva no processo de gravação, interrompendo o fluxo com mensagem explicativa caso haja coincidência.

---

### Key Entities *(include if feature involves data)*

- **Dispositivo de Armazenamento Removível**: Representa uma mídia de bloco elegível para gravação, caracterizada por identificador de dispositivo, modelo/fabricante, capacidade total em bytes, rótulo de volume e indicação se excede o limiar de grande capacidade.
- **Origem da Imagem (ISO Source)**: Representa o arquivo de imagem selecionado, incluindo caminho canônico no sistema de arquivos e identificador do dispositivo de bloco físico no qual está gravado.
- **Estado de Validação de Segurança**: Representa o resultado das checagens pré-gravação, contendo status de aptidão (válido ou bloqueado), motivo do bloqueio (ex.: colisão de disco físico, capacidade insuficiente) e mensagem formatada para apresentação ao usuário.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O tempo de atualização da listagem de dispositivos após o usuário alternar o controle de filtro de discos grandes DEVE ser inferior a 300 milissegundos.
- **SC-002**: 100% das tentativas de gravação em que a ISO e o destino compartilham o mesmo disco físico DEVEM ser bloqueadas antes da execução de qualquer comando de desmontagem ou formatação.
- **SC-003**: 100% dos discos externos com capacidade superior a 64 GB DEVEM ser filtrados da visualização padrão sem requerer configuração prévia do usuário.
- **SC-004**: O usuário DEVE ser capaz de alternar entre a visão de apenas pendrives e a visão de todos os dispositivos com um único clique.
- **SC-005**: Zero ocorrências de perda de imagem ISO ou corrupção de mídias de origem devido a conflito de gravação no mesmo disco físico.

---

## Assumptions

- O limite de 64 GB (aproximadamente 64 GiB / 68.7 GB) foi adotado como corte padrão porque imagens modernas de instalação do Windows requerem entre 8 GB e 32 GB de mídia, sendo pendrives de 16 GB, 32 GB e 64 GB os mais comuns no mercado para criação de instaladores.
- Discos externos com capacidades de 128 GB, 256 GB, 500 GB, 1 TB ou superiores são tipicamente unidades de armazenamento massivo ou discos de backup e não pendrives de uso descartável.
- Usuários que intencionalmente desejam gravar em um SSD ou HD externo grande podem fazê-lo simplesmente desmarcando o filtro na interface.
- A resolução de dispositivo pai da ISO considera caminhos locais canônicos acessíveis ao usuário ou ao ambiente de execução da aplicação.

