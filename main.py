"""Command-line entry point for the NOL Ticket helper."""

from tkinter import TclError


def main() -> None:
    """Load and run the GUI only when the program is started."""
    try:
        from app import run
    except ModuleNotFoundError as error:
        if error.name != "customtkinter":
            raise
        raise SystemExit(
            "CustomTkinter가 필요합니다. 'python -m pip install -r requirements.txt'를 실행하세요."
        ) from error

    try:
        run()
    except TclError as error:
        raise SystemExit(
            "GUI를 시작할 수 없습니다. Tcl/Tk가 포함된 Python을 설치하거나 복구한 뒤 다시 실행하세요."
        ) from error


if __name__ == "__main__":
    main()
