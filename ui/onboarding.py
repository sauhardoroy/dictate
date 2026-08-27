"""First-run onboarding for Dictate with modular liquid-glass hero stages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from ui import theme
from ui.liquid_glass_shader import RIPPLE_SPEED, shader_engine
from ui.settings_dialog import KeyCaptureButton


def _font(size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    return theme.get_font(size, weight)


def _glass_backdrop(size, dark: bool, accent: QColor) -> QPixmap:
    """Create a quiet backdrop for the shared refractive shader."""
    pixmap = QPixmap(size)
    pixmap.fill(QColor(theme.pick(theme.SURFACE_CARD, dark)))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    wash = QColor(accent); wash.setAlpha(24 if dark else 18)
    painter.setBrush(wash); painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(-size.width() * .15, -size.height() * .6, size.width() * 1.1, size.height() * 1.5))
    painter.end()
    return pixmap


class LiquidGlassButton(QPushButton):
    """A restrained control rendered with the shared refraction shader."""

    def __init__(self, text: str, *, primary=False, accent_token=theme.SYSTEM_TEAL, dark=False, parent=None):
        super().__init__(text, parent)
        self.primary, self.accent_token, self.dark = primary, accent_token, dark
        self._hover = self._pressed = False
        self._image = QImage()
        self.setFixedHeight(40); self.setMinimumWidth(104)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(_font(10, QFont.Weight.DemiBold)); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _render(self):
        if self.width() < 8 or self.height() < 8: return
        accent = QColor(theme.pick(self.accent_token, self.dark))
        if self._hover: accent = accent.lighter(108)
        if self._pressed: accent = accent.darker(108)
        self._image = shader_engine.render(_glass_backdrop(self.size(), self.dark, accent), self.width(), self.height(),
                                           dark=self.dark, accent_color=accent, ripple_phase=.18 if self._hover else 0,
                                           supersample_factor=2)

    def resizeEvent(self, event): super().resizeEvent(event); self._render()
    def enterEvent(self, event): self._hover = True; self._render(); self.update(); super().enterEvent(event)
    def leaveEvent(self, event): self._hover = self._pressed = False; self._render(); self.update(); super().leaveEvent(event)
    def mousePressEvent(self, event): self._pressed = event.button() == Qt.MouseButton.LeftButton; self._render(); self.update(); super().mousePressEvent(event)
    def mouseReleaseEvent(self, event): self._pressed = False; self._render(); self.update(); super().mouseReleaseEvent(event)

    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1); path = QPainterPath(); path.addRoundedRect(rect, rect.height()/2, rect.height()/2)
        accent = QColor(theme.pick(self.accent_token, self.dark))
        if self.primary:
            if not self._image.isNull(): p.drawImage(rect, self._image)
            else: p.fillPath(path, accent)
            p.setPen(QPen(QColor(255,255,255,115), 1)); p.drawPath(path); color = QColor("#FFFFFF")
        else:
            fill = QColor(255,255,255,26 if self.dark else 150)
            if self._hover: fill.setAlpha(fill.alpha()+24)
            p.fillPath(path, fill); p.setPen(QPen(QColor(255,255,255,70) if self.dark else QColor(0,0,0,24), 1)); p.drawPath(path)
            color = QColor(theme.pick(theme.TEXT_PRIMARY, self.dark))
        if self.hasFocus(): p.setPen(QPen(QColor(theme.pick(theme.BORDER_FOCUS, self.dark)), 2)); p.drawPath(path)
        p.setFont(self.font()); p.setPen(color); p.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())


class AppleToggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=True, dark=False, parent=None):
        super().__init__(parent)
        self.dark, self._checked, self._position = dark, checked, float(checked)
        self.setFixedSize(46,28); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._animation = QVariantAnimation(self, duration=180); self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._animate)

    def _animate(self, value): self._position = float(value); self.update()
    def isChecked(self): return self._checked
    def setChecked(self, checked):
        if checked == self._checked: return
        self._checked = checked; self._animation.stop(); self._animation.setStartValue(self._position); self._animation.setEndValue(float(checked)); self._animation.start(); self.toggled.emit(checked)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.setChecked(not self._checked)
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return): self.setChecked(not self._checked)
        else: super().keyPressEvent(event)
    def paintEvent(self, _event):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); track = QRectF(self.rect()).adjusted(1,1,-1,-1)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(theme.pick(theme.SYSTEM_TEAL,self.dark)) if self._checked else QColor(120,120,128,90)); p.drawRoundedRect(track,14,14)
        x = track.left()+3+self._position*(track.width()-28); p.setBrush(QColor("#FFFFFF")); p.drawEllipse(QRectF(x,track.top()+3,22,22))


@dataclass(frozen=True)
class HeroAsset:
    """A page hero contract. Use ``widget_factory`` for an animated SVG widget later."""
    name: str
    accent_token: tuple[str,str]
    svg_path: str | None = None
    widget_factory: Callable[[QWidget], QWidget] | None = None


DEFAULT_HEROES = {"welcome": HeroAsset("welcome",theme.SYSTEM_TEAL), "setup": HeroAsset("setup",theme.SYSTEM_PURPLE), "ready": HeroAsset("ready",theme.SYSTEM_GREEN)}


class HeroStage(QWidget):
    """Liquid visual stage whose built-in illustration can be swapped independently."""
    def __init__(self, asset: HeroAsset, dark=False, parent=None):
        super().__init__(parent); self.asset, self.dark, self._phase, self._external_widget = asset, dark, 0.0, None
        self.setFixedHeight(184); self._timer = QTimer(self, interval=33); self._timer.timeout.connect(self._tick); self._timer.start(); self.set_hero_asset(asset)
    def set_hero_asset(self, asset: HeroAsset):
        self.asset = asset
        if self._external_widget: self._external_widget.deleteLater(); self._external_widget = None
        if asset.widget_factory:
            self._external_widget = asset.widget_factory(self); self._external_widget.setGeometry(self.rect()); self._external_widget.show()
        elif asset.svg_path:
            # Static SVGs render immediately; animated SVG wrappers can be supplied
            # through widget_factory without changing this stage or its layout.
            svg = QSvgWidget(asset.svg_path, self)
            if svg.renderer().isValid():
                self._external_widget = svg; svg.setGeometry(self.rect()); svg.show()
            else:
                svg.deleteLater()
        self.update()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self._external_widget: self._external_widget.setGeometry(self.rect())
    def _tick(self): self._phase += .035*RIPPLE_SPEED; self.update()
    def paintEvent(self,_event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect=QRectF(self.rect()).adjusted(1,1,-1,-1); path=QPainterPath(); path.addRoundedRect(rect,22,22); p.fillPath(path,QColor(theme.pick(theme.SURFACE_ELEVATED,self.dark)))
        accent=QColor(theme.pick(self.asset.accent_token,self.dark)); cx,cy=rect.center().x(),rect.center().y(); orb=88
        liquid=shader_engine.render(_glass_backdrop(QRectF(0,0,orb,orb).toRect().size(),self.dark,accent),orb,orb,dark=self.dark,accent_color=accent,ripple_phase=self._phase,supersample_factor=2)
        p.drawImage(QRectF(cx-orb/2,cy-orb/2,orb,orb),liquid); p.setPen(QPen(QColor(255,255,255,205),2.2,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin)); p.setBrush(Qt.BrushStyle.NoBrush)
        if self.asset.name=="welcome":
            p.drawRoundedRect(QRectF(cx-5,cy-16,10,18),5,5); p.drawArc(QRectF(cx-10,cy-8,20,16),0,-180*16); p.drawLine(QPointF(cx,cy+8),QPointF(cx,cy+15)); p.drawLine(QPointF(cx-6,cy+15),QPointF(cx+6,cy+15))
        elif self.asset.name=="setup":
            for y,x in ((-7,-5),(0,6),(7,0)): p.drawLine(QPointF(cx-14,cy+y),QPointF(cx+14,cy+y)); p.setBrush(QColor(255,255,255,220)); p.drawEllipse(QPointF(cx+x,cy+y),3,3); p.setBrush(Qt.BrushStyle.NoBrush)
        else: p.drawLine(QPointF(cx-12,cy),QPointF(cx-4,cy+8)); p.drawLine(QPointF(cx-4,cy+8),QPointF(cx+13,cy-10))
        p.setPen(QPen(QColor(255,255,255,70) if self.dark else QColor(255,255,255,180),1)); p.drawPath(path)


class SidebarNavItem(QWidget):
    clicked=pyqtSignal(int)
    def __init__(self,index,title,dark=False,parent=None):
        super().__init__(parent); self.index,self.title,self.dark,self._active=index,title,dark,False; self.setFixedHeight(40); self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    def set_active(self,active): self._active=active; self.update()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.clicked.emit(self.index)
    def keyPressEvent(self,event):
        if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Space):self.clicked.emit(self.index)
        else:super().keyPressEvent(event)
    def paintEvent(self,_event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);rect=QRectF(self.rect()).adjusted(2,2,-2,-2);path=QPainterPath();path.addRoundedRect(rect,12,12);accent=QColor(theme.pick(theme.SYSTEM_TEAL,self.dark))
        if self._active:
            p.drawImage(rect,shader_engine.render(_glass_backdrop(self.size(),self.dark,accent),self.width(),self.height(),dark=self.dark,accent_color=accent,ripple_phase=.25,supersample_factor=2));p.setPen(QPen(QColor(255,255,255,105),1));p.drawPath(path)
        color=accent if self._active else QColor(theme.pick(theme.TEXT_SECONDARY,self.dark));p.setBrush(color);p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(QRectF(rect.left()+13,rect.center().y()-3,6,6));p.setFont(_font(10,QFont.Weight.DemiBold if self._active else QFont.Weight.Medium));p.setPen(color);p.drawText(QRectF(rect.left()+30,rect.top(),rect.width()-36,rect.height()),Qt.AlignmentFlag.AlignVCenter,self.title)


class OnboardingDialog(QDialog):
    """Three-stage first-run flow. Pass hero_assets to replace any built-in scene."""
    class DialogCode: Accepted=1; Rejected=0
    def __init__(self,trigger_key="ctrl+shift+p",model_id="",dark=False,parent=None,hero_assets=None):
        super().__init__(parent);self.trigger_key,self.model_id,self.dark=trigger_key,model_id,dark;self.hero_assets={**DEFAULT_HEROES,**(hero_assets or {})};self._drag_pos=None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Dialog);self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground);self.setFixedSize(900,590);self._build();self._go_to_scene(0)
    def _label(self,text,size=10,weight=QFont.Weight.Normal,muted=False):
        label=QLabel(text);label.setFont(_font(size,weight));label.setWordWrap(True);label.setStyleSheet(f"color: {theme.pick(theme.TEXT_SECONDARY if muted else theme.TEXT_PRIMARY,self.dark)}; background: transparent;");return label
    def _build(self):
        outer=QVBoxLayout(self);outer.setContentsMargins(0,0,0,0);shell=QFrame();shell.setObjectName("onboardingShell");outer.addWidget(shell);bg=theme.pick(theme.SURFACE_BG,self.dark);border="rgba(255,255,255,.14)" if self.dark else "rgba(0,0,0,.09)";shell.setStyleSheet(f"#onboardingShell {{background:{bg};border:1px solid {border};border-radius:24px;}}")
        root=QHBoxLayout(shell);root.setContentsMargins(0,0,0,0);root.setSpacing(0);rail=QFrame();rail.setFixedWidth(190);rail.setStyleSheet(f"background:{theme.pick(theme.SURFACE_ELEVATED,self.dark)};border-top-left-radius:24px;border-bottom-left-radius:24px;");rail_layout=QVBoxLayout(rail);rail_layout.setContentsMargins(18,28,18,24);rail_layout.setSpacing(4)
        brand=self._label("Dictate",11,QFont.Weight.DemiBold);brand.setStyleSheet(brand.styleSheet()+"padding:0 10px 18px;");rail_layout.addWidget(brand);self.nav_items=[SidebarNavItem(0,"Welcome",self.dark),SidebarNavItem(1,"Setup",self.dark),SidebarNavItem(2,"Get Started",self.dark)]
        for item in self.nav_items:item.clicked.connect(self._go_to_scene);rail_layout.addWidget(item)
        rail_layout.addStretch();root.addWidget(rail);content=QWidget();content_layout=QVBoxLayout(content);content_layout.setContentsMargins(42,34,42,30);self.stack=QStackedWidget();self.stack.addWidget(self._welcome());self.stack.addWidget(self._setup());self.stack.addWidget(self._ready());content_layout.addWidget(self.stack);root.addWidget(content)
    def _page(self,hero_name,title,subtitle):
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0);layout.addWidget(HeroStage(self.hero_assets[hero_name],self.dark));layout.addSpacing(24);layout.addWidget(self._label(title,21,QFont.Weight.DemiBold));layout.addSpacing(7);layout.addWidget(self._label(subtitle,10,muted=True));return page,layout
    def _actions(self,layout,back,forward,handler):
        layout.addStretch();row=QHBoxLayout()
        if back is not None:
            button=LiquidGlassButton("Back",dark=self.dark);button.clicked.connect(lambda:self._go_to_scene(back));row.addWidget(button)
        row.addStretch();primary=LiquidGlassButton(forward,primary=True,dark=self.dark);primary.clicked.connect(handler);row.addWidget(primary);layout.addLayout(row)
    def _welcome(self):
        page,layout=self._page("welcome","Dictate, wherever you write.","Hold a shortcut, speak, and Dictate places clean text at your cursor.");layout.addSpacing(16);layout.addWidget(self._label("Speech recognition stays on your device.",9,QFont.Weight.Medium,True));self._actions(layout,None,"Continue",lambda:self._go_to_scene(1));return page
    def _setup_row(self,title,detail,control):
        row=QWidget();row.setMinimumHeight(58);box=QHBoxLayout(row);box.setContentsMargins(0,8,0,8);texts=QVBoxLayout();texts.setSpacing(2);texts.addWidget(self._label(title,10,QFont.Weight.DemiBold));texts.addWidget(self._label(detail,9,muted=True));box.addLayout(texts);box.addStretch();box.addWidget(control);return row
    def _setup(self):
        page,layout=self._page("setup","A few essentials.","Set the shortcut you’ll use to start dictating.");layout.addSpacing(13);self.btn_capture=KeyCaptureButton(self.trigger_key);self.btn_capture.setFixedWidth(138);layout.addWidget(self._setup_row("Dictation shortcut","Available in any app.",self.btn_capture));divider=QFrame();divider.setFixedHeight(1);divider.setStyleSheet(f"background:{theme.pick(theme.BORDER_SUBTLE,self.dark)};");layout.addWidget(divider);info=QWidget();info_layout=QVBoxLayout(info);info_layout.setContentsMargins(0,10,0,8);info_layout.setSpacing(2);info_layout.addWidget(self._label("Local speech model",10,QFont.Weight.DemiBold));info_layout.addWidget(self._label("Ready for offline transcription",9,muted=True));layout.addWidget(info);self._actions(layout,0,"Continue",lambda:self._go_to_scene(2));return page
    def _ready(self):
        page,layout=self._page("ready","Ready when you are.","Focus a text field, hold your shortcut, then speak naturally.");layout.addSpacing(16);self.toggle_ai=AppleToggle(True,self.dark);layout.addWidget(self._setup_row("Polish transcripts","Remove filler words and tidy punctuation.",self.toggle_ai));self._actions(layout,1,"Start Dictating",self.accept);return page
    def _go_to_scene(self,index):
        self.stack.setCurrentIndex(index)
        for i,item in enumerate(self.nav_items):item.set_active(i==index)
    def values(self):return {"trigger_key":getattr(self.btn_capture,"key",self.trigger_key),"ai_polish":self.toggle_ai.isChecked()}
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self._drag_pos=event.globalPosition().toPoint()-self.frameGeometry().topLeft()
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if event.buttons()==Qt.MouseButton.LeftButton and self._drag_pos:self.move(event.globalPosition().toPoint()-self._drag_pos)
        super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):self._drag_pos=None;super().mouseReleaseEvent(event)
