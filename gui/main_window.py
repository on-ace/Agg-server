import os
import webbrowser
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QMessageBox, QListWidget,
    QListWidgetItem, QSplitter, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QTextEdit, QComboBox, QDialog,
    QFormLayout, QCheckBox, QSpinBox, QHeaderView, QAbstractItemView,
    QStatusBar, QScrollArea, QFrame, QDialogButtonBox, QInputDialog,
    QFileDialog, QApplication, QMenu, QAction
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIntValidator, QFont, QColor, QIcon
from server.local_server import ServerThread
from db.database import DatabaseManager


# ── Worker thread untuk query berat ──────────────────────────────────────────
class QueryWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        result = self.fn(*self.args, **self.kwargs)
        self.finished.emit(result)


# ── Dialog: Tambah kolom tabel ────────────────────────────────────────────────
class CreateTableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buat Tabel Baru")
        self.setMinimumSize(680, 480)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self.columns = []
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        # Nama tabel
        top = QHBoxLayout()
        top.addWidget(QLabel("Nama Tabel:"))
        self.tbl_name = QLineEdit()
        self.tbl_name.setPlaceholderText("contoh: users")
        top.addWidget(self.tbl_name)
        lay.addLayout(top)

        # Tabel kolom
        self.col_table = QTableWidget(0, 7)
        self.col_table.setHorizontalHeaderLabels(
            ["Nama Kolom", "Tipe", "Panjang", "Not Null", "PK", "AI", "Default"]
        )
        self.col_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.col_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.col_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.col_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.col_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        lay.addWidget(self.col_table)

        # Tombol tambah/hapus kolom
        btn_row = QHBoxLayout()
        add_col = QPushButton("+ Tambah Kolom")
        add_col.clicked.connect(self._add_column)
        del_col = QPushButton("− Hapus Kolom")
        del_col.clicked.connect(self._del_column)
        # Preset kolom id
        preset_id = QPushButton("⚡ Tambah id (PK AUTO)")
        preset_id.clicked.connect(self._preset_id)
        btn_row.addWidget(add_col)
        btn_row.addWidget(del_col)
        btn_row.addWidget(preset_id)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # OK / Batal
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._add_column()  # mulai dengan 1 kolom kosong

    TYPES = ["INT", "BIGINT", "VARCHAR", "TEXT", "LONGTEXT", "CHAR",
             "FLOAT", "DOUBLE", "DECIMAL", "DATE", "DATETIME", "TIMESTAMP",
             "BOOLEAN", "TINYINT", "SMALLINT", "MEDIUMINT", "JSON", "BLOB"]

    def _add_column(self):
        r = self.col_table.rowCount()
        self.col_table.insertRow(r)
        self.col_table.setItem(r, 0, QTableWidgetItem(""))
        cb = QComboBox()
        cb.addItems(self.TYPES)
        self.col_table.setCellWidget(r, 1, cb)
        self.col_table.setItem(r, 2, QTableWidgetItem(""))
        for c in (3, 4, 5):
            chk = QCheckBox()
            chk.setStyleSheet("margin-left:14px")
            self.col_table.setCellWidget(r, c, chk)
        self.col_table.setItem(r, 6, QTableWidgetItem(""))

    def _del_column(self):
        rows = set(i.row() for i in self.col_table.selectedItems())
        for r in sorted(rows, reverse=True):
            self.col_table.removeRow(r)

    def _preset_id(self):
        r = self.col_table.rowCount()
        self.col_table.insertRow(r)
        self.col_table.setItem(r, 0, QTableWidgetItem("id"))
        cb = QComboBox(); cb.addItems(self.TYPES); cb.setCurrentText("INT")
        self.col_table.setCellWidget(r, 1, cb)
        self.col_table.setItem(r, 2, QTableWidgetItem("11"))
        not_null = QCheckBox(); not_null.setChecked(True); not_null.setStyleSheet("margin-left:14px")
        pk = QCheckBox(); pk.setChecked(True); pk.setStyleSheet("margin-left:14px")
        ai = QCheckBox(); ai.setChecked(True); ai.setStyleSheet("margin-left:14px")
        self.col_table.setCellWidget(r, 3, not_null)
        self.col_table.setCellWidget(r, 4, pk)
        self.col_table.setCellWidget(r, 5, ai)
        self.col_table.setItem(r, 6, QTableWidgetItem(""))

    def get_data(self):
        name = self.tbl_name.text().strip()
        columns = []
        for r in range(self.col_table.rowCount()):
            col_name = (self.col_table.item(r, 0) or QTableWidgetItem("")).text().strip()
            if not col_name:
                continue
            type_cb = self.col_table.cellWidget(r, 1)
            length = (self.col_table.item(r, 2) or QTableWidgetItem("")).text().strip()
            not_null = self.col_table.cellWidget(r, 3)
            pk = self.col_table.cellWidget(r, 4)
            ai = self.col_table.cellWidget(r, 5)
            default = (self.col_table.item(r, 6) or QTableWidgetItem("")).text().strip()
            columns.append({
                "name": col_name,
                "type": type_cb.currentText() if type_cb else "VARCHAR",
                "length": length or None,
                "nullable": not (not_null.isChecked() if not_null else False),
                "primary_key": pk.isChecked() if pk else False,
                "auto_increment": ai.isChecked() if ai else False,
                "default": default or None,
            })
        return name, columns


# ── Dialog: Tambah / Edit Row ─────────────────────────────────────────────────
class RowEditDialog(QDialog):
    def __init__(self, columns, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tambah Row" if data is None else "Edit Row")
        self.setMinimumWidth(420)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        self.inputs = {}
        lay = QFormLayout(self)
        for col in columns:
            name = col.get("Field", col.get("name", ""))
            val = str(data.get(name, "")) if data else ""
            inp = QLineEdit(val)
            inp.setPlaceholderText("NULL" if col.get("Null", "YES") == "YES" else "")
            self.inputs[name] = inp
            lay.addRow(f"{name} ({col.get('Type', '')})", inp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addRow(btns)

    def get_data(self):
        return {k: (v.text() if v.text() != "" else None) for k, v in self.inputs.items()}


# ── Utama ─────────────────────────────────────────────────────────────────────
class AggServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Agg Server")
        self.setMinimumSize(1100, 660)
        self.setStyleSheet(self._style())

        self.server_thread = None
        self.current_port = 8000
        self.db = DatabaseManager()
        self._current_db = None
        self._current_table = None
        self._page = 0
        self._page_size = 100

        self._build_ui()
        self.ensure_www_directory()
        self.refresh_folder_list()

    # ═══════════════════════════════════════════════════════════
    # STYLE
    # ═══════════════════════════════════════════════════════════
    def _style(self):
        return """
        QMainWindow, QDialog { background: #0f172a; }
        QWidget { font-family: "Segoe UI", Arial, sans-serif; color: #e2e8f0; font-size: 12px; }
        QTabWidget::pane { border: 1px solid #1e293b; background: #0f172a; }
        QTabBar::tab {
            background: #1e293b; color: #64748b; padding: 7px 20px;
            border-top-left-radius: 6px; border-top-right-radius: 6px;
            margin-right: 2px;
        }
        QTabBar::tab:selected { background: #0f172a; color: #e2e8f0; border-bottom: 2px solid #3b82f6; }
        QTabBar::tab:hover { color: #cbd5e1; }
        QGroupBox {
            background: rgba(30,41,59,.4); border: 1px solid #1e293b;
            border-radius: 10px; margin-top: 10px; font-weight: 600; font-size: 11px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #475569; }
        QLineEdit, QComboBox, QSpinBox, QTextEdit {
            background: #1e293b; border: 1px solid #334155; border-radius: 6px;
            padding: 5px 10px; color: #f1f5f9; selection-background-color: #2563eb;
        }
        QLineEdit:focus, QTextEdit:focus { border-color: #3b82f6; }
        QComboBox::drop-down { border: none; }
        QComboBox QAbstractItemView { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; }
        QPushButton {
            background: #1e293b; border: 1px solid #334155; border-radius: 20px;
            padding: 5px 16px; color: #e2e8f0; font-weight: 500;
        }
        QPushButton:hover { background: #334155; border-color: #475569; }
        QPushButton:pressed { background: #0f172a; }
        QPushButton#btn_primary { background: #2563eb; border: none; color: #fff; }
        QPushButton#btn_primary:hover { background: #1d4ed8; }
        QPushButton#btn_danger { background: #dc2626; border: none; color: #fff; }
        QPushButton#btn_danger:hover { background: #b91c1c; }
        QPushButton#btn_success { background: #16a34a; border: none; color: #fff; }
        QPushButton#btn_success:hover { background: #15803d; }
        QPushButton#btn_warn { background: #d97706; border: none; color: #fff; }
        QPushButton#btn_warn:hover { background: #b45309; }
        QPushButton#run_btn { background: #059669; border: none; color: #fff; font-weight: bold; }
        QPushButton#run_btn:hover { background: #047857; }
        QPushButton#stop_btn { background: #dc2626; border: none; color: #fff; font-weight: bold; }
        QPushButton#stop_btn:hover { background: #b91c1c; }
        QTreeWidget, QListWidget {
            background: #0b1120; border: 1px solid #1e293b; border-radius: 8px; outline: none;
        }
        QTreeWidget::item, QListWidget::item { padding: 5px 8px; color: #94a3b8; }
        QTreeWidget::item:selected, QListWidget::item:selected { background: #1d4ed8; color: #fff; }
        QTreeWidget::item:hover, QListWidget::item:hover { background: rgba(59,130,246,.15); }
        QTableWidget {
            background: #0b1120; border: 1px solid #1e293b; gridline-color: #1e293b;
            border-radius: 0px; outline: none;
        }
        QTableWidget::item { color: #cbd5e1; padding: 3px 6px; border: none; }
        QTableWidget::item:selected { background: #1d4ed8; color: #fff; }
        QHeaderView::section {
            background: #1e293b; color: #64748b; font-weight: 600; font-size: 11px;
            padding: 5px 8px; border: none; border-right: 1px solid #0b1120;
            border-bottom: 1px solid #334155;
        }
        QSplitter::handle { background: #1e293b; }
        QSplitter::handle:hover { background: #3b82f6; }
        QScrollBar:vertical { background: #0b1120; width: 6px; }
        QScrollBar::handle:vertical { background: #334155; border-radius: 3px; min-height: 20px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal { background: #0b1120; height: 6px; }
        QScrollBar::handle:horizontal { background: #334155; border-radius: 3px; min-width: 20px; }
        QStatusBar { background: #0b1120; color: #475569; font-size: 11px; border-top: 1px solid #1e293b; }
        QLabel#title { font-size: 22px; font-weight: bold; color: #22d3ee; padding: 6px; }
        QLabel#sec_title { font-size: 13px; font-weight: 600; color: #94a3b8; }
        QCheckBox { color: #94a3b8; }
        QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #475569; border-radius: 3px; background: #1e293b; }
        QCheckBox::indicator:checked { background: #2563eb; border-color: #2563eb; }
        QMenu { background: #1e293b; border: 1px solid #334155; color: #e2e8f0; }
        QMenu::item:selected { background: #2563eb; }
        QMenu::separator { height: 1px; background: #334155; }
        """

    # ═══════════════════════════════════════════════════════════
    # BUILD UI
    # ═══════════════════════════════════════════════════════════
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background:#0b1120; border-bottom:1px solid #1e293b;")
        header.setFixedHeight(48)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        ttl = QLabel("⚡ Agg Server")
        ttl.setObjectName("title")
        hl.addWidget(ttl)
        hl.addStretch()
        # status server di header
        self.header_status = QLabel("● OFFLINE")
        self.header_status.setStyleSheet("color:#f87171; font-weight:600; font-size:12px;")
        hl.addWidget(self.header_status)
        root.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs)

        self.tabs.addTab(self._build_server_tab(), "  🌐  Server  ")
        self.tabs.addTab(self._build_db_tab(),     "  🗄️  Database  ")

        # Status bar
        self.setStatusBar(QStatusBar())

    # ──────────────────────────────────────────────────────────
    # TAB: SERVER
    # ──────────────────────────────────────────────────────────
    def _build_server_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Horizontal)
        lay.addWidget(splitter)

        # Kiri
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 8, 0)

        ctrl = QGroupBox("SERVER CONTROL")
        cl = QVBoxLayout(ctrl)

        # Port
        pr = QHBoxLayout()
        pr.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit("8000")
        self.port_input.setValidator(QIntValidator(1024, 65535))
        self.port_input.setFixedWidth(100)
        pr.addWidget(self.port_input)
        pr.addStretch()
        cl.addLayout(pr)

        self.run_stop_btn = QPushButton("▶  START SERVER")
        self.run_stop_btn.setObjectName("run_btn")
        self.run_stop_btn.clicked.connect(self.toggle_server)
        cl.addWidget(self.run_stop_btn)

        sr = QHBoxLayout()
        sr.addWidget(QLabel("Status:"))
        self.status_indicator = QLabel("● OFFLINE")
        self.status_indicator.setStyleSheet("color:#f87171; font-weight:bold;")
        sr.addWidget(self.status_indicator)
        sr.addStretch()
        cl.addLayout(sr)

        ur = QHBoxLayout()
        ur.addWidget(QLabel("URL:"))
        self.url_label = QLabel("—")
        self.url_label.setStyleSheet("color:#38bdf8; font-family:monospace;")
        ur.addWidget(self.url_label)
        ur.addStretch()
        cl.addLayout(ur)

        self.browser_btn = QPushButton("🌐  Open Browser")
        self.browser_btn.setObjectName("btn_primary")
        self.browser_btn.setEnabled(False)
        self.browser_btn.clicked.connect(self.open_browser)
        cl.addWidget(self.browser_btn)

        ctrl.setLayout(cl)
        ll.addWidget(ctrl)

        info = QGroupBox("INFO")
        il = QVBoxLayout(info)
        il.addWidget(QLabel("Folder di dalam 'www' dapat diakses via browser."))
        self.path_label = QLabel(f"📁 {self.get_www_path()}")
        self.path_label.setStyleSheet("font-family:monospace; font-size:10px; color:#475569;")
        self.path_label.setWordWrap(True)
        il.addWidget(self.path_label)
        ll.addWidget(info)
        ll.addStretch()
        splitter.addWidget(left)

        # Kanan
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)

        browse = QGroupBox("BROWSE ROOT (www)")
        bl = QVBoxLayout(browse)
        ref = QPushButton("⟳ Refresh")
        ref.setFixedWidth(90)
        ref.clicked.connect(self.refresh_folder_list)
        bl.addWidget(ref, alignment=Qt.AlignRight)
        self.folder_list = QListWidget()
        self.folder_list.itemDoubleClicked.connect(self.on_folder_double_click)
        bl.addWidget(self.folder_list)
        rl.addWidget(browse)
        splitter.addWidget(right)
        splitter.setSizes([300, 500])

        return w

    # ──────────────────────────────────────────────────────────
    # TAB: DATABASE
    # ──────────────────────────────────────────────────────────
    def _build_db_tab(self):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Panel kiri: koneksi + tree ──
        left = QWidget()
        left.setFixedWidth(240)
        left.setStyleSheet("background:#0b1120; border-right:1px solid #1e293b;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(8, 10, 8, 8)
        ll.setSpacing(6)

        # Koneksi
        conn_box = QGroupBox("KONEKSI MySQL")
        conn_lay = QFormLayout(conn_box)
        conn_lay.setContentsMargins(8, 14, 8, 8)
        conn_lay.setSpacing(6)
        self.db_host = QLineEdit("localhost")
        self.db_port = QLineEdit("3306")
        self.db_user = QLineEdit("root")
        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.Password)
        for w2, label in [(self.db_host, "Host"), (self.db_port, "Port"),
                          (self.db_user, "User"), (self.db_pass, "Password")]:
            conn_lay.addRow(label, w2)
        self.conn_btn = QPushButton("🔌  Connect")
        self.conn_btn.setObjectName("btn_primary")
        self.conn_btn.clicked.connect(self.toggle_db_connect)
        conn_lay.addRow(self.conn_btn)
        self.conn_status = QLabel("Belum terhubung")
        self.conn_status.setStyleSheet("color:#f87171; font-size:11px;")
        conn_lay.addRow(self.conn_status)
        ll.addWidget(conn_box)

        # Tree: Database > Tabel
        lbl = QLabel("Database & Tabel")
        lbl.setObjectName("sec_title")
        ll.addWidget(lbl)

        tree_btns = QHBoxLayout()
        btn_new_db = QPushButton("+ DB")
        btn_new_db.setFixedHeight(26)
        btn_new_db.clicked.connect(self.create_database)
        btn_refresh_tree = QPushButton("⟳")
        btn_refresh_tree.setFixedWidth(32)
        btn_refresh_tree.setFixedHeight(26)
        btn_refresh_tree.clicked.connect(self.refresh_db_tree)
        tree_btns.addWidget(btn_new_db)
        tree_btns.addWidget(btn_refresh_tree)
        tree_btns.addStretch()
        ll.addLayout(tree_btns)

        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderHidden(True)
        self.db_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.db_tree.customContextMenuRequested.connect(self._tree_context_menu)
        self.db_tree.itemClicked.connect(self._on_tree_click)
        ll.addWidget(self.db_tree)

        lay.addWidget(left)

        # ── Panel kanan: sub-tabs ──
        right = QWidget()
        right.setStyleSheet("background:#0f172a;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)

        self.db_tabs = QTabWidget()
        self.db_tabs.setDocumentMode(True)
        rl.addWidget(self.db_tabs)

        # Sub-tab: Browse Data
        self.db_tabs.addTab(self._build_browse_tab(), " 📋  Browse Data ")
        # Sub-tab: SQL Query
        self.db_tabs.addTab(self._build_sql_tab(),    " 🖊️  SQL Query ")
        # Sub-tab: Struktur
        self.db_tabs.addTab(self._build_struct_tab(), " 🏗️  Struktur ")
        # Sub-tab: Export
        self.db_tabs.addTab(self._build_export_tab(), " 💾  Export ")

        lay.addWidget(right)
        return w

    # ── Sub-tab: Browse Data ──────────────────────────────────
    def _build_browse_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Toolbar
        tb = QHBoxLayout()
        self.browse_label = QLabel("Pilih tabel dari panel kiri")
        self.browse_label.setStyleSheet("color:#475569;")
        tb.addWidget(self.browse_label)
        tb.addStretch()

        btn_insert = QPushButton("+ Insert Row")
        btn_insert.setObjectName("btn_success")
        btn_insert.clicked.connect(self.insert_row)

        btn_edit = QPushButton("✎ Edit Row")
        btn_edit.setObjectName("btn_primary")
        btn_edit.clicked.connect(self.edit_row)

        btn_del = QPushButton("✕ Hapus Row")
        btn_del.setObjectName("btn_danger")
        btn_del.clicked.connect(self.delete_row)

        btn_refresh = QPushButton("⟳ Refresh")
        btn_refresh.clicked.connect(self.load_table_data)

        for b in (btn_insert, btn_edit, btn_del, btn_refresh):
            tb.addWidget(b)
        lay.addLayout(tb)

        # Tabel data
        self.data_table = QTableWidget()
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setStyleSheet(
            "QTableWidget { alternate-background-color: #0f172a; }"
        )
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.data_table)

        # Paginasi
        pg = QHBoxLayout()
        self.page_info = QLabel("—")
        self.page_info.setStyleSheet("color:#475569; font-size:11px;")
        pg.addWidget(self.page_info)
        pg.addStretch()
        self.btn_prev = QPushButton("‹ Prev")
        self.btn_prev.setFixedWidth(70)
        self.btn_prev.clicked.connect(self._page_prev)
        self.btn_next = QPushButton("Next ›")
        self.btn_next.setFixedWidth(70)
        self.btn_next.clicked.connect(self._page_next)
        pg.addWidget(self.btn_prev)
        pg.addWidget(self.btn_next)
        lay.addLayout(pg)

        return w

    # ── Sub-tab: SQL Query ────────────────────────────────────
    def _build_sql_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)

        # DB selector
        top = QHBoxLayout()
        top.addWidget(QLabel("Database:"))
        self.sql_db_combo = QComboBox()
        self.sql_db_combo.setFixedWidth(160)
        top.addWidget(self.sql_db_combo)

        btn_run_sql = QPushButton("▶  Jalankan  (F5)")
        btn_run_sql.setObjectName("btn_success")
        btn_run_sql.setShortcut("F5")
        btn_run_sql.clicked.connect(self.run_sql)

        btn_clear = QPushButton("✕ Clear")
        btn_clear.clicked.connect(lambda: self.sql_editor.clear())

        top.addWidget(btn_run_sql)
        top.addWidget(btn_clear)
        top.addStretch()
        lay.addLayout(top)

        splitter = QSplitter(Qt.Vertical)

        # Editor SQL
        self.sql_editor = QTextEdit()
        self.sql_editor.setPlaceholderText(
            "Tulis query SQL di sini...\n\n"
            "Contoh:\n"
            "SELECT * FROM users;\n"
            "SHOW TABLES;\n"
            "INSERT INTO users (name, email) VALUES ('Agung', 'a@b.com');"
        )
        self.sql_editor.setFont(QFont("Consolas", 12))
        self.sql_editor.setStyleSheet("background:#0b1120; color:#e2e8f0; border:1px solid #1e293b;")
        splitter.addWidget(self.sql_editor)

        # Hasil
        result_w = QWidget()
        res_lay = QVBoxLayout(result_w)
        res_lay.setContentsMargins(0, 4, 0, 0)
        self.sql_result_label = QLabel("Hasil query akan muncul di sini")
        self.sql_result_label.setStyleSheet("color:#475569; font-size:11px;")
        res_lay.addWidget(self.sql_result_label)
        self.sql_result_table = QTableWidget()
        self.sql_result_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sql_result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.sql_result_table.horizontalHeader().setStretchLastSection(True)
        res_lay.addWidget(self.sql_result_table)
        splitter.addWidget(result_w)

        splitter.setSizes([200, 300])
        lay.addWidget(splitter)
        return w

    # ── Sub-tab: Struktur ─────────────────────────────────────
    def _build_struct_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)

        # Toolbar
        tb = QHBoxLayout()
        self.struct_label = QLabel("Pilih tabel untuk melihat struktur")
        self.struct_label.setStyleSheet("color:#475569;")
        tb.addWidget(self.struct_label)
        tb.addStretch()
        btn_show_sql = QPushButton("📋 Lihat CREATE SQL")
        btn_show_sql.clicked.connect(self.show_create_sql)
        tb.addWidget(btn_show_sql)
        lay.addLayout(tb)

        self.struct_table = QTableWidget()
        self.struct_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.struct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.struct_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.struct_table)

        # CREATE SQL viewer
        lay.addWidget(QLabel("CREATE TABLE SQL:"))
        self.create_sql_view = QTextEdit()
        self.create_sql_view.setReadOnly(True)
        self.create_sql_view.setFont(QFont("Consolas", 11))
        self.create_sql_view.setFixedHeight(120)
        self.create_sql_view.setStyleSheet("background:#0b1120; color:#4ade80; border:1px solid #1e293b;")
        lay.addWidget(self.create_sql_view)
        return w

    # ── Sub-tab: Export ───────────────────────────────────────
    def _build_export_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Export SQL dump tabel yang sedang aktif:"))
        self.export_preview = QTextEdit()
        self.export_preview.setReadOnly(True)
        self.export_preview.setFont(QFont("Consolas", 11))
        self.export_preview.setStyleSheet("background:#0b1120; color:#94a3b8; border:1px solid #1e293b;")
        lay.addWidget(self.export_preview)

        btn_row = QHBoxLayout()
        btn_gen = QPushButton("🔄 Generate SQL")
        btn_gen.setObjectName("btn_primary")
        btn_gen.clicked.connect(self.generate_export_sql)
        btn_save = QPushButton("💾 Simpan ke File (.sql)")
        btn_save.clicked.connect(self.save_export_sql)
        btn_row.addWidget(btn_gen)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        return w

    # ═══════════════════════════════════════════════════════════
    # SERVER LOGIC
    # ═══════════════════════════════════════════════════════════
    def get_www_path(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")

    def ensure_www_directory(self):
        p = self.get_www_path()
        os.makedirs(p, exist_ok=True)
        idx = os.path.join(p, "index.html")
        if not os.path.exists(idx):
            with open(idx, "w", encoding="utf-8") as f:
                f.write("<!DOCTYPE html><html><head><title>Agg Server</title><meta charset='UTF-8'></head>"
                        "<body style='background:#0f172a;color:#22d3ee;text-align:center;margin-top:15%;font-family:Segoe UI'>"
                        "<h1>⚡ Agg Server Running</h1><p>Tambahkan file/folder ke direktori <code>www</code>.</p></body></html>")

    def refresh_folder_list(self):
        self.folder_list.clear()
        p = self.get_www_path()
        if not os.path.exists(p):
            return
        folders = sorted(f for f in os.listdir(p) if os.path.isdir(os.path.join(p, f)))
        if not folders:
            self.folder_list.addItem("📂 (Belum ada folder)")
        for f in folders:
            item = QListWidgetItem(f"📁  {f}")
            item.setData(Qt.UserRole, f)
            self.folder_list.addItem(item)

    def on_folder_double_click(self, item):
        folder = item.data(Qt.UserRole)
        if not folder:
            return
        if self.server_thread and self.server_thread.is_running:
            webbrowser.open(f"http://localhost:{self.current_port}/{folder}")
        else:
            QMessageBox.warning(self, "Server Belum Aktif", "Start server terlebih dahulu.")

    def toggle_server(self):
        if self.server_thread and self.server_thread.is_running:
            self.server_thread.stop_server()
            self.server_thread = None
            self._set_server_ui(False)
        else:
            port = int(self.port_input.text() or "8000")
            self.current_port = port
            self.server_thread = ServerThread(port, self.get_www_path())
            self.server_thread.status_changed.connect(self.on_server_status_changed)
            if self.server_thread.start_server():
                self._set_server_ui(True)
            else:
                self.server_thread = None

    def _set_server_ui(self, running):
        if running:
            self.run_stop_btn.setText("■  STOP SERVER")
            self.run_stop_btn.setObjectName("stop_btn")
            self.status_indicator.setText("● ONLINE")
            self.status_indicator.setStyleSheet("color:#4ade80; font-weight:bold;")
            self.header_status.setText("● ONLINE")
            self.header_status.setStyleSheet("color:#4ade80; font-weight:600; font-size:12px;")
            self.url_label.setText(f"http://localhost:{self.current_port}")
            self.browser_btn.setEnabled(True)
            self.port_input.setEnabled(False)
        else:
            self.run_stop_btn.setText("▶  START SERVER")
            self.run_stop_btn.setObjectName("run_btn")
            self.status_indicator.setText("● OFFLINE")
            self.status_indicator.setStyleSheet("color:#f87171; font-weight:bold;")
            self.header_status.setText("● OFFLINE")
            self.header_status.setStyleSheet("color:#f87171; font-weight:600; font-size:12px;")
            self.url_label.setText("—")
            self.browser_btn.setEnabled(False)
            self.port_input.setEnabled(True)
        self.run_stop_btn.setStyleSheet(self._style())

    def on_server_status_changed(self, is_running, message):
        self.statusBar().showMessage(message, 4000)

    def open_browser(self):
        if self.server_thread and self.server_thread.is_running:
            webbrowser.open(f"http://localhost:{self.current_port}")

    # ═══════════════════════════════════════════════════════════
    # DATABASE LOGIC
    # ═══════════════════════════════════════════════════════════
    def toggle_db_connect(self):
        if self.db.is_connected():
            self.db.disconnect()
            self.conn_status.setText("Terputus")
            self.conn_status.setStyleSheet("color:#f87171; font-size:11px;")
            self.conn_btn.setText("🔌  Connect")
            self.db_tree.clear()
            self.sql_db_combo.clear()
            self.statusBar().showMessage("Database terputus.", 3000)
        else:
            self.db.host = self.db_host.text().strip() or "localhost"
            self.db.port = int(self.db_port.text().strip() or "3306")
            self.db.user = self.db_user.text().strip() or "root"
            self.db.password = self.db_pass.text()
            result = self.db.connect()
            if result is True:
                self.conn_status.setText(f"✔ Terhubung ke {self.db.host}")
                self.conn_status.setStyleSheet("color:#4ade80; font-size:11px;")
                self.conn_btn.setText("🔌  Disconnect")
                self.refresh_db_tree()
                self.statusBar().showMessage("Berhasil terhubung ke MySQL.", 3000)
            else:
                self.conn_status.setText("Gagal!")
                self.conn_status.setStyleSheet("color:#f87171; font-size:11px;")
                QMessageBox.critical(self, "Koneksi Gagal", str(result))

    def refresh_db_tree(self):
        if not self.db.is_connected():
            return
        self.db_tree.clear()
        self.sql_db_combo.clear()
        dbs = self.db.get_databases()
        system_dbs = {"information_schema", "performance_schema", "mysql", "sys"}
        for db_name in dbs:
            parent = QTreeWidgetItem([f"🗄️  {db_name}"])
            parent.setData(0, Qt.UserRole, ("db", db_name))
            if db_name in system_dbs:
                parent.setForeground(0, QColor("#334155"))
            self.db_tree.addTopLevelItem(parent)
            tables = self.db.get_tables(db_name)
            for tbl in tables:
                child = QTreeWidgetItem([f"   📋  {tbl}"])
                child.setData(0, Qt.UserRole, ("table", db_name, tbl))
                parent.addChild(child)
            parent.setExpanded(db_name not in system_dbs)
            self.sql_db_combo.addItem(db_name)

    def _on_tree_click(self, item, col):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if data[0] == "table":
            _, db, tbl = data
            self._current_db = db
            self._current_table = tbl
            self._page = 0
            self.load_table_data()
            self.load_struct_data()
            self.db_tabs.setCurrentIndex(0)
        elif data[0] == "db":
            self._current_db = data[1]
            self._current_table = None
            self.sql_db_combo.setCurrentText(data[1])

    def _tree_context_menu(self, pos):
        item = self.db_tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        menu = QMenu(self)
        if data[0] == "db":
            db_name = data[1]
            a_new_tbl = menu.addAction("+ Buat Tabel Baru")
            menu.addSeparator()
            a_drop = menu.addAction("🗑 Drop Database")
            action = menu.exec_(self.db_tree.viewport().mapToGlobal(pos))
            if action == a_new_tbl:
                self._current_db = db_name
                self.create_table()
            elif action == a_drop:
                self.drop_database(db_name)
        elif data[0] == "table":
            _, db, tbl = data
            a_browse = menu.addAction("📋 Browse Data")
            a_struct = menu.addAction("🏗 Lihat Struktur")
            menu.addSeparator()
            a_truncate = menu.addAction("⚠ Truncate (Kosongkan)")
            a_drop = menu.addAction("🗑 Drop Tabel")
            action = menu.exec_(self.db_tree.viewport().mapToGlobal(pos))
            if action == a_browse:
                self._current_db = db; self._current_table = tbl
                self._page = 0; self.load_table_data(); self.db_tabs.setCurrentIndex(0)
            elif action == a_struct:
                self._current_db = db; self._current_table = tbl
                self.load_struct_data(); self.db_tabs.setCurrentIndex(2)
            elif action == a_truncate:
                self._current_db = db; self._current_table = tbl; self.truncate_table()
            elif action == a_drop:
                self._current_db = db; self._current_table = tbl; self.drop_table()

    # ── Browse Data ──────────────────────────────────────────
    def load_table_data(self):
        if not self._current_db or not self._current_table:
            return
        self.browse_label.setText(f"🗄️ {self._current_db}  ›  📋 {self._current_table}")
        offset = self._page * self._page_size
        result = self.db.get_table_data(self._current_db, self._current_table,
                                        self._page_size, offset)
        rows = result.get("rows", [])
        total = result.get("total", 0)

        self.data_table.clearContents()
        if not rows:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            self.page_info.setText(f"Total: {total} baris")
            return

        cols = list(rows[0].keys())
        self.data_table.setColumnCount(len(cols))
        self.data_table.setHorizontalHeaderLabels(cols)
        self.data_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, col in enumerate(cols):
                val = row[col]
                item = QTableWidgetItem("" if val is None else str(val))
                if val is None:
                    item.setForeground(QColor("#475569"))
                    item.setText("NULL")
                self.data_table.setItem(r, c, item)

        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        self.page_info.setText(
            f"Halaman {self._page + 1}/{total_pages}  |  "
            f"Baris {offset+1}–{min(offset+self._page_size, total)} dari {total}"
        )
        self.btn_prev.setEnabled(self._page > 0)
        self.btn_next.setEnabled((self._page + 1) * self._page_size < total)

    def _page_prev(self):
        if self._page > 0:
            self._page -= 1
            self.load_table_data()

    def _page_next(self):
        self._page += 1
        self.load_table_data()

    # ── Row CRUD ─────────────────────────────────────────────
    def insert_row(self):
        if not self._current_db or not self._current_table:
            return QMessageBox.warning(self, "Pilih Tabel", "Pilih tabel terlebih dahulu.")
        cols = self.db.get_table_columns(self._current_db, self._current_table)
        dlg = RowEditDialog(cols, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            data = {k: v for k, v in dlg.get_data().items() if v is not None}
            r = self.db.insert_row(self._current_db, self._current_table, data)
            if r.get("success"):
                self.statusBar().showMessage(r["message"], 3000)
                self.load_table_data()
            else:
                QMessageBox.critical(self, "Error", r.get("error", "Gagal"))

    def edit_row(self):
        if not self._current_db or not self._current_table:
            return
        sel = self.data_table.selectedItems()
        if not sel:
            return QMessageBox.information(self, "Edit Row", "Pilih row yang akan diedit.")
        r = sel[0].row()
        cols_headers = [self.data_table.horizontalHeaderItem(c).text()
                        for c in range(self.data_table.columnCount())]
        row_data = {}
        for c, h in enumerate(cols_headers):
            item = self.data_table.item(r, c)
            row_data[h] = None if (item and item.text() == "NULL") else (item.text() if item else "")

        cols = self.db.get_table_columns(self._current_db, self._current_table)
        dlg = RowEditDialog(cols, data=row_data, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_data = dlg.get_data()
            # where = semua kolom lama sebagai identifier
            where = {k: v for k, v in row_data.items() if v is not None}
            res = self.db.update_row(self._current_db, self._current_table, new_data, where)
            if res.get("success"):
                self.statusBar().showMessage(res["message"], 3000)
                self.load_table_data()
            else:
                QMessageBox.critical(self, "Error", res.get("error", "Gagal"))

    def delete_row(self):
        if not self._current_db or not self._current_table:
            return
        sel = self.data_table.selectedItems()
        if not sel:
            return QMessageBox.information(self, "Hapus Row", "Pilih row yang akan dihapus.")
        r = sel[0].row()
        cols_headers = [self.data_table.horizontalHeaderItem(c).text()
                        for c in range(self.data_table.columnCount())]
        where = {}
        for c, h in enumerate(cols_headers):
            item = self.data_table.item(r, c)
            if item and item.text() != "NULL":
                where[h] = item.text()

        reply = QMessageBox.question(self, "Hapus Row", "Yakin ingin menghapus row ini?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        res = self.db.delete_row(self._current_db, self._current_table, where)
        if res.get("success"):
            self.statusBar().showMessage(res["message"], 3000)
            self.load_table_data()
        else:
            QMessageBox.critical(self, "Error", res.get("error", "Gagal"))

    # ── SQL Query ────────────────────────────────────────────
    def run_sql(self):
        query = self.sql_editor.toPlainText().strip()
        if not query:
            return
        if not self.db.is_connected():
            return QMessageBox.warning(self, "Tidak Terhubung", "Hubungkan ke MySQL terlebih dahulu.")
        db = self.sql_db_combo.currentText()
        result = self.db.execute_query(db, query)

        if "error" in result:
            self.sql_result_label.setText(f"❌  Error: {result['error']}")
            self.sql_result_label.setStyleSheet("color:#f87171; font-size:11px;")
            self.sql_result_table.clearContents()
            self.sql_result_table.setRowCount(0)
            self.sql_result_table.setColumnCount(0)
        elif "rows" in result:
            rows = result["rows"]
            cols = result.get("columns", list(rows[0].keys()) if rows else [])
            self.sql_result_label.setText(f"✔  {len(rows)} baris dikembalikan")
            self.sql_result_label.setStyleSheet("color:#4ade80; font-size:11px;")
            self.sql_result_table.setColumnCount(len(cols))
            self.sql_result_table.setHorizontalHeaderLabels(cols)
            self.sql_result_table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                vals = list(row.values()) if isinstance(row, dict) else list(row)
                for c, v in enumerate(vals):
                    self.sql_result_table.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))
            self.refresh_db_tree()
        else:
            self.sql_result_label.setText(
                f"✔  {result.get('message', '')}  — {result.get('affected_rows', 0)} baris terpengaruh"
            )
            self.sql_result_label.setStyleSheet("color:#4ade80; font-size:11px;")
            self.sql_result_table.clearContents()
            self.sql_result_table.setRowCount(0)
            self.sql_result_table.setColumnCount(0)
            self.refresh_db_tree()

    # ── Struktur ─────────────────────────────────────────────
    def load_struct_data(self):
        if not self._current_db or not self._current_table:
            return
        self.struct_label.setText(f"🗄️ {self._current_db}  ›  📋 {self._current_table}")
        cols = self.db.get_table_columns(self._current_db, self._current_table)
        if not cols:
            return
        keys = list(cols[0].keys())
        self.struct_table.setColumnCount(len(keys))
        self.struct_table.setHorizontalHeaderLabels(keys)
        self.struct_table.setRowCount(len(cols))
        for r, col in enumerate(cols):
            for c, k in enumerate(keys):
                v = col.get(k)
                self.struct_table.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))

        sql = self.db.get_create_table_sql(self._current_db, self._current_table)
        self.create_sql_view.setPlainText(sql)

    def show_create_sql(self):
        if not self._current_db or not self._current_table:
            return QMessageBox.information(self, "Info", "Pilih tabel terlebih dahulu.")
        sql = self.db.get_create_table_sql(self._current_db, self._current_table)
        dlg = QDialog(self)
        dlg.setWindowTitle(f"CREATE TABLE `{self._current_table}`")
        dlg.setMinimumSize(600, 320)
        lay = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setFont(QFont("Consolas", 11))
        te.setPlainText(sql)
        te.setStyleSheet("background:#0b1120; color:#4ade80; border:1px solid #1e293b;")
        lay.addWidget(te)
        lay.addWidget(QDialogButtonBox(QDialogButtonBox.Close, accepted=dlg.accept, rejected=dlg.reject))
        dlg.exec_()

    # ── Database/Table DDL ────────────────────────────────────
    def create_database(self):
        if not self.db.is_connected():
            return QMessageBox.warning(self, "Tidak Terhubung", "Hubungkan ke MySQL terlebih dahulu.")
        name, ok = QInputDialog.getText(self, "Buat Database", "Nama Database:")
        if ok and name.strip():
            r = self.db.create_database(name.strip())
            if r.get("success"):
                self.statusBar().showMessage(r["message"], 3000)
                self.refresh_db_tree()
            else:
                QMessageBox.critical(self, "Error", r.get("error", "Gagal"))

    def drop_database(self, db_name=None):
        if not self.db.is_connected():
            return
        name = db_name or self._current_db
        if not name:
            return
        reply = QMessageBox.warning(self, "Drop Database",
                                    f"Hapus database '{name}' beserta semua isinya?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        r = self.db.drop_database(name)
        if r.get("success"):
            self.statusBar().showMessage(r["message"], 3000)
            self.refresh_db_tree()
        else:
            QMessageBox.critical(self, "Error", r.get("error", "Gagal"))

    def create_table(self):
        if not self._current_db:
            return QMessageBox.warning(self, "Pilih Database", "Pilih database terlebih dahulu.")
        dlg = CreateTableDialog(parent=self)
        if dlg.exec_() == QDialog.Accepted:
            name, columns = dlg.get_data()
            if not name:
                return QMessageBox.warning(self, "Nama Tabel", "Nama tabel tidak boleh kosong.")
            if not columns:
                return QMessageBox.warning(self, "Kolom", "Tambahkan minimal satu kolom.")
            r = self.db.create_table(self._current_db, name, columns)
            if r.get("success"):
                self.statusBar().showMessage(r["message"], 3000)
                self.refresh_db_tree()
            else:
                QMessageBox.critical(self, "Error", r.get("error", "Gagal") + f"\n\nSQL:\n{r.get('sql','')}")

    def drop_table(self):
        if not self._current_db or not self._current_table:
            return
        reply = QMessageBox.warning(self, "Drop Tabel",
                                    f"Hapus tabel '{self._current_table}'?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        r = self.db.drop_table(self._current_db, self._current_table)
        if r.get("success"):
            self.statusBar().showMessage(r["message"], 3000)
            self._current_table = None
            self.data_table.clearContents()
            self.data_table.setRowCount(0)
            self.refresh_db_tree()
        else:
            QMessageBox.critical(self, "Error", r.get("error", "Gagal"))

    def truncate_table(self):
        if not self._current_db or not self._current_table:
            return
        reply = QMessageBox.warning(self, "Truncate Tabel",
                                    f"Kosongkan semua data di tabel '{self._current_table}'?",
                                    QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        r = self.db.truncate_table(self._current_db, self._current_table)
        if r.get("success"):
            self.statusBar().showMessage(r["message"], 3000)
            self.load_table_data()
        else:
            QMessageBox.critical(self, "Error", r.get("error", "Gagal"))

    # ── Export ────────────────────────────────────────────────
    def generate_export_sql(self):
        if not self._current_db or not self._current_table:
            return QMessageBox.information(self, "Info", "Pilih tabel terlebih dahulu.")
        sql = self.db.export_table_sql(self._current_db, self._current_table)
        self.export_preview.setPlainText(sql)
        self.statusBar().showMessage("SQL dump berhasil di-generate.", 3000)

    def save_export_sql(self):
        content = self.export_preview.toPlainText()
        if not content.strip():
            return QMessageBox.information(self, "Info", "Generate SQL terlebih dahulu.")
        fname = f"{self._current_table or 'export'}.sql"
        path, _ = QFileDialog.getSaveFileName(self, "Simpan SQL", fname, "SQL Files (*.sql)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.statusBar().showMessage(f"Tersimpan: {path}", 4000)

    # ── closeEvent ────────────────────────────────────────────
    def closeEvent(self, event):
        if self.server_thread and self.server_thread.is_running:
            reply = QMessageBox.question(self, "Keluar",
                                         "Server masih berjalan. Hentikan dan keluar?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.server_thread.stop_server()
            else:
                event.ignore()
                return
        self.db.disconnect()
        event.accept()
