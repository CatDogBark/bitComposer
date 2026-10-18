/*
    bitComposer player window: the Plasma widget's popup as a desktop window.

    The layout, colours and wording are the old Plasma widget's (removed in
    1.0.0rc3); what changed is the plumbing. The widget polled a
    D-Bus daemon through qdbus6 processes; here `backend` (bitcomposer/
    player/app.py) wraps the engine in-process, so state is pushed rather
    than polled and there is no cooldown dance.

    Resolution: every size below is in logical pixels, which Qt scales by the
    screen's device pixel ratio (125%, 150%, 200%...). The window opens no
    taller than the screen it lands on and the whole column scrolls when it
    does not fit; option rows wrap instead of running off the edge. Ctrl +/-
    zooms the whole window on top of that (Ctrl 0 resets), and the zoom is
    remembered.
*/
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Shapes
import QtQuick.Window

ApplicationWindow {
    id: root
    visible: false          // shown by Component.onCompleted, at its starting size
    title: root.trackTitle ? root.trackTitle + "  ·  bitComposer" : "bitComposer"
    color: root.darkBg

    // Set by app.py: which panels start open (the screenshot mode opens them).
    property bool startSettings: false
    property bool startMaster: false
    // The screenshot mode: no scanline sweep caught mid-frame.
    property bool still: false
    // Started at login (--minimized): no window until asked for (the tray,
    // the app menu, the desktop's media controls).
    property bool startHidden: false

    // ── Zoom ──
    property real ui: 1.0
    function setZoom(z) {
        var old = root.ui
        root.ui = Math.max(0.75, Math.min(2.0, Math.round(z * 20) / 20))
        // the window widens with the type; its height stays and the column scrolls
        if (root._sized) root.width = Math.min(Math.round(root.width * root.ui / old), root.availW)
        root._save()
    }
    Shortcut { sequences: ["Ctrl+=", "Ctrl++"]; onActivated: root.setZoom(root.ui + 0.1) }
    Shortcut { sequence: "Ctrl+-"; onActivated: root.setZoom(root.ui - 0.1) }
    Shortcut { sequence: "Ctrl+0"; onActivated: root.setZoom(1.0) }
    Shortcut { sequence: "Space"; onActivated: backend.playPause() }

    // ── Size: fit the screen ──
    // The available area of the screen the window is on, from app.py (the
    // screenshot mode hands in the screen it pretends to be).
    readonly property real availW: backend.screenAvail[0] > 0 ? backend.screenAvail[0] : Screen.desktopAvailableWidth
    readonly property real availH: backend.screenAvail[1] > 0 ? backend.screenAvail[1] : Screen.desktopAvailableHeight
    readonly property real contentH: popupColumn.implicitHeight + 32
    // Room for the title bar and the taskbar edge the available area may not count.
    readonly property real maxH: Math.max(240, root.availH - 64)
    minimumWidth: Math.min(320, root.availW)
    minimumHeight: Math.min(240, root.maxH)
    // The window sizes itself once. It opens as tall as the screen allows
    // (or at the size the user last gave it), and after its first frame,
    // when the text has wrapped, shrinks to the content; the column stays
    // transparent until then. Only ever shrinking after the window manager
    // has placed it keeps it on the screen: Wayland lets no program move
    // its own window, so one that grows runs off the bottom. After that
    // the size is the user's: SET and MIX open inside it and scroll into
    // view (growing for them, as the widget's popup did, ran the window
    // off the screen and flashed), and a size the user drags is kept.
    width: Math.min(400, root.availW)
    height: root.maxH
    property real savedW: 0
    property real savedH: 0
    property bool _sized: false
    property bool _shown: false
    property double _sizedAt: 0
    function _start() {
        root.width = Math.min(root.savedW > 0 ? root.savedW : Math.round(400 * root.ui), root.availW)
        root.height = root.savedH > 0 ? Math.max(root.minimumHeight, Math.min(root.savedH, root.maxH)) : root.maxH
        root._sizedAt = Date.now()
        if (!root.startHidden) root.visible = true
    }
    function _fitOnce() {
        // not while hidden: the column is only laid out for a shown window
        if (root._sized || !root.visible || root.visibility === Window.Minimized || popupColumn.implicitHeight < 50) return
        root._sized = true
        if (root.savedH <= 0)
            root.height = Math.max(root.minimumHeight, Math.min(root.contentH, root.maxH))
        root._sizedAt = Date.now()
        Qt.callLater(function() { root._shown = true })
    }
    // Fit when the column has stopped changing for a moment after the window
    // shows. A fixed delay was too short where the first frame is slow (GNOME
    // drawing in software): the fit ran before the layout and never again.
    // (A frame only starts the wait, it does not restart it: animations
    // draw frames all the time, the layout changing is what restarts it.)
    onFrameSwapped: if (!root._sized && !settle.running) settle.start()
    onContentHChanged: if (!root._sized && root.visible) settle.restart()
    onVisibilityChanged: if (!root._sized && root.visibility !== Window.Minimized && root.visibility !== Window.Hidden) settle.restart()
    Timer { id: settle; interval: 150; onTriggered: { root._fitOnce(); if (root._sized) root._shown = true } }
    Timer { interval: 3000; running: true; onTriggered: if (root.visible && root.visibility !== Window.Minimized) root._shown = true }   // never leave the column unseen
    onMaxHChanged: if (root._sized && root.height > root.maxH) root.height = root.maxH
    // A size change well after the window sized itself is the user's.
    onWidthChanged: root._noteSize()
    onHeightChanged: root._noteSize()
    function _noteSize() { if (root._sized && Date.now() - root._sizedAt > 1000) sizeSave.restart() }
    Timer { id: sizeSave; interval: 800; onTriggered: { root.savedW = root.width; root.savedH = root.height; root._save() } }

    // Opening a panel scrolls it into view (top first when it is taller
    // than the window).
    onShowSettingsChanged: if (root.showSettings && root._sized) reveal.show(settingsPanel)
    onShowMasterChanged: if (root.showMaster && root._sized) reveal.show(masterPanel)
    Timer {
        id: reveal
        interval: 40            // after the column has laid the panel out
        property Item target: null
        function show(item) { target = item; restart() }
        onTriggered: {
            if (!target) return
            var top = popupColumn.y + target.y - 8
            var bottom = popupColumn.y + target.y + target.height + 8
            var y = flick.contentY
            if (bottom > y + flick.height) y = bottom - flick.height
            if (top < y) y = top
            y = Math.max(0, Math.min(y, flick.contentHeight - flick.height))
            if (Math.abs(y - flick.contentY) > 1) { revealAnim.to = y; revealAnim.restart() }
        }
    }
    NumberAnimation { id: revealAnim; target: flick; property: "contentY"; duration: 180; easing.type: Easing.OutCubic }

    // ── State, from the engine ──
    property string playbackStatus: backend.state.status || "Stopped"
    property real trackPosition: backend.position
    property real trackDuration: backend.state.duration || 0
    property int trackChannels: backend.state.channels || 0
    property string trackTitle: backend.state.title || ""
    property string trackArtist: backend.state.artist || ""
    property string trackFormat: backend.state.format || ""
    property string trackFile: backend.state.file || ""
    property int trackPatterns: backend.state.patterns || 0
    property bool shuffleOn: !!backend.state.shuffle
    property int currentIndex: backend.state.currentIndex !== undefined ? backend.state.currentIndex : -1
    property var playlistInfo: backend.playlist
    property string trackMessage: backend.state.message || ""
    property var songVoices: backend.state.voices || ({})
    property var songDrew: backend.state.drew || ({})
    readonly property string songReadout: {
        var d = songDrew; if (!d || !d.form) return ""
        var parts = []
        if (d.intro && d.intro !== "none") parts.push(d.intro.replace(/_/g, " ") + " intro")
        parts.push(d.form + " form")
        if (d.harmony) parts.push(d.harmony.replace(/_/g, " ") + " harmony")
        if (d.bass) { var b = d.bass.split("/"); parts.push(b[0] + " bass" + (b[1] ? " (" + b[1].replace(/_/g, " ") + ")" : "")) }
        if (d.echo) { if (d.echo === "off") parts.push("no echo"); else { var e = d.echo.split("/"); parts.push(e[0] + " echo" + (e[1] ? " fb " + e[1] : "") + (e[2] ? " " + e[2] : "")) } }
        return parts.join("  ·  ")
    }
    // The drawn voice behind a channel, short: the pack prefix dropped,
    // underscores to spaces ("mmx_lead_guitar" -> "lead guitar").
    function voiceLabel(i) {
        var r = String(layout[i] || ""), v = songVoices || {}
        var key = r === "melody" ? "melody" : r === "openhat" ? "open_hihat" : r
        var name = v[key]
        if (!name) return ""
        return String(name).replace(/^(ffvi|mana|evm|mmx|snes|gen|chip)_/, "").replace(/_/g, " ")
    }
    property real volumeGain: backend.state.volume !== undefined ? backend.state.volume : 1.0
    readonly property real maxGain: backend.maxGain
    property bool generating: !!backend.state.generating
    property bool autoGenerate: !!backend.state.autoGenerate
    property bool showSettings: false
    property bool showMaster: false
    property int settingsTab: 0  // 0=COMPOSE, 1=DRUMS, 2=PARTS
    onSettingsTabChanged: root._save()

    // ── Colors ──
    readonly property color accentGreen: "#00ff88"
    readonly property color accentCyan: "#00ffcc"
    readonly property color accentPink: "#ff0055"
    readonly property color textColor: "#b0ddcc"
    readonly property color dimText: "#508264"
    readonly property color tileBg: "#0e1612"
    readonly property color tileBorder: "#1a2e26"
    readonly property color darkBg: "#0a100e"
    readonly property string mono: "JetBrains Mono"

    // ── Transport ──
    function dbusPlayPause() { backend.playPause() }
    function dbusStop() { backend.stop() }
    function dbusNext() { backend.next() }
    function dbusPrevious() { backend.previous() }
    function dbusToggleShuffle() { backend.toggleShuffle() }
    function dbusSetVolume(gain) { backend.setVolume(Math.max(0, Math.min(maxGain, gain))) }
    function dbusPlayIndex(idx) { backend.playIndex(idx) }

    // ── Mixer ──
    // The channel layout comes from the song message's "layout:" line (the
    // engine reads it), so the mixer follows whatever the composer wrote.
    // Roles starting with "echo." are returns and fold into one ECHO bus.
    property var layout: backend.state.layout || []
    property var channelVolumes: []
    readonly property int channelCount: layout.length
    readonly property var dryChannels: { var a = []; for (var i = 0; i < layout.length; i++) if (String(layout[i]).indexOf("echo.") !== 0) a.push(i); return a }
    readonly property var echoChannels: { var a = []; for (var i = 0; i < layout.length; i++) if (String(layout[i]).indexOf("echo.") === 0) a.push(i); return a }
    readonly property var echoGroups: { var g = []; for (var i = 0; i < echoChannels.length; i++) { var r = String(layout[echoChannels[i]]).substring(5); if (g.indexOf(r) < 0) g.push(r) } return g }
    // Bus and group faders are ratios against the mix the file was written
    // with, 0 = off, 1 = as written, 2 = double.
    property var echoBase: []
    property real echoBus: 1.0
    readonly property var kitRoles: ["kick", "snare", "hihat", "tom", "crash", "openhat"]
    readonly property var kitChannels: { var a = []; for (var i = 0; i < dryChannels.length; i++) if (kitRoles.indexOf(String(layout[dryChannels[i]])) >= 0) a.push(dryChannels[i]); return a }
    readonly property var partChannels: { var a = []; for (var i = 0; i < dryChannels.length; i++) if (kitRoles.indexOf(String(layout[dryChannels[i]])) < 0) a.push(dryChannels[i]); return a }
    property var kitBase: []
    property real kitBus: 1.0
    property bool kitExpanded: false
    function setKitRatio(r) {
        kitBus = Math.max(0, Math.min(2, r))
        for (var k = 0; k < kitChannels.length; k++) {
            var ch = kitChannels[k]
            applyChannelVolume(ch, Math.max(0, Math.min(64, Math.round((kitBase[ch] || 0) * kitBus))))
        }
    }
    function _resetKitRatios() { kitBase = channelVolumes.slice(); kitBus = 1.0 }
    property var echoGroupRatio: ({})
    property bool echoExpanded: false
    readonly property var echoRows: echoChannels.length ? ["bus"].concat(echoExpanded ? echoGroups : []) : []
    // One label column and one value column for every mixer row, so the
    // faders line up: wide enough for a voice name when any row has one.
    readonly property bool _anyVoice: { for (var i = 0; i < dryChannels.length; i++) if (voiceLabel(dryChannels[i])) return true; return false }
    readonly property int mixLabelW: Math.round((_anyVoice ? 92 : 56) * root.ui)
    readonly property int mixValueW: Math.round(30 * root.ui)
    function channelLabel(i) {
        var r = String(layout[i] || ""), n = 0
        if (r === "harmony") { for (var k = 0; k <= i; k++) if (layout[k] === "harmony") n++; return "HARM " + n }
        if (r === "openhat") return "OP HAT"
        if (r.indexOf("echo.") === 0) { for (var k2 = 0; k2 <= i; k2++) if (String(layout[k2]).indexOf("echo.") === 0) n++; return "ECHO " + n }
        return r.toUpperCase()
    }
    function channelColor(i) {   // 0=green, 1=cyan, 2=pink
        var r = String(layout[i] || "")
        if (r === "melody" || r === "bass" || r === "arp") return 0
        if (r === "harmony" || r === "counter" || r.indexOf("echo.") === 0) return 1
        return 2
    }
    function echoRatioOf(role) { return role === "bus" ? echoBus : (echoGroupRatio[role] !== undefined ? echoGroupRatio[role] : 1.0) }
    function setEchoRatio(role, r) {
        r = Math.max(0, Math.min(2, r))
        if (role === "bus") echoBus = r
        else { var m = echoGroupRatio; m[role] = r; echoGroupRatio = m; echoGroupRatioChanged() }
        for (var k = 0; k < echoChannels.length; k++) {
            var ch = echoChannels[k], g = echoRatioOf(String(layout[ch]).substring(5))
            applyChannelVolume(ch, Math.max(0, Math.min(64, Math.round((echoBase[ch] || 0) * echoBus * g))))
        }
    }
    function _resetEchoRatios() { echoBase = channelVolumes.slice(); echoBus = 1.0; echoGroupRatio = ({}); echoGroupRatioChanged(); _resetKitRatios() }
    // Faders are live: each change goes straight to the loaded module.
    // APPLY TO TRACK writes the same numbers into the file.
    function applyChannelVolume(channel, value) {
        if (channelVolumes[channel] === value) return
        channelVolumes[channel] = value
        channelVolumesChanged()
        backend.setChannelVolume(channel, value)
    }
    function _applyMasterToFile() {
        if (backend.applyMix()) _resetEchoRatios()   // the written mix is now the base the buses scale
    }
    Connections {
        target: backend
        function onChannelVolumesChanged() { root.channelVolumes = backend.channelVolumes.slice(); root._resetEchoRatios() }
    }

    // ── Folder ──
    function shortDir() { return backend.state.shortDir || "" }
    function keepTrack(idx) { backend.keep(idx) }
    function rescan() { backend.rescan() }
    function openMusicDir() { backend.openFolder() }

    // ── Compose settings ──
    // Saved with the window (QSettings), so they survive a restart; every
    // change also becomes the auto-generate settings, as in the widget.
    property string settTempo: "random"
    property string settEnergy: "random"
    property string settScale: "random"
    property string settSound: "random"
    property string settDrumDensity: "random"
    property bool settDrumFills: true
    property string settDrumSwing: "random"
    property string settMelody: "random"
    property string settHarmonyVoicing: "random"
    property string settHarmonyMode: "random"
    property string settBassWeight: "random"
    property string settForm: "random"
    property string settEcho: "random"
    property string settEchoWet: "random"
    property string activePreset: ""
    property bool _applyingPreset: false
    property bool _loading: true
    function _onSettingChanged() {
        if (root._loading) return
        if (!_applyingPreset) activePreset = ""
        backend.setAutoFlags(_buildSettingsFlags().trim())
        root._save()
    }
    onSettTempoChanged: _onSettingChanged()
    onSettEnergyChanged: _onSettingChanged()
    onSettScaleChanged: _onSettingChanged()
    onSettSoundChanged: _onSettingChanged()
    onSettDrumDensityChanged: _onSettingChanged()
    onSettDrumFillsChanged: _onSettingChanged()
    onSettDrumSwingChanged: _onSettingChanged()
    onSettMelodyChanged: _onSettingChanged()
    onSettHarmonyVoicingChanged: _onSettingChanged()
    onSettHarmonyModeChanged: _onSettingChanged()
    onSettBassWeightChanged: _onSettingChanged()
    onSettFormChanged: _onSettingChanged()
    onSettEchoChanged: _onSettingChanged()
    onSettEchoWetChanged: _onSettingChanged()
    onActivePresetChanged: root._save()

    readonly property var _savedKeys: ["settTempo", "settEnergy", "settScale", "settSound", "settDrumDensity", "settDrumFills",
        "settDrumSwing", "settMelody", "settHarmonyVoicing", "settHarmonyMode", "settBassWeight", "settForm",
        "settEcho", "settEchoWet", "activePreset", "settingsTab", "ui", "savedW", "savedH"]
    function _save() {
        if (root._loading) return
        var o = {}
        for (var i = 0; i < _savedKeys.length; i++) o[_savedKeys[i]] = root[_savedKeys[i]]
        backend.saveUi(JSON.stringify(o))
    }
    function _load() {
        var s = backend.loadUi()
        if (s) {
            try {
                var o = JSON.parse(s)
                for (var i = 0; i < _savedKeys.length; i++) if (o[_savedKeys[i]] !== undefined) root[_savedKeys[i]] = o[_savedKeys[i]]
            } catch (e) {}
        }
        root._loading = false
    }

    function applyPreset(name) {
        var presets = {
            "FM DRIVE":     { tempo: "fast",   energy: "intense", scale: "minor",      sound: "genesis", drumDensity: "busy",   fills: true,  swing: "light",  melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "standard" },
            "GOTHIC":       { tempo: "medium", energy: "normal",  scale: "minor",      sound: "random",  drumDensity: "normal", fills: true,  swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "rondo"    },
            "BOSS FIGHT":   { tempo: "fast",   energy: "intense", scale: "minor",      sound: "genesis", drumDensity: "busy",   fills: true,  swing: "heavy",  melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "short"    },
            "OVERWORLD":    { tempo: "medium", energy: "normal",  scale: "major",      sound: "snes",    drumDensity: "normal", fills: true,  swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "standard" },
            "CHILL WAVE":   { tempo: "slow",   energy: "chill",   scale: "pentatonic", sound: "snes",    drumDensity: "sparse", fills: false, swing: "light",  melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba"     },
            "DUNGEON":      { tempo: "slow",   energy: "chill",   scale: "minor",      sound: "random",  drumDensity: "sparse", fills: false, swing: "off",    melody: "phrased", voicing: "thin", mode: "stabs",    bass: "medium", form: "rondo"    },
            "CREDITS":      { tempo: "slow",   energy: "chill",   scale: "major",      sound: "snes",    drumDensity: "sparse", fills: false, swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba"     },
            "FIGHT THEME":  { tempo: "fast",   energy: "intense", scale: "pentatonic", sound: "genesis", drumDensity: "busy",   fills: true,  swing: "heavy",  melody: "phrased", voicing: "full", mode: "stabs",    bass: "heavy",  form: "short"    },
            "CYBER NOIR":   { tempo: "medium", energy: "normal",  scale: "minor",      sound: "genesis", drumDensity: "normal", fills: true,  swing: "light",  melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "linear"   },
            "ANY":          { tempo: "random", energy: "random",  scale: "random",     sound: "random",  drumDensity: "random", fills: true,  swing: "random", melody: "random",  voicing: "random", mode: "random", bass: "random", form: "random"   },
        }
        var p = presets[name]
        if (!p) return
        root._applyingPreset = true
        root.settTempo = p.tempo
        root.settEnergy = p.energy
        root.settScale = p.scale
        root.settSound = p.sound
        root.settDrumDensity = p.drumDensity
        root.settDrumFills = p.fills
        root.settDrumSwing = p.swing
        root.settMelody = p.melody
        root.settHarmonyVoicing = p.voicing
        root.settHarmonyMode = p.mode
        root.settBassWeight = p.bass
        root.settForm = p.form
        root.activePreset = name
        root._applyingPreset = false
    }

    function _buildSettingsFlags() {
        var flags = ""
        if (settTempo !== "random") flags += " --tempo " + settTempo
        if (settEnergy !== "random") flags += " --energy " + settEnergy
        if (settScale !== "random") flags += " --scale " + settScale
        if (settSound !== "random") flags += " --sound " + settSound
        if (settDrumDensity !== "random") flags += " --drum-density " + settDrumDensity
        if (!settDrumFills) flags += " --no-fills"
        if (settDrumSwing !== "random") flags += " --swing " + settDrumSwing
        if (settMelody !== "random") flags += " --melody " + settMelody
        if (settHarmonyVoicing !== "random") flags += " --harmony-voicing " + settHarmonyVoicing
        if (settHarmonyMode !== "random") flags += " --harmony-mode " + settHarmonyMode
        if (settBassWeight !== "random") flags += " --bass-weight " + settBassWeight
        if (settForm !== "random") flags += " --form " + settForm
        if (settEcho !== "random") flags += " --echo " + settEcho
        if (settEchoWet !== "random") flags += " --echo-wet " + settEchoWet
        return flags
    }

    // One line describing what GENERATE will do, shown while the settings
    // panel is closed.
    function settingsSummary() {
        var prefix = ""
        if (autoGenerate)
            prefix = (playbackStatus === "Playing" ? "AUTO: next track generates when this one ends" : "AUTO: generates when playback stops") + "   |   "
        if (activePreset && activePreset !== "ANY") return prefix + activePreset
        var parts = []
        if (settTempo !== "random") parts.push(settTempo)
        if (settEnergy !== "random") parts.push(settEnergy)
        if (settScale !== "random") parts.push(settScale)
        if (settSound !== "random") parts.push(settSound)
        if (settDrumDensity !== "random") parts.push(settDrumDensity + " drums")
        if (!settDrumFills) parts.push("no fills")
        if (settDrumSwing !== "random") parts.push(settDrumSwing + " swing")
        if (settMelody !== "random") parts.push(settMelody + " melody")
        if (settHarmonyVoicing !== "random") parts.push(settHarmonyVoicing + " harmony")
        if (settHarmonyMode !== "random") parts.push(settHarmonyMode)
        if (settBassWeight !== "random") parts.push(settBassWeight + " bass")
        if (settForm !== "random") parts.push(settForm + " form")
        if (settEcho !== "random") parts.push("echo " + settEcho)
        if (settEchoWet !== "random") parts.push(settEchoWet + " echo")
        return prefix + (parts.length ? parts.join("  ·  ") : "any  ·  everything left to chance")
    }

    function generateTrack() {
        if (root.generating) return
        backend.generate(_buildSettingsFlags().trim())
    }
    // A second click within the debounce window is ignored: a bounce or an
    // impatient re-click used to flip it straight back off.
    property bool _autoDebounce: false
    Timer { id: autoDebounceTimer; interval: 500; onTriggered: root._autoDebounce = false }
    function toggleAutoGenerate() {
        if (root._autoDebounce) return
        root._autoDebounce = true
        autoDebounceTimer.restart()
        backend.setAutoGenerate(!root.autoGenerate, _buildSettingsFlags().trim())
    }

    function formatTime(secs) {
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return String(m).padStart(2, '0') + ":" + String(s).padStart(2, '0')
    }

    Component.onCompleted: {
        root._load()
        root.showSettings = root.startSettings
        root.showMaster = root.startMaster
        root.channelVolumes = backend.channelVolumes.slice()
        root._resetEchoRatios()
        root._start()
    }

    // Close to the tray when there is one: it keeps playing and generating,
    // the way the widget's daemon did. The tray menu quits.
    onClosing: function(close) {
        if (backend.trayAvailable) {
            close.accepted = false
            root.hide()
            backend.hiddenToTray()
        }
    }

    // ── Pieces ──

    // A row of choices: label on the left, chips that wrap when the window
    // is narrow (the widget's rows were fixed and ran off the edge).
    component OptionRow: RowLayout {
        id: optRow
        property string label: ""
        property var options: []
        property string value: ""
        property color accent: root.accentGreen
        signal picked(string choice)
        Layout.fillWidth: true
        spacing: 8
        Text {
            Layout.preferredWidth: Math.round(56 * root.ui)
            Layout.alignment: Qt.AlignTop
            topPadding: Math.round(4 * root.ui)
            text: optRow.label
            color: root.dimText
            font.family: root.mono
            font.pixelSize: Math.round(9 * root.ui)
        }
        Flow {
            Layout.fillWidth: true
            spacing: 3
            Repeater {
                model: optRow.options
                Chip {
                    required property string modelData
                    text: modelData.toUpperCase()
                    active: optRow.value === modelData
                    accent: optRow.accent
                    onClicked: optRow.picked(modelData)
                }
            }
        }
    }

    component Chip: Rectangle {
        id: chip
        property string text: ""
        property bool active: false
        property color accent: root.accentGreen
        signal clicked()
        implicitWidth: chipLabel.implicitWidth + Math.round(10 * root.ui)
        implicitHeight: Math.round(20 * root.ui)
        radius: 3
        color: active ? "#1a2e26" : (chipMouse.containsMouse ? "#0f1a16" : "transparent")
        border.width: 1
        border.color: active ? chip.accent : (chipMouse.containsMouse ? root.tileBorder : "transparent")
        Text {
            id: chipLabel
            anchors.centerIn: parent
            text: chip.text
            color: chip.active ? chip.accent : root.dimText
            font.family: root.mono
            font.pixelSize: Math.round(8 * root.ui)
        }
        MouseArea { id: chipMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: chip.clicked() }
    }

    // A square tool button with a glyph over a caption (AUTO, SET, MIX).
    // Line icons for the symbols JetBrains Mono does not have (shuffle,
    // settings, mixer, pause). As text they came from whatever fallback
    // font the system had, and on Windows from none: empty boxes. Drawn on
    // a 24-unit grid in the colour the text would have had.
    component Icon: Shape {
        id: icon
        property string name: ""
        property color color: root.textColor
        property real size: Math.round(14 * root.ui)
        readonly property var strokes: ({
            "shuffle": "M3 7 H7 C11 7 13 17 17 17 H21 M3 17 H7 C11 17 13 7 17 7 H21 M18 4 L21 7 L18 10 M18 14 L21 17 L18 20",
            "gear": "M18.5 12 A6.5 6.5 0 1 1 5.5 12 A6.5 6.5 0 1 1 18.5 12 M14.5 12 A2.5 2.5 0 1 1 9.5 12 A2.5 2.5 0 1 1 14.5 12"
                  + " M18.5 12 H22 M16.6 7.4 L19.1 4.9 M12 5.5 V2 M7.4 7.4 L4.9 4.9 M5.5 12 H2 M7.4 16.6 L4.9 19.1 M12 18.5 V22 M16.6 16.6 L19.1 19.1",
            "faders": "M6 3 V21 M12 3 V21 M18 3 V21",
        })
        readonly property var fills: ({
            "faders": "M3.5 13 H8.5 V17 H3.5 Z M9.5 6 H14.5 V10 H9.5 Z M15.5 10.5 H20.5 V14.5 H15.5 Z",
            "pause": "M6.5 4.5 H10 V19.5 H6.5 Z M14 4.5 H17.5 V19.5 H14 Z",
        })
        implicitWidth: size
        implicitHeight: size
        antialiasing: true
        ShapePath {
            strokeColor: icon.strokes[icon.name] ? icon.color : "transparent"
            strokeWidth: 2.2 * icon.size / 24
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            scale: Qt.size(icon.size / 24, icon.size / 24)
            PathSvg { path: icon.strokes[icon.name] || "M0 0" }
        }
        ShapePath {
            strokeColor: "transparent"
            fillColor: icon.fills[icon.name] ? icon.color : "transparent"
            scale: Qt.size(icon.size / 24, icon.size / 24)
            PathSvg { path: icon.fills[icon.name] || "M0 0" }
        }
    }

    component ToolTile: Rectangle {
        id: tile
        property string glyph: ""
        property string icon: ""
        property string caption: ""
        property bool on: false
        property color onColor: root.accentCyan
        property color onFill: root.tileBg
        signal clicked()
        Layout.preferredWidth: Math.round(36 * root.ui)
        Layout.preferredHeight: Math.round(36 * root.ui)
        radius: 4
        color: tile.on ? tile.onFill : (tileMouse.containsMouse ? "#142018" : root.tileBg)
        border.width: 1
        border.color: tile.on ? tile.onColor : (tileMouse.containsMouse ? root.accentGreen : root.tileBorder)
        Behavior on color { ColorAnimation { duration: 100 } }
        Behavior on border.color { ColorAnimation { duration: 100 } }
        Text {
            visible: tile.icon === ""
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: 1
            text: tile.glyph
            color: tile.on ? tile.onColor : (tileMouse.containsMouse ? root.accentGreen : root.textColor)
            font.family: root.mono
            font.pixelSize: Math.round(14 * root.ui)
        }
        Icon {
            visible: tile.icon !== ""
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.topMargin: Math.round(5 * root.ui)
            name: tile.icon
            size: Math.round(14 * root.ui)
            color: tile.on ? tile.onColor : (tileMouse.containsMouse ? root.accentGreen : root.textColor)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 2
            text: tile.caption
            color: tile.on ? tile.onColor : root.dimText
            font.family: root.mono
            font.pixelSize: Math.round(7 * root.ui)
            font.letterSpacing: 1
        }
        MouseArea { id: tileMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: tile.clicked() }
    }

    // A thin fader: value 0..1 of the track, a handle, live on drag.
    component Fader: Item {
        id: fader
        property real ratio: 0
        property color accent: root.accentGreen
        property bool centreMark: false
        signal moved(real ratio)
        Layout.fillWidth: true
        implicitHeight: Math.round(14 * root.ui)
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width; height: Math.round(4 * root.ui); radius: 2
            color: root.darkBg; border.width: 1; border.color: root.tileBorder
        }
        Rectangle {
            visible: fader.centreMark
            x: parent.width / 2; width: 1; height: Math.round(8 * root.ui)
            anchors.verticalCenter: parent.verticalCenter
            color: root.tileBorder
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width * Math.max(0, Math.min(1, fader.ratio)); height: Math.round(4 * root.ui); radius: 2
            color: fader.accent; opacity: 0.6
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: parent.width * Math.max(0, Math.min(1, fader.ratio)) - width / 2
            width: Math.round(8 * root.ui); height: Math.round(12 * root.ui); radius: 2
            color: faderMouse.pressed ? "#2a4e36" : (faderMouse.containsMouse ? "#1a3e26" : "#142018")
            border.width: 1; border.color: fader.accent
        }
        MouseArea {
            id: faderMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            preventStealing: true
            onPressed: function(mouse) { fader.moved(Math.max(0, Math.min(1, mouse.x / width))) }
            onPositionChanged: function(mouse) { if (pressed) fader.moved(Math.max(0, Math.min(1, mouse.x / width))) }
        }
    }

    component SectionHead: RowLayout {
        property string text: ""
        property color accent: root.accentCyan
        property real spacingLetters: 3
        Layout.fillWidth: true
        spacing: 8
        Text {
            text: parent.text
            color: parent.accent
            font.family: root.mono
            font.pixelSize: Math.round(9 * root.ui)
            font.letterSpacing: parent.spacingLetters
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.rgba(parent.accent.r, parent.accent.g, parent.accent.b, 0.12) }
    }

    // ── The window ──
    Flickable {
        id: flick
        objectName: "scroll"
        opacity: root._shown ? 1 : 0       // laid out, not seen, until the window has its size
        readonly property bool needBar: contentHeight > height + 1
        anchors.fill: parent
        contentWidth: width
        contentHeight: root.contentH
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar {
            id: vbar
            policy: flick.needBar ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
            width: Math.round(8 * root.ui)
            contentItem: Rectangle { radius: 3; color: vbar.pressed ? root.accentGreen : Qt.rgba(0, 1, 0.53, 0.35) }
            background: Rectangle { color: root.tileBg }
        }

        // The scroll bar has its own gutter, shown or not, so its coming and
        // going never changes the column's width (and so its wrapping).
        Item {
            width: flick.width - vbar.width
            height: root.contentH

            ColumnLayout {
                id: popupColumn
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                anchors.rightMargin: Math.max(4, 16 - vbar.width)   // the gutter makes up the rest
                spacing: Math.round(12 * root.ui)

                // ── Header ──
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    // The bit family's wordmark: [bit]Name, brackets dim, bit bold.
                    Text {
                        textFormat: Text.StyledText
                        text: "<font color='#2f8f5f'>[</font><b><font color='#00ff88'>bit</font></b><font color='#2f8f5f'>]</font>Composer"
                        color: root.textColor
                        font.family: root.mono
                        font.pixelSize: Math.round(13 * root.ui)
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.rgba(0, 1, 0.53, 0.12) }
                    Rectangle {
                        visible: backend.updateVersion !== ""
                        implicitWidth: updLabel.implicitWidth + 12
                        implicitHeight: Math.round(18 * root.ui)
                        radius: 3
                        color: updMouse.containsMouse ? "#1a2e26" : "transparent"
                        border.width: 1
                        border.color: root.accentPink
                        Text {
                            id: updLabel
                            anchors.centerIn: parent
                            text: backend.updating ? "UPDATING…" : "UPDATE " + backend.updateVersion
                            color: root.accentPink
                            font.family: root.mono
                            font.pixelSize: Math.round(8 * root.ui)
                            font.letterSpacing: 1
                        }
                        MouseArea { id: updMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: backend.applyUpdate() }
                    }
                    Text {
                        text: "v" + backend.version
                        color: root.dimText
                        font.family: root.mono
                        font.pixelSize: Math.round(8 * root.ui)
                    }
                }

                // ── Now Playing ──
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: nowPlayingCol.implicitHeight + 20
                    color: root.tileBg
                    radius: 4
                    border.width: 1
                    border.color: root.tileBorder

                    ColumnLayout {
                        id: nowPlayingCol
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        Text {
                            text: "[ NOW PLAYING ]"
                            color: root.accentCyan
                            font.family: root.mono
                            font.pixelSize: Math.round(9 * root.ui)
                            font.letterSpacing: 2
                            visible: root.trackTitle !== ""
                        }
                        Text {
                            id: titleText
                            Layout.fillWidth: true
                            text: root.trackTitle || "AWAITING SIGNAL..."
                            color: root.trackTitle ? root.accentGreen : root.dimText
                            font.family: root.mono
                            font.pixelSize: Math.round(14 * root.ui)
                            font.bold: true
                            elide: Text.ElideRight
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                running: !root.trackTitle
                                NumberAnimation { to: 0.3; duration: 800 }
                                NumberAnimation { to: 1.0; duration: 800 }
                                onRunningChanged: if (!running) titleText.opacity = 1
                            }
                        }
                        Text {
                            Layout.fillWidth: true
                            visible: root.trackMessage !== ""
                            text: root.trackMessage
                            color: root.textColor
                            font.family: root.mono
                            font.pixelSize: Math.round(9 * root.ui)
                            wrapMode: Text.WordWrap
                        }
                        // What the song drew (intro, form, harmony, bass, echo).
                        Text {
                            Layout.fillWidth: true
                            visible: root.songReadout !== ""
                            text: root.songReadout
                            color: root.dimText
                            font.family: root.mono
                            font.pixelSize: Math.round(8 * root.ui)
                            wrapMode: Text.WordWrap
                        }
                        Text {
                            visible: root.trackArtist !== ""
                            text: "by " + root.trackArtist
                            color: root.textColor
                            font.family: root.mono
                            font.pixelSize: Math.round(10 * root.ui)
                        }
                        Flow {
                            Layout.fillWidth: true
                            visible: root.trackFormat !== ""
                            spacing: 16
                            Text { text: "FMT: " + root.trackFormat.toUpperCase(); color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                            Text { text: "CH: " + root.trackChannels; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                            Text { text: "PAT: " + root.trackPatterns; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                        }
                    }
                }

                // ── Progress Bar ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Item {
                        Layout.fillWidth: true
                        implicitHeight: Math.round(18 * root.ui)
                        Rectangle {
                            id: progressBar
                            anchors.centerIn: parent
                            width: parent.width
                            height: Math.round(6 * root.ui)
                            radius: 3
                            color: root.tileBg
                            border.width: 1
                            border.color: progressMouse.containsMouse ? root.accentGreen : root.tileBorder
                            Behavior on border.color { ColorAnimation { duration: 100 } }
                            Rectangle {
                                width: root.trackDuration > 0 ? progressBar.width * Math.min(1, root.trackPosition / root.trackDuration) : 0
                                height: parent.height
                                radius: 3
                                color: root.accentGreen
                                Rectangle {
                                    anchors.fill: parent
                                    anchors.margins: -1
                                    radius: 4
                                    color: "transparent"
                                    border.width: 1
                                    border.color: Qt.rgba(0, 1, 0.53, 0.3)
                                    visible: parent.width > 0
                                }
                            }
                        }
                        MouseArea {
                            id: progressMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: root.trackDuration > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: function(mouse) {
                                if (root.trackDuration <= 0) return
                                backend.seek(Math.max(0, Math.min(1, mouse.x / width)) * root.trackDuration)
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: formatTime(root.trackPosition); color: root.accentGreen; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                        Item { Layout.fillWidth: true }
                        Text { text: formatTime(root.trackDuration); color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                    }
                }

                // ── Transport Controls ──
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 6
                    Repeater {
                        // The model must not reference changing state, or the
                        // delegates are recreated mid-click.
                        model: ["prev", "playpause", "stop", "next", "shuffle"]
                        Rectangle {
                            required property string modelData
                            property bool isPlayPause: modelData === "playpause"
                            property bool isShuffle: modelData === "shuffle"
                            property string label: {
                                switch (modelData) {
                                    case "prev": return "|◀"
                                    case "playpause": return "▶"
                                    case "stop": return "■"
                                    case "next": return "▶|"
                                    case "shuffle": return ""
                                }
                                return ""
                            }
                            // Drawn instead of a glyph the font lacks.
                            property string iconName: isShuffle ? "shuffle" : (isPlayPause && root.playbackStatus === "Playing") ? "pause" : ""
                            property color tint: {
                                if (isShuffle && root.shuffleOn) return root.accentPink
                                if (isPlayPause && root.playbackStatus === "Playing") return root.accentGreen
                                if (transportMouse.containsMouse) return root.accentGreen
                                return root.textColor
                            }
                            Layout.preferredWidth: Math.round((isPlayPause ? 56 : 42) * root.ui)
                            Layout.preferredHeight: Math.round(32 * root.ui)
                            radius: 4
                            color: transportMouse.containsMouse ? "#142018" : root.tileBg
                            border.width: 1
                            border.color: {
                                if (isShuffle && root.shuffleOn) return root.accentPink
                                if (transportMouse.containsMouse) return root.accentGreen
                                return root.tileBorder
                            }
                            Behavior on color { ColorAnimation { duration: 100 } }
                            Behavior on border.color { ColorAnimation { duration: 100 } }
                            Text {
                                visible: parent.iconName === ""
                                anchors.centerIn: parent
                                text: parent.label
                                color: parent.tint
                                font.family: root.mono
                                font.pixelSize: Math.round((parent.isPlayPause ? 14 : 12) * root.ui)
                            }
                            Icon {
                                visible: parent.iconName !== ""
                                anchors.centerIn: parent
                                name: parent.iconName
                                size: Math.round((parent.isPlayPause ? 14 : 15) * root.ui)
                                color: parent.tint
                            }
                            MouseArea {
                                id: transportMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    switch (modelData) {
                                        case "prev": root.dbusPrevious(); break
                                        case "playpause": root.dbusPlayPause(); break
                                        case "stop": root.dbusStop(); break
                                        case "next": root.dbusNext(); break
                                        case "shuffle": root.dbusToggleShuffle(); break
                                    }
                                }
                            }
                        }
                    }
                }

                // ── Gain ──
                // Linear gain into the output stage. Past 1.0 it boosts, with
                // the engine soft-limiting peaks.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "GAIN"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 1 }
                    Item {
                        Layout.fillWidth: true
                        implicitHeight: Math.round(16 * root.ui)
                        Rectangle {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            height: Math.round(6 * root.ui)
                            radius: 3
                            color: root.tileBg
                            border.width: 1
                            border.color: gainMouse.containsMouse ? root.accentGreen : root.tileBorder
                            Rectangle {
                                width: parent.width * Math.min(1, root.volumeGain / root.maxGain)
                                height: parent.height
                                radius: 3
                                color: root.volumeGain > 1.0 ? root.accentPink : root.accentGreen
                            }
                            Rectangle {   // unity mark
                                x: parent.width / root.maxGain - width / 2
                                width: 2
                                height: parent.height + 4
                                anchors.verticalCenter: parent.verticalCenter
                                color: root.dimText
                            }
                        }
                        MouseArea {
                            id: gainMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            preventStealing: true
                            function _set(mx) {
                                var g = Math.round(Math.max(0, Math.min(1, mx / width)) * root.maxGain * 20) / 20
                                if (Math.abs(g - 1.0) < 0.06) g = 1.0     // snap to unity
                                root.dbusSetVolume(g)
                            }
                            onPressed: function(mouse) { _set(mouse.x) }
                            onPositionChanged: function(mouse) { if (pressed) _set(mouse.x) }
                            onWheel: function(wheel) { root.dbusSetVolume(root.volumeGain + (wheel.angleDelta.y > 0 ? 0.05 : -0.05)) }
                        }
                    }
                    Text {
                        Layout.preferredWidth: Math.round(34 * root.ui)
                        text: Math.round(root.volumeGain * 100) + "%"
                        color: root.volumeGain > 1.0 ? root.accentPink : root.textColor
                        font.family: root.mono
                        font.pixelSize: Math.round(9 * root.ui)
                        horizontalAlignment: Text.AlignRight
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.dbusSetVolume(1.0) }
                    }
                }

                // ── Generate + Settings ──
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(36 * root.ui)
                        radius: 4
                        color: generateMouse.containsMouse ? "#142018" : root.tileBg
                        border.width: 1
                        border.color: root.generating ? root.accentCyan : (generateMouse.containsMouse ? root.accentGreen : root.tileBorder)
                        Behavior on color { ColorAnimation { duration: 100 } }
                        Behavior on border.color { ColorAnimation { duration: 100 } }
                        Text {
                            id: generateText
                            anchors.centerIn: parent
                            width: parent.width - 8
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                            text: root.generating ? "[ GENERATING... ]" : "[ GENERATE NEW TRACK ]"
                            color: root.generating ? root.accentCyan : (generateMouse.containsMouse ? root.accentGreen : root.textColor)
                            font.family: root.mono
                            font.pixelSize: Math.round(10 * root.ui)
                            font.letterSpacing: 2
                            SequentialAnimation on opacity {
                                loops: Animation.Infinite
                                running: root.generating
                                NumberAnimation { to: 0.3; duration: 400 }
                                NumberAnimation { to: 1.0; duration: 400 }
                                onRunningChanged: if (!running) generateText.opacity = 1
                            }
                        }
                        MouseArea {
                            id: generateMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: root.generating ? Qt.BusyCursor : Qt.PointingHandCursor
                            onClicked: root.generateTrack()
                        }
                    }
                    ToolTile {
                        glyph: "∞"; caption: root.autoGenerate ? "ON" : "AUTO"
                        on: root.autoGenerate; onColor: root.accentPink; onFill: "#3a0f1e"
                        onClicked: root.toggleAutoGenerate()
                    }
                    ToolTile {
                        icon: "gear"; caption: "SET"
                        on: root.showSettings; onColor: root.accentCyan
                        onClicked: root.showSettings = !root.showSettings
                    }
                    ToolTile {
                        icon: "faders"; caption: "MIX"
                        on: root.showMaster; onColor: root.accentPink
                        onClicked: root.showMaster = !root.showMaster
                    }
                }

                // ── Settings summary (what GENERATE will do) ──
                Text {
                    Layout.fillWidth: true
                    visible: !root.showSettings
                    text: root.settingsSummary()
                    color: root.dimText
                    font.family: root.mono
                    font.pixelSize: Math.round(8 * root.ui)
                    font.letterSpacing: 1
                    wrapMode: Text.WordWrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                }

                // ── Settings Panel ──
                Rectangle {
                    id: settingsPanel
                    Layout.fillWidth: true
                    visible: root.showSettings
                    implicitHeight: settingsCol.implicitHeight + 16
                    color: root.tileBg
                    radius: 4
                    border.width: 1
                    border.color: root.tileBorder

                    ColumnLayout {
                        id: settingsCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 8
                        spacing: 6

                        Text { text: "PRESETS"; color: root.accentCyan; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 2 }
                        Flow {
                            Layout.fillWidth: true
                            spacing: 3
                            Repeater {
                                model: ["FM DRIVE", "GOTHIC", "BOSS FIGHT", "OVERWORLD", "CHILL WAVE", "DUNGEON", "CREDITS", "FIGHT THEME", "CYBER NOIR", "ANY"]
                                Chip {
                                    required property string modelData
                                    text: modelData
                                    active: root.activePreset === modelData
                                    accent: root.accentPink
                                    onClicked: root.applyPreset(modelData)
                                }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.rgba(0, 1, 0.53, 0.08) }

                        Row {
                            spacing: 2
                            Repeater {
                                model: ["COMPOSE", "DRUMS", "PARTS", "PLAYER"]
                                Rectangle {
                                    required property string modelData
                                    required property int index
                                    property bool active: root.settingsTab === index
                                    width: tabLabel.implicitWidth + 16; height: Math.round(22 * root.ui); radius: 3
                                    color: active ? "#1a2e26" : (tabMa.containsMouse ? "#0f1a16" : "transparent")
                                    border.width: 1; border.color: active ? root.accentCyan : (tabMa.containsMouse ? root.tileBorder : "transparent")
                                    Text { id: tabLabel; anchors.centerIn: parent; text: modelData; color: active ? root.accentCyan : root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 2 }
                                    MouseArea { id: tabMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settingsTab = index }
                                }
                            }
                        }

                        // ── COMPOSE ──
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: root.settingsTab === 0
                            OptionRow { label: "TEMPO"; options: ["random", "slow", "medium", "fast"]; value: root.settTempo; onPicked: function(c) { root.settTempo = c } }
                            OptionRow { label: "ENERGY"; options: ["random", "chill", "normal", "intense"]; value: root.settEnergy; onPicked: function(c) { root.settEnergy = c } }
                            OptionRow { label: "SCALE"; options: ["random", "minor", "major", "pentatonic"]; value: root.settScale; onPicked: function(c) { root.settScale = c } }
                            OptionRow { label: "SOUND"; options: ["random", "chip", "genesis", "snes", "ffvi", "mana", "evermore", "megamanx"]; value: root.settSound; onPicked: function(c) { root.settSound = c } }
                            OptionRow { label: "ECHO"; options: ["random", "on", "off"]; value: root.settEcho; onPicked: function(c) { root.settEcho = c } }
                            OptionRow { label: "WET"; options: ["random", "light", "normal", "wet"]; value: root.settEchoWet; onPicked: function(c) { root.settEchoWet = c } }
                            OptionRow { label: "BASS"; options: ["random", "heavy", "medium", "light"]; value: root.settBassWeight; onPicked: function(c) { root.settBassWeight = c } }
                            OptionRow { label: "FORM"; options: ["random", "standard", "aaba", "rondo", "short", "linear"]; value: root.settForm; onPicked: function(c) { root.settForm = c } }
                        }

                        // ── DRUMS ──
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: root.settingsTab === 1
                            OptionRow { label: "DENSITY"; options: ["random", "sparse", "normal", "busy"]; value: root.settDrumDensity; onPicked: function(c) { root.settDrumDensity = c } }
                            OptionRow { label: "FILLS"; options: ["on", "off"]; value: root.settDrumFills ? "on" : "off"; onPicked: function(c) { root.settDrumFills = (c === "on") } }
                            OptionRow { label: "SWING"; options: ["random", "off", "light", "heavy"]; value: root.settDrumSwing; onPicked: function(c) { root.settDrumSwing = c } }
                        }

                        // ── PARTS: melody and harmony ──
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: root.settingsTab === 2
                            OptionRow { label: "STYLE"; options: ["random", "phrased", "simple"]; value: root.settMelody; onPicked: function(c) { root.settMelody = c } }
                            Text {
                                Layout.fillWidth: true
                                text: root.settMelody === "phrased"
                                    ? "Motif-based melodies with phrase structure, contour shaping, and chorus callbacks"
                                    : root.settMelody === "simple"
                                    ? "Random walk melodies — simpler, more unpredictable"
                                    : "Randomly picks phrased or simple per song"
                                color: root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                wrapMode: Text.WordWrap
                            }
                            OptionRow { label: "VOICING"; options: ["random", "full", "thin"]; value: root.settHarmonyVoicing; onPicked: function(c) { root.settHarmonyVoicing = c } }
                            OptionRow { label: "MODE"; options: ["random", "sustain", "stabs", "rhythmic"]; value: root.settHarmonyMode; onPicked: function(c) { root.settHarmonyMode = c } }
                            Text {
                                Layout.fillWidth: true
                                text: {
                                    var modeDesc = root.settHarmonyMode === "sustain" ? "Sustained pads." : root.settHarmonyMode === "rhythmic" ? "Rhythmic chord hits." : root.settHarmonyMode === "stabs" ? "Short chord stabs." : "Random mode per song."
                                    if (root.settHarmonyVoicing === "full") return "Three-voice chords with counter-melodies. " + modeDesc
                                    if (root.settHarmonyVoicing === "thin") return "Two-voice harmony. " + modeDesc
                                    return "Random voicing per song. " + modeDesc
                                }
                                color: root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                wrapMode: Text.WordWrap
                            }
                        }

                        // ── PLAYER: the program, not the songs ──
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: root.settingsTab === 3
                            OptionRow {
                                visible: backend.autostartSupported
                                label: "LOGIN"; options: ["on", "off"]; value: backend.autostart ? "on" : "off"
                                onPicked: function(c) { if ((c === "on") !== backend.autostart) backend.setAutostart(c === "on") }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: !backend.autostartSupported
                                    ? "Start at login works from an installed copy (pipx or the installer), not from a checkout."
                                    : backend.trayAvailable
                                    ? "Start bitComposer when you log in: in the tray, not playing, so the media keys and the tray menu work from the start."
                                    : "Start bitComposer when you log in, in the background and not playing: the media keys work from the start, and opening bitComposer from the app menu shows it. (This desktop has no system tray; on GNOME the AppIndicator extension adds one.)"
                                color: root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                wrapMode: Text.WordWrap
                            }
                            OptionRow {
                                label: "UPDATES"; options: ["on", "off"]; value: backend.checkUpdates ? "on" : "off"
                                onPicked: function(c) { if ((c === "on") !== backend.checkUpdates) backend.setCheckUpdates(c === "on") }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "At start the player asks GitHub's releases list whether a newer version exists, for the UPDATE button. It sends nothing about you or your music. Off: it never asks."
                                color: root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: "MEDIA KEYS  " + (backend.mediaKeys ? backend.mediaKeys.toUpperCase() : "NOT AVAILABLE HERE")
                                color: backend.mediaKeys ? root.textColor : root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                font.letterSpacing: 1
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                Layout.fillWidth: true
                                text: backend.trayAvailable
                                    ? "Closing the window keeps the music going in the tray; quit from the tray menu."
                                    : "Closing the window quits: this desktop has no system tray to keep it in. Minimize it to keep the music going."
                                color: root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }

                // ── Mix Panel ──
                Rectangle {
                    id: masterPanel
                    Layout.fillWidth: true
                    visible: root.showMaster
                    implicitHeight: masterCol.implicitHeight + 16
                    color: root.tileBg
                    radius: 4
                    border.width: 1
                    border.color: root.tileBorder

                    ColumnLayout {
                        id: masterCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 8
                        spacing: 4

                        SectionHead { text: "CHANNEL MIX"; accent: root.accentPink; spacingLetters: 2 }
                        Text {
                            visible: root.channelCount === 0
                            text: "nothing loaded"
                            color: root.dimText
                            font.family: root.mono
                            font.pixelSize: Math.round(8 * root.ui)
                        }

                        Component {
                            id: channelRow
                            RowLayout {
                                required property int modelData
                                readonly property int ch: modelData
                                readonly property string voice: root.voiceLabel(ch)
                                readonly property color tint: root.channelColor(ch) === 0 ? root.accentGreen : root.channelColor(ch) === 1 ? root.accentCyan : root.accentPink
                                Layout.fillWidth: true
                                spacing: 6
                                // Channel name, with the drawn voice beneath when the file names it
                                Column {
                                    Layout.preferredWidth: root.mixLabelW
                                    spacing: 0
                                    Text {
                                        width: parent.width
                                        text: root.channelLabel(ch)
                                        color: tint
                                        font.family: root.mono
                                        font.pixelSize: Math.round(8 * root.ui)
                                        horizontalAlignment: Text.AlignRight
                                    }
                                    Text {
                                        width: parent.width
                                        visible: voice !== ""
                                        text: voice
                                        color: root.dimText
                                        font.family: root.mono
                                        font.pixelSize: Math.round(7 * root.ui)
                                        horizontalAlignment: Text.AlignRight
                                        elide: Text.ElideLeft
                                    }
                                }
                                Fader {
                                    ratio: (root.channelVolumes[ch] || 0) / 64
                                    accent: tint
                                    onMoved: function(r) { root.applyChannelVolume(ch, Math.round(r * 64)) }
                                }
                                Text {
                                    Layout.preferredWidth: root.mixValueW
                                    text: root.channelVolumes[ch] !== undefined ? root.channelVolumes[ch] : ""
                                    color: root.dimText
                                    font.family: root.mono
                                    font.pixelSize: Math.round(8 * root.ui)
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }

                        // The parts: lead, harmony, bass, arp, counter.
                        Repeater { model: root.partChannels; delegate: channelRow }

                        // KIT bus: the six pieces at once; expand for the pieces.
                        RowLayout {
                            visible: root.kitChannels.length > 0
                            Layout.fillWidth: true
                            spacing: 6
                            Text {
                                Layout.preferredWidth: root.mixLabelW
                                horizontalAlignment: Text.AlignRight
                                text: (root.kitExpanded ? "▾ " : "▸ ") + "KIT"
                                color: root.accentPink
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.kitExpanded = !root.kitExpanded }
                            }
                            Fader {
                                ratio: root.kitBus / 2
                                accent: root.accentPink
                                centreMark: true
                                onMoved: function(r) { root.setKitRatio(Math.round(r * 2 * 20) / 20) }
                            }
                            Text {
                                Layout.preferredWidth: root.mixValueW
                                text: Math.round(root.kitBus * 100) + "%"
                                color: root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(8 * root.ui)
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                        Repeater { model: root.kitExpanded ? root.kitChannels : []; delegate: channelRow }

                        // ECHO bus: every return channel at once; expand for LEAD / HARM / ARP.
                        Repeater {
                            model: root.echoRows
                            delegate: RowLayout {
                                required property string modelData
                                readonly property bool isBus: modelData === "bus"
                                readonly property real ratio: root.echoRatioOf(modelData)
                                Layout.fillWidth: true
                                spacing: 6
                                Text {
                                    Layout.preferredWidth: root.mixLabelW
                                    horizontalAlignment: Text.AlignRight
                                    text: isBus ? ((root.echoExpanded ? "▾ " : "▸ ") + "ECHO")
                                                : (modelData === "melody" ? "LEAD" : modelData === "harmony" ? "HARM" : modelData.toUpperCase())
                                    color: isBus ? root.accentCyan : root.dimText
                                    font.family: root.mono
                                    font.pixelSize: Math.round(8 * root.ui)
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: isBus
                                        cursorShape: isBus ? Qt.PointingHandCursor : Qt.ArrowCursor
                                        onClicked: root.echoExpanded = !root.echoExpanded
                                    }
                                }
                                Fader {
                                    ratio: parent.ratio / 2
                                    accent: root.accentCyan
                                    centreMark: true
                                    onMoved: function(r) { root.setEchoRatio(modelData, Math.round(r * 2 * 20) / 20) }
                                }
                                Text {
                                    Layout.preferredWidth: root.mixValueW
                                    text: Math.round(parent.ratio * 100) + "%"
                                    color: root.dimText
                                    font.family: root.mono
                                    font.pixelSize: Math.round(8 * root.ui)
                                    horizontalAlignment: Text.AlignRight
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.round(26 * root.ui)
                            visible: root.channelCount > 0
                            radius: 3
                            color: saveMasterMouse.containsMouse ? "#142018" : root.darkBg
                            border.width: 1
                            border.color: saveMasterMouse.containsMouse ? root.accentPink : root.tileBorder
                            Text {
                                anchors.centerIn: parent
                                text: "[ APPLY TO TRACK ]"
                                color: saveMasterMouse.containsMouse ? root.accentPink : root.dimText
                                font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 2
                            }
                            MouseArea { id: saveMasterMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root._applyMasterToFile() }
                        }
                    }
                }

                // ── Playlist ──
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    Text { text: "PLAYLIST"; color: root.accentCyan; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 3 }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.rgba(0, 1, 0.53, 0.12) }
                    Text { text: root.playlistInfo.length + " TRACKS"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(8 * root.ui); font.letterSpacing: 1 }
                    Chip { text: "REFRESH"; onClicked: root.rescan() }
                }
                // Where the music lives: click to open it, FOLDER to choose
                // another. Auto-generated tracks are marked and the oldest
                // beyond the limit are pruned; KEEP renames one out of that set.
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    Text {
                        Layout.fillWidth: true
                        text: root.shortDir() + "  ↗"
                        color: dirMouse.containsMouse ? root.accentGreen : root.dimText
                        font.family: root.mono
                        font.pixelSize: Math.round(8 * root.ui)
                        elide: Text.ElideMiddle
                        MouseArea { id: dirMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.openMusicDir() }
                    }
                    Chip { text: "FOLDER"; onClicked: backend.chooseFolder() }
                    Text {
                        text: "AUTO = pruned after " + backend.autogenMax
                        color: Qt.rgba(1, 0, 0.33, 0.5)
                        font.family: root.mono
                        font.pixelSize: Math.round(7 * root.ui)
                        font.letterSpacing: 1
                    }
                }

                ListView {
                    id: playlistView
                    Layout.fillWidth: true
                    // The list grows with the folder up to twelve rows, then
                    // scrolls inside the window's own scroll.
                    Layout.preferredHeight: Math.min(contentHeight, Math.round(26 * root.ui) * 12)
                    clip: true
                    interactive: contentHeight > height
                    boundsBehavior: Flickable.StopAtBounds
                    model: root.playlistInfo
                    ScrollBar.vertical: ScrollBar {
                        id: listBar
                        policy: playlistView.contentHeight > playlistView.height + 1 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                        width: Math.round(6 * root.ui)
                        contentItem: Rectangle { radius: 3; color: Qt.rgba(0, 1, 0.53, 0.35) }
                    }
                    Connections {
                        target: root
                        function onCurrentIndexChanged() {
                            if (root.currentIndex >= 0 && root.currentIndex < playlistView.count)
                                playlistView.positionViewAtIndex(root.currentIndex, ListView.Contain)
                        }
                    }
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        width: playlistView.width - (playlistView.contentHeight > playlistView.height + 1 ? listBar.width : 0)
                        height: Math.round(26 * root.ui)
                        color: rowHover.hovered ? "#142018" : (index === root.currentIndex ? "#0f1a16" : "transparent")
                        radius: 3
                        HoverHandler { id: rowHover }
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 8
                            z: 1
                            Text {
                                text: String(index + 1).padStart(2, '0') + "."
                                color: index === root.currentIndex ? root.accentGreen : root.dimText
                                font.family: root.mono
                                font.pixelSize: Math.round(9 * root.ui)
                            }
                            Text {
                                Layout.fillWidth: true
                                text: modelData.title
                                color: index === root.currentIndex ? root.accentGreen : root.textColor
                                font.family: root.mono
                                font.pixelSize: Math.round(9 * root.ui)
                                elide: Text.ElideRight
                            }
                            Text {
                                visible: modelData.auto && !rowHover.hovered
                                text: "AUTO"
                                color: Qt.rgba(1, 0, 0.33, 0.6)
                                font.family: root.mono
                                font.pixelSize: Math.round(7 * root.ui)
                                font.letterSpacing: 1
                            }
                            Rectangle {
                                visible: modelData.auto && rowHover.hovered
                                implicitWidth: keepLabel.implicitWidth + 10
                                implicitHeight: Math.round(16 * root.ui)
                                radius: 3
                                color: keepMouse.containsMouse ? "#1a2e26" : "transparent"
                                border.width: 1
                                border.color: root.accentPink
                                Text { id: keepLabel; anchors.centerIn: parent; text: "KEEP"; color: root.accentPink; font.family: root.mono; font.pixelSize: Math.round(7 * root.ui); font.letterSpacing: 1 }
                                MouseArea { id: keepMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.keepTrack(index) }
                            }
                            Text {
                                visible: index === root.currentIndex && root.playbackStatus === "Playing"
                                text: "▶"
                                color: root.accentGreen
                                font.pixelSize: Math.round(8 * root.ui)
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.dbusPlayIndex(index)
                        }
                    }
                }
                Text {
                    visible: root.playlistInfo.length === 0
                    Layout.fillWidth: true
                    text: "No songs here yet. GENERATE NEW TRACK makes one, or turn on AUTO."
                    color: root.dimText
                    font.family: root.mono
                    font.pixelSize: Math.round(8 * root.ui)
                    wrapMode: Text.WordWrap
                }

                // ── Footer: the last thing the engine said, then the badge ──
                Text {
                    Layout.fillWidth: true
                    visible: backend.notice !== ""
                    text: backend.notice
                    color: root.dimText
                    font.family: root.mono
                    font.pixelSize: Math.round(8 * root.ui)
                    elide: Text.ElideRight
                }
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: "[16-BIT AUDIO SUBSYSTEM]"
                    color: Qt.rgba(0.314, 0.51, 0.392, 0.25)
                    font.family: root.mono
                    font.pixelSize: Math.round(8 * root.ui)
                    font.letterSpacing: 2
                }
            }
        }
    }

    // ── The update screen ──
    // Over the whole window while an update is asked for, running, or has
    // ended: what will happen, then the work as it happens (the pipx output
    // on Linux, the installer's download on Windows), then the result. The
    // player underneath keeps playing until the update takes over.
    component PanelButton: Rectangle {
        id: pb
        property string text: ""
        property color accent: root.accentGreen
        signal clicked()
        implicitWidth: pbLabel.implicitWidth + Math.round(28 * root.ui)
        implicitHeight: Math.round(32 * root.ui)
        radius: 4
        color: pbMouse.containsMouse ? "#142018" : root.tileBg
        border.width: 1
        border.color: pbMouse.containsMouse ? pb.accent : root.tileBorder
        Text {
            id: pbLabel
            anchors.centerIn: parent
            text: pb.text
            color: pbMouse.containsMouse ? pb.accent : root.textColor
            font.family: root.mono
            font.pixelSize: Math.round(9 * root.ui)
            font.letterSpacing: 2
        }
        MouseArea { id: pbMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: pb.clicked() }
    }

    property double _updStarted: 0
    property int _updElapsed: 0
    Connections {
        target: backend
        function onUpdateChanged() {
            if (backend.updateState === "running" && root._updStarted === 0) { root._updStarted = Date.now(); root._updElapsed = 0 }
            if (backend.updateState !== "running") root._updStarted = 0
        }
    }
    Timer {
        interval: 1000; repeat: true; running: backend.updateState === "running"
        onTriggered: root._updElapsed = Math.round((Date.now() - root._updStarted) / 1000)
    }

    Rectangle {
        id: updatePanel
        objectName: "updatePanel"
        anchors.fill: parent
        visible: backend.updateState !== ""
        color: Qt.rgba(0.02, 0.05, 0.04, 1)
        z: 30
        MouseArea { anchors.fill: parent; hoverEnabled: true; preventStealing: true; onWheel: function(w) { w.accepted = true } }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: Math.round(10 * root.ui)

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text { text: "[ UPDATE ]"; color: root.accentCyan; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); font.letterSpacing: 3 }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Qt.rgba(0, 1, 0.8, 0.15) }
            }
            Text {
                text: "v" + backend.version + "  \u2192  v" + backend.updateVersion
                color: root.accentGreen
                font.family: root.mono
                font.pixelSize: Math.round(14 * root.ui)
                font.bold: true
            }
            Text {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: backend.updateState === "failed" ? root.accentPink : root.textColor
                font.family: root.mono
                font.pixelSize: Math.round(9 * root.ui)
                text: {
                    var st = backend.updateState, kind = backend.updateKind
                    if (st === "confirm") {
                        if (kind === "pipx") return "pipx reinstalls bitComposer at the new version (with Qt, about 80 MB the first time), then the player restarts on it. The music stops while it does."
                        if (kind === "frozen") return "The new installer downloads here, then runs with its own progress window and opens bitComposer again when it is done."
                        return "This copy was not installed by pipx or the installer (a checkout, or a plain pip), so it cannot update itself: update it the way it was installed."
                    }
                    if (st === "running") return (kind === "frozen" ? "Downloading the installer\u2026" : "Updating\u2026") + "  " + root._updElapsed + " s"
                    if (st === "done") return kind === "pipx" ? "Updated. Restarting\u2026" : "The installer is taking over: it shows its progress, then opens bitComposer."
                    if (st === "failed") return "The update did not finish; the player is unchanged. The log says why."
                    return ""
                }
            }

            // Progress: filling when the amount is known (a download), a
            // sweep while it is not (pip says nothing until it is done).
            Rectangle {
                id: updBar
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(6 * root.ui)
                visible: backend.updateState === "running" || backend.updateState === "done"
                radius: 3
                color: root.tileBg
                border.width: 1
                border.color: root.tileBorder
                clip: true
                Rectangle {
                    visible: backend.updateProgress >= 0 || backend.updateState === "done"
                    height: parent.height
                    radius: 3
                    width: parent.width * (backend.updateState === "done" ? 1 : Math.max(0, Math.min(1, backend.updateProgress)))
                    color: root.accentGreen
                    Behavior on width { NumberAnimation { duration: 200 } }
                }
                Rectangle {
                    id: sweep
                    visible: backend.updateProgress < 0 && backend.updateState === "running"
                    height: parent.height
                    width: parent.width * 0.28
                    radius: 3
                    color: root.accentGreen
                    opacity: 0.85
                    SequentialAnimation on x {
                        running: sweep.visible
                        loops: Animation.Infinite
                        NumberAnimation { from: -sweep.width; to: updBar.width; duration: 1400; easing.type: Easing.InOutQuad }
                    }
                }
            }

            // The log, terminal style: the command, then everything it says.
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: backend.updateState !== "confirm"
                color: "#050907"
                radius: 4
                border.width: 1
                border.color: root.tileBorder
                ListView {
                    id: updLog
                    objectName: "updateLog"
                    anchors.fill: parent
                    anchors.margins: 8
                    clip: true
                    model: backend.updateLog
                    boundsBehavior: Flickable.StopAtBounds
                    onCountChanged: Qt.callLater(updLog.positionViewAtEnd)
                    ScrollBar.vertical: ScrollBar { policy: updLog.contentHeight > updLog.height ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff; width: Math.round(6 * root.ui)
                        contentItem: Rectangle { radius: 3; color: Qt.rgba(0, 1, 0.53, 0.35) } }
                    delegate: Text {
                        required property string modelData
                        width: updLog.width - Math.round(8 * root.ui)
                        text: modelData
                        wrapMode: Text.WrapAnywhere
                        color: modelData.indexOf("$ ") === 0 ? root.accentCyan
                             : /failed|error|exited with|not found|could not/i.test(modelData) ? root.accentPink
                             : "#86c7a4"
                        font.family: root.mono
                        font.pixelSize: Math.round(8 * root.ui)
                        lineHeight: 1.15
                    }
                }
            }
            Item { Layout.fillHeight: true; visible: backend.updateState === "confirm" }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 8
                PanelButton {
                    visible: backend.updateState === "confirm" || backend.updateState === "failed"
                    text: backend.updateState === "failed" ? "CLOSE" : "LATER"
                    onClicked: backend.closeUpdate()
                }
                PanelButton {
                    visible: backend.updateState === "failed" || (backend.updateState === "confirm" && backend.updateKind === "other")
                    text: "RELEASE PAGE"
                    accent: root.accentCyan
                    onClicked: backend.openReleasePage()
                }
                PanelButton {
                    objectName: "updateNow"
                    visible: backend.updateState === "confirm" && backend.updateKind !== "other"
                    text: "UPDATE NOW"
                    accent: root.accentPink
                    onClicked: backend.confirmUpdate()
                }
            }
        }
    }

    // Scanline sweep, over everything and taking no input.
    Rectangle {
        visible: !root.still
        anchors.left: parent.left
        anchors.right: parent.right
        height: 1
        color: Qt.rgba(0, 1, 0.53, 0.04)
        z: 10
        SequentialAnimation on y {
            loops: Animation.Infinite
            NumberAnimation { from: 0; to: root.height; duration: 4000; easing.type: Easing.Linear }
        }
    }
}
