from gi.repository import Gtk, Adw
from view.objects import App
from view.events import Event, event_connect, event_emit
from .util import compose_entry_box, _make_box

class LaunchEntry(Gtk.Box):
    def __init__(self, entry, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entry = entry
        self._make_widgets()
        self._configure_widgets()

    def _make_widgets(self):
        self.set_orientation(Gtk.Orientation.VERTICAL)
        description_box, self.description_entry = compose_entry_box("Description", "Unspecified")
        executable_box, self.execuable_entry = compose_entry_box("Executable", "Unspecified", False, "folder")
        workdir_box, self.workdir_entry = compose_entry_box("Working Directory", "Unspecified", False, "folder")
        arguments_box, self.arguments_entry = compose_entry_box("Launch Arguments", "Unspecified")
        delete_button = Gtk.Button()
        bottom_box = Gtk.Box()
        checkbutton_box = Gtk.Box(hexpand=True)
        self.windows_checkbutton = Gtk.CheckButton(label="Windows")
        self.mac_checkbutton = Gtk.CheckButton(label="Mac")
        self.linux_checkbutton = Gtk.CheckButton(label="Linux")

        delete_button.set_icon_name("edit-delete")
        delete_button.connect("clicked", lambda *_: self._delete_self())
        delete_button.set_css_classes(["button", "delete_button"])

        checkbutton_box.append(self.windows_checkbutton)
        checkbutton_box.append(self.mac_checkbutton)
        checkbutton_box.append(self.linux_checkbutton)
        bottom_box.append(checkbutton_box)
        bottom_box.append(delete_button)
        bottom_box.set_hexpand(True)

        self.append(description_box)
        self.append(executable_box)
        self.append(workdir_box)
        self.append(arguments_box)
        self.append(bottom_box)

    def _configure_widgets(self):
        self.set_spacing(15)
        self.description_entry.set_text(self.entry.get("description", ""))
        self.execuable_entry.set_text(self.entry.get("executable", ""))
        self.workdir_entry.set_text(self.entry.get("workingdir", ""))
        arguments = self.entry.get("arguments", "")
        if isinstance(arguments, int): arguments = ""
        self.arguments_entry.set_text(arguments)

        entry_oslist = self.entry.get("config", {}).get("oslist", "").lower()
        self.windows_checkbutton.set_active("windows" in entry_oslist)
        self.mac_checkbutton.set_active("macos" in entry_oslist)
        self.linux_checkbutton.set_active("linux" in entry_oslist)

    def _delete_self(self):
        event_emit(Event.DELETE_LAUNCH_ENTRY, self)

    def _make_oslist_string(self) -> str:
        selected_os = []
        if self.windows_checkbutton.get_active():
            selected_os.append("windows")
        if self.mac_checkbutton.get_active():
            selected_os.append("macos")
        if self.linux_checkbutton.get_active():
            selected_os.append("linux")
        return ','.join(selected_os)

    def get_updated_entry(self) -> dict:
        if self.description_entry.get_text():
            self.entry["description"] = self.description_entry.get_text()
        if self.execuable_entry.get_text():
            self.entry["executable"] = self.execuable_entry.get_text()
        if self.workdir_entry.get_text():
            self.entry["workingdir"] = self.workdir_entry.get_text()
        if self.arguments_entry.get_text():
            self.entry["arguments"] = self.arguments_entry.get_text()
        oslist = self._make_oslist_string()
        if oslist:
            self.entry.setdefault("config", {})
            self.entry["config"]["oslist"] = oslist
        return self.entry


class LaunchMenu(Gtk.Frame):
    def __init__(self, model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self._current_app: App = None
        self._initial_app_launch_options = None
        self.set_vexpand(True)
        self._make_widgets()
        self._connect_signals()
        self.set_css_classes(['launch_menu'])

    def _make_widgets(self):
        scrolled_window = Gtk.ScrolledWindow()
        self._entries_box = _make_box()
        tool_bar = Adw.ToolbarView()
        action_bar = Gtk.ActionBar()

        add_button = Gtk.Button()
        add_button.set_icon_name("list-add")
        add_button.connect("clicked", lambda *_: self._add_empty_entry())
        action_bar.pack_end(add_button)
        tool_bar.add_bottom_bar(action_bar)
        tool_bar.set_content(scrolled_window)

        self.set_child(tool_bar)
        scrolled_window.set_child(self._entries_box)

    def _connect_signals(self):
        event_connect(Event.LOAD_APP, self._load_app)
        event_connect(Event.DELETE_LAUNCH_ENTRY, self._delete_launch_entry)
        event_connect(Event.SAVE_CHANGES, self._save_current_app)

    def _delete_launch_entry(self, entry: LaunchEntry):
        self._entries_box.remove(entry)
        self._recalculate_entry_css_classes()

    def _make_entries(self):
        if not self._current_app: return
        app_entries = self.model.get_app_launch_menu(self._current_app.id)
        self._initial_app_launch_options = app_entries or {}
        if not app_entries: return
        for i, entry in enumerate(app_entries):
            self._add_launch_entry(app_entries[entry])

    def _delete_all_entries_from_box(self):
        for entry in self._get_entry_list():
            self._entries_box.remove(entry)

    def _add_launch_entry(self, values: dict):
        self._entries_box.append(LaunchEntry(values))
        self._recalculate_entry_css_classes()

    def _recalculate_entry_css_classes(self):
        for i, entry in enumerate(self._get_entry_list()):
            if i % 2 == 0:
                entry.set_css_classes(["launch_entry_even"])
            else:
                entry.set_css_classes(["launch_entry_odd"])

    def _add_empty_entry(self):
        self._add_launch_entry({})

    def _load_app_entries(self):
        self._delete_all_entries_from_box()
        self._make_entries()

    def _get_entry_list(self) -> [LaunchEntry]:
        entries = []
        child = self._entries_box.get_first_child()
        while child:
            entries.append(child)
            child = child.get_next_sibling()
        return entries

    def _get_updated_entries(self) -> dict:
        results = {}
        for i, entry in enumerate(self._get_entry_list()):
            updated_entry = entry.get_updated_entry()
            if updated_entry:
                results[str(i)] = updated_entry
        return results

    def _load_app(self, app: App):
        self._current_app = app
        self._load_app_entries()

    def _save_current_app(self):
        updated_entries = self._get_updated_entries()
        if self._initial_app_launch_options is not None \
           and self._initial_app_launch_options != updated_entries:
            self.model.set_app_launch_menu(self._current_app.id, updated_entries)
