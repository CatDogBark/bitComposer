"""MPRIS on Linux: the player on the session bus as
org.mpris.MediaPlayer2.bitcomposer, so the media keys, the Plasma media
applet and lock screen, GNOME's media controls and playerctl drive it, and
show what is playing (what the old Plasma widget's daemon did for it).

jeepney (pure Python) speaks D-Bus here rather than QtDBus: MPRIS clients
check types (PropertiesChanged must be sa{sv}as, lengths int64, track ids
object paths), which jeepney writes exactly and PySide's variant
conversions do not. A thread reads method calls; anything that changes the
player runs on the Qt main thread through the backend's dispatcher, and
replies are sent at once. Property values are a snapshot the main thread
rebuilds on every state change, except Position, which is read live.
"""
import os
import threading
import zlib
from pathlib import Path

BUS_NAME = "org.mpris.MediaPlayer2.bitcomposer"
PATH = "/org/mpris/MediaPlayer2"
ROOT = "org.mpris.MediaPlayer2"
PLAYER = "org.mpris.MediaPlayer2.Player"
PROPS = "org.freedesktop.DBus.Properties"
INTROSPECTABLE = "org.freedesktop.DBus.Introspectable"
PEER = "org.freedesktop.DBus.Peer"
ICON = Path(__file__).resolve().parent / "icons" / "bitcomposer.svg"

INTROSPECTION = """<!DOCTYPE node PUBLIC "-//freedesktop//DTD D-BUS Object Introspection 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd">
<node>
  <interface name="org.freedesktop.DBus.Introspectable">
    <method name="Introspect"><arg name="xml" type="s" direction="out"/></method>
  </interface>
  <interface name="org.freedesktop.DBus.Properties">
    <method name="Get"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="out"/></method>
    <method name="GetAll"><arg type="s" direction="in"/><arg type="a{sv}" direction="out"/></method>
    <method name="Set"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="v" direction="in"/></method>
    <signal name="PropertiesChanged"><arg type="s"/><arg type="a{sv}"/><arg type="as"/></signal>
  </interface>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/>
    <method name="Previous"/>
    <method name="Pause"/>
    <method name="PlayPause"/>
    <method name="Stop"/>
    <method name="Play"/>
    <method name="Seek"><arg name="Offset" type="x" direction="in"/></method>
    <method name="SetPosition"><arg name="TrackId" type="o" direction="in"/><arg name="Position" type="x" direction="in"/></method>
    <method name="OpenUri"><arg name="Uri" type="s" direction="in"/></method>
    <signal name="Seeked"><arg name="Position" type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>
"""

ROOT_PROPS = {
    "CanQuit": ("b", True), "CanRaise": ("b", True), "HasTrackList": ("b", False),
    "Identity": ("s", "bitComposer"), "DesktopEntry": ("s", "bitcomposer-player"),
    "SupportedUriSchemes": ("as", []), "SupportedMimeTypes": ("as", []),
}


def track_id(file: str) -> str:
    """A stable object path per file (the index moves when the folder changes)."""
    return f"/org/bitcomposer/track/t{zlib.crc32(file.encode()):08x}"


class Mpris:
    def __init__(self, backend, bus: str = "SESSION"):
        self.b = backend
        self.bus = bus
        self.conn = None
        self.name = ""
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._props = {}          # Player properties, (signature, value), rebuilt on the main thread

    # ── lifetime ──
    def start(self) -> bool:
        try:
            from jeepney.bus_messages import message_bus
            from jeepney.io.blocking import open_dbus_connection
        except ImportError:
            return False
        try:
            self.conn = open_dbus_connection(bus=self.bus)
            # A second player (another settings folder) takes the instance name the spec allows.
            for name in (BUS_NAME, f"{BUS_NAME}.instance{os.getpid()}"):
                reply = self.conn.send_and_get_reply(message_bus.RequestName(name, 4), timeout=2)   # 4: do not queue
                if reply.body and reply.body[0] in (1, 4):                                       # primary / already owner
                    self.name = name
                    break
        except Exception as e:                                  # no session bus, refused, timed out
            print(f"[MPRIS] not on the session bus: {e}")
            self._close()
            return False
        if not self.name:
            self._close()
            return False
        self._props = self._snapshot()
        self._thread = threading.Thread(target=self._loop, name="mpris", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)
        self._close()

    def _close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def _send(self, msg) -> None:
        with self._send_lock:
            if self.conn is not None:
                self.conn.send(msg)

    # ── the main thread tells the bus ──
    def update(self) -> None:
        """After a state change: send what changed (Position never; Seeked covers jumps)."""
        if self.conn is None:
            return
        new = self._snapshot()
        changed = {k: v for k, v in new.items() if self._props.get(k) != v}
        self._props = new
        if changed:
            from jeepney import DBusAddress, new_signal
            emitter = DBusAddress(PATH, interface=PROPS)
            self._send(new_signal(emitter, "PropertiesChanged", "sa{sv}as", (PLAYER, changed, [])))

    def seeked(self, seconds: float) -> None:
        if self.conn is None:
            return
        from jeepney import DBusAddress, new_signal
        self._send(new_signal(DBusAddress(PATH, interface=PLAYER), "Seeked", "x", (int(seconds * 1e6),)))

    def _snapshot(self) -> dict:
        st = self.b.state
        has = bool(self.b.playlist)
        loaded = bool(st.get("file"))
        meta = {}
        if loaded:
            path = self.b.current_path()
            meta = {
                "mpris:trackid": ("o", track_id(path or st["file"])),
                "mpris:length": ("x", int(float(st.get("duration") or 0) * 1e6)),
                "xesam:title": ("s", st.get("title") or Path(st["file"]).stem),
                "xesam:artist": ("as", [st.get("artist") or "bitComposer"]),
                "xesam:album": ("s", "bitComposer"),
                "mpris:artUrl": ("s", ICON.as_uri()),
            }
            if path:
                meta["xesam:url"] = ("s", Path(path).as_uri())
        return {
            "PlaybackStatus": ("s", st.get("status") or "Stopped"),
            "Rate": ("d", 1.0), "MinimumRate": ("d", 1.0), "MaximumRate": ("d", 1.0),
            "Shuffle": ("b", bool(st.get("shuffle"))),
            "Metadata": ("a{sv}", meta),
            # Volume is the player's gain: 1.0 unity, above it boost (the spec
            # calls 1.0 a sensible maximum, not a limit).
            "Volume": ("d", float(st.get("volume", 1.0))),
            "CanGoNext": ("b", has), "CanGoPrevious": ("b", has),
            "CanPlay": ("b", has), "CanPause": ("b", has),
            "CanSeek": ("b", loaded), "CanControl": ("b", True),
        }

    # ── the bus thread ──
    def _loop(self) -> None:
        from jeepney import MessageType
        while not self._stop.is_set():
            try:
                msg = self.conn.receive(timeout=0.5)
            except TimeoutError:
                continue
            except Exception:                                   # bus gone
                break
            if msg.header.message_type != MessageType.method_call:
                continue
            try:
                reply = self._handle(msg)
            except Exception as e:
                from jeepney import new_error
                reply = new_error(msg, "org.freedesktop.DBus.Error.Failed", "s", (str(e),))
            if reply is not None and not (msg.header.flags & 1):   # 1: no reply expected
                try:
                    self._send(reply)
                except Exception:
                    break

    def _main(self, fn) -> None:
        self.b.on_main(fn)

    def _handle(self, msg):
        from jeepney import HeaderFields, new_error, new_method_return
        f = msg.header.fields
        path, iface, member = f.get(HeaderFields.path), f.get(HeaderFields.interface), f.get(HeaderFields.member)
        if member == "Introspect" and iface in (None, INTROSPECTABLE):
            if path == PATH:
                return new_method_return(msg, "s", (INTROSPECTION,))
            if PATH.startswith(path.rstrip("/") + "/"):                 # "/", "/org", "/org/mpris": point the way down
                child = PATH[len(path.rstrip("/")) + 1:].split("/")[0]
                return new_method_return(msg, "s", (f'<node><node name="{child}"/></node>',))
        if iface == PEER and member == "Ping":
            return new_method_return(msg)
        if path != PATH:
            return new_error(msg, "org.freedesktop.DBus.Error.UnknownObject", "s", (path,))

        if iface == PROPS:
            if member == "GetAll":
                (name,) = msg.body
                return new_method_return(msg, "a{sv}", (self._table(name),))
            if member == "Get":
                name, prop = msg.body
                table = self._table(name)
                if prop not in table:
                    return new_error(msg, "org.freedesktop.DBus.Error.UnknownProperty", "s", (prop,))
                return new_method_return(msg, "v", (table[prop],))
            if member == "Set":
                name, prop, (_sig, value) = msg.body
                if name == PLAYER and prop == "Volume":
                    v = max(0.0, float(value))
                    self._main(lambda: self.b.setVolume(v))
                elif name == PLAYER and prop == "Shuffle":
                    if bool(value) != bool(self.b.state.get("shuffle")):
                        self._main(self.b.toggleShuffle)
                elif name == PLAYER and prop == "Rate":
                    pass                                                # fixed at 1.0
                else:
                    return new_error(msg, "org.freedesktop.DBus.Error.PropertyReadOnly", "s", (prop,))
                return new_method_return(msg)

        if iface in (ROOT, None) and member in ("Raise", "Quit"):
            self._main(self.b.raiseRequested.emit if member == "Raise" else self.b.quitRequested.emit)
            return new_method_return(msg)

        if iface in (PLAYER, None):
            b = self.b
            status = lambda: b.state.get("status")                     # noqa: E731
            if member == "PlayPause":
                self._main(b.playPause)
            elif member == "Play":
                self._main(lambda: status() != "Playing" and b.playPause())
            elif member == "Pause":
                self._main(lambda: status() == "Playing" and b.playPause())
            elif member == "Stop":
                self._main(b.stop)
            elif member == "Next":
                self._main(b.next)
            elif member == "Previous":
                self._main(b.previous)
            elif member == "Seek":
                (offset,) = msg.body
                self._main(lambda: self._seek_by(offset / 1e6))
            elif member == "SetPosition":
                tid, pos = msg.body
                self._main(lambda: self._set_position(tid, pos / 1e6))
            elif member == "OpenUri":
                return new_error(msg, "org.mpris.MediaPlayer2.Error.NotSupported", "s", ("OpenUri",))
            else:
                return new_error(msg, "org.freedesktop.DBus.Error.UnknownMethod", "s", (member,))
            return new_method_return(msg)
        return new_error(msg, "org.freedesktop.DBus.Error.UnknownInterface", "s", (iface or "",))

    def _table(self, name: str) -> dict:
        if name == ROOT:
            return dict(ROOT_PROPS)
        if name == PLAYER:
            t = dict(self._props)
            t["Position"] = ("x", int(self.b.player.position() * 1e6))
            return t
        return {}

    # main thread
    def _seek_by(self, delta: float) -> None:
        dur = float(self.b.state.get("duration") or 0)
        target = max(0.0, self.b.player.position() + delta)
        if dur and target >= dur:
            self.b.next()                       # the spec: seeking past the end goes to the next track
        else:
            self.b.seek(target)

    def _set_position(self, tid: str, seconds: float) -> None:
        path = self.b.current_path()
        dur = float(self.b.state.get("duration") or 0)
        if path and tid == track_id(path) and 0 <= seconds <= dur:
            self.b.seek(seconds)
