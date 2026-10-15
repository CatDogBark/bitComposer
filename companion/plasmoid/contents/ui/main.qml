/*
    Cyberpunk Chiptune Player — KDE Plasma 6 Applet
    Panel widget + popup for controlling the chiptune daemon via D-Bus/MPRIS.
*/

import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PC3
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as P5Support

PlasmoidItem {
    id: root

    // ── State ──
    property string playbackStatus: "Stopped"
    property real trackPosition: 0
    property real trackDuration: 0
    property int trackChannels: 0
    property string trackTitle: ""
    property string trackArtist: ""
    property string trackFormat: ""
    property string trackFile: ""
    property int trackPatterns: 0
    property bool shuffleOn: false
    property int playlistCount: 0
    property int currentIndex: -1
    property var playlistInfo: []      // [{file, title, auto}] from GetPlaylistInfo
    property string trackMessage: ""   // key / BPM / palette / form, from the module's song message
    property real volumeGain: 1.0      // 1.0 = unity, up to maxGain (boost)
    readonly property real maxGain: 3.0

    // ── Scale ──
    // Every size here is a pixel count tuned at 1x. Kirigami's grid unit
    // tracks the font DPI (about 18 px at 1x), so scaling by it keeps the
    // widget the same physical size next to the rest of Plasma on HiDPI.
    readonly property real ui: Math.max(1, Kirigami.Units.gridUnit / 18)

    // ── Colors ──
    readonly property color accentGreen: "#00ff88"
    readonly property color accentCyan: "#00ffcc"
    readonly property color accentPink: "#ff0055"
    readonly property color textColor: "#b0ddcc"
    readonly property color dimText: "#508264"
    readonly property color tileBg: "#0e1612"
    readonly property color tileBorder: "#1a2e26"
    readonly property color darkBg: "#0a100e"

    // ── D-Bus via qdbus6 (fast, ~4ms per call) ──
    readonly property string busName: "org.mpris.MediaPlayer2.CyberpunkChiptune"
    readonly property string busPath: "/org/mpris/MediaPlayer2"
    readonly property string playerIface: "org.mpris.MediaPlayer2.Player"

    // Cooldown: ignore polls briefly after a command so optimistic state isn't
    // overwritten. A qdbus6 round trip is under 20 ms and polls run every
    // 500 ms, so 400 ms is plenty; 800 made the progress bar lag after seeks.
    property bool cooldown: false
    Timer {
        id: cooldownTimer
        interval: 400
        onTriggered: root.cooldown = false
    }
    function startCooldown() {
        root.cooldown = true
        cooldownTimer.restart()
    }

    function dbusCmd(method) {
        cmdSource.connectSource("qdbus6 " + busName + " " + busPath + " " + playerIface + "." + method)
    }
    function dbusCustom(method) {
        cmdSource.connectSource("qdbus6 " + busName + " " + busPath + " " + busName + "." + method)
    }

    function dbusPlayPause() {
        root.playbackStatus = (root.playbackStatus === "Playing") ? "Paused" : "Playing"
        startCooldown()
        dbusCmd("PlayPause")
    }
    function dbusStop() {
        root.playbackStatus = "Stopped"
        startCooldown()
        dbusCmd("Stop")
    }
    function dbusNext() {
        root.trackTitle = "..."
        startCooldown()
        dbusCmd("Next")
    }
    function dbusPrevious() {
        startCooldown()
        dbusCmd("Previous")
    }
    function dbusToggleShuffle() {
        root.shuffleOn = !root.shuffleOn
        startCooldown()
        cmdSource.connectSource("qdbus6 " + busName + " " + busPath
            + " org.freedesktop.DBus.Properties.Set " + playerIface
            + " Shuffle " + root.shuffleOn)
    }
    function dbusSetVolume(gain) {
        gain = Math.max(0, Math.min(maxGain, gain))
        root.volumeGain = gain
        startCooldown()
        cmdSource.connectSource("qdbus6 " + busName + " " + busPath
            + " org.freedesktop.DBus.Properties.Set " + playerIface
            + " Volume " + gain.toFixed(2))
    }
    function dbusPlayIndex(idx) {
        root.currentIndex = idx
        root.playbackStatus = "Playing"
        startCooldown()
        dbusCustom("PlayIndex " + idx)
    }

    // ── Generate ──
    property bool generating: false
    property bool autoGenerate: false
    property bool showSettings: false
    property bool showMaster: false
    property int settingsTab: Math.min(2, Plasmoid.configuration.settingsTab)  // 0=COMPOSE, 1=DRUMS, 2=PARTS
    onSettingsTabChanged: Plasmoid.configuration.settingsTab = settingsTab

    // Channel volumes for mastering (0-64, matches IT header bytes 128-191).
    // The channel layout comes from the daemon's GetLayout (the "layout:" line
    // bitcomposer writes into the song message), so the mixer follows whatever
    // the composer wrote: 14 channels for older files, 19 with the echo sends.
    // Roles starting with "echo." are returns; they do not get faders of their
    // own but fold into one ECHO bus (with an expand to LEAD / HARM / ARP).
    property var layout: ["melody", "harmony", "harmony", "harmony", "bass", "arp", "kick", "snare", "hihat", "tom", "crash", "openhat", "echo.melody", "echo.melody"]
    property var channelVolumes: [13, 25, 25, 25, 8, 33, 36, 36, 36, 36, 36, 36, 13, 13]
    readonly property int channelCount: layout.length
    readonly property var dryChannels: { var a = []; for (var i = 0; i < layout.length; i++) if (String(layout[i]).indexOf("echo.") !== 0) a.push(i); return a }
    readonly property var echoChannels: { var a = []; for (var i = 0; i < layout.length; i++) if (String(layout[i]).indexOf("echo.") === 0) a.push(i); return a }
    readonly property var echoGroups: { var g = []; for (var i = 0; i < echoChannels.length; i++) { var r = String(layout[echoChannels[i]]).substring(5); if (g.indexOf(r) < 0) g.push(r) } return g }
    // The bus and group faders are ratios against the mix the file was
    // written with (echoBase), 0 = off, 1 = as written, 2 = double.
    property var echoBase: []
    property real echoBus: 1.0
    property var echoGroupRatio: ({})
    property bool echoExpanded: false
    readonly property var echoRows: echoChannels.length ? ["bus"].concat(echoExpanded ? echoGroups : []) : []
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
        if (r === "harmony" || r.indexOf("echo.") === 0) return 1
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
    function _resetEchoRatios() { echoBase = channelVolumes.slice(); echoBus = 1.0; echoGroupRatio = ({}); echoGroupRatioChanged() }

    // Sliders are live: each change goes to the daemon, which sets the
    // channel's volume on the playing module at once. Sends are coalesced
    // so a drag does not spawn a qdbus6 process per pixel. APPLY TO TRACK
    // then writes the same numbers into the file so they persist.
    property var _pendingMix: ({})
    Timer {
        id: mixFlush
        interval: 60
        onTriggered: {
            for (var ch in root._pendingMix)
                root.dbusCustom("SetChannelVolume " + ch + " " + root._pendingMix[ch])
            root._pendingMix = ({})
        }
    }
    function applyChannelVolume(channel, value) {
        if (channelVolumes[channel] === value) return
        channelVolumes[channel] = value
        channelVolumesChanged()
        _pendingMix[channel] = value
        mixFlush.restart()
    }

    property string musicDir: ""   // installer writes a fallback; the daemon reports the live one
    function shortDir() {
        if (!root.musicDir) return "waiting for daemon…"
        var d = root.musicDir.replace(/\/$/, "")
        var m = d.match(/^\/home\/[^\/]+\//)
        return m ? "~/" + d.substring(m[0].length) : d
    }

    function _trackPath() {
        if (!root.trackFile) return ""
        // trackFile may be just a filename or a full path
        if (root.trackFile.startsWith("/")) return root.trackFile
        return root.musicDir + root.trackFile
    }

    function _applyMasterToFile() {
        var path = _trackPath()
        if (!path) return
        var cmd = "bitcomposer-master.sh '" + path.replace(/'/g, "'\\''") + "'"
        for (var i = 0; i < channelCount; i++) cmd += " " + channelVolumes[i]
        masterSource.connectSource(cmd)
        _resetEchoRatios()   // the written mix is now the base the bus scales
    }

    function _loadMasterFromFile() {
        if (!_trackPath()) return
        // The layout first (it sets channelCount), then the header block.
        layoutSource.connectSource("qdbus6 " + busName + " " + busPath + " " + busName + ".GetLayout")
    }
    function _readMixFromFile() {
        var path = _trackPath()
        if (!path) return
        // Read the per-channel volume block straight from the file header.
        var cmd = "od -An -tu1 -j128 -N" + channelCount + " '" + path.replace(/'/g, "'\\''") + "'"
        masterLoadSource.connectSource(cmd)
    }

    P5Support.DataSource {
        id: layoutSource
        engine: "executable"
        onNewData: function(source, data) {
            disconnectSource(source)
            var lines = (data["stdout"] || "").split("\n").map(function(l) { return l.trim() }).filter(function(l) { return l.length })
            if (lines.length) root.layout = lines
            root._readMixFromFile()
        }
    }

    P5Support.DataSource {
        id: masterSource
        engine: "executable"
        onNewData: function(source, data) { disconnectSource(source) }
    }

    P5Support.DataSource {
        id: masterLoadSource
        engine: "executable"
        onNewData: function(source, data) {
            disconnectSource(source)
            var stdout = (data["stdout"] || "").trim()
            if (!stdout) return
            var parts = stdout.split(/\s+/)
            if (parts.length >= channelCount) {
                var vols = []
                for (var i = 0; i < channelCount; i++)
                    vols.push(parseInt(parts[i]) || 0)
                root.channelVolumes = vols
                root._resetEchoRatios()
                // Reopening the panel shows the file's mix; make the live mix match it.
                for (var c = 0; c < channelCount; c++) root._pendingMix[c] = vols[c]
                mixFlush.restart()
            }
        }
    }
    property string settTempo: Plasmoid.configuration.settTempo
    property string settEnergy: Plasmoid.configuration.settEnergy
    property string settScale: Plasmoid.configuration.settScale
    property string settStyle: Plasmoid.configuration.settStyle
    property string settDrumDensity: Plasmoid.configuration.settDrumDensity
    property bool settDrumFills: Plasmoid.configuration.settDrumFills
    property string settDrumSwing: Plasmoid.configuration.settDrumSwing
    property string settMelody: Plasmoid.configuration.settMelody
    property string settHarmonyVoicing: Plasmoid.configuration.settHarmonyVoicing
    property string settHarmonyMode: Plasmoid.configuration.settHarmonyMode
    property string settBassWeight: Plasmoid.configuration.settBassWeight
    property string settForm: Plasmoid.configuration.settForm
    property string settEcho: Plasmoid.configuration.settEcho
    property string settPack: Plasmoid.configuration.settPack
    property string settEchoWet: Plasmoid.configuration.settEchoWet
    property string activePreset: Plasmoid.configuration.activePreset
    onActivePresetChanged: Plasmoid.configuration.activePreset = activePreset
    function _onSettingChanged() {
        if (!_applyingPreset) activePreset = ""
        if (autoGenerate) _pushAutoGenSettings()
    }
    function _pushAutoGenSettings() {
        var flags = _buildSettingsFlags()
        cmdSource.connectSource("qdbus6 " + busName + " " + busPath + " "
            + busName + ".SetAutoGenerate true '" + flags.trim() + "'")
    }
    onTrackFileChanged: if (showMaster) _loadMasterFromFile()
    onShowMasterChanged: if (showMaster) _loadMasterFromFile()
    onSettTempoChanged: { Plasmoid.configuration.settTempo = settTempo; _onSettingChanged() }
    onSettEnergyChanged: { Plasmoid.configuration.settEnergy = settEnergy; _onSettingChanged() }
    onSettScaleChanged: { Plasmoid.configuration.settScale = settScale; _onSettingChanged() }
    onSettStyleChanged: { Plasmoid.configuration.settStyle = settStyle; _onSettingChanged() }
    onSettDrumDensityChanged: { Plasmoid.configuration.settDrumDensity = settDrumDensity; _onSettingChanged() }
    onSettDrumFillsChanged: { Plasmoid.configuration.settDrumFills = settDrumFills; _onSettingChanged() }
    onSettDrumSwingChanged: { Plasmoid.configuration.settDrumSwing = settDrumSwing; _onSettingChanged() }
    onSettMelodyChanged: { Plasmoid.configuration.settMelody = settMelody; _onSettingChanged() }
    onSettHarmonyVoicingChanged: { Plasmoid.configuration.settHarmonyVoicing = settHarmonyVoicing; _onSettingChanged() }
    onSettHarmonyModeChanged: { Plasmoid.configuration.settHarmonyMode = settHarmonyMode; _onSettingChanged() }
    onSettBassWeightChanged: { Plasmoid.configuration.settBassWeight = settBassWeight; _onSettingChanged() }
    onSettFormChanged: { Plasmoid.configuration.settForm = settForm; _onSettingChanged() }
    onSettEchoChanged: { Plasmoid.configuration.settEcho = settEcho; _onSettingChanged() }
    onSettPackChanged: { Plasmoid.configuration.settPack = settPack; _onSettingChanged() }
    onSettEchoWetChanged: { Plasmoid.configuration.settEchoWet = settEchoWet; _onSettingChanged() }
    property bool _applyingPreset: false

    function applyPreset(name) {
        var presets = {
            "FM DRIVE":     { tempo: "fast",   energy: "intense", scale: "minor",      style: "genesis", drumDensity: "busy",   fills: true,  swing: "light",  melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "standard" },
            "GOTHIC":       { tempo: "medium", energy: "normal",  scale: "minor",      style: "random",  drumDensity: "normal", fills: true,  swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "rondo"    },
            "BOSS FIGHT":   { tempo: "fast",   energy: "intense", scale: "minor",      style: "genesis", drumDensity: "busy",   fills: true,  swing: "heavy",  melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "short"    },
            "OVERWORLD":    { tempo: "medium", energy: "normal",  scale: "major",      style: "snes",    drumDensity: "normal", fills: true,  swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "standard" },
            "CHILL WAVE":   { tempo: "slow",   energy: "chill",   scale: "pentatonic", style: "snes",    drumDensity: "sparse", fills: false, swing: "light",  melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba"     },
            "DUNGEON":      { tempo: "slow",   energy: "chill",   scale: "minor",      style: "random",  drumDensity: "sparse", fills: false, swing: "off",    melody: "phrased", voicing: "thin", mode: "stabs",    bass: "medium", form: "rondo"    },
            "CREDITS":      { tempo: "slow",   energy: "chill",   scale: "major",      style: "snes",    drumDensity: "sparse", fills: false, swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba"     },
            "FIGHT THEME":  { tempo: "fast",   energy: "intense", scale: "pentatonic", style: "genesis", drumDensity: "busy",   fills: true,  swing: "heavy",  melody: "phrased", voicing: "full", mode: "stabs",    bass: "heavy",  form: "short"    },
            "CYBER NOIR":   { tempo: "medium", energy: "normal",  scale: "minor",      style: "genesis", drumDensity: "normal", fills: true,  swing: "light",  melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "linear"   },
            "ANY":          { tempo: "random", energy: "random",  scale: "random",     style: "random",  drumDensity: "random", fills: true,  swing: "random", melody: "random",  voicing: "random", mode: "random", bass: "random", form: "random"   },
        }
        var p = presets[name]
        if (!p) return
        root._applyingPreset = true
        root.settTempo = p.tempo
        root.settEnergy = p.energy
        root.settScale = p.scale
        root.settStyle = p.style
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
        if (settStyle !== "random") flags += " --style " + settStyle
        if (settDrumDensity !== "random") flags += " --drum-density " + settDrumDensity
        if (!settDrumFills) flags += " --no-fills"
        if (settDrumSwing !== "random") flags += " --swing " + settDrumSwing
        if (settMelody !== "random") flags += " --melody " + settMelody
        if (settHarmonyVoicing !== "random") flags += " --harmony-voicing " + settHarmonyVoicing
        if (settHarmonyMode !== "random") flags += " --harmony-mode " + settHarmonyMode
        if (settBassWeight !== "random") flags += " --bass-weight " + settBassWeight
        if (settForm !== "random") flags += " --form " + settForm
        if (settEcho !== "random") flags += " --echo " + settEcho
        if (settPack !== "random") flags += " --pack " + settPack
        if (settEchoWet !== "random") flags += " --echo-wet " + settEchoWet
        return flags
    }

    // One line describing what GENERATE will do, shown while the settings
    // panel is closed. The preset name if one is active, otherwise every
    // setting that is not left to chance.
    function settingsSummary() {
        var prefix = ""
        if (autoGenerate)
            prefix = (playbackStatus === "Playing" ? "AUTO: next track generates when this one ends" : "AUTO: generates when playback stops") + "   |   "
        if (activePreset && activePreset !== "ANY") return prefix + activePreset
        var parts = []
        if (settTempo !== "random") parts.push(settTempo)
        if (settEnergy !== "random") parts.push(settEnergy)
        if (settScale !== "random") parts.push(settScale)
        if (settStyle !== "random") parts.push(settStyle)
        if (settDrumDensity !== "random") parts.push(settDrumDensity + " drums")
        if (!settDrumFills) parts.push("no fills")
        if (settDrumSwing !== "random") parts.push(settDrumSwing + " swing")
        if (settMelody !== "random") parts.push(settMelody + " melody")
        if (settHarmonyVoicing !== "random") parts.push(settHarmonyVoicing + " harmony")
        if (settHarmonyMode !== "random") parts.push(settHarmonyMode)
        if (settBassWeight !== "random") parts.push(settBassWeight + " bass")
        if (settForm !== "random") parts.push(settForm + " form")
        if (settEcho !== "random") parts.push("echo " + settEcho)
        if (settPack !== "random") parts.push(settPack === "none" ? "no pack" : settPack + " pack")
        if (settEchoWet !== "random") parts.push(settEchoWet + " echo")
        return prefix + (parts.length ? parts.join("  ·  ") : "any  ·  everything left to chance")
    }

    function refreshPlaylist() {
        playlistSource.connectedSources = []
        playlistSource.connectedSources = [
            "qdbus6 " + root.busName + " " + root.busPath + " " + root.busName + ".GetPlaylistInfo"
        ]
    }
    function keepTrack(idx) {
        startCooldown()
        dbusCustom("KeepTrack " + idx)
        keepRefresh.restart()
    }
    Timer { id: keepRefresh; interval: 300; onTriggered: root.refreshPlaylist() }
    function rescan() {
        startCooldown()
        dbusCustom("Rescan")
        keepRefresh.restart()   // re-read the playlist once the daemon has rescanned
    }
    function openMusicDir() {
        cmdSource.connectSource("xdg-open '" + root.musicDir.replace(/'/g, "'\\''") + "'")
    }

    function generateTrack() {
        if (root.generating) return
        root.generating = true
        var cmd = "bitcomposer-generate.sh"
        if (root.autoGenerate) cmd += " --auto"
        cmd += _buildSettingsFlags()
        generateSource.connectSource(cmd)
    }

    // A second click within the debounce window is ignored: a bounce or an
    // impatient re-click used to flip it straight back off.
    property bool _autoDebounce: false
    Timer { id: autoDebounceTimer; interval: 500; onTriggered: root._autoDebounce = false }
    function toggleAutoGenerate() {
        if (root._autoDebounce) return
        root._autoDebounce = true
        autoDebounceTimer.restart()
        root.autoGenerate = !root.autoGenerate
        startCooldown()
        var flags = _buildSettingsFlags()
        cmdSource.connectSource("qdbus6 " + busName + " " + busPath + " "
            + busName + ".SetAutoGenerate " + root.autoGenerate + " '"
            + flags.trim() + "'")
    }

    P5Support.DataSource {
        id: generateSource
        engine: "executable"
        onNewData: function(source, data) {
            disconnectSource(source)
            root.generating = false
            startCooldown()
            root.refreshPlaylist()
        }
    }

    // ── State polling (qdbus6 — ~4ms, every 500ms) ──
    P5Support.DataSource {
        id: stateSource
        engine: "executable"
        connectedSources: [
            "qdbus6 " + root.busName + " " + root.busPath + " " + root.busName + ".GetState"
        ]
        interval: 500

        onNewData: function(source, data) {
            var stdout = (data["stdout"] || "").trim()
            if (!stdout) return
            var parts = stdout.split("|")
            if (parts.length < 12) return

            // Skip all state updates during cooldown to prevent flicker
            if (root.cooldown) return

            root.trackPosition = parseFloat(parts[1]) || 0
            root.trackDuration = parseFloat(parts[2]) || 0

            root.playbackStatus = parts[0]
            root.trackChannels = parseInt(parts[3]) || 0
            root.trackTitle = parts[4]
            root.trackArtist = parts[5]
            root.trackFormat = parts[6]
            root.trackFile = parts[7]
            root.trackPatterns = parseInt(parts[8]) || 0
            root.shuffleOn = parts[9] === "1"
            root.playlistCount = parseInt(parts[10]) || 0
            root.currentIndex = parseInt(parts[11]) || 0
            if (parts.length > 12) root.autoGenerate = parts[12] === "1"
            if (parts.length > 13) {
                var g = parseFloat(parts[13])
                if (!isNaN(g)) root.volumeGain = g
            }
            if (parts.length > 14) root.trackMessage = parts[14]
            if (parts.length > 15 && parts[15]) {
                var d = parts[15]
                root.musicDir = d.endsWith("/") ? d : d + "/"
            }
        }
    }

    // Playlist polling (less frequent)
    P5Support.DataSource {
        id: playlistSource
        engine: "executable"
        connectedSources: [
            "qdbus6 " + root.busName + " " + root.busPath + " " + root.busName + ".GetPlaylistInfo"
        ]
        interval: 2000

        onNewData: function(source, data) {
            var stdout = (data["stdout"] || "").trim()
            var rows = []
            if (stdout) {
                var lines = stdout.split("\n")
                for (var i = 0; i < lines.length; i++) {
                    var f = lines[i].split("|")
                    rows.push({ file: f[0], title: f.length > 1 && f[1] ? f[1] : f[0],
                                auto: f.length > 2 && f[2] === "1" })
                }
            }
            root.playlistInfo = rows
        }
    }

    // Fire-and-forget command source
    P5Support.DataSource {
        id: cmdSource
        engine: "executable"
        onNewData: function(source, data) {
            disconnectSource(source)
        }
    }

    // ── Helper ──
    function formatTime(secs) {
        var m = Math.floor(secs / 60)
        var s = Math.floor(secs % 60)
        return String(m).padStart(2, '0') + ":" + String(s).padStart(2, '0')
    }

    // ── Compact Representation (panel) ──
    compactRepresentation: MouseArea {
        id: compactRoot
        Layout.minimumWidth: compactRow.implicitWidth + 16
        Layout.preferredWidth: compactRow.implicitWidth + 16
        Layout.fillHeight: true
        acceptedButtons: Qt.LeftButton
        onClicked: root.expanded = !root.expanded

        Rectangle {
            anchors.fill: parent
            color: root.darkBg
            radius: 3
            border.width: 1
            border.color: root.tileBorder
        }

        RowLayout {
            id: compactRow
            anchors.centerIn: parent
            spacing: 8

            // Play state icon
            Text {
                text: root.playbackStatus === "Playing" ? "▶" :
                      root.playbackStatus === "Paused" ? "❚❚" : "■"
                color: root.playbackStatus === "Playing" ? root.accentGreen :
                       root.playbackStatus === "Paused" ? root.accentCyan : root.dimText
                font.pixelSize: Math.round(10 * root.ui)

                SequentialAnimation on opacity {
                    loops: root.playbackStatus === "Paused" ? Animation.Infinite : 0
                    running: root.playbackStatus === "Paused"
                    NumberAnimation { to: 0.3; duration: 530 }
                    NumberAnimation { to: 1.0; duration: 530 }
                    onRunningChanged: if (!running) parent.opacity = 1
                }
            }

            // Track title
            Text {
                Layout.maximumWidth: 180
                text: root.trackTitle || "NO SIGNAL"
                color: root.trackTitle ? root.textColor : root.dimText
                font.family: "JetBrains Mono"
                font.pixelSize: Math.round(11 * root.ui)
                elide: Text.ElideRight
            }

            // Time
            Text {
                visible: root.trackDuration > 0
                text: formatTime(root.trackPosition)
                color: root.dimText
                font.family: "JetBrains Mono"
                font.pixelSize: Math.round(9 * root.ui)
            }
        }
    }

    // ── Full Representation (popup) ──
    fullRepresentation: Rectangle {
        id: popup
        // Plasma sizes the popup from these hints, not from implicitWidth;
        // without them it fell back to its own default and the popup came
        // up far wider than the content needs.
        implicitWidth: 360 * root.ui
        implicitHeight: popupColumn.implicitHeight + 40
        Layout.preferredWidth: 360 * root.ui
        Layout.minimumWidth: 320 * root.ui
        Layout.maximumWidth: 440 * root.ui
        Layout.preferredHeight: implicitHeight
        Layout.minimumHeight: Math.min(implicitHeight, 520 * root.ui)
        color: root.darkBg
        border.width: 1
        border.color: root.tileBorder
        radius: 6

        // Scanline effect
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(0, 1, 0.53, 0.04)
            y: 0
            z: 10
            SequentialAnimation on y {
                loops: Animation.Infinite
                NumberAnimation { from: 0; to: popup.height; duration: 4000; easing.type: Easing.Linear }
            }
        }

        ColumnLayout {
            id: popupColumn
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            // ── Header ──
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: "CHIPTUNE PLAYER"
                    color: root.accentCyan
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(10 * root.ui)
                    font.letterSpacing: 4
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(0, 1, 0.53, 0.12) }
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
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(9 * root.ui)
                        font.letterSpacing: 2
                        visible: root.trackTitle !== ""
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.trackTitle || "AWAITING SIGNAL..."
                        color: root.trackTitle ? root.accentGreen : root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(14 * root.ui)
                        font.bold: true
                        elide: Text.ElideRight

                        SequentialAnimation on opacity {
                            loops: root.trackTitle ? 0 : Animation.Infinite
                            running: !root.trackTitle
                            NumberAnimation { to: 0.3; duration: 800 }
                            NumberAnimation { to: 1.0; duration: 800 }
                            onRunningChanged: if (!running) parent.opacity = 1
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.trackMessage !== ""
                        text: root.trackMessage
                        color: root.textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(9 * root.ui)
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        visible: root.trackArtist !== ""
                        text: "by " + root.trackArtist
                        color: root.textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(10 * root.ui)
                    }

                    RowLayout {
                        visible: root.trackFormat !== ""
                        spacing: 16
                        Text {
                            text: "FMT: " + root.trackFormat.toUpperCase()
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(9 * root.ui)
                        }
                        Text {
                            text: "CH: " + root.trackChannels
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(9 * root.ui)
                        }
                        Text {
                            text: "PAT: " + root.trackPatterns
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(9 * root.ui)
                        }
                    }
                }
            }

            // ── Progress Bar ──
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4

                // Click target wrapper — taller than the visual bar for easy clicking
                Item {
                    Layout.fillWidth: true
                    height: 18
                    property bool seeking: false

                    Rectangle {
                        id: progressBar
                        anchors.centerIn: parent
                        width: parent.width
                        height: 6
                        radius: 3
                        color: root.tileBg
                        border.width: 1
                        border.color: progressMouse.containsMouse ? root.accentGreen : root.tileBorder

                        Behavior on border.color { ColorAnimation { duration: 100 } }

                        Rectangle {
                            id: progressFill
                            width: root.trackDuration > 0
                                ? progressBar.width * (root.trackPosition / root.trackDuration)
                                : 0
                            height: parent.height
                            radius: 3
                            color: root.accentGreen

                            // Glow
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
                            var ratio = Math.max(0, Math.min(1, mouse.x / width))
                            var seekTo = ratio * root.trackDuration
                            startCooldown()
                            root.trackPosition = seekTo
                            cmdSource.connectSource("qdbus6 " + root.busName + " " + root.busPath
                                + " " + root.playerIface + ".SetPosition /org/cyberpunk/chiptune/track/"
                                + root.currentIndex + " " + Math.floor(seekTo * 1000000))
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: formatTime(root.trackPosition)
                        color: root.accentGreen
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(9 * root.ui)
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: formatTime(root.trackDuration)
                        color: root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(9 * root.ui)
                    }
                }
            }

            // ── Transport Controls ──
            RowLayout {
                Layout.alignment: Qt.AlignHCenter
                spacing: 6

                Repeater {
                    // IMPORTANT: model must NOT reference playbackStatus or any
                    // changing property — that causes delegate recreation and
                    // duplicate click events. Dynamic state is read in the delegates.
                    model: [
                        { role: "prev" },
                        { role: "playpause" },
                        { role: "stop" },
                        { role: "next" },
                        { role: "shuffle" }
                    ]

                    Rectangle {
                        required property var modelData
                        required property int index

                        property bool isPlayPause: modelData.role === "playpause"
                        property bool isShuffle: modelData.role === "shuffle"
                        property string label: {
                            switch (modelData.role) {
                                case "prev": return "|◀"
                                case "playpause": return root.playbackStatus === "Playing" ? "❚❚" : "▶"
                                case "stop": return "■"
                                case "next": return "▶|"
                                case "shuffle": return "⟳"
                            }
                        }

                        width: isPlayPause ? 56 : 42
                        height: 32
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
                            anchors.centerIn: parent
                            text: parent.label
                            color: {
                                if (parent.isShuffle && root.shuffleOn) return root.accentPink
                                if (parent.isPlayPause && root.playbackStatus === "Playing")
                                    return root.accentGreen
                                if (transportMouse.containsMouse) return root.accentGreen
                                return root.textColor
                            }
                            font.family: "JetBrains Mono"
                            font.pixelSize: parent.isPlayPause ? 14 : 12

                            Behavior on color { ColorAnimation { duration: 100 } }
                        }

                        MouseArea {
                            id: transportMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                switch (modelData.role) {
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
            // Linear gain into the daemon's output stage. Past 1.0 it boosts,
            // with the daemon soft-limiting peaks; generated modules sit around
            // -6 to -9 dBFS, so unity sounded quiet next to everything else.
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: "GAIN"
                    color: root.dimText
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(9 * root.ui)
                    font.letterSpacing: 1
                }
                Item {
                    id: gainTrack
                    Layout.fillWidth: true
                    height: 16
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width
                        height: 6
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
                        // unity mark
                        Rectangle {
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
                            var ratio = Math.max(0, Math.min(1, mx / width))
                            var g = Math.round(ratio * root.maxGain * 20) / 20   // 0.05 steps
                            // snap to unity when close
                            if (Math.abs(g - 1.0) < 0.06) g = 1.0
                            root.dbusSetVolume(g)
                        }
                        onPressed: function(mouse) { _set(mouse.x) }
                        onPositionChanged: function(mouse) { if (pressed) _set(mouse.x) }
                        onWheel: function(wheel) {
                            root.dbusSetVolume(root.volumeGain + (wheel.angleDelta.y > 0 ? 0.05 : -0.05))
                        }
                    }
                }
                Text {
                    Layout.preferredWidth: 34
                    text: Math.round(root.volumeGain * 100) + "%"
                    color: root.volumeGain > 1.0 ? root.accentPink : root.textColor
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(9 * root.ui)
                    horizontalAlignment: Text.AlignRight
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.dbusSetVolume(1.0)   // click the number to reset
                    }
                }
            }

            // ── Generate + Settings ──
            RowLayout {
                Layout.fillWidth: true
                spacing: 4

                // Generate button
                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    radius: 4
                    color: generateMouse.containsMouse ? "#142018" : root.tileBg
                    border.width: 1
                    border.color: root.generating ? root.accentCyan :
                        (generateMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.centerIn: parent
                        text: root.generating ? "[ GENERATING... ]" : "[ GENERATE NEW TRACK ]"
                        color: root.generating ? root.accentCyan :
                            (generateMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(10 * root.ui)
                        font.letterSpacing: 2

                        Behavior on color { ColorAnimation { duration: 100 } }

                        SequentialAnimation on opacity {
                            loops: root.generating ? Animation.Infinite : 0
                            running: root.generating
                            NumberAnimation { to: 0.3; duration: 400 }
                            NumberAnimation { to: 1.0; duration: 400 }
                            onRunningChanged: if (!running) parent.opacity = 1
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

                // Auto-generate toggle button
                Rectangle {
                    width: 36
                    height: 36
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: 4
                    color: root.autoGenerate ? "#3a0f1e" : (autoGenMouse.containsMouse ? "#142018" : root.tileBg)
                    border.width: 1
                    border.color: root.autoGenerate ? root.accentPink :
                        (autoGenMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 1
                        text: "∞"
                        color: root.autoGenerate ? root.accentPink :
                            (autoGenMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.pixelSize: Math.round(15 * root.ui)
                        font.bold: root.autoGenerate

                        Behavior on color { ColorAnimation { duration: 100 } }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
                        text: root.autoGenerate ? "ON" : "AUTO"
                        color: root.autoGenerate ? root.accentPink : root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(7 * root.ui)
                        font.letterSpacing: 1
                    }

                    MouseArea {
                        id: autoGenMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.toggleAutoGenerate()
                    }
                }

                // Settings gear button
                Rectangle {
                    width: 36
                    height: 36
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: 4
                    color: settingsMouse.containsMouse ? "#142018" : root.tileBg
                    border.width: 1
                    border.color: root.showSettings ? root.accentCyan :
                        (settingsMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 1
                        text: "⚙"
                        color: root.showSettings ? root.accentCyan :
                            (settingsMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.pixelSize: Math.round(14 * root.ui)

                        Behavior on color { ColorAnimation { duration: 100 } }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
                        text: "SET"
                        color: root.showSettings ? root.accentCyan : root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(7 * root.ui)
                        font.letterSpacing: 1
                    }

                    MouseArea {
                        id: settingsMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showSettings = !root.showSettings
                    }
                }

                // Master toggle button
                Rectangle {
                    width: 36
                    height: 36
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    radius: 4
                    color: masterBtnMouse.containsMouse ? "#142018" : root.tileBg
                    border.width: 1
                    border.color: root.showMaster ? root.accentPink :
                        (masterBtnMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: parent.top
                        anchors.topMargin: 1
                        text: "♬"
                        color: root.showMaster ? root.accentPink :
                            (masterBtnMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.pixelSize: Math.round(14 * root.ui)

                        Behavior on color { ColorAnimation { duration: 100 } }
                    }

                    Text {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 2
                        text: "MIX"
                        color: root.showMaster ? root.accentPink : root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(7 * root.ui)
                        font.letterSpacing: 1
                    }

                    MouseArea {
                        id: masterBtnMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showMaster = !root.showMaster
                    }
                }

            }

            // ── Settings summary (what GENERATE will do) ──
            Text {
                Layout.fillWidth: true
                visible: !root.showSettings
                text: root.settingsSummary()
                color: root.dimText
                font.family: "JetBrains Mono"
                font.pixelSize: Math.round(8 * root.ui)
                font.letterSpacing: 1
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
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6

                    // Preset selector
                    Text {
                        text: "PRESETS"
                        color: root.accentCyan
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(9 * root.ui)
                        font.letterSpacing: 2
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 3
                        Repeater {
                            model: ["FM DRIVE", "GOTHIC", "BOSS FIGHT", "OVERWORLD", "CHILL WAVE", "DUNGEON", "CREDITS", "FIGHT THEME", "CYBER NOIR", "ANY"]
                            Rectangle {
                                required property string modelData
                                property bool active: root.activePreset === modelData
                                width: _tp.implicitWidth + 10; height: 20; radius: 3
                                color: active ? "#1a2e26" : (_mp.containsMouse ? "#0f1a16" : "transparent")
                                border.width: 1; border.color: active ? root.accentPink : (_mp.containsMouse ? root.tileBorder : "transparent")
                                Text { id: _tp; anchors.centerIn: parent; text: modelData; color: active ? root.accentPink : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                MouseArea { id: _mp; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.applyPreset(modelData) }
                            }
                        }
                    }

                    // Divider
                    Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(0, 1, 0.53, 0.08) }

                    // Tab bar
                    Row {
                        spacing: 2
                        Repeater {
                            model: ["COMPOSE", "DRUMS", "PARTS"]
                            Rectangle {
                                required property string modelData
                                required property int index
                                property bool active: root.settingsTab === index
                                width: tabLabel.implicitWidth + 16; height: 22; radius: 3
                                color: active ? "#1a2e26" : (tabMa.containsMouse ? "#0f1a16" : "transparent")
                                border.width: 1; border.color: active ? root.accentCyan : (tabMa.containsMouse ? root.tileBorder : "transparent")
                                Text { id: tabLabel; anchors.centerIn: parent; text: modelData; color: active ? root.accentCyan : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 2 }
                                MouseArea { id: tabMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settingsTab = index }
                            }
                        }
                    }

                    // ── COMPOSE tab ──
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: root.settingsTab === 0

                        // TEMPO
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "TEMPO"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "slow", "medium", "fast"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settTempo === modelData
                                        width: _t.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _m; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settTempo = modelData }
                                    }
                                }
                            }
                        }
                        // ENERGY
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "ENERGY"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "chill", "normal", "intense"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settEnergy === modelData
                                        width: _t2.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m2.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m2.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t2; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _m2; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settEnergy = modelData }
                                    }
                                }
                            }
                        }
                        // SCALE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "SCALE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "minor", "major", "pentatonic"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settScale === modelData
                                        width: _t3.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m3.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m3.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t3; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _m3; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settScale = modelData }
                                    }
                                }
                            }
                        }
                        // STYLE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "STYLE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "chip", "snes", "genesis"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settStyle === modelData
                                        width: _t4.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m4.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m4.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t4; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _m4; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settStyle = modelData }
                                    }
                                }
                            }
                        }
                        // PACK (an instrument set with the habits of the scores it imitates)
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "PACK"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "none", "ffvi"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settPack === modelData
                                        width: _tp.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mp.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mp.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tp; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mp; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settPack = modelData }
                                    }
                                }
                            }
                        }
                        // ECHO
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "ECHO"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "on", "off"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settEcho === modelData
                                        width: _te.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_me.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_me.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _te; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _me; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settEcho = modelData }
                                    }
                                }
                            }
                        }
                        // WET (how much of the lead, harmony and arp the echo carries)
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "WET"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "light", "normal", "wet"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settEchoWet === modelData
                                        width: _tw.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mw.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mw.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tw; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mw; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settEchoWet = modelData }
                                    }
                                }
                            }
                        }
                        // BASS
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "BASS"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "heavy", "medium", "light"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settBassWeight === modelData
                                        width: _tb.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mb.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mb.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tb; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mb; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settBassWeight = modelData }
                                    }
                                }
                            }
                        }
                        // FORM
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "FORM"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "standard", "aaba", "rondo", "short", "linear"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settForm === modelData
                                        width: _tf5.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mf5.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mf5.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tf5; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mf5; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settForm = modelData }
                                    }
                                }
                            }
                        }
                    }

                    // ── DRUMS tab ──
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: root.settingsTab === 1

                        // DENSITY
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "DENSITY"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "sparse", "normal", "busy"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settDrumDensity === modelData
                                        width: _td.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_md.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_md.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _td; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _md; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settDrumDensity = modelData }
                                    }
                                }
                            }
                        }
                        // FILLS
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "FILLS"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["on", "off"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: (modelData === "on") === root.settDrumFills
                                        width: _tf.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mf.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mf.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tf; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mf; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settDrumFills = (modelData === "on") }
                                    }
                                }
                            }
                        }
                        // SWING
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "SWING"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "off", "light", "heavy"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settDrumSwing === modelData
                                        width: _ts.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_ms.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_ms.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _ts; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _ms; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settDrumSwing = modelData }
                                    }
                                }
                            }
                        }
                    }

                    // ── MELODY tab ──
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: root.settingsTab === 2

                        // STYLE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "STYLE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "phrased", "simple"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settMelody === modelData
                                        width: _tm.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mm.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mm.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tm; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mm; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settMelody = modelData }
                                    }
                                }
                            }
                        }

                        // Description
                        Text {
                            Layout.fillWidth: true
                            text: root.settMelody === "phrased"
                                ? "Motif-based melodies with phrase structure, contour shaping, and chorus callbacks"
                                : root.settMelody === "simple"
                                ? "Random walk melodies — simpler, more unpredictable"
                                : "Randomly picks phrased or simple per song"
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(8 * root.ui)
                            wrapMode: Text.WordWrap
                        }
                    }

                    // ── HARMONY tab ──
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: root.settingsTab === 2

                        // VOICING
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "VOICING"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "full", "thin"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settHarmonyVoicing === modelData
                                        width: _thv.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mhv.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mhv.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _thv; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mhv; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settHarmonyVoicing = modelData }
                                    }
                                }
                            }
                        }
                        // MODE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "MODE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui) }
                            Row { spacing: 3
                                Repeater { model: ["random", "sustain", "stabs", "rhythmic"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settHarmonyMode === modelData
                                        width: _thm.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mhm.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mhm.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _thm; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: Math.round(8 * root.ui) }
                                        MouseArea { id: _mhm; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settHarmonyMode = modelData }
                                    }
                                }
                            }
                        }

                        // Description
                        Text {
                            Layout.fillWidth: true
                            text: {
                                var modeDesc = root.settHarmonyMode === "sustain" ? "Sustained pads." : root.settHarmonyMode === "rhythmic" ? "Rhythmic chord hits." : root.settHarmonyMode === "stabs" ? "Short chord stabs." : "Random mode per song."
                                if (root.settHarmonyVoicing === "full")
                                    return "2-3 note chord voicings with counter-melodies. " + modeDesc
                                if (root.settHarmonyVoicing === "thin")
                                    return "Single-note harmony. " + modeDesc
                                return "Random voicing per song. " + modeDesc
                            }
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(8 * root.ui)
                            wrapMode: Text.WordWrap
                        }
                    }

                }
            }

            // ── Master Panel ──
            Rectangle {
                Layout.fillWidth: true
                visible: root.showMaster
                implicitHeight: masterCol.implicitHeight + 16
                color: root.tileBg
                radius: 4
                border.width: 1
                border.color: root.tileBorder

                ColumnLayout {
                    id: masterCol
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 4

                    // Header
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Text {
                            text: "CHANNEL MIX"
                            color: root.accentPink
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(9 * root.ui)
                            font.letterSpacing: 2
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(1, 0, 0.33, 0.12) }
                    }

                    // Channel sliders — horizontal rows
                    Repeater {
                        model: root.dryChannels.length
                        delegate: RowLayout {
                            required property int index
                            readonly property int ch: root.dryChannels[index]
                            Layout.fillWidth: true
                            spacing: 6
                            height: 18

                            // Channel name
                            Text {
                                Layout.preferredWidth: 48
                                text: root.channelLabel(ch)
                                color: root.channelColor(ch) === 0 ? root.accentGreen :
                                       root.channelColor(ch) === 1 ? root.accentCyan :
                                       root.accentPink
                                font.family: "JetBrains Mono"
                                font.pixelSize: Math.round(8 * root.ui)
                                horizontalAlignment: Text.AlignRight
                            }

                            // Slider
                            Item {
                                Layout.fillWidth: true
                                height: 14

                                // Track background
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width
                                    height: 4
                                    radius: 2
                                    color: root.darkBg
                                    border.width: 1
                                    border.color: root.tileBorder
                                }

                                // Fill bar
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width * (root.channelVolumes[ch] / 64)
                                    height: 4
                                    radius: 2
                                    color: root.channelColor(ch) === 0 ? root.accentGreen :
                                           root.channelColor(ch) === 1 ? root.accentCyan :
                                           root.accentPink
                                    opacity: 0.6
                                }

                                // Handle
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    x: parent.width * (root.channelVolumes[ch] / 64) - width / 2
                                    width: 8
                                    height: 12
                                    radius: 2
                                    color: hSliderMa.pressed ? "#2a4e36" : (hSliderMa.containsMouse ? "#1a3e26" : "#142018")
                                    border.width: 1
                                    border.color: root.channelColor(ch) === 0 ? root.accentGreen :
                                                  root.channelColor(ch) === 1 ? root.accentCyan :
                                                  root.accentPink
                                }

                                MouseArea {
                                    id: hSliderMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    preventStealing: true
                                    onPressed: function(mouse) { _setH(mouse.x) }
                                    onPositionChanged: function(mouse) { if (pressed) _setH(mouse.x) }
                                    function _setH(mouseX) {
                                        var ratio = Math.max(0, Math.min(1, mouseX / width))
                                        root.applyChannelVolume(ch, Math.round(ratio * 64))
                                    }
                                }
                            }

                            // Value
                            Text {
                                Layout.preferredWidth: 20
                                text: root.channelVolumes[ch]
                                color: root.dimText
                                font.family: "JetBrains Mono"
                                font.pixelSize: Math.round(8 * root.ui)
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }

                    // Echo bus: every return channel at once, as a ratio of the
                    // written mix; expand for LEAD / HARM / ARP.
                    Repeater {
                        model: root.echoRows
                        delegate: RowLayout {
                            required property string modelData
                            readonly property bool isBus: modelData === "bus"
                            readonly property real ratio: root.echoRatioOf(modelData)
                            Layout.fillWidth: true
                            spacing: 6
                            height: 18

                            Item {
                                Layout.preferredWidth: 48
                                height: 14
                                Text {
                                    anchors.right: parent.right
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: isBus ? ((root.echoExpanded ? "\u25BE " : "\u25B8 ") + "ECHO")
                                                : (modelData === "melody" ? "LEAD" : modelData === "harmony" ? "HARM" : modelData.toUpperCase())
                                    color: isBus ? root.accentCyan : root.dimText
                                    font.family: "JetBrains Mono"
                                    font.pixelSize: Math.round(8 * root.ui)
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    enabled: isBus
                                    cursorShape: isBus ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: root.echoExpanded = !root.echoExpanded
                                }
                            }

                            Item {
                                Layout.fillWidth: true
                                height: 14
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width; height: 4; radius: 2
                                    color: root.darkBg; border.width: 1; border.color: root.tileBorder
                                }
                                Rectangle {   // the written level is the middle of the track
                                    x: parent.width / 2; width: 1; height: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                    color: root.tileBorder
                                }
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width * (ratio / 2); height: 4; radius: 2
                                    color: root.accentCyan; opacity: 0.6
                                }
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    x: parent.width * (ratio / 2) - width / 2
                                    width: 8; height: 12; radius: 2
                                    color: eSliderMa.pressed ? "#2a4e36" : (eSliderMa.containsMouse ? "#1a3e26" : "#142018")
                                    border.width: 1; border.color: root.accentCyan
                                }
                                MouseArea {
                                    id: eSliderMa
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    preventStealing: true
                                    onPressed: function(mouse) { _setE(mouse.x) }
                                    onPositionChanged: function(mouse) { if (pressed) _setE(mouse.x) }
                                    function _setE(mouseX) {
                                        var r = Math.max(0, Math.min(1, mouseX / width)) * 2
                                        root.setEchoRatio(modelData, Math.round(r * 20) / 20)
                                    }
                                }
                            }

                            Text {
                                Layout.preferredWidth: 28
                                text: Math.round(ratio * 100) + "%"
                                color: root.dimText
                                font.family: "JetBrains Mono"
                                font.pixelSize: Math.round(8 * root.ui)
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }

                    // Apply button
                    Rectangle {
                        Layout.fillWidth: true
                        height: 26
                        radius: 3
                        color: saveMasterMouse.containsMouse ? "#142018" : root.darkBg
                        border.width: 1
                        border.color: saveMasterMouse.containsMouse ? root.accentPink : root.tileBorder
                        Behavior on color { ColorAnimation { duration: 100 } }
                        Behavior on border.color { ColorAnimation { duration: 100 } }
                        Text {
                            anchors.centerIn: parent
                            text: "[ APPLY TO TRACK ]"
                            color: saveMasterMouse.containsMouse ? root.accentPink : root.dimText
                            font.family: "JetBrains Mono"; font.pixelSize: Math.round(9 * root.ui); font.letterSpacing: 2
                            Behavior on color { ColorAnimation { duration: 100 } }
                        }
                        MouseArea {
                            id: saveMasterMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root._applyMasterToFile()
                        }
                    }
                }
            }

            // ── Playlist ──
            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    text: "PLAYLIST"
                    color: root.accentCyan
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(9 * root.ui)
                    font.letterSpacing: 3
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(0, 1, 0.53, 0.12) }
                Text {
                    text: root.playlistInfo.length + " TRACKS"
                    color: root.dimText
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(8 * root.ui)
                    font.letterSpacing: 1
                }
                // Rescan the folder now. The daemon also watches the folder,
                // but a button beats waiting when you have just dropped files in.
                Rectangle {
                    width: refreshLabel.implicitWidth + 12
                    height: 18
                    radius: 3
                    color: refreshMouse.containsMouse ? "#142018" : "transparent"
                    border.width: 1
                    border.color: refreshMouse.containsMouse ? root.accentGreen : root.tileBorder
                    Text {
                        id: refreshLabel
                        anchors.centerIn: parent
                        text: "↻ REFRESH"
                        color: refreshMouse.containsMouse ? root.accentGreen : root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: Math.round(8 * root.ui)
                        font.letterSpacing: 1
                    }
                    MouseArea {
                        id: refreshMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.rescan()
                    }
                }
            }
            // Where the music lives. Click to open the folder. Auto-generated
            // tracks are marked and the oldest beyond ten are pruned; KEEP
            // renames one out of that set.
            RowLayout {
                Layout.fillWidth: true
                spacing: 6
                Text {
                    text: root.shortDir() + "  ↗"
                    color: dirMouse.containsMouse ? root.accentGreen : root.dimText
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(8 * root.ui)
                    elide: Text.ElideMiddle
                    Layout.fillWidth: true
                    MouseArea {
                        id: dirMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.openMusicDir()
                    }
                }
                Text {
                    text: "AUTO = pruned after 10"
                    color: Qt.rgba(1, 0, 0.33, 0.5)
                    font.family: "JetBrains Mono"
                    font.pixelSize: Math.round(7 * root.ui)
                    font.letterSpacing: 1
                }
            }

            ListView {
                id: playlistView
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(contentHeight, 200)
                clip: true
                model: root.playlistInfo

                delegate: Rectangle {
                    required property var modelData
                    required property int index

                    width: playlistView.width
                    height: 26
                    color: rowHover.hovered ? "#142018" :
                           (index === root.currentIndex ? "#0f1a16" : "transparent")
                    radius: 3

                    // Hover state for the whole row. A HoverHandler never takes
                    // input, so it cannot fight the KEEP button for the click.
                    HoverHandler { id: rowHover }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8
                        // Above plMouse, which is declared later and would
                        // otherwise sit on top and take the KEEP click. Text
                        // items ignore mouse events, so row clicks still fall
                        // through to plMouse.
                        z: 1

                        Text {
                            text: String(index + 1).padStart(2, '0') + "."
                            color: index === root.currentIndex ? root.accentGreen : root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(9 * root.ui)
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.title
                            color: index === root.currentIndex ? root.accentGreen : root.textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(9 * root.ui)
                            elide: Text.ElideRight
                        }
                        Text {
                            visible: modelData.auto && !rowHover.hovered
                            text: "AUTO"
                            color: Qt.rgba(1, 0, 0.33, 0.6)
                            font.family: "JetBrains Mono"
                            font.pixelSize: Math.round(7 * root.ui)
                            font.letterSpacing: 1
                        }
                        Rectangle {
                            visible: modelData.auto && rowHover.hovered
                            width: keepLabel.implicitWidth + 10
                            height: 16
                            radius: 3
                            color: keepMouse.containsMouse ? "#1a2e26" : "transparent"
                            border.width: 1
                            border.color: root.accentPink
                            Text {
                                id: keepLabel
                                anchors.centerIn: parent
                                text: "KEEP"
                                color: root.accentPink
                                font.family: "JetBrains Mono"
                                font.pixelSize: Math.round(7 * root.ui)
                                font.letterSpacing: 1
                            }
                            MouseArea {
                                id: keepMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.keepTrack(index)
                            }
                        }

                        Text {
                            visible: index === root.currentIndex && root.playbackStatus === "Playing"
                            text: "▶"
                            color: root.accentGreen
                            font.pixelSize: Math.round(8 * root.ui)
                        }
                    }

                    MouseArea {
                        id: plMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.dbusPlayIndex(index)
                    }
                }
            }

            // Any height the popup has beyond what the content needs goes
            // here, so the sections stay packed at the top instead of the
            // layout spreading the surplus into gaps between them.
            Item { Layout.fillHeight: true }

            // ── Footer ──
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "[16-BIT AUDIO SUBSYSTEM]"
                color: Qt.rgba(0.314, 0.51, 0.392, 0.25)
                font.family: "JetBrains Mono"
                font.pixelSize: Math.round(8 * root.ui)
                font.letterSpacing: 2
            }
        }

    }
}
