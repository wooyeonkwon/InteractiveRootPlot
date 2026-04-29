# Example usage

```bash
cd root_plot_designer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py --host 0.0.0.0 --port 8050
```

On local machine:

```bash
ssh -L 8050:localhost:8050 user@hpc.server
```

Open `http://localhost:8050` in browser.
