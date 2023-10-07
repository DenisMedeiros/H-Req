import sys
import json
import logging
import requests
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QComboBox, QPushButton, QLineEdit, QTextBrowser, QStatusBar
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtGui import QIcon

REQUEST_TIMEOUT_SEC = 30

class Application:

    def __init__(self, ui_file_name: str, icon_name: str):

        self.app = QApplication(sys.argv)

        # Load main window UI file.
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            raise Exception(f"Cannot open UI file '{ui_file_name}': {ui_file.errorString()}")

        loader = QUiLoader()
        self.window: QMainWindow = loader.load(ui_file)
        ui_file.close()
        if not self.window:
            raise Exception(f"Window cannot be loaded: {loader.errorString()}")

        # Set window icon and style.
        self.window.setObjectName("main")
        self.window.setWindowTitle("H-Req v0.1.0")
        self.window.setWindowIcon(QIcon(icon_name))
        self.window.setStyleSheet("#main { background: #fefae0; }")

        # HTTP Verb config.
        self.http_verbs_combo_box: QComboBox = self.window.frame2.findChild(QComboBox, name="http_verbs_combo_box")
        self.http_verbs_combo_box.addItems(["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "DELETE"])
        self.http_verbs_combo_box.setStyleSheet("#http_verbs_combo_box { background: #d4a373; }")

        # URL line.
        self.url_line_edit: QLineEdit = self.window.frame2.findChild(QLineEdit, name="url_line_edit")
        self.url_line_edit.setStyleSheet("QLineEdit { background: #ffffff; }")
        self.url_line_edit.setPlaceholderText("http://localhost:8000/endpoint/123")

        # Send button config.
        self.send_push_button: QPushButton = self.window.frame2.findChild(QPushButton, name="send_push_button")
        self.send_push_button.setStyleSheet("QPushButton { background: #d4a373; }")
        self.send_push_button.clicked.connect(self.process_request)

        # Response area config.
        self.response_text_edit: QTextBrowser = self.window.frame2.findChild(QTextBrowser, name="response_text_edit")
        self.response_text_edit.setStyleSheet("QTextBrowser { background: #ffffff; }")

        # Status bar config.
        self.status_bar: QStatusBar = self.window.status_bar


    def process_request(self):
        # Get HTTP verb and URL.
        selected_http_verb = self.http_verbs_combo_box.currentText()
        selected_url = self.url_line_edit.text()

        logging.info(f"Processing '{selected_http_verb}' request to URL '{selected_url}'...")
        content_type = "text/html"
        try:
            response = requests.request(selected_http_verb.lower(), selected_url, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
            # Prepare response based on content type.
            if response.headers["Content-Type"].startswith("text/html"):
                # Add result to result area as HTML.
                self.response_text_edit.setHtml(response.text)
            elif response.headers["Content-Type"].startswith("application/json"):
                content_type = "application/json"
                self.response_text_edit.setText(json.dumps(response.json(), indent=4))
        except Exception as err:
            self.response_text_edit.setText(str(err))
            logging.error(f"Request failed: {err}")

        response_size_bytes = len(response.content)
        self.status_bar.showMessage(f"Response: Content-Type={content_type}, Code={response.status_code}, Elapsed={response.elapsed}, Size={response_size_bytes} B.")

    def show(self):
        # Show window
        self.window.show()
        # Finally, exit.
        sys.exit(self.app.exec())


def main():
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    logging.info("Starting app...")
    app = Application("res/ui/main.ui", "res/icons/icon.png")
    app.show()

if __name__ == "__main__":
    main()