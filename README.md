# liquipedia-convert

Converter of Liquipedia tournament pages

## Dependencies

Dependencies are listed in the file `pyproject.toml`.

## Usage

* If you have [uv](https://github.com/astral-sh/uv) installed, run `uv run main.py`.
* You can also install the dependencies via pip or another Python package manager, then run `python main.py`.

This starts a web server on localhost, on port 1234 by default (it can be changed with the argument `--port`, e.g. `--port 10000`).

Open `http://localhost:<port>/` in a web browser to access it.
