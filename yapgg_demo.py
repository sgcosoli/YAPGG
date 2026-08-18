import pygame
import sys
import math
from yapgg import (
    UIManager, Theme, PanelGui, GridPanel, BtnDraw, LblGui, VlblFn, 
    TxtBox, BarGui, GaugeGui, SldGui, DropdownGui, ChkBox, RadBtn, 
    LstGui, LogBox, ArrayButton, CustomCursor
)

def create_fallback_cursor():
    """Generates a simple crosshair cursor surface so we don't need image files."""
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.line(surf, (255, 255, 255), (16, 0), (16, 32), 2)
    pygame.draw.line(surf, (255, 255, 255), (0, 16), (32, 16), 2)
    pygame.draw.circle(surf, (255, 50, 50), (16, 16), 4)
    return surf

def main():
    pygame.init()
    pygame.font.init()

    SCREEN_W, SCREEN_H = 1000, 700
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("YAPGG - Kitchen Sink Capability Demo")
    clock = pygame.time.Clock()

    custom_theme = Theme(font_name="Segoe UI", font_size=18)
    custom_theme.bg_color = (60, 65, 75)
    custom_theme.text_color = (240, 240, 240)
    custom_theme.input_bg = (40, 45, 55)
    custom_theme.border_light = (100, 105, 120)
    custom_theme.border_dark = (30, 35, 45)
    custom_theme.check_color = (200, 200, 200)
    custom_theme.tooltip_bg = (20, 25, 35)
    custom_theme.tooltip_text = (255, 255, 200)
    
    ui = UIManager(screen, theme=custom_theme)
    
    app_state = {
        "mana": 50,
        "stamina": 75,
        "show_popup": False,
        "difficulty": "Normal",
        "bg_color": (30, 32, 40)
    }

    # --- TOP NAVIGATION PANEL ---
    top_panel = PanelGui(screen, 0, 0, SCREEN_W, 60, theme=custom_theme, z_index=10)
    top_panel.theme.bg_color = (40, 45, 60)
    
    title_lbl = LblGui(screen, 20, 18, "YAPGG Capability Engine", theme=custom_theme)
    
    def toggle_popup():
        app_state["show_popup"] = not app_state["show_popup"]
        popup_panel.ypos = 100 if app_state["show_popup"] else -1000 
        log_box.add_message(f"Settings popup toggled: {app_state['show_popup']}")

    toggle_btn = BtnDraw(screen, 750, 10, 230, 40, text="Toggle Settings Popup", 
                         color=(100, 150, 200), on_click=toggle_popup, 
                         tooltip_text="Demonstrates Z-Index Overlapping", theme=custom_theme)

    top_panel.add(title_lbl)
    top_panel.add(toggle_btn)
    ui.add(top_panel)


    # --- LEFT STATS GRID PANEL ---
    left_grid = GridPanel(screen, 20, 80, 300, 400, rows=4, cols=1, padding=15, theme=custom_theme)
    
    mana_lbl = VlblFn(screen, 0, 0, lambda: f"Current Mana: {app_state['mana']}", theme=custom_theme)
    left_grid.add_grid(mana_lbl, row=0, col=0)
    
    def on_mana_slide(val): app_state["mana"] = val
    mana_sld = SldGui(screen, 0, 0, length=250, default=50, max_value=100, horizontal=True, 
                      on_change=on_mana_slide, tooltip_text="Slide to adjust Mana", theme=custom_theme)
    left_grid.add_grid(mana_sld, row=1, col=0)

    mana_bar = BarGui(screen, 0, 0, 250, 30, max_value=100, value_fn=lambda: app_state["mana"],
                      bar_color=(50, 100, 220), bg_color=(30, 30, 30), tooltip_text="Mana Pool", theme=custom_theme)
    left_grid.add_grid(mana_bar, row=2, col=0)
    
    stamina_gauge = GaugeGui(screen, 0, 0, radius=40, max_value=100, value_fn=lambda: app_state["stamina"],
                             needle_color=(220, 200, 50), half_circle=True, tooltip_text="Stamina Gauge", theme=custom_theme)
    left_grid.add_grid(stamina_gauge, row=3, col=0)
    ui.add(left_grid)


    # --- CENTER CONTENT ---
    center_panel = PanelGui(screen, 340, 80, 300, 400, theme=custom_theme)
    center_panel.add(LblGui(screen, 20, 15, "Scrollable Inventory", theme=custom_theme))
    
    inventory_items = [f"Health Potion x{i}" for i in range(1, 20)]
    def on_list_select(idx, state):
        log_box.add_message(f"Selected list index {idx}: {inventory_items[idx]}")
        
    inv_list = LstGui(screen, 20, 50, 260, 200, options=inventory_items, 
                      on_change=on_list_select, multi_select=False, theme=custom_theme)
    center_panel.add(inv_list)
    
    center_panel.add(LblGui(screen, 20, 270, "Console Input:", theme=custom_theme))
    def on_txt_submit(txt):
        log_box.add_message(f"Player command: {txt}")
    
    txt_input = TxtBox(screen, 20, 300, chars=20, text="", on_submit=on_txt_submit, 
                       tooltip_text="Press Enter to submit command", theme=custom_theme)
    center_panel.add(txt_input)
    ui.add(center_panel)

    # Note: We add the DropdownGui directly to the UI Manager (NOT the panel) 
    # and give it Z-Index=5 so it drops gracefully OVER the logbox (Z-index=0).
    def on_diff_change(idx, val):
        app_state["difficulty"] = val
        log_box.add_message(f"Difficulty changed to: {val}")
        
    diff_drop = DropdownGui(screen, 360, 430, 260, 30, ["Peaceful", "Normal", "Hardcore", "Nightmare"],
                            on_change=on_diff_change, tooltip_text="Select Difficulty", theme=custom_theme, z_index=5)
    ui.add(diff_drop) 

    # --- BOTTOM LOG BOX (Z-Index 0) ---
    log_box = LogBox(screen, 20, 500, 960, 180, live_mode=True, theme=custom_theme)
    log_box.add_message("System initialized with Auto-Polling UIManager.")
    log_box.add_message("Welcome to the Kitchen Sink Demo! Try clicking and scrolling around.")
    ui.add(log_box)


    # --- OVERLAPPING SETTINGS POPUP (Z-Index 50) ---
    popup_theme = Theme(font_name="Segoe UI", font_size=18)
    popup_theme.bg_color = (180, 160, 120) 
    popup_theme.text_color = (20, 20, 20)
    
    popup_panel = PanelGui(screen, 300, -1000, 400, 350, theme=popup_theme, z_index=50)
    popup_panel.add(LblGui(screen, 120, 15, "GAME SETTINGS", theme=popup_theme))
    
    def on_chk_change(idx, state): log_box.add_message(f"Checkbox {idx} toggled to {state}")
    chk_box = ChkBox(screen, 30, 60, ["Enable V-Sync", "Fullscreen", "Show FPS"], on_change=on_chk_change, theme=popup_theme)
    popup_panel.add(chk_box)
    
    def on_rad_change(idx): log_box.add_message(f"Graphics profile set to {idx}")
    rad_btn = RadBtn(screen, 220, 60, ["Low", "Medium", "Ultra"], on_change=on_rad_change, theme=popup_theme)
    popup_panel.add(rad_btn)
    
    color_options = [(30, 32, 40), (40, 20, 20), (20, 40, 20), (20, 20, 40)] # Background colors
    palette_surfs = [pygame.Surface((20, 20)) for _ in color_options]
    for s, c in zip(palette_surfs, color_options): s.fill(c)
    
    def on_palette_change(idx, val): 
        log_box.add_message(f"App background color repainted to Index {idx}")
        app_state["bg_color"] = color_options[idx]

    palette_grid = ArrayButton(screen, 30, 200, cols=4, cell_size=40, options=palette_surfs, 
                               on_change=on_palette_change, theme=popup_theme)
    popup_panel.add(LblGui(screen, 30, 170, "UI Color Theme:", theme=popup_theme))
    popup_panel.add(palette_grid)
    
    def on_stam_slide(val): app_state["stamina"] = val
    stam_sld = SldGui(screen, 350, 180, length=100, default=75, max_value=100, horizontal=False, 
                      on_change=on_stam_slide, tooltip_text="Adjust Stamina", theme=popup_theme)
    popup_panel.add(stam_sld)
    
    close_btn = BtnDraw(screen, 125, 290, 150, 40, text="Close Settings", color=(200, 80, 80), on_click=toggle_popup, theme=popup_theme)
    popup_panel.add(close_btn)
    
    ui.add(popup_panel)

    # --- CUSTOM CURSOR ---
    cursor_surf = create_fallback_cursor()
    ui.add(CustomCursor(screen, [cursor_surf, cursor_surf], offset=(-16, -16), ui_manager=ui))


    # --- MAIN LOOP ---
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        ui.process_events(events)
        
        # Pull the background color dynamically from App State
        screen.fill(app_state["bg_color"])
        ui.draw()
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
