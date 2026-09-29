"""Tema visual do desktop AGCN Live Voice.

Mantém a aparência consistente entre Dashboard, Produto, Voz e áudio e
Configurações sem espalhar QSS por toda a lógica da aplicação.
"""

APP_STYLESHEET = r"""
QMainWindow {
    background: #F5F7FB;
}

QWidget {
    color: #152238;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
}

QWidget#AppRoot,
QWidget#PageRoot,
QWidget#PageContent {
    background: #F5F7FB;
}

QWidget#Sidebar {
    background: #FFFFFF;
    border-right: 1px solid #E3E9F2;
}

QLabel#BrandTitle {
    color: #101828;
    font-size: 23px;
    font-weight: 800;
}

QLabel#BrandSubtitle {
    color: #7B879B;
    font-size: 11px;
}

QLabel#SidebarFooter {
    color: #18A66A;
    font-size: 11px;
    padding: 12px 16px;
}

QLabel#PageTitle {
    color: #121B2C;
    font-size: 29px;
    font-weight: 750;
}

QLabel#PageSubtitle {
    color: #6B7890;
    font-size: 13px;
}

QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #E3E9F2;
    border-radius: 15px;
}

QFrame#SoftCard {
    background: #F8FAFD;
    border: 1px solid #E7ECF4;
    border-radius: 12px;
}

QFrame#PlanCurrent {
    background: #F4F8FF;
    border: 2px solid #1677FF;
    border-radius: 12px;
}

QLabel#CardTitle {
    color: #172033;
    font-size: 15px;
    font-weight: 700;
}

QLabel#CardSubtitle,
QLabel#Muted {
    color: #718096;
    font-size: 12px;
}

QLabel#MetricLabel {
    color: #7A879A;
    font-size: 11px;
    font-weight: 600;
}

QLabel#MetricValue {
    color: #101828;
    font-size: 19px;
    font-weight: 750;
}

QLabel#ValueStrong {
    color: #172033;
    font-size: 14px;
    font-weight: 700;
}

QLabel#StatusGood {
    color: #0B8A5B;
    background: #E8F8F1;
    border: 1px solid #CBEFDF;
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#StatusInfo {
    color: #075CCF;
    background: #EAF3FF;
    border: 1px solid #D7E8FF;
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 700;
}

QLabel#InfoBanner {
    color: #1E4B8F;
    background: #EDF5FF;
    border: 1px solid #D8E9FF;
    border-radius: 10px;
    padding: 10px 12px;
}

QLineEdit,
QTextEdit,
QComboBox,
QListWidget {
    background: #FFFFFF;
    border: 1px solid #D8E0EB;
    border-radius: 9px;
    padding: 8px 10px;
    selection-background-color: #1677FF;
}

QLineEdit,
QComboBox {
    min-height: 37px;
}

QLineEdit:focus,
QTextEdit:focus,
QComboBox:focus,
QListWidget:focus {
    border: 1px solid #1677FF;
}

QComboBox {
    padding-right: 28px;
}

QComboBox::drop-down {
    border: 0;
    width: 28px;
}

QComboBox QAbstractItemView {
    background: #FFFFFF;
    border: 1px solid #D8E0EB;
    selection-background-color: #EAF3FF;
    selection-color: #0B63F6;
    padding: 5px;
}

QPushButton {
    min-height: 36px;
    background: #FFFFFF;
    border: 1px solid #D5DDE9;
    border-radius: 9px;
    padding: 8px 14px;
    color: #24324A;
    font-weight: 600;
}

QPushButton:hover {
    background: #F6F9FD;
    border-color: #BFCBDD;
}

QPushButton:pressed {
    background: #EDF3FB;
}

QPushButton:disabled {
    color: #A6AFBD;
    background: #F3F5F8;
    border-color: #E2E7EE;
}

QPushButton#PrimaryButton {
    color: #FFFFFF;
    background: #116CF4;
    border: 1px solid #116CF4;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover {
    background: #075EDC;
}

QPushButton#DangerButton {
    color: #FFFFFF;
    background: #F04463;
    border: 1px solid #F04463;
    font-weight: 700;
}

QPushButton#DangerButton:hover {
    background: #DC3554;
}

QPushButton#GhostButton {
    background: #F8FAFD;
    border: 1px solid #E1E7F0;
}

QGroupBox {
    background: #FFFFFF;
    border: 1px solid #E3E9F2;
    border-radius: 15px;
    margin-top: 18px;
    padding: 20px 14px 14px 14px;
    font-size: 15px;
    font-weight: 700;
    color: #172033;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    top: 2px;
    padding: 0 6px;
    background: #FFFFFF;
}

QFormLayout QLabel {
    color: #5F6E84;
    font-size: 12px;
}

QScrollArea {
    border: 0;
    background: transparent;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QListWidget#SidebarNav {
    border: 0;
    background: transparent;
    color: #34445F;
    padding: 4px 0;
    outline: 0;
}

QListWidget#SidebarNav::item {
    border: 0;
    border-radius: 10px;
    padding: 13px 14px;
    margin: 3px 10px;
}

QListWidget#SidebarNav::item:hover {
    background: #F1F5FB;
}

QListWidget#SidebarNav::item:selected {
    color: #075FD3;
    background: #EAF3FF;
    font-weight: 700;
}

QListWidget#DataList {
    background: #FFFFFF;
    border: 0;
    padding: 2px;
}

QListWidget#DataList::item {
    border-bottom: 1px solid #EEF2F7;
    padding: 9px 7px;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #E6ECF4;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #1680FF;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
    background: #FFFFFF;
    border: 3px solid #1677FF;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
}

QMessageBox {
    background: #FFFFFF;
}
"""


def apply_card(widget, *, variant: str = "Card") -> None:
    widget.setObjectName(variant)


def apply_primary(button) -> None:
    button.setObjectName("PrimaryButton")


def apply_danger(button) -> None:
    button.setObjectName("DangerButton")


def apply_ghost(button) -> None:
    button.setObjectName("GhostButton")
