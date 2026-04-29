from __future__ import annotations

import argparse
import base64
from pathlib import Path

import dash
from dash import Dash, Input, Output, State, dcc, html

from src.export_plot import build_repro_script, export_layout_matplotlib, render_layout_png_bytes
from src.io_root import list_objects, load_th1
from src.layout_schema import LabelConfig, LayoutModel, PadConfig, PlotObjectConfig
from src.plot_model import Hist1DData
from src.template_io import dump_template, load_template

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H2("ROOT Plot Designer (MVP)"),
    dcc.Store(id="loaded-hists", data={}),
    dcc.Store(id="layout-store", data=LayoutModel().to_dict()),
    html.Div([html.Label("ROOT file path"), dcc.Input(id="root-path", type="text", style={"width": "60%"}), html.Button("Scan Objects", id="scan-btn")]),
    dcc.Dropdown(id="object-dropdown", placeholder="Select ROOT object"),
    html.Button("Load Object", id="load-btn"),
    html.Div(id="status"),
    html.Hr(),
    html.Div([html.Label("Canvas width"), dcc.Input(id="canvas-width", type="number", value=800), html.Label("Canvas height"), dcc.Input(id="canvas-height", type="number", value=600)]),
    html.Div([html.Button("Add Pad", id="add-pad"), html.Button("Remove Last Pad", id="rm-pad")]),
    html.Div([html.Label("Pad ID"), dcc.Input(id="pad-id", type="text", value="pad1"), html.Label("Coords x1,y1,x2,y2"), dcc.Input(id="pad-coords", type="text", value="0.12,0.12,0.95,0.92"), dcc.Checklist(options=[{"label":"logx","value":"logx"},{"label":"logy","value":"logy"},{"label":"logz","value":"logz"}], id="pad-logs", value=[])]),
    html.Div([html.Label("X title"), dcc.Input(id="x-title", type="text"), html.Label("Y title"), dcc.Input(id="y-title", type="text"), html.Label("X min"), dcc.Input(id="x-min", type="number"), html.Label("X max"), dcc.Input(id="x-max", type="number"), html.Label("Y min"), dcc.Input(id="y-min", type="number"), html.Label("Y max"), dcc.Input(id="y-max", type="number")]),
    html.Div([html.Label("Draw option"), dcc.Input(id="draw-option", value="E1"), html.Label("Legend"), dcc.Input(id="legend-label")]),
    html.Button("Assign Selected Object to Pad", id="assign-obj"),
    html.Hr(),
    html.Div([html.Label("Label text"), dcc.Input(id="label-text", value="CMS Preliminary"), html.Label("Target pad"), dcc.Input(id="label-target", value="pad1"), html.Label("Position x,y"), dcc.Input(id="label-pos", value="0.02,0.98"), html.Label("Font size"), dcc.Input(id="label-size", type="number", value=11), html.Label("Align"), dcc.Dropdown(id="label-align", options=[{"label":x,"value":x} for x in ["left","center","right"]], value="left")]),
    html.Button("Add Label", id="add-label"),
    html.Img(id="plot-preview", style={"maxWidth": "100%", "border": "1px solid #ddd"}),
    html.Hr(),
    html.Button("Download layout.yaml", id="save-layout-btn"), dcc.Download(id="download-layout"),
    dcc.Upload(id="upload-layout", children=html.Button("Load layout.yaml/json"), multiple=False),
    html.Button("Export PNG", id="export-png"), html.Button("Export PDF", id="export-pdf"), html.Button("Export SVG", id="export-svg"), dcc.Download(id="download-export"),
    html.Button("Export make_plot.py", id="export-script"), dcc.Download(id="download-script"),
])

@app.callback(Output("object-dropdown", "options"), Input("scan-btn", "n_clicks"), State("root-path", "value"), prevent_initial_call=True)
def scan(_, root_path):
    metas = list_objects(root_path) if root_path else []
    return [{"label": f"{m.name} [{m.class_name}]", "value": m.name} for m in metas]

@app.callback(Output("loaded-hists", "data"), Input("load-btn", "n_clicks"), State("root-path", "value"), State("object-dropdown", "value"), State("loaded-hists", "data"), prevent_initial_call=True)
def load_hist(_, root_path, object_name, loaded):
    if not(root_path and object_name):
        return loaded
    hist = load_th1(root_path, object_name)
    loaded = loaded or {}
    loaded[object_name] = hist.to_payload()
    return loaded

@app.callback(Output("layout-store", "data"), Input("add-pad", "n_clicks"), Input("rm-pad", "n_clicks"), Input("assign-obj", "n_clicks"), Input("add-label", "n_clicks"), State("layout-store", "data"), State("pad-id", "value"), State("pad-coords", "value"), State("pad-logs", "value"), State("object-dropdown", "value"), State("draw-option", "value"), State("legend-label", "value"), State("label-text", "value"), State("label-target", "value"), State("label-pos", "value"), State("label-size", "value"), State("label-align", "value"), State("canvas-width", "value"), State("canvas-height", "value"), State("x-title", "value"), State("y-title", "value"), State("x-min", "value"), State("x-max", "value"), State("y-min", "value"), State("y-max", "value"), prevent_initial_call=True)
def update_layout(a,b,c,d,layout_raw,pad_id,pad_coords,pad_logs,obj,draw_opt,legend,label_text,label_target,label_pos,label_size,label_align,cw,ch,x_title,y_title,x_min,x_max,y_min,y_max):
    layout = LayoutModel.from_dict(layout_raw)
    layout.canvas.width = int(cw or 800)
    layout.canvas.height = int(ch or 600)
    trig = dash.ctx.triggered_id
    if trig == "add-pad":
        layout.pads.append(PadConfig(pad_id=f"pad{len(layout.pads)+1}"))
    elif trig == "rm-pad" and len(layout.pads) > 1:
        layout.pads.pop()
    elif trig == "assign-obj" and obj:
        coords = [float(x.strip()) for x in (pad_coords or "0.12,0.12,0.95,0.92").split(",")]
        p = next((x for x in layout.pads if x.pad_id == pad_id), None)
        if p is None:
            p = PadConfig(pad_id=pad_id or f"pad{len(layout.pads)+1}")
            layout.pads.append(p)
        p.coords = coords
        logs = set(pad_logs or [])
        p.logx, p.logy, p.logz = ("logx" in logs), ("logy" in logs), ("logz" in logs)
        p.x_title = x_title or ""
        p.y_title = y_title or ""
        p.x_min, p.x_max = x_min, x_max
        p.y_min, p.y_max = y_min, y_max
        p.objects.append(PlotObjectConfig(root_object_path=obj, draw_option=draw_opt or "E1", legend_label=legend or obj, style={"line_color": "#1f77b4", "marker_size": 7, "marker_style": "circle"}))
    elif trig == "add-label":
        pos = [float(x.strip()) for x in (label_pos or "0.02,0.98").split(",")]
        layout.labels.append(LabelConfig(text=label_text or "", target_pad=label_target or "pad1", position=pos, font_size=float(label_size or 11), alignment=label_align or "left"))
    return layout.to_dict()

@app.callback(Output("plot-preview", "src"), Input("loaded-hists", "data"), Input("layout-store", "data"))
def preview(loaded, layout_raw):
    layout = LayoutModel.from_dict(layout_raw)
    hists = {k: Hist1DData.from_payload(v) for k, v in (loaded or {}).items()}
    png_bytes = render_layout_png_bytes(hists, layout)
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"

@app.callback(Output("download-layout", "data"), Input("save-layout-btn", "n_clicks"), State("layout-store", "data"), prevent_initial_call=True)
def save_layout(_, data):
    return dict(content=dump_template(data, "yaml"), filename="layout.yaml")

@app.callback(
    Output("canvas-width", "value"),
    Output("canvas-height", "value"),
    Output("layout-store", "data"),
    Input("upload-layout", "contents"),
    prevent_initial_call=True,
)
def load_layout(contents):
    raw = base64.b64decode(contents.split(',',1)[1]).decode('utf-8')
    l = LayoutModel.from_dict(load_template(raw))
    return l.canvas.width, l.canvas.height, l.to_dict()

@app.callback(Output("download-export", "data"), Input("export-png", "n_clicks"), Input("export-pdf", "n_clicks"), Input("export-svg", "n_clicks"), State("layout-store", "data"), State("loaded-hists", "data"), State("root-path", "value"), prevent_initial_call=True)
def export(p1,p2,p3,layout_raw,loaded,root_path):
    ext = {"export-png":"png","export-pdf":"pdf","export-svg":"svg"}[dash.ctx.triggered_id]
    layout = LayoutModel.from_dict(layout_raw)
    hists = {k:Hist1DData.from_payload(v) for k,v in (loaded or {}).items()}
    required_paths = {obj.root_object_path for pad in layout.pads for obj in pad.objects}
    if root_path:
        for path in required_paths:
            if path not in hists:
                try:
                    hists[path] = load_th1(root_path, path)
                except Exception:
                    pass
    if not any(path in hists for path in required_paths):
        raise dash.exceptions.PreventUpdate
    out = Path('exports')/f'layout_export.{ext}'
    export_layout_matplotlib(hists, layout, str(out))
    return dcc.send_file(str(out))

@app.callback(Output("download-script", "data"), Input("export-script", "n_clicks"), State("root-path", "value"), State("layout-store", "data"), prevent_initial_call=True)
def script(_, root_path, layout_raw):
    if not root_path:
        raise dash.exceptions.PreventUpdate
    return dict(content=build_repro_script(root_path, LayoutModel.from_dict(layout_raw)), filename="make_plot.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8050, type=int)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    app.run(host=args.host, port=args.port, debug=args.debug)
