
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def run_command(command):
    subprocess.run(command, cwd=BASE_DIR, check=True)


def main():
    python = sys.executable

    print("Installing requirements...")
    run_command([
        python, "-m", "pip", "install",
        "-r", "requirements.txt"
    ])

    print("Checking Django configuration...")
    run_command([python, "manage.py", "check"])

    print("Applying database migrations...")
    run_command([python, "manage.py", "migrate"])

    print("Collecting static files...")
    run_command([
        python, "manage.py", "collectstatic", "--noinput"
    ])

    print("Starting Django development server...")
    run_command([
        python, "manage.py", "runserver"
    ])


if __name__ == "__main__":
    main()
