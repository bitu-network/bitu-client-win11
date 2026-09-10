# file: README.md
# BITU Core

A self-sovereign peer-to-peer web architecture and local Windows automation environment.

| Folder | Purpose | Interaction Level | Example |
| :--- | :--- | :--- | :--- |
| **`src/hotkeys/`** | Centralized hotkey worker scripts invoked by `hotkey_engine.py` | Background / Hooked | `v_ctrl.py`, `n_alt.py` |
| **`src/cli/`** | Direct CLI utilities and execution entry points | Direct (User-invoked) | YouTube thumbnail fetchers, file migration tools |
| **`lib/`** | Common context providers, COM interface helpers, and network protocols | Internal-only | `hotkey_context.py` |

## Cloudflare Tunnel Setup

1. Copy `cloudflare.example.yml` to `cloudflare.yml`.
2. Update the tunnel name and path to your local `.cloudflared` credentials file.