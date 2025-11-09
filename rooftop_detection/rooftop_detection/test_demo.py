"""Run the demo pipeline and create a map (fast smoke test)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DETECTOR = ROOT / 'challenge-02-sports-mapping' / 'rooftop_detection' / 'rooftop_detector.py'
RESULTS_DIR = ROOT / 'challenge-02-sports-mapping' / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def run_demo():
    # call the demo
    subprocess.check_call(['python', str(DETECTOR), '--mode', 'demo'])


def find_latest_geojson():
    files = sorted(RESULTS_DIR.glob('berlin_rooftops_demo_*.geojson'), reverse=True)
    if not files:
        # try any produced file
        files = sorted(RESULTS_DIR.glob('berlin_rooftops_*.geojson'), reverse=True)
    return files[0] if files else None


if __name__ == '__main__':
    run_demo()
    out = find_latest_geojson()
    if out:
        print('Demo produced:', out)
    else:
        print('No output found in results/')
