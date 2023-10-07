# H-Req

A simple GUI tool to process HTTP requests (Python + Qt).

UI files are designed using Qt Designer.

## Usage

### Command Line

```
python3 main.py -u http://127.0.0.1:5000 -m POST -t JSON -b '{"test": "value"}' -d '{"header1": "value1"}'
```

## Development

Running Flask App:

```
flask --app tests/flask-app/main.py run
```