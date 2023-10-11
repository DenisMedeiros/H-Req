# H-Req

A simple GUI tool to process HTTP requests written in Python + Qt.

Important notes:

- All UI files are designed using [QtDesigner](https://doc.qt.io/qt-5/qtdesigner-manual.html).
- All icon files are defined as SVG and edited using [Inkscape](https://inkscape.org/).

## Usage

To run the application, follow the steps bellow.

1. Create a Python virtual environment and activate it.

    ```bash
    python3 -m venv venv/
    source venv/bin/activate
    ```

2. Install the [requirements.txt](./requirements.txt).

    ```bash
    python3 -m pip install -r requirements.txt
    ```
    If you want to install additional libraries for deveopment, also install the libraries listed in [requirements-dev.txt](./requirements-dev.txt).

    ```bash
    python3 -m pip install -r requirements-dev.txt
    ```

3. Finally, run the file [hreq.py](./hreq.py).

    ```bash
    python3 hreq.py
    ```

### Command Line Arguments

This application also supports some command line arguments that pre-populate some of the GUI fields. To see all available options, run the help menu:

```bash
python3 hreq.py -h/--help
```

Example of command with some of the fields:

```bash
python3 hreq.py \
    --url 'http://127.0.0.1:5000' \
    --method 'POST' \
    --content-type 'JSON' \
    --body '{"test": "value"}' \
    --headers '{"header1": "value1"}'
```


## Development

For development purposes, there is a small [Flask](https://flask.palletsprojects.com/) web application that can be used to validate the HTTP requests. It can be found in the folder [tests/flask-app/](./tests/flask-app/) and can be run with the following command:

```bash
flask --app tests/flask-app/app.py run
```

This will run a small webserver running locally. You can hit this endpoint at:

```bash
curl http://127.0.0.1:5000
```
