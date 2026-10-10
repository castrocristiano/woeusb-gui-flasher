# WoeUSB-GUI (Windows USB Flasher)

Aplicação desktop em Python com interface gráfica moderna (**PySide6 / Qt6**) para criação de pendrives inicializáveis do Windows no Linux (BigLinux, Arch, Manjaro, Ubuntu, Debian, Fedora), com backend baseado no utilitário **WoeUSB**.

---

## 📁 Estrutura do Projeto (GitHub Spec Kit)

O projeto adota a metodologia **Spec-Driven Development (SDD)** do [GitHub Spec Kit](https://github.com/github/spec-kit):

```
woeusb-gui/
├── .specify/
│   ├── memory/
│   │   └── constitution.md     # Princípios fundamentais e guardrails do projeto
│   └── templates/
│       ├── spec-template.md    # Template de especificação de requisitos
│       ├── plan-template.md    # Template do plano técnico de arquitetura
│       └── tasks-template.md   # Template do plano de tarefas executáveis
├── specs/
│   └── 001-woeusb-gui/
│       └── spec.md             # Especificação completa da feature (Fase de Spec)
├── SPEC.md -> specs/001-woeusb-gui/spec.md
└── README.md
```

---

## 📌 Status Atual: Fase de Especificação (`spec.md`)

Conforme a metodologia do Spec Kit, a fase de especificação detalha:
1. **Histórias de Usuário Priorizadas (P1, P2, P3)** com critérios de aceitação no formato *Given/When/Then*.
2. **Requisitos Funcionais (FR-001 a FR-018)** com proteção rígida contra formatação acidental de discos de sistema.
3. **Entidades Principais**: `StorageDevice`, `WindowsISO`, `BurnConfiguration`, `BurnExecutionState`.
4. **Critérios de Sucesso Mensuráveis (SC-001 a SC-005)**.
5. **Tratamento de Edge Cases** (pendrives desconectados, discos montados, divisão de `install.wim` > 4 GB para FAT32).

Para consultar a especificação completa, veja [`specs/001-woeusb-gui/spec.md`](specs/001-woeusb-gui/spec.md) ou [`SPEC.md`](SPEC.md).

