# Contract: DiskManager Safety Extensions

**Component**: `woeusb_gui_flasher.disk_manager.DiskManager`  
**Feature**: `002-device-safety-filters`  
**Date**: 2026-10-10  

---

## 1. get_removable_devices

### Assinatura
```python
def get_removable_devices(self, hide_large_drives: bool = True) -> list[StorageDevice]: ...
```

### Comportamento
- Quando `hide_large_drives=True` (comportamento padrão):
  - Retorna apenas dispositivos USB removíveis com tamanho $\le 68.719.476.736$ bytes ($64\text{ GiB}$) e $\ge 2\text{ GB}$.
  - Dispositivos maiores (como discos de 128 GB, 500 GB, 1 TB) são excluídos da lista retornada.
- Quando `hide_large_drives=False`:
  - Retorna todos os dispositivos USB removíveis elegíveis ($\ge 2\text{ GB}$ e não-sistema), incluindo os de grande porte.
- Dispositivos contendo partições de sistema (`/`, `/boot`, `/home`, etc.) são **sempre** excluídos independentemente do valor de `hide_large_drives`.

---

## 2. get_parent_disk_name

### Assinatura
```python
@staticmethod
def get_parent_disk_name(device_or_partition: str | Path) -> str: ...
```

### Comportamento
- Normaliza o caminho do bloco para retornar o identificador canônico do disco físico pai.
- Exemplos de mapeamento:
  - `"/dev/sdd1"` $\to$ `"/dev/sdd"`
  - `"/dev/sdd"` $\to$ `"/dev/sdd"`
  - `"/dev/sdc2"` $\to$ `"/dev/sdc"`
  - `"/dev/nvme0n1p2"` $\to$ `"/dev/nvme0n1"`
  - `"/dev/nvme0n1"` $\to$ `"/dev/nvme0n1"`
  - `"/dev/mmcblk0p1"` $\to$ `"/dev/mmcblk0"`
  - `"sdd1"` $\to$ `"/dev/sdd"`

---

## 3. resolve_file_source_block_device

### Assinatura
```python
def resolve_file_source_block_device(self, file_path: Path) -> str | None: ...
```

### Comportamento
- Inspeciona o caminho do arquivo (resolvendo symlinks via `resolve()`).
- Consulta `/proc/self/mountinfo` e `os.stat(resolved_path).st_dev` para localizar o dispositivo de bloco correspondente à partição de montagem onde o arquivo reside.
- Retorna o caminho do dispositivo de partição (ex.: `"/dev/sdc2"` ou `"/dev/nvme0n1p3"`).
- Se o arquivo estiver em um sistema de arquivos virtual (ex.: `tmpfs`, montagem de rede `nfs` ou `ramfs`), retorna `None`.

---

## 4. check_same_disk_collision

### Assinatura
```python
def check_same_disk_collision(
    self,
    iso_path: Path | str,
    target_device: StorageDevice,
) -> DiskCollisionCheckResult: ...
```

### Comportamento
- Resolve o dispositivo de bloco de origem do `iso_path`.
- Se o dispositivo de origem for `None` (ex.: memória RAM ou rede), retorna `has_collision=False`.
- Obtém o disco pai da origem (`get_parent_disk_name(source_part)`).
- Obtém o disco pai do destino (`get_parent_disk_name(target_device.path)`).
- Se os discos pais coincidirem:
  - Retorna `DiskCollisionCheckResult(has_collision=True, ...)` com mensagem explicativa em português detalhando a colisão.
- Se forem discos diferentes:
  - Retorna `DiskCollisionCheckResult(has_collision=False, ...)`.

