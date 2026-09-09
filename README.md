# file: README.md
| Folder         | Purpose                                                                                                  | Interaction Level                        | Example                                                                  |
| -------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| **`/cli`**     | Entry points, user-invoked scripts                                                                       | Direct (user runs commands)              | `/cli/start/start.py`                                                    |
| **`/service`** | Externally exposed interfaces — e.g., background daemons, IPC endpoints, REST/WebSocket bridges          | Semi-direct (used by user or other apps) | `/service/ipc_server/`, `/service/api_gateway/`                          |
| **`/module`**  | Internal subsystems that implement app functionality but aren’t intended for direct user/app interaction | Internal-only                            | `/module/key_shortcuts/`, `/module/single_instance/`, `/module/archive/` |
⬛
🟫
🟥
🟧
🟨
🟩
🟦
🟪
⬜

⚫
🟤
🔴
🟠
🟡
🟢
🔵
🟣
⚪

⏸️▶️


1. Copy `cloudflare.example.yml` to `cloudflare.yml`.
2. Update the tunnel name and path to your local `.cloudflared` credentials file.