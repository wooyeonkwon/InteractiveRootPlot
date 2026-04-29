from __future__ import annotations

import argparse
import base64
from pathlib import Path

import dash
from dash import Dash, Input, Output, State, dcc, html
import plotly.graph_objects as go

from src.export_plot import build_repro_script, export_hist1_matplotlib
from src.io_root import list_objects, load_th1
from src.plot_model import Hist1DData, marker_symbol_map
from src.style_schema import PlotStyle
from src.template_io import dump_template, load_template


app = Dash(__name__)
server = app.server

app.layout = html.Div(
    [
        html.H2("ROOT Plot Designer (MVP)"),
        html.Div([
            html.Label("ROOT file path"),
            dcc.Input(id="root-path", type="text", placeholder="/path/to/file.root", style={"width": "60%"}),
            html.Button("Scan Objects", id="scan-btn"),
        ]),
        dcc.Store(id="loaded-hist"),
        dcc.Store(id="style-store", data=PlotStyle().to_dict()),
        html.Hr(),
        dcc.Dropdown(id="object-dropdown", placeholder="Select TH1 object"),
        html.Button("Load TH1", id="load-btn"),
        html.Div(id="status", style={"marginTop": "10px", "color": "#2c3e50"}),
        html.Hr(),
        html.Div([
            html.Div([
                html.Label("X title"), dcc.Input(id="x-title", type="text"),
                html.Label("Y title"), dcc.Input(id="y-title", type="text"),
                html.Label("X min"), dcc.Input(id="x-min", type="number"),
                html.Label("X max"), dcc.Input(id="x-max", type="number"),
                html.Label("Y min"), dcc.Input(id="y-min", type="number"),
                html.Label("Y max"), dcc.Input(id="y-max", type="number"),
                dcc.Checklist(options=[{"label": "log Y", "value": "logy"}], id="logy", value=[]),
                html.Label("Line color"), dcc.Input(id="line-color", type="text", value="#1f77b4"),
                html.Label("Marker style"),
                dcc.Dropdown(id="marker-style", options=[{"label": x, "value": x} for x in ["circle", "square", "diamond", "cross", "x", "triangle-up"]], value="circle"),
                html.Label("Marker size"), dcc.Input(id="marker-size", type="number", value=7),
                html.Label("Legend text"), dcc.Input(id="legend-text", type="text"),
                html.Label("CMS label"), dcc.Input(id="cms-label", type="text", value="CMS Preliminary"),
            ], style={"display": "grid", "gridTemplateColumns": "150px 1fr", "gap": "6px", "maxWidth": "540px"}),
            dcc.Graph(id="plot-preview", style={"height": "600px"}),
        ], style={"display": "grid", "gridTemplateColumns": "560px 1fr", "gap": "20px"}),
        html.Hr(),
        html.Button("Download style.yaml", id="save-style-btn"),
        dcc.Download(id="download-style"),
        dcc.Upload(id="upload-style", children=html.Button("Load style.yaml/json"), multiple=False),
        html.Button("Export PNG", id="export-png"),
        html.Button("Export PDF", id="export-pdf"),
        html.Button("Export SVG", id="export-svg"),
        dcc.Download(id="download-export"),
        html.Button("Export make_plot.py", id="export-script"),
        dcc.Download(id="download-script"),
    ],
    style={"padding": "20px"},
)


@app.callback(
    Output("object-dropdown", "options"),
    Output("status", "children"),
    Input("scan-btn", "n_clicks"),
    State("root-path", "value"),
    prevent_initial_call=True,
)
def scan_objects(_, root_path):
    if not root_path:
        return [], "Please provide ROOT file path"
    metas = list_objects(root_path)
    options = [{"label": f"{m.name} [{m.class_name}]", "value": m.name} for m in metas if m.class_name.startswith("TH1")]
    return options, f"Found {len(metas)} objects, TH1 selectable: {len(options)}"


@app.callback(
    Output("loaded-hist", "data"),
    Input("load-btn", "n_clicks"),
    State("root-path", "value"),
    State("object-dropdown", "value"),
    prevent_initial_call=True,
)
def load_hist(_, root_path, object_name):
    if not (root_path and object_name):
        return None
    hist = load_th1(root_path, object_name)
    return hist.to_payload()


@app.callback(
    Output("style-store", "data"),
    Input("x-title", "value"), Input("y-title", "value"),
    Input("x-min", "value"), Input("x-max", "value"),
    Input("y-min", "value"), Input("y-max", "value"),
    Input("logy", "value"), Input("line-color", "value"),
    Input("marker-style", "value"), Input("marker-size", "value"),
    Input("legend-text", "value"), Input("cms-label", "value"),
)
def update_style(x_title, y_title, x_min, x_max, y_min, y_max, logy, line_color, marker_style, marker_size, legend_text, cms_label):
    return PlotStyle(
        x_title=x_title or "",
        y_title=y_title or "",
        x_min=x_min, x_max=x_max,
        y_min=y_min, y_max=y_max,
        log_y="logy" in (logy or []),
        line_color=line_color or "#1f77b4",
        marker_style=marker_style or "circle",
        marker_size=marker_size or 7,
        legend_text=legend_text or "",
        cms_label=cms_label or "CMS Preliminary",
    ).to_dict()


@app.callback(
    Output("plot-preview", "figure"),
    Input("loaded-hist", "data"),
    Input("style-store", "data"),
)
def render_plot(hist_payload, style_raw):
    fig = go.Figure()
    if not hist_payload:
        fig.update_layout(title="Load TH1 to preview")
        return fig
    hist = Hist1DData.from_payload(hist_payload)
    style = PlotStyle.from_dict(style_raw)
    centers = 0.5 * (hist.edges[:-1] + hist.edges[1:])
    fig.add_trace(
        go.Scatter(
            x=centers,
            y=hist.values,
            error_y={"type": "data", "array": hist.errors, "visible": True},
            mode="markers+lines",
            marker={"symbol": marker_symbol_map(style.marker_style), "size": style.marker_size, "color": style.line_color},
            line={"color": style.line_color},
            name=style.legend_text or hist.name,
        )
    )
    fig.update_layout(
        template="plotly_white",
        xaxis_title=style.x_title,
        yaxis_title=style.y_title,
        yaxis_type="log" if style.log_y else "linear",
        annotations=[{"x": 0.01, "y": 0.99, "xref": "paper", "yref": "paper", "text": style.cms_label, "showarrow": False}],
    )
    fig.update_xaxes(range=[style.x_min, style.x_max] if style.x_min is not None and style.x_max is not None else None)
    fig.update_yaxes(range=[style.y_min, style.y_max] if style.y_min is not None and style.y_max is not None and not style.log_y else None)
    return fig


@app.callback(
    Output("download-style", "data"),
    Input("save-style-btn", "n_clicks"),
    State("style-store", "data"),
    prevent_initial_call=True,
)
def save_style(_, style):
    content = dump_template(style, fmt="yaml")
    return dict(content=content, filename="style.yaml")


@app.callback(
    Output("x-title", "value"), Output("y-title", "value"),
    Output("x-min", "value"), Output("x-max", "value"),
    Output("y-min", "value"), Output("y-max", "value"),
    Output("logy", "value"), Output("line-color", "value"),
    Output("marker-style", "value"), Output("marker-size", "value"),
    Output("legend-text", "value"), Output("cms-label", "value"),
    Input("upload-style", "contents"),
    prevent_initial_call=True,
)
def load_style(contents):
    if not contents:
        raise dash.exceptions.PreventUpdate
    encoded = contents.split(",", 1)[1]
    raw = base64.b64decode(encoded).decode("utf-8")
    style = PlotStyle.from_dict(load_template(raw))
    return style.x_title, style.y_title, style.x_min, style.x_max, style.y_min, style.y_max, (["logy"] if style.log_y else []), style.line_color, style.marker_style, style.marker_size, style.legend_text, style.cms_label


@app.callback(
    Output("download-export", "data"),
    Input("export-png", "n_clicks"), Input("export-pdf", "n_clicks"), Input("export-svg", "n_clicks"),
    State("loaded-hist", "data"), State("style-store", "data"),
    prevent_initial_call=True,
)
def export_plot(png_clicks, pdf_clicks, svg_clicks, hist_payload, style_raw):
    trigger = dash.ctx.triggered_id
    if not hist_payload:
        raise dash.exceptions.PreventUpdate
    ext = {"export-png": "png", "export-pdf": "pdf", "export-svg": "svg"}[trigger]
    hist = Hist1DData.from_payload(hist_payload)
    style = PlotStyle.from_dict(style_raw)
    out_path = Path("exports") / f"{hist.name}.{ext}"
    export_hist1_matplotlib(hist, style, str(out_path))
    return dcc.send_file(str(out_path))


@app.callback(
    Output("download-script", "data"),
    Input("export-script", "n_clicks"),
    State("root-path", "value"), State("object-dropdown", "value"), State("style-store", "data"),
    prevent_initial_call=True,
)
def export_script(_, root_path, object_name, style_raw):
    if not (root_path and object_name):
        raise dash.exceptions.PreventUpdate
    script = build_repro_script(root_path, object_name, PlotStyle.from_dict(style_raw))
    return dict(content=script, filename="make_plot.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8050, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
