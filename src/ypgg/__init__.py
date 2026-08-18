"""
Yet Another PyGame GUI Library (YAPGG)
======================================================
A self-contained, typed, and layered PyGame widget library.

Licensed under the MIT License. See licenses/LICENSE.txt for details.

DESIGN OVERVIEW
---------------
Every widget follows the same architectural pattern:
    __init__(surface, x, y, ..., z_index=0) -> Configures the widget.
    process_events(events) -> Processes input (handling event.consumed). No drawing happens here.
    draw(...) -> Renders the widget for the current frame.
"""

import pygame
import math
from pygame.locals import *
from typing import List, Callable, Any, Optional, Tuple, Union, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Typing Protocols
# ---------------------------------------------------------------------------
@runtime_checkable
class Widget(Protocol):
    xpos: int
    ypos: int
    z_index: int
    def process_events(self, events: List[pygame.event.Event]) -> None: ...
    def draw(self) -> Optional[pygame.Rect]: ...

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------
class Theme:
    """Centralised visual settings."""
    def __init__(self, font_name: str = "Courier", font_size: int = 18):
        self._font_name = font_name
        self._font_size = font_size
        self._font: Optional[pygame.font.Font] = None
        
        self.text_color: Tuple[int, int, int]   = (0, 0, 0)
        self.bg_color: Tuple[int, int, int]     = (175, 175, 175)
        self.border_dark: Tuple[int, int, int]  = (80, 80, 80)
        self.border_light: Tuple[int, int, int] = (220, 220, 220)
        self.hover_shift: int                   = 15       
        self.check_color: Tuple[int, int, int]  = (0, 0, 0)
        self.select_color: Tuple[int, int, int] = (0, 200, 0)
        self.input_bg: Tuple[int, int, int]     = (255, 255, 255)
        self.focus_color: Tuple[int, int, int]  = (0, 150, 255)
        self.tooltip_bg: Tuple[int, int, int]   = (255, 255, 220) 
        self.tooltip_text: Tuple[int, int, int] = (0, 0, 0)

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.SysFont(self._font_name, self._font_size)
        return self._font

default_theme = Theme()

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------
def _clamp(value: float, lo: float = 0, hi: float = 255) -> float:
    return max(lo, min(hi, value))

def _shift_color(color: Tuple[int, int, int], offset: int) -> Tuple[int, int, int]:
    return (int(_clamp(color[0] + offset)),
            int(_clamp(color[1] + offset)),
            int(_clamp(color[2] + offset)))

def _render_bevel(surface: pygame.Surface, rect: pygame.Rect, base_color: Tuple[int, int, int], inward: bool = False):
    x, y, w, h = rect
    light    = _shift_color(base_color,  25)
    dark     = _shift_color(base_color, -50)
    tl_color = dark  if inward else light
    br_color = light if inward else dark

    pygame.draw.lines(surface, tl_color, False, [(x, y), (x+w-1, y)], 2)
    pygame.draw.lines(surface, tl_color, False, [(x+w-2, y), (x+w-2, y+h-1)], 2)
    pygame.draw.lines(surface, br_color, False, [(x, y+h-2), (x+w-1, y+h-2)], 2)
    pygame.draw.lines(surface, br_color, False, [(x, y), (x, y+h-1)], 2)

# ---------------------------------------------------------------------------
# UIManager
# ---------------------------------------------------------------------------
class UIManager:
    def __init__(self, surface: pygame.Surface, theme: Optional[Theme] = None):
        self.widgets: List[Widget] = []
        self.surface = surface
        self.theme = theme or default_theme

    def add(self, widget: Widget) -> Widget:
        self.widgets.append(widget)
        if type(widget).__name__ == "CustomCursor":
            widget.ui_manager = self
        self.widgets.sort(key=lambda w: getattr(w, 'z_index', 0))
        return widget

    def remove(self, widget: Widget):
        if widget in self.widgets:
            self.widgets.remove(widget)

    def _get_focusables(self, widgets_list: List[Widget]) -> List[Widget]:
        focusables = []
        for w in widgets_list:
            if hasattr(w, 'widgets'):
                focusables.extend(self._get_focusables(getattr(w, 'widgets')))
            elif getattr(w, 'can_focus', False) and not getattr(w, 'disabled', False):
                focusables.append(w)
        return focusables

    def process_events(self, events: List[pygame.event.Event]):
        mouse_pos = pygame.mouse.get_pos()
        blocking_rect = None
        active_dropdown = None
        
        for w in reversed(self.widgets): 
            if type(w).__name__ == "DropdownGui" and getattr(w, 'is_open', False):
                blocking_rect = pygame.Rect(w.xpos, w.ypos, w.width, w.height * (len(getattr(w, 'options', [])) + 1))
                active_dropdown = w
                break

        focusables = self._get_focusables(self.widgets)
        tab_event = next((e for e in events if e.type == KEYDOWN and e.key == K_TAB and not getattr(e, 'consumed', False)), None)
        if tab_event and focusables:
            setattr(tab_event, 'consumed', True)
            curr_idx = next((i for i, w in enumerate(focusables) if getattr(w, 'is_focused', False)), -1)
            for w in focusables: w.is_focused = False
            
            if pygame.key.get_mods() & KMOD_SHIFT:
                curr_idx = (curr_idx - 1) % len(focusables)
            else:
                curr_idx = (curr_idx + 1) % len(focusables)
            focusables[curr_idx].is_focused = True

        self.active_tooltip = None
        cursor_widget = None

        for widget in reversed(self.widgets):
            if type(widget).__name__ == "CustomCursor":
                cursor_widget = widget
                continue

            is_blocked = False
            if blocking_rect and widget is not active_dropdown:
                if blocking_rect.collidepoint(mouse_pos):
                    is_blocked = True

            if hasattr(widget, 'process_events'):
                widget.process_events([] if is_blocked else events)

            if not is_blocked and hasattr(widget, 'get_tooltip_at') and self.active_tooltip is None:
                text = widget.get_tooltip_at(mouse_pos)
                if text: self.active_tooltip = text

        focus_target = next((getattr(e, 'focus_target', None) for e in events if hasattr(e, 'focus_target')), None)
        if focus_target:
            for w in focusables: w.is_focused = (w is focus_target)
            
        self.cursor_widget = cursor_widget

    def draw(self):
        for widget in self.widgets:
            if type(widget).__name__ != "CustomCursor" and hasattr(widget, 'draw'):
                widget.draw()

        if getattr(self, 'active_tooltip', None) and self.surface:
            txt_surf = self.theme.font.render(self.active_tooltip, True, self.theme.tooltip_text)
            padding = 4
            mouse_pos = pygame.mouse.get_pos()
            bg_rect = pygame.Rect(mouse_pos[0] + 12, mouse_pos[1] + 12, txt_surf.get_width() + (padding * 2), txt_surf.get_height() + (padding * 2))
            
            pygame.draw.rect(self.surface, self.theme.tooltip_bg, bg_rect)
            pygame.draw.rect(self.surface, self.theme.check_color, bg_rect, 1)
            self.surface.blit(txt_surf, (bg_rect.x + padding, bg_rect.y + padding))

        if getattr(self, 'cursor_widget', None):
            if hasattr(self.cursor_widget, 'draw'): self.cursor_widget.draw()


# ---------------------------------------------------------------------------
# Panels (Container Widgets)
# ---------------------------------------------------------------------------
class PanelGui:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int, theme: Optional[Theme]=None, z_index: int=0):
        self.surface = surface
        self.xpos = xpos
        self.ypos = ypos
        self.width = width
        self.height = height
        self.theme = theme or default_theme
        self.z_index = z_index
        self.panel_rect = pygame.Rect(xpos, ypos, width, height)
        self.widgets: List[Widget] = []
        self.local_positions = {}

    def add(self, widget: Widget) -> Widget:
        self.local_positions[id(widget)] = (getattr(widget, 'xpos', 0), getattr(widget, 'ypos', 0))
        self.widgets.append(widget)
        return widget
        
    def _update_child_coords(self):
        self.panel_rect.topleft = (self.xpos, self.ypos)
        self.panel_rect.size = (self.width, self.height)
        for w in self.widgets:
            lx, ly = self.local_positions.get(id(w), (0,0))
            w.xpos = self.xpos + lx
            w.ypos = self.ypos + ly
            if hasattr(w, '_update_child_coords'): w._update_child_coords()

    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        self._update_child_coords()
        if not self.panel_rect.collidepoint(pos): return None
        for w in self.widgets:
            if hasattr(w, 'get_tooltip_at'):
                tip = w.get_tooltip_at(pos)
                if tip: return tip
        return None

    def process_events(self, events: List[pygame.event.Event]):
        self._update_child_coords()
        for w in reversed(self.widgets):
            if hasattr(w, 'process_events'): w.process_events(events)

    def draw(self):
        self._update_child_coords()
        pygame.draw.rect(self.surface, self.theme.bg_color, self.panel_rect)
        _render_bevel(self.surface, self.panel_rect, self.theme.bg_color)
        
        for w in self.widgets:
            if hasattr(w, 'draw'): w.draw()
            
        return self.panel_rect

class GridPanel(PanelGui):
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int, rows: int, cols: int, padding: int=5, theme: Optional[Theme]=None, z_index: int=0):
        super().__init__(surface, xpos, ypos, width, height, theme, z_index)
        self.rows = rows
        self.cols = cols
        self.padding = padding
        self.cell_w = (width - (padding * (cols + 1))) // cols
        self.cell_h = (height - (padding * (rows + 1))) // rows

    def add_grid(self, widget: Widget, row: int, col: int) -> Widget:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            lx = self.padding + col * (self.cell_w + self.padding)
            ly = self.padding + row * (self.cell_h + self.padding)
            self.local_positions[id(widget)] = (lx, ly)
            self.widgets.append(widget)
        return widget


# ---------------------------------------------------------------------------
# Buttons
# ---------------------------------------------------------------------------
class BtnDraw:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int,
                 color: Tuple[int,int,int]=(175, 175, 175), text: str="Button",
                 on_click: Optional[Callable]=None, tooltip_text: str="", disabled: bool=False, 
                 theme: Optional[Theme]=None, z_index: int = 0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.width        = width
        self.height       = height
        self.color        = color
        self.text         = text
        self.on_click     = on_click
        self.tooltip_text = tooltip_text
        self.disabled     = disabled
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self.btnRect      = pygame.Rect(xpos, ypos, width, height)
        self._pressed     = False
        self._is_hovered  = False
        self.can_focus    = True
        self.is_focused   = False

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text

    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.btnRect.collidepoint(pos) and self.tooltip_text: return self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        self.btnRect.topleft = (self.xpos, self.ypos)
        self._is_hovered = self.btnRect.collidepoint(pygame.mouse.get_pos())
        if not self.disabled:
            for event in events:
                if getattr(event, 'consumed', False): continue
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    if self._is_hovered:
                        self._pressed = True
                        self.is_focused = True
                        setattr(event, 'focus_target', self)
                        setattr(event, 'consumed', True)
                if event.type == MOUSEBUTTONUP and event.button == 1:
                    if self._pressed and self._is_hovered:
                        if self.on_click: self.on_click()
                        setattr(event, 'consumed', True)
                    self._pressed = False 
                if self.is_focused and event.type == KEYDOWN and (event.key == K_RETURN or event.key == K_SPACE):
                    if self.on_click: self.on_click()
                    setattr(event, 'consumed', True)

    def _draw_state(self, color, inward=False, flat=False):
        pygame.draw.rect(self.surface, color, (self.xpos+2, self.ypos+2, self.width-4, self.height-4))
        if flat:
            pygame.draw.rect(self.surface, self.theme.border_dark, self.btnRect, 2)
        else:
            _render_bevel(self.surface, self.btnRect, color, inward=inward)
            
        txt_surf = self.theme.font.render(self.text, True, (120, 120, 120) if self.disabled else self.theme.text_color)
        tx = self.xpos + (self.width - txt_surf.get_width()) // 2
        ty = self.ypos + (self.height - txt_surf.get_height()) // 2
        self.surface.blit(txt_surf, (tx, ty))

    def draw(self):
        hover = getattr(self, '_is_hovered', False)
        pressed = getattr(self, '_pressed', False) and hover
        if self.disabled:
            self._draw_state(_shift_color(self.color, -30), flat=True)
        elif pressed:
            self._draw_state(_shift_color(self.color, -15), inward=True)
        elif hover:
            self._draw_state(_shift_color(self.color, self.theme.hover_shift))
        else:
            self._draw_state(self.color)
        
        if self.is_focused:
            pygame.draw.rect(self.surface, self.theme.focus_color, self.btnRect, 2)
        return self.btnRect

class BtnPic:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int,
                 img_normal: pygame.Surface, img_hover: pygame.Surface, img_pressed: pygame.Surface, 
                 img_disabled: Optional[pygame.Surface]=None, on_click: Optional[Callable]=None, 
                 tooltip_text: str="", disabled: bool=False, theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.img_normal   = img_normal
        self.img_hover    = img_hover
        self.img_pressed  = img_pressed
        if img_disabled is None:
            self.img_disabled = img_normal.copy()
            self.img_disabled.fill((100, 100, 100, 180), special_flags=pygame.BLEND_RGBA_MULT)
        else: 
            self.img_disabled = img_disabled
        self.on_click     = on_click
        self.tooltip_text = tooltip_text
        self.disabled     = disabled
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self._pressed     = False
        self._is_hovered  = False
        self.can_focus    = True
        self.is_focused   = False
        self.btnRect      = pygame.Rect(xpos, ypos, img_normal.get_width(), img_normal.get_height())

    def set_tooltip(self, new_text: str): 
        self.tooltip_text = new_text

    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.btnRect.collidepoint(pos) and self.tooltip_text: 
            return self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        self.btnRect.topleft = (self.xpos, self.ypos)
        self._is_hovered = self.btnRect.collidepoint(pygame.mouse.get_pos())
        if not self.disabled:
            for event in events:
                if getattr(event, 'consumed', False): continue
                if event.type == MOUSEBUTTONDOWN and event.button == 1:
                    if self._is_hovered:
                        self._pressed = True
                        self.is_focused = True
                        setattr(event, 'focus_target', self)
                        setattr(event, 'consumed', True)
                if event.type == MOUSEBUTTONUP and event.button == 1:
                    if self._pressed and self._is_hovered:
                        if self.on_click: self.on_click()
                        setattr(event, 'consumed', True)
                    self._pressed = False
                if self.is_focused and event.type == KEYDOWN and (event.key == K_RETURN or event.key == K_SPACE):
                    if self.on_click: self.on_click()
                    setattr(event, 'consumed', True)

    def draw(self):
        hover = getattr(self, '_is_hovered', False)
        pressed = getattr(self, '_pressed', False) and hover
        if self.disabled: 
            img = self.img_disabled
        elif pressed: 
            img = self.img_pressed
        elif hover: 
            img = self.img_hover
        else: 
            img = self.img_normal
            
        self.surface.blit(img, (self.xpos, self.ypos))
        
        if self.is_focused:
            pygame.draw.rect(self.surface, self.theme.focus_color, self.btnRect, 2)
        return self.btnRect

# ---------------------------------------------------------------------------
# Base & Derived Labels
# ---------------------------------------------------------------------------
class BaseLabel:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, theme: Optional[Theme]=None, z_index: int=0):
        self.surface = surface
        self.xpos    = xpos
        self.ypos    = ypos
        self.theme   = theme or default_theme
        self.z_index = z_index
        self.lblRect = pygame.Rect(xpos, ypos, 0, 0)
        
    def process_events(self, events: List[pygame.event.Event]): pass

    def _render_text(self, text: str):
        txt_surf = self.theme.font.render(text, True, self.theme.text_color)
        self.lblRect.topleft = (self.xpos, self.ypos)
        self.lblRect.size = txt_surf.get_size()
        self.surface.blit(txt_surf, (self.xpos, self.ypos))
        return self.lblRect

class LblGui(BaseLabel):
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, text: str, theme: Optional[Theme]=None, z_index: int=0):
        super().__init__(surface, xpos, ypos, theme, z_index)
        self.text = text

    def draw(self): return self._render_text(self.text)

class LblExt(BaseLabel):
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, chars: int, text: str, align: int=1, theme: Optional[Theme]=None, z_index: int=0):
        super().__init__(surface, xpos, ypos, theme, z_index)
        self.chars = chars
        self.text = text
        self.align = align

    def draw(self):
        avg_char_w = self.theme.font.size("A")[0]
        char_h = self.theme.font.get_height()
        lines = [self.text[i:i+self.chars] for i in range(0, len(self.text), self.chars)]
        rows = max(1, len(lines))
        self.lblRect = pygame.Rect(self.xpos, self.ypos, self.chars * avg_char_w, rows * char_h)
        for row, line in enumerate(lines):
            n = len(line)
            if self.align == 1: x = self.xpos
            elif self.align == 2: x = int(self.xpos + 0.5 * self.chars * avg_char_w - n * 0.5 * avg_char_w)
            else: x = self.xpos + self.chars * avg_char_w - n * avg_char_w
            y = self.ypos + row * (char_h - 3)   
            self.surface.blit(self.theme.font.render(line, True, self.theme.text_color), (x, y))
        return self.lblRect

class VlblGui(BaseLabel):
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, obj: Any, attr_name: str, prefix: str="", theme: Optional[Theme]=None, z_index: int=0):
        super().__init__(surface, xpos, ypos, theme, z_index)
        self.obj = obj
        self.attr_name = attr_name
        self.prefix = prefix

    def draw(self): return self._render_text(self.prefix + str(getattr(self.obj, self.attr_name)))

class VlblFn(BaseLabel):
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, fn: Callable, theme: Optional[Theme]=None, z_index: int=0):
        super().__init__(surface, xpos, ypos, theme, z_index)
        self.fn = fn

    def draw(self): return self._render_text(str(self.fn()))

# ---------------------------------------------------------------------------
# Text Input Box (With Pygame-CE Clipboard Support)
# ---------------------------------------------------------------------------
class TxtBox:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, chars: int, text: str="",
                 on_submit: Optional[Callable]=None, tooltip_text: Union[str, Callable]="", 
                 theme: Optional[Theme]=None, z_index: int=0, max_chars: int=250):
        self.surface   = surface
        self.xpos      = xpos
        self.ypos      = ypos
        self.theme     = theme or default_theme
        self.tooltip_text = tooltip_text
        
        avg_char_w = self.theme.font.size("A")[0]
        self.box_width = (chars * avg_char_w) + 10
        self.box_height = self.theme.font.get_height() + 8
        
        self.max_chars = max_chars
        self.text      = list(text)   
        self.on_submit = on_submit
        self.z_index   = z_index
        self.can_focus = True
        self.is_focused= False
        self._cursor_visible = True
        self._cursor_timer   = 0       
        self.txtRect   = pygame.Rect(xpos, ypos, self.box_width, self.box_height)

    def set_tooltip(self, new_text: str): 
        self.tooltip_text = new_text

    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.txtRect.collidepoint(pos) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        now = pygame.time.get_ticks()
        self.txtRect.topleft = (self.xpos, self.ypos)
        
        if self.is_focused and now - self._cursor_timer > 500:
            self._cursor_visible = not self._cursor_visible
            self._cursor_timer   = now

        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
                
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self.txtRect.collidepoint(pos):
                    self.is_focused = True
                    self._cursor_timer = now
                    self._cursor_visible = True
                    setattr(event, 'focus_target', self)
                    setattr(event, 'consumed', True)
                else:
                    self.is_focused = False
                    
            if self.is_focused and event.type == KEYDOWN:
                mods = pygame.key.get_mods()
                if (mods & KMOD_CTRL) or (mods & KMOD_META):
                    if event.key == K_c:
                        try:
                            pygame.scrap.put_text("".join(self.text))
                        except Exception: pass
                    elif event.key == K_v:
                        try:
                            if pygame.scrap.has_text():
                                clip_text = pygame.scrap.get_text().replace('\r', '').replace('\n', '').strip('\x00')
                                for c in clip_text:
                                    if len(self.text) < self.max_chars and c.isprintable():
                                        self.text.append(c)
                        except Exception: pass
                    continue

                if event.key == K_RETURN or event.key == K_KP_ENTER:
                    self.is_focused = False
                    if self.on_submit: self.on_submit("".join(self.text))
                elif event.key == K_BACKSPACE:
                    if self.text: self.text.pop()
                elif event.unicode and len(self.text) < self.max_chars and event.key != K_TAB:
                    self.text.append(event.unicode)

    def draw(self):
        pygame.draw.rect(self.surface, self.theme.input_bg, (self.xpos+1, self.ypos+1, self.box_width-2, self.box_height-2))
        pygame.draw.rect(self.surface, self.theme.check_color, self.txtRect, 1)
        
        max_render_width = self.box_width - 10
        display = ""
        cursor_char = "|" if (self.is_focused and self._cursor_visible) else ""
        
        for char in reversed(self.text):
            test_display = char + display
            if self.theme.font.size(test_display + cursor_char)[0] > max_render_width:
                break
            display = test_display
        
        txt_surf = self.theme.font.render(display + cursor_char, True, self.theme.text_color)
        self.surface.blit(txt_surf, (self.xpos+4, self.ypos+4))
        
        if self.is_focused:
            pygame.draw.rect(self.surface, self.theme.focus_color, self.txtRect, 2)
            
        return self.txtRect

# ---------------------------------------------------------------------------
# Complex Interactive Widgets
# ---------------------------------------------------------------------------
class DropdownGui:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int, 
                 options: List[str], on_change: Optional[Callable]=None, tooltip_text: str="", 
                 theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.width        = width
        self.height       = height
        self.options      = options
        self.on_change    = on_change
        self.tooltip_text = tooltip_text
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self.selected_idx = 0
        self.is_open      = False
        self.main_rect    = pygame.Rect(xpos, ypos, width, height)

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text

    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        self.main_rect.topleft = (self.xpos, self.ypos)
        if self.main_rect.collidepoint(pos) and self.tooltip_text: return self.tooltip_text
        if self.is_open and self.tooltip_text:
            for i in range(len(self.options)):
                opt_rect = pygame.Rect(self.xpos, self.ypos + self.height + (i * self.height), self.width, self.height)
                if opt_rect.collidepoint(pos): return self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        pos = pygame.mouse.get_pos()
        self.main_rect.topleft = (self.xpos, self.ypos)
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self.main_rect.collidepoint(pos):
                    self.is_open = not self.is_open
                    setattr(event, 'consumed', True)
                elif self.is_open:
                    clicked_inside = False
                    for i, opt in enumerate(self.options):
                        opt_rect = pygame.Rect(self.xpos, self.ypos + self.height + (i * self.height), self.width, self.height)
                        if opt_rect.collidepoint(pos):
                            self.selected_idx = i
                            self.is_open = False
                            clicked_inside = True
                            setattr(event, 'consumed', True)
                            if self.on_change: self.on_change(i, opt)
                            break
                    if not clicked_inside:
                        self.is_open = False 

    def draw(self):
        self.main_rect.topleft = (self.xpos, self.ypos)
        pygame.draw.rect(self.surface, self.theme.input_bg, self.main_rect)
        pygame.draw.rect(self.surface, self.theme.check_color, self.main_rect, 1)
        
        current_text = self.options[self.selected_idx] if self.options else ""
        txt_surf = self.theme.font.render(current_text, True, self.theme.text_color)
        self.surface.blit(txt_surf, (self.xpos + 5, self.ypos + 4))

        if self.is_open:
            for i, opt in enumerate(self.options):
                opt_rect = pygame.Rect(self.xpos, self.ypos + self.height + (i * self.height), self.width, self.height)
                bg_col = self.theme.select_color if i == self.selected_idx else self.theme.input_bg
                pygame.draw.rect(self.surface, bg_col, opt_rect)
                pygame.draw.rect(self.surface, self.theme.check_color, opt_rect, 1)
                opt_surf = self.theme.font.render(opt, True, self.theme.text_color)
                self.surface.blit(opt_surf, (opt_rect.x + 5, opt_rect.y + 4))

class ArrayButton:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, cols: int, cell_size: int, options: List[Any], on_change: Optional[Callable]=None, tooltip_texts: Optional[List[str]]=None, theme: Optional[Theme]=None, z_index: int=0, multi_select: bool=False):
        self.surface = surface
        self.xpos = xpos
        self.ypos = ypos
        self.cols = cols
        self.cell_size = cell_size
        self.options = options  
        self.on_change = on_change
        self.tooltip_texts = tooltip_texts or [""] * len(options)
        self.theme = theme or default_theme
        self.z_index = z_index
        self.multi_select = multi_select
        self.statelist = [0] * len(options) 
        self.selected = -1
        self._handled = False

    def _get_cell_rect(self, i: int) -> pygame.Rect:
        r = i // self.cols
        c = i % self.cols
        cx = self.xpos + (c * self.cell_size)
        cy = self.ypos + (r * self.cell_size)
        return pygame.Rect(cx, cy, self.cell_size, self.cell_size)

    def set_tooltip(self, index: int, new_text: str):
        if 0 <= index < len(self.tooltip_texts): self.tooltip_texts[index] = new_text

    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        for i, t_text in enumerate(self.tooltip_texts):
            if self._get_cell_rect(i).collidepoint(pos) and t_text: return t_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if not self._handled:
                    for i in range(len(self.options)):
                        if self._get_cell_rect(i).collidepoint(pos):
                            setattr(event, 'consumed', True)
                            if self.multi_select:
                                self.statelist[i] ^= 1
                                if self.on_change: self.on_change(i, self.statelist[i])
                            else:
                                self.selected = i
                                if self.on_change: self.on_change(i, self.options[i])
                    self._handled = True
            if event.type == MOUSEBUTTONUP and event.button == 1:
                self._handled = False

    def draw(self):
        for i, opt in enumerate(self.options):
            cell_rect = self._get_cell_rect(i)
            is_selected = self.statelist[i] if self.multi_select else (self.selected == i)
            bg = self.theme.select_color if is_selected else self.theme.input_bg
            
            pygame.draw.rect(self.surface, bg, cell_rect)
            pygame.draw.rect(self.surface, self.theme.check_color, cell_rect, 1)
            
            if opt is not None:
                if isinstance(opt, pygame.Surface):
                    img_rect = opt.get_rect(center=cell_rect.center)
                    self.surface.blit(opt, img_rect)
                else:
                    txt_surf = self.theme.font.render(str(opt), True, self.theme.text_color)
                    self.surface.blit(txt_surf, (cell_rect.x + 5, cell_rect.y + 5))

class ChkBox:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, options: List[str], on_change: Optional[Callable]=None, theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.options      = options
        self.on_change    = on_change
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self.statelist    = [0] * len(options)   
        self._handled     = False   
        self.can_focus    = True
        self.is_focused   = False
        self.focused_item = 0

    def _get_hit_rect(self, i: int) -> pygame.Rect:
        ry = self.ypos + i * 30
        width = self.theme.font.size(self.options[i])[0]
        return pygame.Rect(self.xpos, ry, width + 30, 30)

    def process_events(self, events: List[pygame.event.Event]):
        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if not self._handled:
                    for i in range(len(self.options)):
                        if self._get_hit_rect(i).collidepoint(pos):
                            self.is_focused = True
                            setattr(event, 'focus_target', self)
                            self.focused_item = i
                            self.statelist[i] ^= 1   
                            setattr(event, 'consumed', True)
                            if self.on_change: self.on_change(i, self.statelist[i])
                    self._handled = True   
            if event.type == MOUSEBUTTONUP and event.button == 1:
                self._handled = False      

            if self.is_focused and event.type == KEYDOWN:
                if event.key == K_UP:
                    self.focused_item = max(0, self.focused_item - 1)
                    setattr(event, 'consumed', True)
                elif event.key == K_DOWN:
                    self.focused_item = min(len(self.options) - 1, self.focused_item + 1)
                    setattr(event, 'consumed', True)
                elif event.key == K_SPACE or event.key == K_RETURN:
                    self.statelist[self.focused_item] ^= 1
                    setattr(event, 'consumed', True)
                    if self.on_change: self.on_change(self.focused_item, self.statelist[self.focused_item])

    def draw(self):
        for i, label in enumerate(self.options):
            ry = self.ypos + i * 30
            box_rect = pygame.Rect(self.xpos, ry + 3, 15, 15)
            pygame.draw.rect(self.surface, self.theme.check_color, box_rect, 1)  
            if self.statelist[i]:
                pygame.draw.rect(self.surface, self.theme.check_color, box_rect, 0)  
            self.surface.blit(self.theme.font.render(label, True, self.theme.text_color), (self.xpos + 25, ry))

        if self.is_focused and self.options:
            ry = self.ypos + self.focused_item * 30
            focus_rect = pygame.Rect(self.xpos - 2, ry - 2, self.theme.font.size(self.options[self.focused_item])[0] + 34, 30)
            pygame.draw.rect(self.surface, self.theme.focus_color, focus_rect, 1)

class RadBtn:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, options: List[str], on_change: Optional[Callable]=None, theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.options      = options
        self.on_change    = on_change
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self.selected     = -1   
        self._handled     = False
        self.can_focus    = True
        self.is_focused   = False
        self.focused_item = 0

    def _get_hit_rect(self, i: int) -> pygame.Rect:
        ry = self.ypos + i * 30
        width = self.theme.font.size(self.options[i])[0]
        return pygame.Rect(self.xpos - 3, ry, width + 30, 30)

    def process_events(self, events: List[pygame.event.Event]):
        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if not self._handled:
                    for i in range(len(self.options)):
                        if self._get_hit_rect(i).collidepoint(pos):
                            self.is_focused = True
                            setattr(event, 'focus_target', self)
                            self.focused_item = i
                            setattr(event, 'consumed', True)
                            if self.selected != i:   
                                self.selected = i
                                if self.on_change: self.on_change(i)
                    self._handled = True
            if event.type == MOUSEBUTTONUP and event.button == 1:
                self._handled = False

            if self.is_focused and event.type == KEYDOWN:
                if event.key == K_UP:
                    self.focused_item = max(0, self.focused_item - 1)
                    setattr(event, 'consumed', True)
                elif event.key == K_DOWN:
                    self.focused_item = min(len(self.options) - 1, self.focused_item + 1)
                    setattr(event, 'consumed', True)
                elif event.key == K_SPACE or event.key == K_RETURN:
                    if self.selected != self.focused_item:
                        self.selected = self.focused_item
                        setattr(event, 'consumed', True)
                        if self.on_change: self.on_change(self.focused_item)

    def draw(self):
        for i, label in enumerate(self.options):
            ry = self.ypos + i * 30
            cx, cy = self.xpos + 7, ry + 10   
            pygame.draw.circle(self.surface, self.theme.check_color, (cx, cy), 10, 1)
            if self.selected == i:
                pygame.draw.circle(self.surface, self.theme.check_color, (cx, cy), 6)
            self.surface.blit(self.theme.font.render(label, True, self.theme.text_color), (self.xpos + 25, ry))

        if self.is_focused and self.options:
            ry = self.ypos + self.focused_item * 30
            focus_rect = pygame.Rect(self.xpos - 2, ry - 2, self.theme.font.size(self.options[self.focused_item])[0] + 34, 30)
            pygame.draw.rect(self.surface, self.theme.focus_color, focus_rect, 1)

class LstGui:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int, options: List[str], on_change: Optional[Callable]=None, theme: Optional[Theme]=None, z_index: int=0, multi_select: bool=True):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.width        = width
        self.height       = height
        self.options      = options
        self.on_change    = on_change
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self.multi_select = multi_select
        self.statelist    = [0] * len(options)
        self._handled     = False
        self.scroll_offset= 0
        self.can_focus    = True
        self.is_focused   = False
        self.focused_item = 0
        self.list_rect    = pygame.Rect(xpos, ypos, width, height)

    def _get_visible_capacity(self) -> int:
        return self.height // 30

    def process_events(self, events: List[pygame.event.Event]):
        self.list_rect.topleft = (self.xpos, self.ypos)
        pos = pygame.mouse.get_pos()
        visible_rows = self._get_visible_capacity()
        max_scroll = max(0, len(self.options) - visible_rows)

        for event in events:
            if getattr(event, 'consumed', False): continue
            
            if event.type == MOUSEWHEEL and self.list_rect.collidepoint(pos):
                if event.y > 0 and self.scroll_offset > 0:
                    self.scroll_offset -= 1
                elif event.y < 0 and self.scroll_offset < max_scroll:
                    self.scroll_offset += 1
                setattr(event, 'consumed', True)

            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if not self._handled:
                    for i in range(self.scroll_offset, min(len(self.options), self.scroll_offset + visible_rows)):
                        row = pygame.Rect(self.xpos, self.ypos + (i - self.scroll_offset) * 30, self.width, 30)
                        if row.collidepoint(pos):
                            self.is_focused = True
                            setattr(event, 'focus_target', self)
                            self.focused_item = i
                            if self.multi_select:
                                self.statelist[i] ^= 1
                            else:
                                new_state = self.statelist[i] ^ 1
                                self.statelist = [0] * len(self.options)
                                self.statelist[i] = new_state
                                
                            setattr(event, 'consumed', True)
                            if self.on_change: self.on_change(i, self.statelist[i])
                    self._handled = True
            if event.type == MOUSEBUTTONUP and event.button == 1:
                self._handled = False

            if self.is_focused and event.type == KEYDOWN:
                if event.key == K_UP:
                    self.focused_item = max(0, self.focused_item - 1)
                    if self.focused_item < self.scroll_offset:
                        self.scroll_offset = self.focused_item
                    setattr(event, 'consumed', True)
                elif event.key == K_DOWN:
                    self.focused_item = min(len(self.options) - 1, self.focused_item + 1)
                    if self.focused_item >= self.scroll_offset + visible_rows:
                        self.scroll_offset += 1
                    setattr(event, 'consumed', True)
                elif event.key == K_SPACE or event.key == K_RETURN:
                    if self.multi_select:
                        self.statelist[self.focused_item] ^= 1
                    else:
                        new_state = self.statelist[self.focused_item] ^ 1
                        self.statelist = [0] * len(self.options)
                        self.statelist[self.focused_item] = new_state
                    setattr(event, 'consumed', True)
                    if self.on_change: self.on_change(self.focused_item, self.statelist[self.focused_item])

    def draw(self):
        pygame.draw.rect(self.surface, self.theme.input_bg, self.list_rect)
        pygame.draw.rect(self.surface, self.theme.check_color, self.list_rect, 1)

        old_clip = self.surface.get_clip()
        new_clip = old_clip.clip(self.list_rect) if old_clip else self.list_rect
        self.surface.set_clip(new_clip)

        visible_rows = self._get_visible_capacity()
        for i in range(self.scroll_offset, min(len(self.options), self.scroll_offset + visible_rows)):
            ry = self.ypos + (i - self.scroll_offset) * 30
            row = pygame.Rect(self.xpos, ry, self.width, 30)
            
            bg = self.theme.select_color if self.statelist[i] else self.theme.input_bg
            pygame.draw.rect(self.surface, bg, row)
            pygame.draw.rect(self.surface, self.theme.check_color, row, 1)  
            self.surface.blit(self.theme.font.render(self.options[i], True, self.theme.text_color), (self.xpos + 4, ry + 5))

            if self.is_focused and i == self.focused_item:
                focus_rect = pygame.Rect(self.xpos + 2, ry + 2, self.width - 4, 30 - 4)
                pygame.draw.rect(self.surface, self.theme.focus_color, focus_rect, 2)

        self.surface.set_clip(old_clip)

# ---------------------------------------------------------------------------
# Visual Progress & Logging Widgets
# ---------------------------------------------------------------------------
class LogBox:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int, 
                 bg_image: Optional[pygame.Surface]=None, up_button: Optional[Any]=None, 
                 down_button: Optional[Any]=None, theme: Optional[Theme]=None, z_index: int=0,
                 reverse_scroll: bool=False, live_mode: bool=True):
        self.surface = surface
        self.xpos = xpos
        self.ypos = ypos
        self.width = width
        self.height = height
        self.bg_image = bg_image
        self.up_button = up_button
        self.down_button = down_button
        self.theme = theme or default_theme
        self.z_index = z_index
        self.reverse_scroll = reverse_scroll
        self.live_mode = live_mode
        self.unread_count = 0
        
        self.box_rect = pygame.Rect(xpos, ypos, width, height)
        self.lines: List[str] = []          
        self.scroll_offset = 0   
        
    def _wrap_text(self, text: str) -> List[str]:
        target_font = self.theme.font
        max_width = self.width - 20  
        wrapped_lines = []
        for paragraph in str(text).split('\n'):
            words = paragraph.split(' ')
            current_line = ""
            for word in words:
                if target_font.size(word)[0] > max_width:
                    if current_line:
                        wrapped_lines.append(current_line)
                        current_line = ""
                    chunk = ""
                    for char in word:
                        if target_font.size(chunk + char)[0] <= max_width: chunk += char
                        else:
                            wrapped_lines.append(chunk)
                            chunk = char
                    current_line = chunk
                else:
                    test_line = current_line + " " + word if current_line else word
                    if target_font.size(test_line)[0] <= max_width: current_line = test_line
                    else:
                        wrapped_lines.append(current_line)
                        current_line = word
            if current_line: wrapped_lines.append(current_line)
        return wrapped_lines

    def add_message(self, message: str):
        wrapped = self._wrap_text(message)
        num_lines = len(wrapped)
        self.lines.extend(wrapped)
        
        if self.live_mode and self.scroll_offset == 0:
            self.scroll_offset = 0
            self.unread_count = 0
        else:
            self.scroll_offset += num_lines
            self.unread_count += num_lines

    def scroll_up(self):
        max_scroll = max(0, len(self.lines) - self._get_visible_capacity())
        if self.scroll_offset < max_scroll: 
            self.scroll_offset += 1

    def scroll_down(self):
        if self.scroll_offset > 0: 
            self.scroll_offset -= 1
        if self.scroll_offset == 0:
            self.unread_count = 0

    def _get_visible_capacity(self) -> int:
        return (self.height - 20) // 20

    def process_events(self, events: List[pygame.event.Event]):
        self.box_rect.topleft = (self.xpos, self.ypos)
        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEWHEEL and self.box_rect.collidepoint(pos):
                scroll_delta = -event.y if self.reverse_scroll else event.y
                if scroll_delta > 0: 
                    self.scroll_up()
                elif scroll_delta < 0: 
                    self.scroll_down()
                if self.scroll_offset == 0:
                    self.unread_count = 0
                setattr(event, 'consumed', True)

        if self.down_button:
            if hasattr(self.down_button, 'text'):
                if self.unread_count > 0:
                    self.down_button.text = f"New! ({self.unread_count})"
                else:
                    self.down_button.text = "Scroll Down"
            if hasattr(self.down_button, 'process_events'): 
                self.down_button.process_events(events)

        if self.up_button and hasattr(self.up_button, 'process_events'): 
            self.up_button.process_events(events)

    def draw(self):
        if self.bg_image:
            scaled_bg = pygame.transform.scale(self.bg_image, (self.width, self.height))
            self.surface.blit(scaled_bg, (self.xpos, self.ypos))
        else:
            pygame.draw.rect(self.surface, self.theme.input_bg, self.box_rect)
            
        border_color = (255, 165, 0) if self.unread_count > 0 else self.theme.border_dark
        pygame.draw.rect(self.surface, border_color, self.box_rect, 2)

        visible_count = self._get_visible_capacity()
        start_y = self.ypos + 5
        start_x = self.xpos + 10

        end_idx = len(self.lines) - self.scroll_offset
        start_idx = max(0, end_idx - visible_count)
        visible_lines = self.lines[start_idx : end_idx]
        
        old_clip = self.surface.get_clip()
        new_clip = old_clip.clip(self.box_rect) if old_clip else self.box_rect
        self.surface.set_clip(new_clip)
        
        for i, line_text in enumerate(visible_lines):
            text_surf = self.theme.font.render(line_text, True, self.theme.text_color)
            self.surface.blit(text_surf, (start_x, start_y + (i * 20)))
            
        self.surface.set_clip(old_clip)

        if self.up_button and hasattr(self.up_button, 'draw'): self.up_button.draw()
        if self.down_button and hasattr(self.down_button, 'draw'): self.down_button.draw()
        return self.box_rect

class BarGui:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, width: int, height: int,
                 value: int=100, max_value: int=100, value_fn: Optional[Callable]=None,
                 bar_color: Tuple[int,int,int]=(200, 0, 0), bg_color: Tuple[int,int,int]=(50, 50, 50),
                 horizontal: bool=True, tooltip_text: Union[str, Callable]="", theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.width        = width
        self.height       = height
        self.value        = value
        self.max_value    = max_value
        self.value_fn     = value_fn
        self.bar_color    = bar_color
        self.bg_color     = bg_color
        self.horizontal   = horizontal
        self.tooltip_text = tooltip_text
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self.bar_rect     = pygame.Rect(xpos, ypos, width, height)

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text
    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.bar_rect.collidepoint(pos) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]): pass

    def draw(self):
        curr_val = self.value_fn() if callable(self.value_fn) else self.value
        pct = _clamp(curr_val / max(1, self.max_value), 0.0, 1.0)
        self.bar_rect.topleft = (self.xpos, self.ypos)
        pygame.draw.rect(self.surface, self.bg_color, self.bar_rect)
        if pct > 0:
            if self.horizontal:
                fill_w = int(self.width * pct)
                fill_rect = pygame.Rect(self.xpos, self.ypos, fill_w, self.height)
            else:
                fill_h = int(self.height * pct)
                fill_rect = pygame.Rect(self.xpos, self.ypos + (self.height - fill_h), self.width, fill_h)
            pygame.draw.rect(self.surface, self.bar_color, fill_rect)
        pygame.draw.rect(self.surface, self.theme.check_color, self.bar_rect, 1)
        return self.bar_rect

class BarPic:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, img_bg: pygame.Surface, img_fill: pygame.Surface,
                 value: int=100, max_value: int=100, value_fn: Optional[Callable]=None,
                 horizontal: bool=True, tooltip_text: Union[str, Callable]="", z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.img_bg       = img_bg
        self.img_fill     = img_fill
        self.value        = value
        self.max_value    = max_value
        self.value_fn     = value_fn
        self.horizontal   = horizontal
        self.tooltip_text = tooltip_text
        self.z_index      = z_index
        self.width        = img_bg.get_width()
        self.height       = img_bg.get_height()
        self.bar_rect     = pygame.Rect(xpos, ypos, self.width, self.height)

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text
    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.bar_rect.collidepoint(pos) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]): pass

    def draw(self):
        curr_val = self.value_fn() if callable(self.value_fn) else self.value
        pct = _clamp(curr_val / max(1, self.max_value), 0.0, 1.0)
        self.surface.blit(self.img_bg, (self.xpos, self.ypos))
        if pct > 0:
            if self.horizontal:
                crop_area = pygame.Rect(0, 0, max(1, int(self.width * pct)), self.height)
                self.surface.blit(self.img_fill.subsurface(crop_area), (self.xpos, self.ypos))
            else:
                crop_h = max(1, int(self.height * pct))
                crop_y = self.height - crop_h
                crop_area = pygame.Rect(0, crop_y, self.width, crop_h)
                self.surface.blit(self.img_fill.subsurface(crop_area), (self.xpos, self.ypos + crop_y))
        return self.bar_rect

class GaugeGui:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, radius: int,
                 value: int=0, max_value: int=100, value_fn: Optional[Callable]=None,
                 needle_color: Tuple[int,int,int]=(220, 20, 20), bg_color: Optional[Tuple[int,int,int]]=None,
                 half_circle: bool=False, tooltip_text: Union[str, Callable]="", theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.radius       = radius
        self.value        = value
        self.max_value    = max_value
        self.value_fn     = value_fn
        self.needle_color = needle_color
        self.half_circle  = half_circle
        self.tooltip_text = tooltip_text
        self.theme        = theme or default_theme
        self.bg_color     = bg_color or self.theme.input_bg
        self.z_index      = z_index
        self.gauge_rect   = pygame.Rect(xpos, ypos, radius * 2, radius if half_circle else radius * 2)

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text
    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.gauge_rect.collidepoint(pos) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]): pass

    def draw(self):
        curr_val = self.value_fn() if callable(self.value_fn) else self.value
        pct = _clamp(curr_val / max(1, self.max_value), 0.0, 1.0)
        cx, cy = self.xpos + self.radius, self.ypos + self.radius

        if self.half_circle:
            rect = pygame.Rect(self.xpos, self.ypos, self.radius * 2, self.radius * 2)
            pygame.draw.arc(self.surface, self.bg_color, rect, 0, math.pi, self.radius)
            pygame.draw.arc(self.surface, self.theme.check_color, rect, 0, math.pi, 2)
            pygame.draw.line(self.surface, self.theme.check_color, (self.xpos, cy), (self.xpos + self.radius * 2, cy), 2)
            angle_deg = 180 - (pct * 180)
        else:
            pygame.draw.circle(self.surface, self.bg_color, (cx, cy), self.radius)
            pygame.draw.circle(self.surface, self.theme.check_color, (cx, cy), self.radius, 2)
            angle_deg = 225 - (pct * 270)

        rad = math.radians(angle_deg)
        nx = cx + math.cos(rad) * (self.radius * 0.85)
        ny = cy - math.sin(rad) * (self.radius * 0.85)

        pygame.draw.line(self.surface, self.needle_color, (cx, cy), (nx, ny), 2)
        pygame.draw.circle(self.surface, (20, 20, 20), (cx, cy), 4)
        return self.gauge_rect

class GaugePic:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, img_bg: pygame.Surface, img_needle: pygame.Surface,
                 value: int=0, max_value: int=100, value_fn: Optional[Callable]=None,
                 half_circle: bool=False, tooltip_text: Union[str, Callable]="", z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.img_bg       = img_bg
        self.img_needle   = img_needle
        self.value        = value
        self.max_value    = max_value
        self.value_fn     = value_fn
        self.half_circle  = half_circle
        self.tooltip_text = tooltip_text
        self.z_index      = z_index
        self.width        = img_bg.get_width()
        self.height       = img_bg.get_height()
        self.gauge_rect   = pygame.Rect(xpos, ypos, self.width, self.height)

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text
    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        if self.gauge_rect.collidepoint(pos) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]): pass

    def draw(self):
        curr_val = self.value_fn() if callable(self.value_fn) else self.value
        pct = _clamp(curr_val / max(1, self.max_value), 0.0, 1.0)

        if self.half_circle:
            angle_deg = 180 - (pct * 180)
            cx, cy = self.xpos + (self.width // 2), self.ypos + self.height
        else:
            angle_deg = 225 - (pct * 270)
            cx, cy = self.xpos + (self.width // 2), self.ypos + (self.height // 2)

        self.surface.blit(self.img_bg, (self.xpos, self.ypos))
        rot_needle = pygame.transform.rotate(self.img_needle, angle_deg)
        self.surface.blit(rot_needle, rot_needle.get_rect(center=(cx, cy)))
        return self.gauge_rect

class SldGui:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, length: int, default: int=0, max_value: int=100, horizontal: bool=True, on_change: Optional[Callable]=None, tooltip_text: Union[str, Callable]="", theme: Optional[Theme]=None, z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.length       = length
        self.max_value    = max_value
        self.value        = _clamp(default, 0, max_value)
        self.measure      = int((self.value / max(1, self.max_value)) * length)
        self.horizontal   = horizontal
        self.on_change    = on_change
        self.tooltip_text = tooltip_text
        self.theme        = theme or default_theme
        self.z_index      = z_index
        self._dragging    = False   

    def _get_sld_rect(self) -> pygame.Rect:
        if self.horizontal:
            return pygame.Rect(self.xpos + self.measure - 2, self.ypos - 6, 5, 15)
        else:
            return pygame.Rect(self.xpos - 6, self.ypos + self.measure - 2, 15, 5)

    def set_tooltip(self, new_text: str): 
        self.tooltip_text = new_text
        
    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        track_rect = pygame.Rect(self.xpos, self.ypos, self.length, 3) if self.horizontal else pygame.Rect(self.xpos, self.ypos, 3, self.length)
        if (self._get_sld_rect().collidepoint(pos) or track_rect.collidepoint(pos)) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self._get_sld_rect().collidepoint(pos):
                    self._dragging = True
                    setattr(event, 'consumed', True)
            if event.type == MOUSEBUTTONUP and event.button == 1:
                self._dragging = False       
        
        if self._dragging:
            if self.horizontal: new_measure = _clamp(pos[0] - self.xpos, 0, self.length)
            else: new_measure = _clamp(pos[1] - self.ypos, 0, self.length)
            
            if new_measure != self.measure:
                self.measure = new_measure
                self.value = int((self.measure / self.length) * self.max_value)
                if self.on_change: self.on_change(self.value)

    def draw(self):
        if self.horizontal:
            pygame.draw.rect(self.surface, self.theme.check_color, (self.xpos, self.ypos, self.length, 3))
        else:
            pygame.draw.rect(self.surface, self.theme.check_color, (self.xpos, self.ypos, 3, self.length))
        pygame.draw.rect(self.surface, self.theme.check_color, self._get_sld_rect())

class SldPic:
    def __init__(self, surface: pygame.Surface, xpos: int, ypos: int, img_track: pygame.Surface, img_handle: pygame.Surface, default: int=0,
                 horizontal: bool=True, on_change: Optional[Callable]=None, tooltip_text: Union[str, Callable]="", z_index: int=0):
        self.surface      = surface
        self.xpos         = xpos
        self.ypos         = ypos
        self.img_track    = img_track
        self.img_handle   = img_handle
        self.horizontal   = horizontal
        self.on_change    = on_change
        self.tooltip_text = tooltip_text
        self.z_index      = z_index
        self._dragging    = False   
        self.track_w      = img_track.get_width()
        self.track_h      = img_track.get_height()
        self.handle_w     = img_handle.get_width()
        self.handle_h     = img_handle.get_height()
        self.length       = self.track_w if horizontal else self.track_h
        self.measure      = _clamp(default, 0, self.length)

    def _get_sld_rect(self) -> pygame.Rect:
        if self.horizontal:
            hx = self.xpos + self.measure - (self.handle_w // 2)
            hy = self.ypos + (self.track_h // 2) - (self.handle_h // 2)
        else:
            hx = self.xpos + (self.track_w // 2) - (self.handle_w // 2)
            hy = self.ypos + self.measure - (self.handle_h // 2)
        return pygame.Rect(hx, hy, self.handle_w, self.handle_h)

    def set_tooltip(self, new_text: str): self.tooltip_text = new_text
    def get_tooltip_at(self, pos: Tuple[int, int]) -> Optional[str]:
        track_rect = pygame.Rect(self.xpos, self.ypos, self.track_w, self.track_h)
        if (self._get_sld_rect().collidepoint(pos) or track_rect.collidepoint(pos)) and self.tooltip_text:
            return self.tooltip_text() if callable(self.tooltip_text) else self.tooltip_text
        return None

    def process_events(self, events: List[pygame.event.Event]):
        pos = pygame.mouse.get_pos()
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                if self._get_sld_rect().collidepoint(pos):
                    self._dragging = True
                    setattr(event, 'consumed', True)
            if event.type == MOUSEBUTTONUP and event.button == 1:
                self._dragging = False       
        
        if self._dragging:
            if self.horizontal: new_val = _clamp(pos[0] - self.xpos, 0, self.length)
            else: new_val = _clamp(pos[1] - self.ypos, 0, self.length)
            if new_val != self.measure:
                self.measure = new_val
                if self.on_change: self.on_change(self.measure)

    def draw(self):
        self.surface.blit(self.img_track, (self.xpos, self.ypos))
        rect = self._get_sld_rect()
        self.surface.blit(self.img_handle, (rect.x, rect.y))
        return rect

class CustomCursor:
    def __init__(self, surface: pygame.Surface, images: List[pygame.Surface], 
                 offset: Tuple[int, int]=(-16, -16), show_hotspot: bool=False, 
                 ui_manager: Optional[UIManager]=None):
        self.surface = surface
        self.images  = images
        self.offset  = offset
        self.show_hotspot = show_hotspot
        self.ui_manager = ui_manager
        self.mode    = 0
        pygame.mouse.set_visible(False)

    def process_events(self, events: List[pygame.event.Event]):
        for event in events:
            if getattr(event, 'consumed', False): continue
            if event.type == MOUSEBUTTONDOWN and event.button == 3:
                self.mode = (self.mode + 1) % len(self.images)
                setattr(event, 'consumed', True)

    def draw(self):
        if self.ui_manager:
            for widget in self.ui_manager.widgets:
                if type(widget).__name__ == "TxtBox" and getattr(widget, 'is_focused', False):
                    return
        pos = pygame.mouse.get_pos()
        img = self.images[self.mode % len(self.images)]
        self.surface.blit(img, (pos[0] + self.offset[0], pos[1] + self.offset[1]))
        if self.show_hotspot: pygame.draw.rect(self.surface, (255, 255, 0), (pos[0], pos[1], 2, 2))
