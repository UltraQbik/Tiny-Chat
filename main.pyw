from UI import UI
from networking import Networking


def main():
    net = Networking()
    app = UI(net)

    app.run()


if __name__ == '__main__':
    main()
