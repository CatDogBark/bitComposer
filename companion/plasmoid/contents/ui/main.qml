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
    property var playlistNames: []

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

    // Cooldown: ignore polls briefly after a command so optimistic state isn't overwritten
    property bool cooldown: false
    Timer {
        id: cooldownTimer
        interval: 800
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
    property int settingsTab: 0  // 0=COMPOSE, 1=DRUMS, 2=MELODY, 3=HARMONY

    // Channel volumes for mastering (0-64, matches IT header bytes 128-191)
    property var channelVolumes: [13, 25, 25, 25, 8, 33, 36, 36, 36, 36, 36, 36]
    readonly property var channelNames: ["MELODY", "HARM 1", "HARM 2", "HARM 3", "BASS", "ARP", "KICK", "SNARE", "HIHAT", "TOM", "CRASH", "OP HAT"]
    readonly property var channelColors: [0, 1, 1, 1, 0, 0, 2, 2, 2, 2, 2, 2] // 0=green, 1=cyan, 2=pink

    function applyChannelVolume(channel, value) {
        channelVolumes[channel] = value
        channelVolumesChanged()
    }

    readonly property string musicDir: "/home/troy/Music/Chiptune/"

    function _trackPath() {
        if (!root.trackFile) return ""
        // trackFile may be just a filename or a full path
        if (root.trackFile.startsWith("/")) return root.trackFile
        return root.musicDir + root.trackFile
    }

    function _applyMasterToFile() {
        var path = _trackPath()
        if (!path) return
        var cmd = "bitcomposer-master.sh '" + path + "'"
        for (var i = 0; i < 12; i++) cmd += " " + channelVolumes[i]
        masterSource.connectSource(cmd)
    }

    function _loadMasterFromFile() {
        var path = _trackPath()
        if (!path) return
        var cmd = "python3 -c \"f=open('" + path + "','rb');f.seek(128);d=f.read(12);f.close();print(' '.join(str(b) for b in d))\""
        masterLoadSource.connectSource(cmd)
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
            var parts = stdout.split(" ")
            if (parts.length >= 12) {
                var vols = []
                for (var i = 0; i < 12; i++)
                    vols.push(parseInt(parts[i]) || 0)
                root.channelVolumes = vols
            }
        }
    }
    property string settTempo: "random"
    property string settEnergy: "random"
    property string settScale: "random"
    property string settStyle: "random"
    property string settDrumDensity: "random"
    property bool settDrumFills: true
    property string settDrumSwing: "random"
    property string settMelody: "random"
    property string settHarmonyVoicing: "random"
    property string settHarmonyMode: "random"
    property string settBassWeight: "random"
    property string settForm: "random"
    property string activePreset: ""
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
    onSettTempoChanged: _onSettingChanged()
    onSettEnergyChanged: _onSettingChanged()
    onSettScaleChanged: _onSettingChanged()
    onSettStyleChanged: _onSettingChanged()
    onSettDrumDensityChanged: _onSettingChanged()
    onSettDrumFillsChanged: _onSettingChanged()
    onSettDrumSwingChanged: _onSettingChanged()
    onSettMelodyChanged: _onSettingChanged()
    onSettHarmonyVoicingChanged: _onSettingChanged()
    onSettHarmonyModeChanged: _onSettingChanged()
    onSettBassWeightChanged: _onSettingChanged()
    onSettFormChanged: _onSettingChanged()
    property bool _applyingPreset: false

    function applyPreset(name) {
        var presets = {
            "MEGA DRIVE":   { tempo: "fast",   energy: "intense", scale: "minor",      style: "genesis", drumDensity: "busy",   fills: true,  swing: "light",  melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "standard" },
            "CASTLEVANIA":  { tempo: "medium", energy: "normal",  scale: "minor",      style: "random",  drumDensity: "normal", fills: true,  swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "rondo"    },
            "BOSS FIGHT":   { tempo: "fast",   energy: "intense", scale: "minor",      style: "genesis", drumDensity: "busy",   fills: true,  swing: "heavy",  melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "short"    },
            "OVERWORLD":    { tempo: "medium", energy: "normal",  scale: "major",      style: "snes",    drumDensity: "normal", fills: true,  swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "standard" },
            "CHILL WAVE":   { tempo: "slow",   energy: "chill",   scale: "pentatonic", style: "snes",    drumDensity: "sparse", fills: false, swing: "light",  melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba"     },
            "DUNGEON":      { tempo: "slow",   energy: "chill",   scale: "minor",      style: "random",  drumDensity: "sparse", fills: false, swing: "off",    melody: "phrased", voicing: "thin", mode: "stabs",    bass: "medium", form: "rondo"    },
            "CREDITS":      { tempo: "slow",   energy: "chill",   scale: "major",      style: "snes",    drumDensity: "sparse", fills: false, swing: "off",    melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba"     },
            "STREET FIGHT": { tempo: "fast",   energy: "intense", scale: "pentatonic", style: "genesis", drumDensity: "busy",   fills: true,  swing: "heavy",  melody: "phrased", voicing: "full", mode: "stabs",    bass: "heavy",  form: "short"    },
            "CYBER NOIR":   { tempo: "medium", energy: "normal",  scale: "minor",      style: "genesis", drumDensity: "normal", fills: true,  swing: "light",  melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "linear"   },
            "RANDOM":       { tempo: "random", energy: "random",  scale: "random",     style: "random",  drumDensity: "random", fills: true,  swing: "random", melody: "random",  voicing: "random", mode: "random", bass: "random", form: "random"   },
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
        return flags
    }

    function generateTrack() {
        if (root.generating) return
        root.generating = true
        var cmd = "bitcomposer-generate.sh"
        if (root.autoGenerate) cmd += " --auto"
        cmd += _buildSettingsFlags()
        generateSource.connectSource(cmd)
    }

    function toggleAutoGenerate() {
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
            // Refresh playlist display
            playlistSource.connectedSources = []
            playlistSource.connectedSources = [
                "qdbus6 " + root.busName + " " + root.busPath + " " + root.busName + ".GetPlaylist"
            ]
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
        }
    }

    // Playlist polling (less frequent)
    P5Support.DataSource {
        id: playlistSource
        engine: "executable"
        connectedSources: [
            "qdbus6 " + root.busName + " " + root.busPath + " " + root.busName + ".GetPlaylist"
        ]
        interval: 2000

        onNewData: function(source, data) {
            var stdout = (data["stdout"] || "").trim()
            root.playlistNames = stdout ? stdout.split("\n") : []
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
                font.pixelSize: 10

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
                font.pixelSize: 11
                elide: Text.ElideRight
            }

            // Time
            Text {
                visible: root.trackDuration > 0
                text: formatTime(root.trackPosition)
                color: root.dimText
                font.family: "JetBrains Mono"
                font.pixelSize: 9
            }
        }
    }

    // ── Full Representation (popup) ──
    fullRepresentation: Rectangle {
        id: popup
        implicitWidth: 340
        implicitHeight: popupColumn.implicitHeight + 40
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
                    font.pixelSize: 10
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
                        font.pixelSize: 9
                        font.letterSpacing: 2
                        visible: root.trackTitle !== ""
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.trackTitle || "AWAITING SIGNAL..."
                        color: root.trackTitle ? root.accentGreen : root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: 14
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
                        visible: root.trackArtist !== ""
                        text: "by " + root.trackArtist
                        color: root.textColor
                        font.family: "JetBrains Mono"
                        font.pixelSize: 10
                    }

                    RowLayout {
                        visible: root.trackFormat !== ""
                        spacing: 16
                        Text {
                            text: "FMT: " + root.trackFormat.toUpperCase()
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: 9
                        }
                        Text {
                            text: "CH: " + root.trackChannels
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: 9
                        }
                        Text {
                            text: "PAT: " + root.trackPatterns
                            color: root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: 9
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
                        font.pixelSize: 9
                    }
                    Item { Layout.fillWidth: true }
                    Text {
                        text: formatTime(root.trackDuration)
                        color: root.dimText
                        font.family: "JetBrains Mono"
                        font.pixelSize: 9
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

            // ── Status Line ──
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Text {
                    text: "SHUFFLE: " + (root.shuffleOn ? "ON" : "OFF")
                    color: root.shuffleOn ? root.accentPink : root.dimText
                    font.family: "JetBrains Mono"
                    font.pixelSize: 9
                    font.letterSpacing: 1
                }
                Text {
                    text: "AUTO: " + (root.autoGenerate ? "ON" : "OFF")
                    color: root.autoGenerate ? root.accentPink : root.dimText
                    font.family: "JetBrains Mono"
                    font.pixelSize: 9
                    font.letterSpacing: 1
                }
                Item { Layout.fillWidth: true }
                Text {
                    text: "TRACKS: " + root.playlistCount
                    color: root.dimText
                    font.family: "JetBrains Mono"
                    font.pixelSize: 9
                    font.letterSpacing: 1
                }
            }

            // ── Generate + Settings ──
            RowLayout {
                Layout.fillWidth: true
                spacing: 4

                // Generate button
                Rectangle {
                    Layout.fillWidth: true
                    height: 30
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
                        font.pixelSize: 10
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
                    width: 30
                    height: 30
                    radius: 4
                    color: autoGenMouse.containsMouse ? "#142018" : root.tileBg
                    border.width: 1
                    border.color: root.autoGenerate ? root.accentPink :
                        (autoGenMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.centerIn: parent
                        text: "∞"
                        color: root.autoGenerate ? root.accentPink :
                            (autoGenMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.pixelSize: 16
                        font.bold: root.autoGenerate

                        Behavior on color { ColorAnimation { duration: 100 } }

                        SequentialAnimation on opacity {
                            loops: root.autoGenerate ? Animation.Infinite : 0
                            running: root.autoGenerate
                            NumberAnimation { to: 0.4; duration: 1200 }
                            NumberAnimation { to: 1.0; duration: 1200 }
                            onRunningChanged: if (!running) parent.opacity = 1
                        }
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
                    width: 30
                    height: 30
                    radius: 4
                    color: settingsMouse.containsMouse ? "#142018" : root.tileBg
                    border.width: 1
                    border.color: root.showSettings ? root.accentCyan :
                        (settingsMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.centerIn: parent
                        text: "⚙"
                        color: root.showSettings ? root.accentCyan :
                            (settingsMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.pixelSize: 14

                        Behavior on color { ColorAnimation { duration: 100 } }
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
                    width: 30
                    height: 30
                    radius: 4
                    color: masterBtnMouse.containsMouse ? "#142018" : root.tileBg
                    border.width: 1
                    border.color: root.showMaster ? root.accentPink :
                        (masterBtnMouse.containsMouse ? root.accentGreen : root.tileBorder)

                    Behavior on color { ColorAnimation { duration: 100 } }
                    Behavior on border.color { ColorAnimation { duration: 100 } }

                    Text {
                        anchors.centerIn: parent
                        text: "♬"
                        color: root.showMaster ? root.accentPink :
                            (masterBtnMouse.containsMouse ? root.accentGreen : root.textColor)
                        font.pixelSize: 14

                        Behavior on color { ColorAnimation { duration: 100 } }
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
                        font.pixelSize: 9
                        font.letterSpacing: 2
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 3
                        Repeater {
                            model: ["MEGA DRIVE", "CASTLEVANIA", "BOSS FIGHT", "OVERWORLD", "CHILL WAVE", "DUNGEON", "CREDITS", "STREET FIGHT", "CYBER NOIR", "RANDOM"]
                            Rectangle {
                                required property string modelData
                                property bool active: root.activePreset === modelData
                                width: _tp.implicitWidth + 10; height: 20; radius: 3
                                color: active ? "#1a2e26" : (_mp.containsMouse ? "#0f1a16" : "transparent")
                                border.width: 1; border.color: active ? root.accentPink : (_mp.containsMouse ? root.tileBorder : "transparent")
                                Text { id: _tp; anchors.centerIn: parent; text: modelData; color: active ? root.accentPink : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
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
                            model: ["COMPOSE", "DRUMS", "MELODY", "HARMONY"]
                            Rectangle {
                                required property string modelData
                                required property int index
                                property bool active: root.settingsTab === index
                                width: tabLabel.implicitWidth + 16; height: 22; radius: 3
                                color: active ? "#1a2e26" : (tabMa.containsMouse ? "#0f1a16" : "transparent")
                                border.width: 1; border.color: active ? root.accentCyan : (tabMa.containsMouse ? root.tileBorder : "transparent")
                                Text { id: tabLabel; anchors.centerIn: parent; text: modelData; color: active ? root.accentCyan : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9; font.letterSpacing: 2 }
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
                            Text { Layout.preferredWidth: 52; text: "TEMPO"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "slow", "medium", "fast"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settTempo === modelData
                                        width: _t.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _m; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settTempo = modelData }
                                    }
                                }
                            }
                        }
                        // ENERGY
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "ENERGY"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "chill", "normal", "intense"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settEnergy === modelData
                                        width: _t2.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m2.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m2.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t2; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _m2; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settEnergy = modelData }
                                    }
                                }
                            }
                        }
                        // SCALE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "SCALE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "minor", "major", "pentatonic"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settScale === modelData
                                        width: _t3.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m3.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m3.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t3; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _m3; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settScale = modelData }
                                    }
                                }
                            }
                        }
                        // STYLE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "STYLE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "snes", "genesis"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settStyle === modelData
                                        width: _t4.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_m4.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_m4.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _t4; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _m4; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settStyle = modelData }
                                    }
                                }
                            }
                        }
                        // BASS
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "BASS"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "heavy", "medium", "light"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settBassWeight === modelData
                                        width: _tb.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mb.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mb.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tb; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _mb; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settBassWeight = modelData }
                                    }
                                }
                            }
                        }
                        // FORM
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "FORM"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "standard", "aaba", "rondo", "short", "linear"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settForm === modelData
                                        width: _tf5.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mf5.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mf5.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tf5; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
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
                            Text { Layout.preferredWidth: 52; text: "DENSITY"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "sparse", "normal", "busy"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settDrumDensity === modelData
                                        width: _td.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_md.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_md.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _td; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _md; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settDrumDensity = modelData }
                                    }
                                }
                            }
                        }
                        // FILLS
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "FILLS"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["on", "off"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: (modelData === "on") === root.settDrumFills
                                        width: _tf.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mf.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mf.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tf; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _mf; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settDrumFills = (modelData === "on") }
                                    }
                                }
                            }
                        }
                        // SWING
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "SWING"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "off", "light", "heavy"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settDrumSwing === modelData
                                        width: _ts.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_ms.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_ms.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _ts; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
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
                            Text { Layout.preferredWidth: 52; text: "STYLE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "phrased", "simple"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settMelody === modelData
                                        width: _tm.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mm.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mm.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _tm; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
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
                            font.pixelSize: 8
                            wrapMode: Text.WordWrap
                        }
                    }

                    // ── HARMONY tab ──
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        visible: root.settingsTab === 3

                        // VOICING
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "VOICING"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "full", "thin"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settHarmonyVoicing === modelData
                                        width: _thv.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mhv.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mhv.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _thv; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
                                        MouseArea { id: _mhv; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.settHarmonyVoicing = modelData }
                                    }
                                }
                            }
                        }
                        // MODE
                        RowLayout { Layout.fillWidth: true; spacing: 8
                            Text { Layout.preferredWidth: 52; text: "MODE"; color: root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 9 }
                            Row { spacing: 3
                                Repeater { model: ["random", "sustain", "stabs", "rhythmic"]
                                    Rectangle {
                                        required property string modelData
                                        property bool active: root.settHarmonyMode === modelData
                                        width: _thm.implicitWidth + 10; height: 20; radius: 3
                                        color: active ? "#1a2e26" : (_mhm.containsMouse ? "#0f1a16" : "transparent")
                                        border.width: 1; border.color: active ? root.accentGreen : (_mhm.containsMouse ? root.tileBorder : "transparent")
                                        Text { id: _thm; anchors.centerIn: parent; text: modelData.toUpperCase(); color: active ? root.accentGreen : root.dimText; font.family: "JetBrains Mono"; font.pixelSize: 8 }
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
                            font.pixelSize: 8
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
                            font.pixelSize: 9
                            font.letterSpacing: 2
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(1, 0, 0.33, 0.12) }
                    }

                    // Channel sliders — horizontal rows
                    Repeater {
                        model: 12
                        delegate: RowLayout {
                            required property int index
                            Layout.fillWidth: true
                            spacing: 6
                            height: 18

                            // Channel name
                            Text {
                                Layout.preferredWidth: 48
                                text: root.channelNames[index]
                                color: root.channelColors[index] === 0 ? root.accentGreen :
                                       root.channelColors[index] === 1 ? root.accentCyan :
                                       root.accentPink
                                font.family: "JetBrains Mono"
                                font.pixelSize: 8
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
                                    width: parent.width * (root.channelVolumes[index] / 64)
                                    height: 4
                                    radius: 2
                                    color: root.channelColors[index] === 0 ? root.accentGreen :
                                           root.channelColors[index] === 1 ? root.accentCyan :
                                           root.accentPink
                                    opacity: 0.6
                                }

                                // Handle
                                Rectangle {
                                    anchors.verticalCenter: parent.verticalCenter
                                    x: parent.width * (root.channelVolumes[index] / 64) - width / 2
                                    width: 8
                                    height: 12
                                    radius: 2
                                    color: hSliderMa.pressed ? "#2a4e36" : (hSliderMa.containsMouse ? "#1a3e26" : "#142018")
                                    border.width: 1
                                    border.color: root.channelColors[index] === 0 ? root.accentGreen :
                                                  root.channelColors[index] === 1 ? root.accentCyan :
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
                                        root.applyChannelVolume(index, Math.round(ratio * 64))
                                    }
                                }
                            }

                            // Value
                            Text {
                                Layout.preferredWidth: 20
                                text: root.channelVolumes[index]
                                color: root.dimText
                                font.family: "JetBrains Mono"
                                font.pixelSize: 8
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
                            font.family: "JetBrains Mono"; font.pixelSize: 9; font.letterSpacing: 2
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
                    font.pixelSize: 9
                    font.letterSpacing: 3
                }
                Rectangle { Layout.fillWidth: true; height: 1; color: Qt.rgba(0, 1, 0.53, 0.12) }
            }

            ListView {
                id: playlistView
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(contentHeight, 200)
                clip: true
                model: root.playlistNames

                delegate: Rectangle {
                    required property string modelData
                    required property int index

                    width: playlistView.width
                    height: 26
                    color: plMouse.containsMouse ? "#142018" :
                           (index === root.currentIndex ? "#0f1a16" : "transparent")
                    radius: 3

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 8
                        anchors.rightMargin: 8
                        spacing: 8

                        Text {
                            text: String(index + 1).padStart(2, '0') + "."
                            color: index === root.currentIndex ? root.accentGreen : root.dimText
                            font.family: "JetBrains Mono"
                            font.pixelSize: 9
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            color: index === root.currentIndex ? root.accentGreen : root.textColor
                            font.family: "JetBrains Mono"
                            font.pixelSize: 9
                            elide: Text.ElideRight
                        }

                        Text {
                            visible: index === root.currentIndex && root.playbackStatus === "Playing"
                            text: "▶"
                            color: root.accentGreen
                            font.pixelSize: 8
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

            // ── Footer ──
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "[16-BIT AUDIO SUBSYSTEM]"
                color: Qt.rgba(0.314, 0.51, 0.392, 0.25)
                font.family: "JetBrains Mono"
                font.pixelSize: 8
                font.letterSpacing: 2
            }
        }

    }
}
