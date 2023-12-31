import os
import sys
import json
import signal
import datetime
import logging
import requests
import argparse

from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QComboBox, QPushButton, QLineEdit, QTextBrowser, QStatusBar, QPlainTextEdit, QMenu,
    QMessageBox, QTreeWidget, QTreeWidgetItem, QFileDialog
)
from PySide6.QtCore import QFile, QIODevice, QCoreApplication, Qt
from PySide6.QtGui import QIcon, QAction, QGuiApplication


REQUEST_TIMEOUT_SEC = 30


class HReqApplication(QApplication):

    def __init__(self, ui_file_name: str, icon_name: str, initial_values: dict = None):
        """Application constructor.

        Args:
            ui_file_name (str): UI file (created on QtDesigner).
            icon_name (str): Filepath for icon.
            initial_values (dict, optional): Initial values to populate app. Defaults to None.
        """

        # This is needed to prevent a ShareOpenGL warning.
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

        # Call QApplication constructor.
        super().__init__(sys.argv)

        # Set style to fusion (needed for a good look-and-feel).
        self.setStyle("fusion")

        # Make app close when Ctrl+C is sent.
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Initialize attributes.
        self.ui_file_name = ui_file_name
        self.icon_name = icon_name
        self.initial_values = initial_values

        # Initialize all UI components.
        self.init_main_window()
        self.init_menus()
        self.init_request_section()
        self.init_response_section()

    def init_main_window(self):
        """Initialize main window.

        Raises:
            ui_file_error: If the UI file cannot be loaded.
            windows_error: If the windows cannot be loaded.
            icon_error: If the icon cannot be loaded.
        """
        # Load main window UI file.
        ui_file = QFile(self.ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            ui_file_error = Exception(f"Cannot open UI file '{self.ui_file_name}': {ui_file.errorString()}")
            raise ui_file_error
        loader = QUiLoader()
        self.window: QMainWindow = loader.load(ui_file)
        ui_file.close()
        if not self.window:
            windows_error = Exception(f"Window cannot be loaded: {loader.errorString()}")
            raise windows_error

        # Set window icon and main style.
        self.window.setObjectName("main")
        self.window.setWindowTitle("H-Req v0.1.0")
        main_icon = QIcon(self.icon_name)
        if main_icon.isNull():
            icon_error = Exception("Main icon cannot be loaded.")
            raise icon_error

        self.window.setWindowIcon(main_icon)
        self.window.setStyleSheet("#main { background: #fefae0; }")

        # Status bar config.
        self.status_bar: QStatusBar = self.window.status_bar

        # Move window to center of the screen.
        center_point = QGuiApplication.primaryScreen().availableGeometry().center()
        frame_geometry = self.window.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.window.move(frame_geometry.topLeft())

    def init_menus(self):
        """Initialize menus.
        """
        # File menu config.
        file_menu: QMenu = self.window.main_menu_bar.findChild(QMenu, name="file_menu")
        exit_action = file_menu.findChildren(QAction, name="exit_action")
        file_menu_actions = file_menu.actions()
        open_action: QAction = file_menu_actions[0]
        open_action.triggered.connect(self.load_request_history)
        save_action: QAction = file_menu_actions[1]
        save_action.triggered.connect(self.save_request_history)
        _: QAction = file_menu_actions[2]  # Separator.
        exit_action: QAction = file_menu_actions[3]
        exit_action.triggered.connect(self.exit)

        # Help menu config.
        help_menu: QMenu = self.window.main_menu_bar.findChild(QMenu, name="help_menu")
        help_menu_actions = help_menu.actions()
        about_action: QAction = help_menu_actions[0]
        about_action.triggered.connect(self.about)

    def init_request_section(self):
        """Initialize the request section. This also includes the request history part.
        """
        # HTTP Verb config.
        http_verbs = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
        self.http_verbs_map = {verb: i for i, verb in enumerate(http_verbs)}
        self.http_verbs_combo_box: QComboBox = self.window.frame2.findChild(QComboBox, name="http_verbs_combo_box")
        self.http_verbs_combo_box.addItems(http_verbs)
        self.http_verbs_combo_box.setStyleSheet("#http_verbs_combo_box { background: #d4a373; }")
        if self.initial_values is not None and "method" in self.initial_values:
            self.http_verbs_combo_box.setCurrentIndex(self.http_verbs_map[self.initial_values["method"].upper()])

        # Requests history config.
        self.request_history_tree: QMenu = self.window.frame1.findChild(QTreeWidget, name="request_history_tree")
        self.request_history_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.request_history_http_verbs = {}
        for http_verb in http_verbs:
            self.request_history_http_verbs[http_verb] = QTreeWidgetItem(self.request_history_tree, [http_verb])
        self.request_history_tree.itemSelectionChanged.connect(self.on_request_history_selection_changed)

        self.delete_history_entry_push_button: QPushButton = self.window.frame1.findChild(
            QPushButton, name="delete_history_entry_push_button")
        self.delete_history_entry_push_button.setEnabled(False)
        self.delete_history_entry_push_button.setStyleSheet((
            "QPushButton { background: #d4a373; }"
            "QPushButton:disabled { background: #f8f1e9; color: #555555; }"

        ))
        self.delete_history_entry_push_button.clicked.connect(self.delete_request_history_entry)

        # Request type config.
        request_content_types = ["PLAIN", "JSON", "XML"]
        self.request_content_types_map = {verb: i for i, verb in enumerate(request_content_types)}
        self.content_type_combo_box: QComboBox = self.window.frame2.findChild(QComboBox, name="content_type_combo_box")
        self.content_type_combo_box.setStyleSheet("QComboBox { background: #d4a373; }")
        self.content_type_combo_box.addItems(request_content_types)
        if self.initial_values is not None and "content_type" in self.initial_values:
            self.content_type_combo_box.setCurrentIndex(
                self.request_content_types_map[self.initial_values["content_type"].upper()])

        # URL line.
        self.url_line_edit: QLineEdit = self.window.frame2.findChild(QLineEdit, name="url_line_edit")
        self.url_line_edit.setStyleSheet("QLineEdit { background: #ffffff; }")
        if self.initial_values is not None and "url" in self.initial_values:
            self.url_line_edit.setText(self.initial_values["url"])
        else:
            self.url_line_edit.setPlaceholderText("http://www.example.com:8080/endpoint/123")
        self.url_line_edit.returnPressed.connect(self.process_request)

        # Send button config.
        self.send_push_button: QPushButton = self.window.frame2.findChild(QPushButton, name="send_push_button")
        self.send_push_button.setStyleSheet("QPushButton { background: #d4a373; }")
        self.send_push_button.clicked.connect(self.process_request)

        # Request body config.
        self.body_text_edit: QPlainTextEdit = self.window.frame2.findChild(QPlainTextEdit, name="body_text_edit")
        if self.initial_values is not None and "body" in self.initial_values:
            self.body_text_edit.setPlainText(self.initial_values["body"])
        else:
            request_body_example = {
                "example1": "value1",
                "example2": 123,
                "example3": {
                    "example4": True
                }
            }
            self.body_text_edit.setPlaceholderText(json_to_str(request_body_example))

        # Request headers config.
        self.headers_text_edit: QPlainTextEdit = self.window.frame2.findChild(QPlainTextEdit, name="headers_text_edit")
        if self.initial_values is not None and "headers" in self.initial_values:
            self.headers_text_edit.setPlainText(self.initial_values["headers"])
        request_header_example = {
            "Content-Type": "application/json",
            "Authorization": "Bearer 123",
        }
        self.headers_text_edit.setPlaceholderText(json_to_str(request_header_example))

    def init_response_section(self):
        """Initialize response section.
        """
        # Response area config.
        self.response_text_edit: QTextBrowser = self.window.frame3.findChild(QTextBrowser, name="response_text_edit")
        self.response_text_edit.setStyleSheet("QTextBrowser { background: #ffffff; }")
        self.response_text_edit.setPlaceholderText("Response will show up here...")

    def process_request(self):
        """Process the request (when the send button is pressed).
        """

        # Get HTTP verb and URL.
        selected_http_verb = self.http_verbs_combo_box.currentText()
        selected_url = self.url_line_edit.text()
        logging.info(f"Processing '{selected_http_verb}' request to URL '{selected_url}'...")

        # Define content-type.
        content_type_text = self.content_type_combo_box.currentText()
        if content_type_text == "PLAIN":
            request_content_type = "text/plain"
        elif content_type_text == "JSON":
            request_content_type = "application/json"
        elif content_type_text == "XML":
            request_content_type = "application/xml "

        # Define data depending on the method.
        body_text = self.body_text_edit.toPlainText()
        data = None
        if body_text.strip():
            data = body_text
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
        headers_text = self.headers_text_edit.toPlainText()
        if headers_text.strip():
            try:
                custom_headers = json.loads(headers_text)
                headers.update(custom_headers)
            except Exception as err:
                error_msg = f"Failed to parse given headers: {err}"
                logging.error(error_msg)
                self.response_text_edit.setText(error_msg)
                return

        response_content_type = "text/html"
        timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S%Z")
        try:
            response = requests.request(
                selected_http_verb.lower(), selected_url, data=data, headers=headers, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
            # Prepare response based on content type.
            if response.headers["Content-Type"].startswith("text/html"):
                # Add result to result area as HTML.
                self.response_text_edit.setHtml(response.text)
            elif response.headers["Content-Type"].startswith("application/json"):
                response_content_type = "application/json"
                self.response_text_edit.setText(json_to_str(response.json()))
            response_size_bytes = len(response.content)
            self.status_bar.showMessage((
                f"Response: Timestamp={timestamp}, Content-Type={response_content_type}, "
                f"Code={response.status_code}, Elapsed={response.elapsed}, Size={response_size_bytes} B."
            ))

            # Save this request in the request history.
            next_request_id = self.request_history_http_verbs[selected_http_verb].childCount() + 1
            request_history_entry = QTreeWidgetItem(
                self.request_history_http_verbs[selected_http_verb], [f"{selected_http_verb} #{next_request_id}"])
            request_history_entry._request_fields = {
                "selected_http_verb": selected_http_verb,
                "selected_url": selected_url,
                "content_type_text": content_type_text,
                "body_text": body_text,
                "headers_text": headers_text,
            }
        except Exception as err:
            error_msg = f"Request failed: {err}"
            logging.error(error_msg)
            self.response_text_edit.setText(error_msg)
            self.status_bar.showMessage(error_msg)

    def run(self) -> int:
        """Run the application.

        Returns:
            int: The return code of from the Qt app.
        """
        # Show window
        self.window.show()
        # Finally, exit.
        return self.exec()

    def exit(self):
        """Closes the application gracefully.
        """
        logging.info("Quitting app...")
        self.quit()

    def about(self):
        """Shows the about message box.
        """
        about_msg_box = QMessageBox(self.window)
        about_msg_box.setWindowTitle("About")
        text = (
            "This is a simple HTTP request/ response processor project developed in Python + Qt.\n"
            "You can find its source code at: https://github.com/DenisMedeiros/H-Req"
        )
        about_msg_box.setText(text)
        about_msg_box.exec_()

    def on_request_history_selection_changed(self):
        """Changes the request session when an item in the request history is selected.
        """
        selected_request: QTreeWidgetItem = self.request_history_tree.selectedItems()[0]
        if not hasattr(selected_request, "_request_fields"):
            self.delete_history_entry_push_button.setEnabled(False)
            return
        self.delete_history_entry_push_button.setEnabled(True)
        request_fields = selected_request._request_fields
        # Since the request fields is present, update the app fields.
        self.http_verbs_combo_box.setCurrentIndex(self.http_verbs_map[request_fields["selected_http_verb"]])
        self.url_line_edit.setText(request_fields["selected_url"])
        self.content_type_combo_box.setCurrentIndex(
            self.request_content_types_map[request_fields["content_type_text"]])
        self.body_text_edit.setPlainText(request_fields["body_text"])
        self.headers_text_edit.setPlainText(request_fields["headers_text"])

    def delete_request_history_entry(self):
        """Deletes an item from the request history when the delete button is pressed.
        """
        selected_request: QTreeWidgetItem = self.request_history_tree.selectedItems()[0]
        if not hasattr(selected_request, "_request_fields"):
            self.delete_history_entry_push_button.setEnabled(False)
            return
        http_verb_item: QTreeWidgetItem = selected_request.parent()
        http_verb = http_verb_item.text(0)
        http_verb_item.removeChild(selected_request)
        # Fix names.
        for i in range(http_verb_item.childCount()):
            http_verb_item.child(i).setText(0, f"{http_verb} #{i+1}")

    def save_request_history(self):
        """Saves the request history into a file.
        """
        # Prepare data to be saved.
        # TODO: Make sure no requests are repeated.
        data = {}
        for http_verb in self.http_verbs_map:
            http_verb_tree_item: QTreeWidgetItem = self.request_history_http_verbs[http_verb]
            # data[http_verb] = [child._request_fields for child in http_verb_tree_item.takeChildren()]
            data[http_verb] = [
                http_verb_tree_item.child(i)._request_fields for i in range(http_verb_tree_item.childCount())]

        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_dialog = QFileDialog()
        # Obtain file path.
        file_path, _ = file_dialog.getSaveFileName(
            self.window, "Save File", "", "JSON Files (*.json);;All Files (*)", options=options)

        # Save request history
        if file_path:
            with open(file_path, "w") as file:
                json.dump(data, file, indent=4)

    def load_request_history(self):
        """Loads the request history from a file.
        """
        # Prepare data to be saved.
        # TODO: Make sure no requests are repeated.
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_dialog = QFileDialog()
        # Obtain file path.
        file_path, _ = file_dialog.getOpenFileName(
            self.window, "Open File", "", "JSON Files (*.json);;All Files (*)", options=options)
        # Load request history.
        if file_path:
            with open(file_path, "r") as file:
                data = json.load(file)
        else:
            return
        # Populate request history section (overwrite everything).
        for http_verb, values in data.items():
            for entry in values:
                next_request_id = self.request_history_http_verbs[http_verb].childCount() + 1
                request_history_entry = QTreeWidgetItem(
                    self.request_history_http_verbs[http_verb], [f"{http_verb} #{next_request_id}"])
                request_history_entry._request_fields = {
                    "selected_http_verb": entry["selected_http_verb"],
                    "selected_url": entry["selected_url"],
                    "content_type_text": entry["content_type_text"],
                    "body_text": entry["body_text"],
                    "headers_text": entry["headers_text"],
                }


def main():
    """Main function.
    """
    logging.basicConfig(
        encoding='utf-8', level=logging.DEBUG,
        format="%(asctime)s :: %(levelname)s :: %(name)s :: %(message)s")
    logging.info("Starting app...")
    parser = argparse.ArgumentParser(description='H-Req')
    parser.add_argument('-u', '--url', help='URL.', default=None)
    parser.add_argument('-m', '--method', help='HTTP method.', default=None)
    parser.add_argument('-t', '--content-type', help='HTTP Content type for payload.', default=None)

    # TODO: Better support body and headers.
    parser.add_argument('-b', '--body', help='The HTTP request body.', default=None)
    parser.add_argument('-d', '--headers', help='The HTTP request headers.', default=None)
    args = vars(parser.parse_args())

    # Check if any parameter was given.
    initial_values = None
    if any([v is not None for v in args.values()]):
        initial_values = args

    # Get app directory and define UI files and icon.
    app_dir = os.path.dirname(os.path.realpath(__file__))
    main_ui = os.path.join(app_dir, "res", "ui", "main.ui")
    main_icon = os.path.join(app_dir, "res", "icons", "main.svg")

    # Run app.
    try:
        app = HReqApplication(main_ui, main_icon, initial_values)
        return_code = app.run()
        logging.info("App gracefully finished.")
        sys.exit(return_code)
    except Exception as err:
        logging.error(f"App finished due to some error: {err}")


def json_to_str(payload: dict) -> str:
    """Formats a JSON payload to a formatted string.

    Args:
        payload (dict): The JSON payload.

    Returns:
        str: The formatted JSON payload.
    """
    return json.dumps(payload, indent=4)


if __name__ == "__main__":
    main()
