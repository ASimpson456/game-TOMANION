"""Сгенерировать assets/tomato.ico для сборки exe."""

from app_icon import write_icon_files

if __name__ == "__main__":
    path = write_icon_files()
    print("Icon saved:", path)
