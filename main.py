import sys
import json
import signal
import datetime
import logging
import requests
import argparse

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QComboBox, QPushButton, QLineEdit, QTextBrowser, QStatusBar, QPlainTextEdit, QMenu, QMessageBox
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtGui import QIcon, QAction

REQUEST_TIMEOUT_SEC = 30

def format_json(payload: dict) -> str:
    return json.dumps(payload, indent=4)

class Application:

    def __init__(self, ui_file_name: str, icon_name: str, initial_values: dict = None):

        self.app = QApplication(sys.argv)
        self.app.setStyle("fusion")
        # Make app close when Ctrl+C is sent.
        signal.signal(signal.SIGINT, signal.SIG_DFL)

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

        # File menu config.
        file_menu: QMenu = self.window.main_menu_bar.findChild(QMenu, name="file_menu")
        exit_action = file_menu.findChildren(QAction, name="exit_action")
        file_menu_actions = file_menu.actions()
        open_action: QAction = file_menu_actions[0]
        # The action 1 is simply a separator.
        exit_action: QAction = file_menu_actions[2]
        exit_action.triggered.connect(self.exit)

        # Help menu config.
        help_menu: QMenu = self.window.main_menu_bar.findChild(QMenu, name="help_menu")
        help_menu_actions = help_menu.actions()
        about_action: QAction = help_menu_actions[0]
        about_action.triggered.connect(self.about)


        # HTTP Verb config.
        http_verbs = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
        http_verbs_map = {verb:i for i, verb in enumerate(http_verbs)}
        self.http_verbs_combo_box: QComboBox = self.window.frame2.findChild(QComboBox, name="http_verbs_combo_box")
        self.http_verbs_combo_box.addItems(http_verbs)
        self.http_verbs_combo_box.setStyleSheet("#http_verbs_combo_box { background: #d4a373; }")
        if initial_values is not None and "method" in initial_values:
            self.http_verbs_combo_box.setCurrentIndex(http_verbs_map[initial_values["method"].upper()])

        # Request type config.
        request_content_types = ["PLAIN", "JSON", "XML"]
        request_content_types_map = {verb:i for i, verb in enumerate(request_content_types)}
        self.content_type_combo_box: QComboBox = self.window.frame2.findChild(QComboBox, name="content_type_combo_box")
        self.content_type_combo_box.setStyleSheet("QComboBox { background: #d4a373; }")
        self.content_type_combo_box.addItems(request_content_types)
        if initial_values is not None and "content_type" in initial_values:
            self.content_type_combo_box.setCurrentIndex(request_content_types_map[initial_values["content_type"].upper()])

        # URL line.
        self.url_line_edit: QLineEdit = self.window.frame2.findChild(QLineEdit, name="url_line_edit")
        self.url_line_edit.setStyleSheet("QLineEdit { background: #ffffff; }")
        if initial_values is not None and "url" in initial_values:
            self.url_line_edit.setText(initial_values["url"])
        else:
            self.url_line_edit.setPlaceholderText("http://www.example.com:8080/endpoint/123")
        self.url_line_edit.returnPressed.connect(self.process_request)

        # Send button config.
        self.send_push_button: QPushButton = self.window.frame2.findChild(QPushButton, name="send_push_button")
        self.send_push_button.setStyleSheet("QPushButton { background: #d4a373; }")
        self.send_push_button.clicked.connect(self.process_request)

        # Request body config.
        self.body_text_edit: QPlainTextEdit = self.window.frame2.findChild(QPlainTextEdit, name="body_text_edit")
        if initial_values is not None and "body" in initial_values:
            self.body_text_edit.setPlainText(initial_values["body"])
        else:
            request_body_example = {
                "example1": "value1",
                "example2": 123,
                "example3": {
                    "example4": True
                }
            }
            self.body_text_edit.setPlaceholderText(format_json(request_body_example))

        # Request headers config.
        self.headers_text_edit: QPlainTextEdit = self.window.frame2.findChild(QPlainTextEdit, name="headers_text_edit")
        if initial_values is not None and "headers" in initial_values:
            self.headers_text_edit.setPlainText(initial_values["headers"])
        request_header_example = {
            "Content-Type": "application/json",
            "Authorization": "Bearer 123",
        }
        self.headers_text_edit.setPlaceholderText(format_json(request_header_example))

        # Response area config.
        self.response_text_edit: QTextBrowser = self.window.frame3.findChild(QTextBrowser, name="response_text_edit")
        self.response_text_edit.setStyleSheet("QTextBrowser { background: #ffffff; }")

        # Status bar config.
        self.status_bar: QStatusBar = self.window.status_bar


    def process_request(self):

        # Get HTTP verb and URL.
        selected_http_verb = self.http_verbs_combo_box.currentText()
        selected_url = self.url_line_edit.text()
        logging.info(f"Processing '{selected_http_verb}' request to URL '{selected_url}'...")

        # Define content-type.
        selected_content_type = self.content_type_combo_box.currentText()
        if selected_content_type == "PLAIN":
            request_content_type = "text/plain"
        elif selected_content_type == "JSON":
            request_content_type = "application/json"
        elif selected_content_type == "XML":
            request_content_type = "application/xml "

        # Define data depending on the method.
        data = None
        if selected_http_verb in {"POST", "PUT", "PATCH"}:
            if request_content_type == "text/plain":
                data = self.body_text_edit.toPlainText()
            elif request_content_type == "application/json":
                # Validate JSON.
                data = self.body_text_edit.toPlainText()
            elif request_content_type == "application/xml":
                # Validate XML.
                data = self.body_text_edit.toPlainText()

        headers = {
            "Content-Type": request_content_type
        }

        # Include headers if they are defined.
        raw_headers = self.headers_text_edit.toPlainText()
        if raw_headers.strip():
            try:
                custom_headers = json.loads(raw_headers)
                headers.update(custom_headers)
            except Exception as err:
                error_msg = f"Failed to parse given headers: {err}"
                logging.error(error_msg)
                self.response_text_edit.setText(error_msg)
                return

        response_content_type = "text/html"
        try:
            response = requests.request(selected_http_verb.lower(), selected_url, data=data, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
            # Prepare response based on content type.
            if response.headers["Content-Type"].startswith("text/html"):
                # Add result to result area as HTML.
                self.response_text_edit.setHtml(response.text)
            elif response.headers["Content-Type"].startswith("application/json"):
                response_content_type = "application/json"
                self.response_text_edit.setText(format_json(response.json()))
        except Exception as err:
            error_msg = f"Request failed: {err}"
            logging.error(error_msg)
            self.response_text_edit.setText(error_msg)

        response_size_bytes = len(response.content)
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%Z")
        self.status_bar.showMessage(f"Response: Timestamp={timestamp}, Content-Type={response_content_type}, Code={response.status_code}, Elapsed={response.elapsed}, Size={response_size_bytes} B.")


    def run(self) -> int:
        # Show window
        self.window.show()
        # Finally, exit.
        return self.app.exec()

    def exit(self):
        self.app.quit()

    def about(self):
        about_msg_box = QMessageBox(self.window)
        about_msg_box.setWindowTitle("About")
        text = (
            "This is a simple HTTP request/ response processor project developed in Python + Qt.\n"
            "You can find its source code at: https://github.com/DenisMedeiros/H-Req"
        )
        about_msg_box.setText(text)
        about_msg_box.exec_()


def main():
    logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
    logging.info("Starting app...")

    parser = argparse.ArgumentParser(description='H-Req')
    parser.add_argument('-u','--url', help='URL.', default=None)
    parser.add_argument('-m','--method', help='HTTP method.', default=None)
    parser.add_argument('-t','--content-type', help='HTTP Content type for payload.', default=None)
    # TODO: Better support body and headers.
    parser.add_argument('-b','--body', help='The HTTP request body.', default=None)
    parser.add_argument('-d','--headers', help='The HTTP request headers.', default=None)

    args = vars(parser.parse_args())

    # Check if any parameter was given.
    initial_values = None
    if any([v is not None for v in args.values()]):
        initial_values = args

    app = Application("res/ui/main.ui", "res/icons/main.png", initial_values)
    return_code = app.run()

    logging.info("App finished.")
    sys.exit(return_code)

if __name__ == "__main__":
    main()