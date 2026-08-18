# Yet Another PyGame GUI Library (YAPGG) 🎮

YAPGG is a lightweight, self-contained, typed, and layered widget library for [Pygame-CE](https://pyga.me/). Built for indie game developers, it bridges the gap between immediate and retained mode GUIs with a focus on simplicity, strict Z-ordering, and clean state management.

## Features
* **Zero Dependencies:** Relies only on standard Python libraries and `pygame-ce`.
* **True Z-Ordering & Clipping:** Overlapping popup menus, strict draw-order depth, and native surface scissoring (clipping) for scrollable containers.
* **Modern Pygame-CE Support:** Utilizes modern event injection and the updated, safe clipboard API (`pygame.scrap.put_text`).
* **Typed & Pythonic:** Fully annotated using Python `Protocol` structural subtyping.
* **Dynamic Data Binding:** Easily bind widget states to variables using lambda functions for auto-updating health bars, gauges, and labels.

## Installation

*(Note: Requires `pygame-ce`, not legacy `pygame`)*

```bash
pip install yapgg
