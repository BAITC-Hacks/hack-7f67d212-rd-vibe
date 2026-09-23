"""Portable one-command launcher; creates a project-local environment on first run."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import threading
import urllib.request
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent


def suitable_python():
    if "mingw" not in sysconfig.get_platform().lower():
        return
    # Some Windows machines put MSYS Python first in PATH; ONNX wheels require CPython/MSVC.
    candidates = []
    try:
        candidates.extend((Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python").glob("Python*/python.exe"))
    except OSError:
        pass
    candidates.append(Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe")
    for candidate in candidates:
        try:
            if candidate.is_file():
                probe = subprocess.run([str(candidate), "-c", "import sys, sysconfig; print(sysconfig.get_platform()); sys.exit(sys.version_info < (3,12))"], capture_output=True,text=True)
                if probe.returncode == 0 and "mingw" not in probe.stdout.lower():
                    raise SystemExit(subprocess.call([str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]]))
        except OSError:
            continue
    raise SystemExit("Install standard 64-bit Python 3.12+ from python.org; MSYS/MinGW Python is not supported by ONNX wheels.")


def main():
    suitable_python()
    parser = argparse.ArgumentParser(description="Run EventMatch with local semantic search")
    parser.add_argument("--port",type=int,default=8000)
    parser.add_argument("--no-browser",action="store_true")
    parser.add_argument("--use-current-env",action="store_true",help="Use already installed dependencies")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if sys.version_info < (3,12):
        raise SystemExit("Python 3.12 or newer is required.")
    if not args.use_current_env:
        environment = ROOT / ".venv"
        executable = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not executable.exists():
            print("Preparing project environment...",flush=True)
            venv.EnvBuilder(with_pip=True).create(environment)
        stamp = environment / "eventmatch-requirements.txt"
        requirements = ROOT / "backend" / "requirements.txt"
        if not stamp.exists() or stamp.read_bytes() != requirements.read_bytes():
            subprocess.run([str(executable),"-m","pip","install","-r",str(requirements)],check=True)
            stamp.write_bytes(requirements.read_bytes())
        raise SystemExit(subprocess.call([str(executable),str(Path(__file__).resolve()),"--use-current-env","--port",str(args.port),*(["--no-browser"] if args.no_browser else [])]))

    sys.path.insert(0,str(ROOT/"backend"))
    from recommender.config import MODEL_DIR
    from download_model import FILES, download
    if not all((MODEL_DIR / name).exists() for name in FILES.values()):
        download()
    import uvicorn
    url = f"http://127.0.0.1:{args.port}/app/"
    print(f"\nEventMatch: {url}\nKeep this window open. Ctrl+C stops the server.\n",flush=True)
    if not args.no_browser:
        def open_when_ready():
            import time
            for _ in range(60):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{args.port}/health",timeout=1) as response:
                        if response.status == 200:
                            webbrowser.open(url)
                            return
                except OSError:
                    time.sleep(0.5)
        threading.Thread(target=open_when_ready,daemon=True).start()
    uvicorn.run("main:app",host="127.0.0.1",port=args.port)


if __name__ == "__main__":
    main()
