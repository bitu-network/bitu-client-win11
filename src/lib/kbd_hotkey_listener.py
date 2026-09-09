# file: src/lib/kbd_hotkey_listener.py

import keyboard


class ComboListener:
    SUPPORTED_MODIFIER_KEYS  = ["ctrl", "shift", "alt"]

    def __init__(self, callback, verbose=False):
        self.callback = callback
        self.verbose = verbose

    def start(self):
        """Start listening for key combos (blocking)"""

        def handler(event):
            if event.event_type != "down":
                return

            # Detect active modifiers
            mods = [m for m in self.SUPPORTED_MODIFIER_KEYS  if keyboard.is_pressed(m)]

            key = event.name
            if not key:
                return

            if key.lower() in self.SUPPORTED_MODIFIER_KEYS :
                return

            key = key.upper().replace(" ", "")

            if self.verbose:
                print(f"[DEBUG] pressed: {key}, modifiers held: {mods}")

            if mods:
                if self.verbose:
                    print(f"[DEBUG] combo detected: {'+'.join(mods)} + {key}")
                self.callback(mods, key)
            else:
                self.callback([], key)

        keyboard.hook(handler)
        keyboard.wait()
