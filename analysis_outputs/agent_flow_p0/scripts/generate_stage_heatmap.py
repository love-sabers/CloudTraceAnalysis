import argparse
import csv
from pathlib import Path

RESOURCE_COLS = [
    "accelerator_gpu_npu",
    "cpu",
    "dram_hbm_memory",
    "storage_io",
    "network_io",
    "browser_display_graphics",
    "vm_container_isolation",
]


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv")
    parser.add_argument("output_svg")
    parser.add_argument("--title", default="stage-resource proxy heatmap")
    args = parser.parse_args()
    rows = list(csv.DictReader(open(args.input_csv, newline="", encoding="utf-8")))
    cell_w, cell_h = 130, 34
    left, top = 190, 70
    width = left + cell_w * len(RESOURCE_COLS) + 30
    height = top + cell_h * len(rows) + 70
    colors = ["#f7fbff", "#c6dbef", "#6baed6", "#2171b5"]

    def color(value):
        return colors[max(0, min(3, int(round(float(value)))))]

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    svg.append('<rect width="100%" height="100%" fill="white"/>')
    svg.append(f'<text x="20" y="30" font-family="Arial" font-size="20" font-weight="700">{esc(args.title)}</text>')
    svg.append('<text x="20" y="52" font-family="Arial" font-size="12" fill="#555">0=none, 1=low, 2=medium, 3=high; proxy demand from trace events, not direct counters</text>')
    for j, col in enumerate(RESOURCE_COLS):
        x = left + j * cell_w + cell_w / 2
        svg.append(f'<text x="{x}" y="{top - 12}" font-family="Arial" font-size="11" text-anchor="middle">{esc(col.replace("_", " "))}</text>')
    for i, row in enumerate(rows):
        y = top + i * cell_h
        label = f"{row['stage_id']} {row['stage_name']}"
        svg.append(f'<text x="12" y="{y + 22}" font-family="Arial" font-size="12">{esc(label)}</text>')
        for j, col in enumerate(RESOURCE_COLS):
            x = left + j * cell_w
            value = float(row[col])
            svg.append(f'<rect x="{x}" y="{y}" width="{cell_w - 2}" height="{cell_h - 2}" fill="{color(value)}" stroke="#fff"/>')
            svg.append(f'<text x="{x + cell_w / 2}" y="{y + 21}" font-family="Arial" font-size="12" text-anchor="middle" fill="#111">{value:.2f}</text>')
    svg.append("</svg>")
    Path(args.output_svg).write_text("\n".join(svg), encoding="utf-8")


if __name__ == "__main__":
    main()
