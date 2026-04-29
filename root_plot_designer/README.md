# Browser-based ROOT Plot Designer (MVP)

HPC 서버에서 실행하고, 로컬 브라우저(SSH port forwarding)로 접속해 ROOT histogram 스타일을 인터랙티브하게 편집하는 Dash 앱입니다.

## Features (MVP)
- ROOT file path 입력 후 object metadata 스캔
- TH1 object 선택/로드 (선택된 object만 실제 load)
- Preview plot
- X/Y axis title, range, log-y, line color, marker style/size, legend text, CMS label 편집
- style template YAML/JSON 저장 및 재적용
- PNG/PDF/SVG export
- 동일 plot 재현용 `make_plot.py` export

## Install
```bash
cd root_plot_designer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run (HPC)
```bash
python app.py --host 0.0.0.0 --port 8050
```

## Access from local PC
```bash
ssh -L 8050:localhost:8050 user@server
```
브라우저에서 `http://localhost:8050`

## Project structure
```
root_plot_designer/
  app.py
  requirements.txt
  README.md
  src/
    io_root.py
    plot_model.py
    style_schema.py
    template_io.py
    export_plot.py
  examples/
    example_style.yaml
    example_usage.md
```

## Notes
- 현재 MVP는 TH1 중심입니다.
- TH2/TGraph parsing 인터페이스는 `io_root.py`에 확장하기 쉽도록 분리되어 있습니다.
- 스타일 변경은 ROOT 재로딩 없이 메모리의 loaded bin data에만 적용됩니다.
