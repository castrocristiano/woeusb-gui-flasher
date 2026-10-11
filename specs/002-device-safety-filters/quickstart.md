# Quickstart Validation Guide: Filtro de Dispositivos Grandes e Prevenção de Conflito de Disco

**Feature**: `002-device-safety-filters`  
**Date**: 2026-10-10  
**Status**: Ready  

---

## 1. Pré-Requisitos

- Ambiente Python com dependências instaladas ou sandbox Flatpak.
- Execução de testes sem interface gráfica: `QT_QPA_PLATFORM=offscreen`.

---

## 2. Cenários de Validação Automatizados

### Cenário 1: Filtragem de Dispositivos de Grande Porte
- **Objetivo**: Verificar que dispositivos USB com tamanho $> 64\text{ GiB}$ ($68.7\text{ GB}$) são excluídos da lista quando o filtro está ativo e incluídos quando desativado.
- **Comando de Teste**:
  ```bash
  QT_QPA_PLATFORM=offscreen PYTHONPATH=src:.venv/lib/python3.12/site-packages python3 -m pytest tests/test_device_safety_filters.py -k "test_filter_large_drives"
  ```
- **Resultado Esperado**:
  - `DiskManager.get_removable_devices(hide_large_drives=True)` retorna apenas mídias $\le 64\text{ GiB}$.
  - `DiskManager.get_removable_devices(hide_large_drives=False)` inclui dispositivos de 1 TB ou 2 TB.

---

### Cenário 2: Detecção de Conflito de Mesmo Disco Físico
- **Objetivo**: Garantir que uma imagem ISO localizada em `/dev/sdc2` gera resultado de colisão `has_collision=True` quando o destino selecionado é `/dev/sdc` ou `/dev/sdc1`.
- **Comando de Teste**:
  ```bash
  QT_QPA_PLATFORM=offscreen PYTHONPATH=src:.venv/lib/python3.12/site-packages python3 -m pytest tests/test_device_safety_filters.py -k "test_same_disk_collision"
  ```
- **Resultado Esperado**:
  - `check_same_disk_collision` identifica a identidade comum do parent block (`/dev/sdc`).
  - O resultado indica `has_collision=True` e bloqueia a gravação.

---

### Cenário 3: Validação no Motor de Gravação (BurnConfiguration)
- **Objetivo**: Confirmar que `BurnConfiguration.validate()` rejeita configurações onde origem e destino compartilham o mesmo disco com uma exceção `ValueError`.
- **Comando de Teste**:
  ```bash
  QT_QPA_PLATFORM=offscreen PYTHONPATH=src:.venv/lib/python3.12/site-packages python3 -m pytest tests/test_device_safety_filters.py -k "test_burn_config_same_disk_validation"
  ```
- **Resultado Esperado**:
  - A tentativa de inicialização lança `ValueError` antes de qualquer chamada a UDisks2 ou particionamento.

---

### Cenário 4: Interação Visual na Interface do Usuário
- **Objetivo**: Comprovar que o checkbox de filtro inicia marcado por padrão e que a UI desabilita o botão "Iniciar Gravação" exibindo mensagem de erro quando há colisão.
- **Comando de Teste**:
  ```bash
  QT_QPA_PLATFORM=offscreen PYTHONPATH=src:.venv/lib/python3.12/site-packages python3 -m pytest tests/test_ui_safety_filters.py
  ```
- **Resultado Esperado**:
  - `card_drive.is_hide_large_drives_active()` é `True` na inicialização.
  - Alternar o checkbox dispara atualização dinâmica dos itens do `QComboBox`.
  - Simulando ISO e pendrive no mesmo disco, `btn_burn.isEnabled()` é `False` e o label de aviso fica visível.

---

## 3. Validação Manual na Interface Gráfica

1. Executar a aplicação localmente:
   ```bash
   ./run.sh
   ```
   ou via Flatpak:
   ```bash
   flatpak run org.woeusb.WoeUsbGui
   ```
2. Verificar que o checkbox `"Ocultar discos grandes (> 64 GB)"` está marcado por padrão.
3. Observar que o HD externo (ex.: Seagate de 1 TB) não aparece na listagem.
4. Desmarcar o checkbox e constatar a aparição imediata do HD externo no seletor.
5. Selecionar uma ISO armazenada no HD externo e tentar selecionar o próprio HD externo: constatar o aviso vermelho e o botão de gravação desabilitado.

