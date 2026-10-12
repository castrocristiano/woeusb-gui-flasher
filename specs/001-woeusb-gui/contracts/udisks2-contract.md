# Interface Contract: UDisks2 D-Bus Integration

**Feature**: WoeUSB GUI Flasher (`001-woeusb-gui`)  
**Interface**: `org.freedesktop.UDisks2` D-Bus Service  
**Bus Type**: System Bus  

---

## 1. Overview

The WoeUSB GUI Flasher uses the system D-Bus service `org.freedesktop.UDisks2` to perform device enumeration, partition management, filesystem formatting, and mounting/unmounting without requiring root privileges inside the Flatpak sandbox.

---

## 2. Object Paths & Interfaces

| Interface | Object Path Pattern | Purpose |
| :--- | :--- | :--- |
| `org.freedesktop.DBus.ObjectManager` | `/org/freedesktop/UDisks2` | GetManagedObjects: Enumerates all drives, block devices, and filesystems. |
| `org.freedesktop.UDisks2.Block` | `/org/freedesktop/UDisks2/block_devices/{dev}` | Block device inspection and partition table creation. |
| `org.freedesktop.UDisks2.Filesystem` | `/org/freedesktop/UDisks2/block_devices/{dev}` | Mount, unmount, and label modifications. |
| `org.freedesktop.UDisks2.PartitionTable` | `/org/freedesktop/UDisks2/block_devices/{dev}` | Partition creation and table layout. |
| `org.freedesktop.UDisks2.Drive` | `/org/freedesktop/UDisks2/drives/{drive_id}` | Hardware metadata: Vendor, Model, ConnectionBus, Removable. |

---

## 3. Method Specifications

### 3.1 Device Enumeration (`GetManagedObjects`)
- **Caller**: `DiskManager.get_removable_devices()`
- **Method**: `org.freedesktop.DBus.ObjectManager.GetManagedObjects()`
- **Output**: Dictionary mapping object paths `o` to dictionaries of interface names `s` and property maps `a{sv}`.
- **Safety Filtering Invariants**:
  ```python
  def is_eligible_target(block_props, drive_props) -> bool:
      # Must be removable USB media
      if drive_props.get("ConnectionBus") != "usb" and not drive_props.get("Removable", False):
          return False
      # Must NOT be marked as a system drive
      if block_props.get("HintSystem", False) or block_props.get("HintIgnore", False):
          return False
      # Check mountpoints: cannot contain core OS paths
      mount_points = [
          mp.decode("utf-8") if isinstance(mp, bytes) else str(mp)
          for mp in block_props.get("MountPoints", [])
      ]
      for mp in mount_points:
          if mp in ("/", "/boot", "/boot/efi", "/home", "/usr", "/var"):
              return False
      return True
  ```

---

### 3.2 Unmount Partitions (`Filesystem.Unmount`)
- **Caller**: `BurnEngine._prepare_device()`
- **Interface**: `org.freedesktop.UDisks2.Filesystem`
- **Method**: `Unmount(options: a{sv}) -> ()`
- **Options**: `{"force": Variant("b", True)}`
- **Error Handling**: If partition is already unmounted (`org.freedesktop.UDisks2.Error.NotMounted`), treat as success.

---

### 3.3 Create Partition Table (`Block.Format`)
- **Caller**: `BurnEngine._partition_disk()`
- **Interface**: `org.freedesktop.UDisks2.Block`
- **Method**: `Format(type: s, options: a{sv}) -> ()`
- **Parameters**:
  - `type`: `"vfat"` (for FAT32) or `"ntfs"`
  - `options`:
    - `"label"`: `Variant("s", "WININSTALL")`
    - `"take-ownership"`: `Variant("b", True)`
    - `"erase"`: `Variant("s", "")` (quick format)

---

### 3.4 Mount Target Partition (`Filesystem.Mount`)
- **Caller**: `BurnEngine._mount_target()`
- **Interface**: `org.freedesktop.UDisks2.Filesystem`
- **Method**: `Mount(options: a{sv}) -> (mount_path: s)`
- **Options**: `{}` (default desktop mount options in `/run/media/{user}/{label}`)
- **Returns**: Absolute path to mount point directory on host, accessible by Flatpak via `--filesystem=/run/media:rw`.

---

## 4. Fallback Execution Policy

If the native D-Bus interface is unavailable or restricted by permissions:
1. Fallback to CLI commands executed via standard process calls:
   - `udisksctl unmount -b /dev/{dev}`
   - `udisksctl mount -b /dev/{dev}`
   - `lsblk --json -b -o NAME,PATH,SIZE,ROTA,RM,MODEL,VENDOR,TRAN,MOUNTPOINTS,FSTYPE`
2. Polkit will prompt the user directly in terminal or desktop dialog.

