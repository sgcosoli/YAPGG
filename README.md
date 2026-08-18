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
```

---

## Usage Instructions

YAPGG separates input processing from rendering. You must pass your events to the `UIManager` first, run your game logic, and then tell the UI to draw.

### 1. Basic Quick Start

```python
import pygame
import sys
from yapgg import UIManager, Theme, BtnDraw

pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# 1. Initialize Theme and Manager
theme = Theme(font_name="Segoe UI", font_size=20)
ui = UIManager(screen, theme=theme)

# 2. Create and add a widget
def on_click():
    print("Button Clicked!")

btn = BtnDraw(screen, 50, 50, 150, 40, text="Click Me", color=(100, 200, 100), on_click=on_click)
ui.add(btn)

# 3. Main Loop
running = True
while running:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

    # Phase 1: Process UI events (Top-to-Bottom Z-Index)
    ui.process_events(events)
    
    # Phase 2: Game Logic updates go here...
    
    # Phase 3: Render everything (Bottom-to-Top Z-Index)
    screen.fill((40, 40, 40))
    ui.draw()
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
```

### 2. Building a Complex ToolKit Interface

YAPGG excels at building complex developer tools and editors. You can use a `PanelGui` to group widgets together. Here is an example of setting up a multi-panel engine toolkit:

```python
import pygame
import yapgg as gui

pygame.init()
screen = pygame.display.set_mode((1248, 700))
pygame.display.set_caption("PyreStorm Engine Toolkit")

# Initialize the UI Manager
ui_manager = gui.UIManager(surface=screen)

# Create a Left Panel for Logging/Linting
panel_left = gui.PanelGui(screen, 20, 20, 380, 660) 
ui_manager.add(panel_left) 

# Add a label and a scrollable LogBox directly to the panel
panel_left.add(gui.LblGui(screen, 20, 20, "Map File Linter & Validator")) 
linter_log = panel_left.add(gui.LogBox(screen, 20, 110, 340, 520)) 

# Create a Middle Panel with Text Inputs
panel_middle = gui.PanelGui(screen, 420, 20, 380, 660) 
ui_manager.add(panel_middle) 

panel_middle.add(gui.LblGui(screen, 20, 20, "Event & Dialogue Generator")) 
panel_middle.add(gui.LblGui(screen, 20, 70, "Room ID:")) 
ev_room = panel_middle.add(gui.TxtBox(screen, 120, 65, chars=10, text="0")) 

# Add interactive buttons with callbacks
def save_event():
    print(f"Saving room: {''.join(ev_room.text)}")

panel_middle.add(gui.BtnDraw(screen, 180, 390, 140, 40, text="Save Event", on_click=save_event)) 
```

---

## Available Widgets

* **Layout & Containers:**
  * `PanelGui` & `GridPanel`: Container widgets with automated layout management and boundary clipping.
* **Buttons:**
  * `BtnDraw`: A highly customizable, auto-beveled drawn button.
  * `BtnPic`: An image-based button supporting distinct normal, hover, pressed, and disabled texture states.
  * `ArrayButton`: A grid of buttons supporting single or multi-select functionality.
* **Inputs & Forms:**
  * `TxtBox`: Keyboard-focusable text input with modern clipboard (Ctrl+C/Ctrl+V) support.
  * `DropdownGui`: Overlapping combo-box selection menus.
  * `ChkBox` & `RadBtn`: Standard form selection widgets.
  * `LstGui`: Scrollable inventory/list containers.
* **Sliders & Data Visualization:**
  * `SldGui` & `SldPic`: Sliders for adjustable mathematical ranges.
  * `BarGui`: Progress/Health bars.
  * `GaugeGui`: Circular dashboard gauges with needle indicators.
* **Logging:**
  * `LogBox`: A scrollable, live-updating console box that automatically wraps text.

## License

This project is open-source and licensed under the [MIT License](LICENSE.txt).
