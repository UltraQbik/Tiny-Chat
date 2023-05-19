import threading as th
import customtkinter as ctk
from abc import ABC

import networking
from networking import Networking


def messagebox(title, message):
    # create top level
    pop = ctk.CTkToplevel()

    # top level setup
    pop.wm_title(title)
    pop.geometry("360x180")
    pop.attributes("-topmost", True)

    # add message label
    msg_ = ctk.CTkLabel(pop, text=message, wraplength=320)
    msg_.pack(padx=12, pady=12, fill="both", expand=True)

    # add exit button
    ext_ = ctk.CTkButton(pop, text="Got it", command=pop.destroy)
    ext_.pack(padx=12, pady=12, fill="x")


class ConnectionTabView(ctk.CTkTabview, ABC):
    def __init__(self, master, net, **kwargs):
        super(ConnectionTabView, self).__init__(master, **kwargs)

        self._net: Networking = net

        # add tabs
        self.add("Local machine")
        self.add("Encryption")

        # add widgets to "Local machine" tab
        self._add_local_machine_tab()

        # add widgets to "Encryption" tab
        self._add_encryption_tab()

    def _add_local_machine_tab(self):
        # define the tab
        tab = self.tab("Local machine")

        # add left and right frames
        left_ = ctk.CTkFrame(tab, width=40)
        left_.pack(padx=10, pady=10, fill="both", expand=True, side="left")

        right_ = ctk.CTkFrame(tab)
        right_.pack(padx=10, pady=10, fill="both", expand=True, side="right")

        # adding entries and labels
        # ip address entry
        local_ip_ = ctk.CTkEntry(left_, width=40)
        local_ip_.insert(0, self._net.get_local_ip)
        local_ip_.pack(padx=4, pady=4, fill="x", anchor="n")

        local_ip_label_ = ctk.CTkLabel(right_, text="IP address of your local machine", anchor="w")
        local_ip_label_.pack(padx=10, pady=4, anchor="nw")

        # username
        username_ = ctk.CTkEntry(left_, width=40)
        username_.insert(0, self._net.user.username)
        username_.pack(padx=4, pady=4, fill="x", anchor="n")

        username_label_ = ctk.CTkLabel(right_, text="Username that will be displayed", anchor="w")
        username_label_.pack(padx=10, pady=4, anchor="nw", side="left")

        def _change_username():
            self._net.change_username(username_.get())
            messagebox("success!", "username changed successfully!")

        username_button_ = ctk.CTkButton(right_, text="change", width=40,
                                         command=_change_username)
        username_button_.pack(padx=10, pady=4, anchor="nw", side="right")

    def _add_encryption_tab(self):
        # define the tab
        tab = self.tab("Encryption")

        # add left and right frames
        left_ = ctk.CTkFrame(tab, width=40)
        left_.pack(padx=10, pady=10, fill="both", expand=True, side="left")

        right_ = ctk.CTkFrame(tab)
        right_.pack(padx=10, pady=10, fill="both", expand=True, side="right")

        # adding entries and labels
        # key size
        key_size_ = ctk.CTkEntry(left_, width=40)
        key_size_.insert(0, self._net.rsa_key_size.__str__())
        key_size_.pack(padx=4, pady=4, fill="x", anchor="n")

        key_size_label_ = ctk.CTkLabel(right_, text="Current length of the RSA encryption key", anchor="w")
        key_size_label_.pack(padx=10, pady=4, anchor="nw")

        # regenerate RSA keys
        key_dropdown_ = ctk.CTkOptionMenu(left_, width=40, values=[str(2**(x+9)) for x in range(5)],
                                          dynamic_resizing=False)
        key_dropdown_.pack(padx=4, pady=4, fill="x", anchor="n")

        def _regen_new_keys():
            self._net.generate_new_rsa_keys(int(key_dropdown_.get()))
            key_size_.delete(0, "end")
            key_size_.insert(0, self._net.rsa_key_size)

        key_regen_ = ctk.CTkButton(right_, text="regenerate RSA keys", width=80,
                                   command=_regen_new_keys)
        key_regen_.pack(padx=10, pady=4, anchor="nw")

        # regenerate AES key
        aes_key_dropdown_ = ctk.CTkOptionMenu(left_, width=40, values=[str(64+x*64) for x in range(4)],
                                              dynamic_resizing=False)
        aes_key_dropdown_.pack(padx=4, pady=4, fill="x", anchor="n")

        def _regen_new_aes_keys():
            pass

        key_regen_ = ctk.CTkButton(right_, text="regenerate AES key", width=80)
        key_regen_.pack(padx=10, pady=4, anchor="nw")


class SettingsMenu(ctk.CTkToplevel):
    def __init__(self, net: networking.Networking, **kwargs):
        super(SettingsMenu, self).__init__(**kwargs)
        self._net: networking.Networking = net

        # setup top level
        self.wm_title("General settings")
        self.geometry("640x480")
        self.attributes("-topmost", True)


class ConnectionMenu(ctk.CTkToplevel):
    def __init__(self, net: networking.Networking, ui_callback, **kwargs):
        super(ConnectionMenu, self).__init__(**kwargs)
        self._net: networking.Networking = net
        self.ui_print = ui_callback

        # setup top level
        self.wm_title("Connection settings")
        self.geometry("640x480")
        self.attributes("-topmost", True)

        # create the tabview
        tabview_ = ConnectionTabView(self, self._net)
        tabview_.pack(padx=10, pady=10, expand=True, fill="both")


class ConnectMenu(ctk.CTkToplevel):
    def __init__(self, net: networking.Networking, **kwargs):
        super(ConnectMenu, self).__init__(**kwargs)
        self._net = net

        # setup top level
        self.wm_title("Connection settings")
        self.geometry("300x300")
        self.attributes("-topmost", True)

        # create all widgets
        self._create_widgets()

    def _create_widgets(self):
        # create inner frame
        inner_ = ctk.CTkFrame(self)
        inner_.pack(padx=10, pady=10, fill="both", expand=True)

        # create host button
        def _host_button():
            if self._net.is_connected:
                self._net.ui_print_callback("[NET]", "You are already connected!")
                return

            th.Thread(target=self._net.bind_server, daemon=True).start()

        host_button_ = ctk.CTkButton(inner_, text="host server", command=_host_button)
        host_button_.pack(padx=8, pady=8, anchor="n", fill="x")

        # add separator
        sep_ = ctk.CTkLabel(inner_, text="")
        sep_.pack(padx=8, pady=8, anchor="n", fill="x")

        # create connect entry and button
        ip_entry_ = ctk.CTkEntry(inner_)
        ip_entry_.pack(padx=8, pady=8, anchor="n", fill="x")

        def _connect_to_button():
            if self._net.is_connected:
                self._net.ui_print_callback("[NET]", "You are already connected!")
                return

            th.Thread(target=self._net.connect_client, args=(ip_entry_.get(),), daemon=True).start()

        connect_button_ = ctk.CTkButton(inner_, text="connect to", command=_connect_to_button)
        connect_button_.pack(padx=8, pady=8, anchor="n", fill="x")

        # add separator
        sep_ = ctk.CTkLabel(inner_, text="")
        sep_.pack(padx=8, pady=8, anchor="n", fill="x")

        # add disconnect button
        def _disconnect_button():
            if not self._net.is_connected:
                self._net.ui_print_callback("[NET]", "You are not connected to any server!")
                return

            self._net.close_connection()

        disconnect_button_ = ctk.CTkButton(inner_, text="disconnect", command=_disconnect_button)
        disconnect_button_.pack(padx=8, pady=8, anchor="n", fill="x")


class UI:
    def __init__(self, net: Networking):
        self._win: ctk.CTk | None = None
        self._net: Networking = net
        self._net.ui_print_callback = self.ui_print_callback

        self._chat: ctk.CTkTextbox | None = None
        self._chat_messages: list[ctk.CTkTabview] = []

    def run(self):
        th.Thread(target=self._create_window).start()

    def close(self):
        self._win.quit()
        self._net.close_connection()

    def open_connect(self):
        ConnectMenu(self._net)

    def open_connection(self):
        ConnectionMenu(self._net, self.ui_print_callback)

    def open_settings(self):
        SettingsMenu(self._net)

    def _create_window(self):
        # create the root
        self._win = ctk.CTk()

        # window setup
        self._win.wm_title("Tiny Chat")
        self._win.geometry("640x480")

        # create top frame
        top_ = ctk.CTkFrame(self._win, height=30)
        top_.pack(padx=10, pady=5, fill="x", anchor="n")

        # create buttons for the top frame
        connect_ = ctk.CTkButton(top_, width=60, text="connect", command=self.open_connect)
        connect_.pack(padx=4, pady=4, side="left")

        settings_ = ctk.CTkButton(top_, width=60, text="settings", command=self.open_settings)
        settings_.pack(padx=4, pady=4, side="right")

        connection_ = ctk.CTkButton(top_, width=60, text="connection", command=self.open_connection)
        connection_.pack(padx=4, pady=4, side="right")

        # create main frame
        main_ = ctk.CTkFrame(self._win)
        main_.pack(padx=10, pady=5, fill="both", expand=True)

        # create chat textbox
        self._chat = ctk.CTkScrollableFrame(main_)
        self._chat.pack(padx=8, pady=8, fill="both", expand=True)

        # create bottom frame
        bottom_ = ctk.CTkFrame(self._win, height=40)
        bottom_.pack(padx=10, pady=5, fill="x", anchor="n")

        # create chatting box
        chat_append_ = ctk.CTkButton(bottom_, text="+", corner_radius=64, width=28)
        chat_append_.pack(padx=8, pady=8, side="left")

        def send_message(_):
            if chat_entry_.get():
                if not self._net.is_connected:
                    self.ui_print_callback("[NET]", "You must connect to the network first!")
                    chat_entry_.delete(0, "end")
                    return
                self.ui_print_callback(self._net.user.username, chat_entry_.get())
                self._net.send_message(chat_entry_.get())
                chat_entry_.delete(0, "end")

        chat_entry_ = ctk.CTkEntry(bottom_)
        chat_entry_.bind("<Return>", send_message)
        chat_entry_.pack(padx=8, pady=8, fill="both", expand=True)

        # what the window should do when it's closed
        self._win.wm_protocol("WM_DELETE_WINDOW", self.close)

        # start the UI
        self._win.mainloop()

    def ui_print_callback(self, title: str, message: str):
        msg_ = ctk.CTkTabview(self._chat, height=0)
        msg_.pack(padx=4, pady=2, fill="x", anchor="n")

        msg_.add(title)

        text_ = ctk.CTkLabel(msg_.tab(title), text=message, wraplength=540)
        text_.pack(padx=0, pady=0, fill="both", expand=True)

        # scroll when new message appears. It sucks but it works
        self._chat._scrollbar.set(1, 1)
        self._chat._scrollbar._command('moveto', 1)


def test():
    net = networking.Networking()
    ui = UI(net)
    ui.run()


if __name__ == '__main__':
    test()
