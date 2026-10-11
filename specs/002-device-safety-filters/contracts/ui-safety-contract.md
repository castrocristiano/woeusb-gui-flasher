# Contract: UI Safety & Visual Validation Components

**Component**: `woeusb_gui_flasher.ui`  
**Feature**: `002-device-safety-filters`  
**Date**: 2026-10-10  

---

## 1. DriveSelectorCard

### Modificações de Interface
- Adição de um widget `QCheckBox` com rótulo:
  `"Ocultar discos grandes (> 64 GB)"`
- Estado inicial: `setChecked(True)`.
- Tooltip explicativo:
  `"Oculta discos rígidos externos e SSDs de grande capacidade para evitar seleção acidental de mídias de backup."`

### Sinal
- `filter_toggled = Signal(bool)`: emitido sempre que o usuário altera o checkbox de filtragem.
- Método `is_hide_large_drives_active() -> bool`: retorna o estado atual do checkbox.

### Comportamento
- Quando o checkbox é alternado:
  - O método interno reaplica o filtro sobre a lista em cache de dispositivos elegíveis ou emite solicitação de atualização para o controlador.
  - Atualiza o `QComboBox` mantendo, se possível, o dispositivo previamente selecionado se ele ainda satisfizer os critérios de filtragem; caso contrário, seleciona o primeiro disponível ou nenhum.
  - Notifica `drive_selected.emit(...)` com a nova seleção.

---

## 2. MainWindow Validação e Feedback de Colisão

### Estados de Validação do Botão "Iniciar Gravação"
A função `MainWindow._update_burn_button_state()` passa a considerar:

```python
ready = (
    self._selected_iso is not None
    and self._selected_drive is not None
    and self._current_worker is None
)

if ready:
    collision = self.disk_manager.check_same_disk_collision(
        self._selected_iso.file_path,
        self._selected_drive,
    )
    if collision.has_collision:
        self.btn_burn.setEnabled(False)
        self.lbl_collision_warning.setText(collision.message)
        self.lbl_collision_warning.setVisible(True)
    else:
        self.btn_burn.setEnabled(True)
        self.lbl_collision_warning.setVisible(False)
else:
    self.btn_burn.setEnabled(False)
    self.lbl_collision_warning.setVisible(False)
```

### Visual do Aviso de Colisão
- Widget `QLabel` (`lbl_collision_warning`) posicionado em destaque acima da barra de botões de ação ou no card de destino.
- Estilizado com fundo vermelho suave / borda de advertência:
  ```css
  QLabel {
      background-color: #fef2f2;
      color: #b91c1c;
      border: 1px solid #f87171;
      border-radius: 6px;
      padding: 8px 12px;
      font-weight: 500;
      font-size: 12px;
  }
  ```

