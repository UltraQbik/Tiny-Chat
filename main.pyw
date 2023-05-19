import customtkinter as ctk
from UI import UI
from networking import Networking


def main():
    ctk.set_default_color_theme("dark-blue.json")

    net = Networking()
    app = UI(net)

    app.run()


if __name__ == '__main__':
    main()
