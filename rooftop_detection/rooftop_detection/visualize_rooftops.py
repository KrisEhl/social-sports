"""Small visualizer that loads a GeoJSON and writes an interactive folium map."""
from pathlib import Path
import json
import folium


def visualize(geojson_path: Path, out_html: Path):
    with open(geojson_path, 'r', encoding='utf-8') as f:
        gj = json.load(f)

    # center on first feature
    if len(gj.get('features', [])) == 0:
        raise SystemExit('GeoJSON contains no features')

    coords = gj['features'][0]['geometry']['coordinates'][0][0]
    start_lat = coords[1]
    start_lon = coords[0]

    m = folium.Map(location=[start_lat, start_lon], zoom_start=13)
    folium.GeoJson(gj, name='rooftops').add_to(m)
    m.save(out_html)
    print(f'Wrote map to {out_html}')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('geojson')
    parser.add_argument('--out', default='challenge-02-sports-mapping/results/rooftops_map.html')
    args = parser.parse_args()
    visualize(Path(args.geojson), Path(args.out))
