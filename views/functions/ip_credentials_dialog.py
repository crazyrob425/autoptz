from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)


class IPCredentialsDialog(QDialog):
    def __init__(self, credential_manager, parent=None):
        super().__init__(parent)
        self.credential_manager = credential_manager
        self.setWindowTitle("Manage IP Camera Credentials")
        self.resize(520, 360)

        root = QVBoxLayout(self)

        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self._on_item_selected)
        root.addWidget(self.list_widget)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Host/IP:"))
        self.host_input = QLineEdit(self)
        row1.addWidget(self.host_input)
        row1.addWidget(QLabel("Port:"))
        self.port_input = QLineEdit(self)
        self.port_input.setText("80")
        row1.addWidget(self.port_input)
        root.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Username:"))
        self.user_input = QLineEdit(self)
        row2.addWidget(self.user_input)
        row2.addWidget(QLabel("Password:"))
        self.pass_input = QLineEdit(self)
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        row2.addWidget(self.pass_input)
        root.addLayout(row2)

        btns = QHBoxLayout()
        self.save_btn = QPushButton("Save / Update", self)
        self.delete_btn = QPushButton("Delete", self)
        self.close_btn = QPushButton("Close", self)
        btns.addWidget(self.save_btn)
        btns.addWidget(self.delete_btn)
        btns.addStretch(1)
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self.save_btn.clicked.connect(self._save)
        self.delete_btn.clicked.connect(self._delete)
        self.close_btn.clicked.connect(self.accept)

        self._reload_list()

    def _reload_list(self):
        self.list_widget.clear()
        for rec in self.credential_manager.get_all():
            item = QListWidgetItem(f"{rec['host']} ({rec['username']})")
            item.setData(32, rec)  # Qt.UserRole
            self.list_widget.addItem(item)

    def _on_item_selected(self, item):
        rec = item.data(32) or {}
        self.host_input.setText(rec.get("host", ""))
        self.port_input.setText(str(rec.get("port", 80)))
        self.user_input.setText(rec.get("username", ""))
        self.pass_input.setText(rec.get("password", ""))

    def _save(self):
        host = self.host_input.text().strip()
        user = self.user_input.text().strip()
        password = self.pass_input.text()
        port_text = self.port_input.text().strip() or "80"

        if not host:
            QMessageBox.information(self, "Information", "Host/IP is required.")
            return
        if not user:
            QMessageBox.information(self, "Information", "Username is required.")
            return

        try:
            port = int(port_text)
        except ValueError:
            QMessageBox.information(self, "Information", "Port must be a number.")
            return

        self.credential_manager.upsert(host=host, username=user, password=password, port=port)
        self._reload_list()

    def _delete(self):
        host = self.host_input.text().strip()
        if not host:
            return
        self.credential_manager.delete(host)
        self._reload_list()
