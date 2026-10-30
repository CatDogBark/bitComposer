/*
    bitComposer's window (2.0): an application with four screens, PLAY,
    WRITE, LIBRARY and SOUNDS, under one header that carries the bit
    family's lockup; SET and MIX open as panels over the current screen.

    The look is the pixel skin chosen on the 2.0 canvas (2026-10-30): a
    slate ground with console-grey panels, a one-pixel bevel inside every
    panel and button, a 2x2 dither in the fills, hard shadows, Silkscreen
    for titles, labels and buttons, JetBrains Mono for everything read as a
    sentence or a number, the pink bit as the one accent (and the family's
    mark in the tile), green only for ready and playing. Nothing sits on a
    fixed grid: the layout is fluid, the text is real text, the controls are
    real controls. Styling only, as the owner asked.

    The plumbing is the 1.x window's: `backend` (bitcomposer/player/app.py)
    wraps the engine in-process, state is pushed, the compose settings
    become the flags GENERATE runs with (_buildSettingsFlags), the window's
    own settings are saved through backend.saveUi. Sizes are logical pixels;
    Ctrl +/- zooms the whole window, Ctrl 0 resets, and the zoom is kept.
*/
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    visible: false          // shown by Component.onCompleted, at its starting size
    title: root.trackTitle ? root.trackTitle + "  ·  bitComposer" : "bitComposer"
    color: root.bg

    property bool startSettings: false
    property bool startMaster: false
    property bool still: false
    property bool startHidden: false
    property int startTab: -1                           // a screen to open on (--panels write|library|sounds), else the one remembered

    // ── Zoom ──
    property real ui: 1.0
    function setZoom(z) {
        var old = root.ui
        root.ui = Math.max(0.75, Math.min(2.0, Math.round(z * 20) / 20))
        if (root._sized) root.width = Math.min(Math.round(root.width * root.ui / old), root.availW)
        root._save()
    }
    Shortcut { sequences: ["Ctrl+=", "Ctrl++"]; onActivated: root.setZoom(root.ui + 0.1) }
    Shortcut { sequence: "Ctrl+-"; onActivated: root.setZoom(root.ui - 0.1) }
    Shortcut { sequence: "Ctrl+0"; onActivated: root.setZoom(1.0) }
    Shortcut { sequence: "Space"; onActivated: backend.playPause() }
    Shortcut { sequence: "Ctrl+1"; onActivated: root.tab = 0 }
    Shortcut { sequence: "Ctrl+2"; onActivated: root.tab = 1 }
    Shortcut { sequence: "Ctrl+3"; onActivated: root.tab = 2 }
    Shortcut { sequence: "Ctrl+4"; onActivated: root.tab = 3 }

    // ── Size: fit the screen ──
    readonly property real availW: backend.screenAvail[0] > 0 ? backend.screenAvail[0] : Screen.desktopAvailableWidth
    readonly property real availH: backend.screenAvail[1] > 0 ? backend.screenAvail[1] : Screen.desktopAvailableHeight
    readonly property real contentH: header.implicitHeight + popupColumn.implicitHeight + footer.implicitHeight + 48
    readonly property real maxH: Math.max(300, root.availH - 64)
    minimumWidth: Math.min(420, root.availW)
    minimumHeight: Math.min(300, root.maxH)
    width: Math.min(760, root.availW)
    height: root.maxH
    property real savedW: 0
    property real savedH: 0
    property bool _sized: false
    property bool _shown: false
    property double _sizedAt: 0
    function _start() {
        root.width = Math.min(root.savedW > 0 ? root.savedW : Math.round(760 * root.ui), root.availW)
        root.height = root.savedH > 0 ? Math.max(root.minimumHeight, Math.min(root.savedH, root.maxH)) : root.maxH
        root._sizedAt = Date.now()
        if (!root.startHidden) root.visible = true
    }
    function _fitOnce() {
        if (root._sized || !root.visible || root.visibility === Window.Minimized || popupColumn.implicitHeight < 50) return
        root._sized = true
        if (root.savedH <= 0)
            root.height = Math.max(root.minimumHeight, Math.min(root.contentH, root.maxH))
        root._sizedAt = Date.now()
        Qt.callLater(function() { root._shown = true })
    }
    onFrameSwapped: if (!root._sized && !settle.running) settle.start()
    onContentHChanged: if (!root._sized && root.visible) settle.restart()
    onVisibilityChanged: if (!root._sized && root.visibility !== Window.Minimized && root.visibility !== Window.Hidden) settle.restart()
    Timer { id: settle; interval: 150; onTriggered: { root._fitOnce(); if (root._sized) root._shown = true } }
    Timer { interval: 3000; running: true; onTriggered: if (root.visible && root.visibility !== Window.Minimized) root._fitOnce() }
    onMaxHChanged: if (root._sized && root.height > root.maxH) root.height = root.maxH
    onWidthChanged: root._noteSize()
    onHeightChanged: root._noteSize()
    function _noteSize() { if (root._sized && Date.now() - root._sizedAt > 1000) sizeSave.restart() }
    Timer { id: sizeSave; interval: 800; onTriggered: { root.savedW = root.width; root.savedH = root.height; root._save() } }

    // ── The screens ──
    property int tab: 0                                  // 0 PLAY, 1 WRITE, 2 LIBRARY, 3 SOUNDS
    onTabChanged: { root._save(); flick.contentY = 0 }
    property bool showSettings: false                    // SET, a panel over the screen
    property bool showMaster: false                      // MIX, the same
    property bool showPacks: false                       // the 1.x name for the library: setting it opens LIBRARY
    onShowPacksChanged: if (root.showPacks) root.tab = 2
    onShowSettingsChanged: if (root.showSettings && root._sized) reveal.show(settingsPanel)
    onShowMasterChanged: if (root.showMaster && root._sized) reveal.show(masterPanel)
    Timer {
        id: reveal
        interval: 40
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
        if (d.echo) { if (d.echo === "off") parts.push("no echo"); else { var e = d.echo.split("/"); parts.push(e[0] + " echo" + (e[1] ? ", " + e[1] : "")) } }
        return parts.join("  ·  ")
    }
    function voiceLabel(i) {
        var r = String(layout[i] || ""), v = songVoices || {}
        var key = r === "melody" ? "melody" : r === "openhat" ? "open_hihat" : r
        var name = v[key]
        if (!name) return ""
        return String(name).replace(/^(bit|ffvi|mana|evm|mmx|snes|gen|chip)_/, "").replace(/_/g, " ")
    }
    property real volumeGain: backend.state.volume !== undefined ? backend.state.volume : 1.0
    readonly property var levels: backend.levels                   // each channel's level while playing (about 0 to 1), else []
    readonly property bool liveLevels: playbackStatus === "Playing" && levels.length > 0
    function meterCells(ch, cells) {                               // live while playing, the channel's set volume otherwise
        if (liveLevels) return Math.round(cells * Math.min(1, levels[ch] || 0))
        return Math.round(cells * (channelVolumes[ch] || 0) / 64)
    }
    function kitCells(cells) {
        if (!liveLevels) return Math.round(cells * kitBus / 2)
        var top = 0
        for (var k = 0; k < kitChannels.length; k++) top = Math.max(top, levels[kitChannels[k]] || 0)
        return Math.round(cells * Math.min(1, top))
    }
    readonly property real maxGain: backend.maxGain
    property bool generating: !!backend.state.generating
    property bool autoGenerate: !!backend.state.autoGenerate
    property string packOpen: ""
    property string packVoice: ""
    property string packVoicePart: ""
    property string packConfirm: ""
    property string packRenaming: ""
    readonly property bool importBusy: !!backend.importState.busy
    readonly property bool gettingEmulator: backend.updatePurpose === "emulator"
    readonly property var builtinSounds: ["random", "chip", "genesis", "snes", "bit", "ffvi", "mana", "evermore", "megamanx"]   // Classic's
    readonly property var snesSets: ["bit", "ffvi", "mana", "evermore", "megamanx"]
    readonly property var packNames: backend.packs.map(function(p) { return p.name })
    readonly property var soundOptions: builtinSounds.concat(packNames)
    readonly property var partOrder: ["lead", "alt_lead", "harmony", "counter", "arp", "bass"]
    readonly property var kitPieces: ["kick", "snare", "hihat", "tom", "crash", "open_hihat", "rim"]
    function isLibraryPack(name) { return packNames.indexOf(name) >= 0 }
    onPackNamesChanged: {
        if (!root._loading && builtinSounds.indexOf(root.settSound) < 0 && !isLibraryPack(root.settSound)) root.settSound = "random"
        if (root.packOpen !== "" && !isLibraryPack(root.packOpen)) root.packOpen = ""
    }
    function pickVoice(pack, voice, part) {
        root.packVoice = voice
        root.packVoicePart = part
        backend.previewVoice(pack, voice, part)
    }
    function shortVoice(v) { return v.length > 8 ? v.substring(0, 7) : v }
    function whyText(p, v) {
        var rows = p.why[v] || []
        if (!rows.length) return "no readings kept for it (the pack was not imported here)"
        return rows.map(function(r) { return r[0] + " in " + r[1] + (r[1] === 1 ? " song" : " songs") + " (" + r[2] + " notes)" }).join(", ")
    }
    function movesFor(p, v) { return (p.drums.indexOf(v) >= 0 ? kitPieces : partOrder).concat(["out"]) }
    function packOf(name) { for (var i = 0; i < backend.packs.length; i++) if (backend.packs[i].name === name) return backend.packs[i]; return null }
    function vocabularyOf(name) { for (var i = 0; i < vocabularies.length; i++) if (vocabularies[i].name === name) return vocabularies[i]; return null }
    property int settingsTab: 0  // Classic's options under WRITE: 0=COMPOSE, 1=DRUMS, 2=PARTS
    onSettingsTabChanged: root._save()

    // ── The skin's tokens ──
    readonly property color bg: "#15141a"
    readonly property color panel: "#1d1c24"
    readonly property color dither: "#22212a"
    readonly property color raised: "#2b2a33"
    readonly property color line: "#3a3946"
    readonly property color edge: "#5a5968"
    readonly property color bevelLight: "#8a8898"
    readonly property color bevelDark: "#0a0a0e"
    readonly property color textColor: "#e8e6f0"
    readonly property color text2: "#cfcde0"
    readonly property color dimText: "#a8a6b8"
    readonly property color accentPink: "#ff0055"
    readonly property color pinkLight: "#ff80aa"
    readonly property color pinkDark: "#99003a"
    readonly property color onFill: "#3d2232"      // a toggle that is on: slate warmed by the pink
    readonly property color accentGreen: "#5be37a"
    readonly property color warn: "#ffcc33"
    readonly property string mono: "JetBrains Mono"
    readonly property string pixel: "Silkscreen"
    // the family's lockup keeps its own colours
    readonly property color brandMint: "#00ff88"
    readonly property color brandBracket: "#2f8f5f"
    readonly property color brandName: "#b0ddcc"
    readonly property color brandTile: "#0e1612"
    readonly property color brandTileBorder: "#1a2e26"
    readonly property color brandUnlit: "#13221b"

    function dbusPlayPause() { backend.playPause() }
    function dbusStop() { backend.stop() }
    function dbusNext() { backend.next() }
    function dbusPrevious() { backend.previous() }
    function dbusToggleShuffle() { backend.toggleShuffle() }
    function dbusSetVolume(gain) { backend.setVolume(Math.max(0, Math.min(maxGain, gain))) }
    function dbusPlayIndex(idx) { backend.playIndex(idx) }

    // ── Mixer ──
    property var layout: backend.state.layout || []
    property var channelVolumes: []
    readonly property int channelCount: layout.length
    readonly property var dryChannels: { var a = []; for (var i = 0; i < layout.length; i++) if (String(layout[i]).indexOf("echo.") !== 0) a.push(i); return a }
    readonly property var echoChannels: { var a = []; for (var i = 0; i < layout.length; i++) if (String(layout[i]).indexOf("echo.") === 0) a.push(i); return a }
    readonly property var echoGroups: { var g = []; for (var i = 0; i < echoChannels.length; i++) { var r = String(layout[echoChannels[i]]).substring(5); if (g.indexOf(r) < 0) g.push(r) } return g }
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
    readonly property bool _anyVoice: { for (var i = 0; i < dryChannels.length; i++) if (voiceLabel(dryChannels[i])) return true; return false }
    readonly property int mixLabelW: Math.round(110 * root.ui)
    readonly property int mixValueW: Math.round(34 * root.ui)
    function channelLabel(i) {
        var r = String(layout[i] || ""), n = 0
        if (r === "harmony") { for (var k = 0; k <= i; k++) if (layout[k] === "harmony") n++; return "harmony " + n }
        if (r === "openhat") return "open hat"
        if (r.indexOf("echo.") === 0) { for (var k2 = 0; k2 <= i; k2++) if (String(layout[k2]).indexOf("echo.") === 0) n++; return "echo " + n }
        return r
    }
    function channelColor(i) {   // 0 the line, 1 the harmony, 2 the kit
        var r = String(layout[i] || "")
        if (r === "melody" || r === "bass" || r === "arp") return 0
        if (kitRoles.indexOf(r) >= 0 || r.indexOf("drum") === 0) return 2
        return 1
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
    function applyChannelVolume(channel, value) {
        if (channelVolumes[channel] === value) return
        channelVolumes[channel] = value
        channelVolumesChanged()
        backend.setChannelVolume(channel, value)
    }
    function _applyMasterToFile() {
        if (backend.applyMix()) _resetEchoRatios()
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
    property string settTempo: "random"
    property string settEnergy: "random"
    property string settScale: "random"
    property string settSound: "random"
    property string settGenerator: "bitcomposer"    // GENERATE writes from a vocabulary (phase 6); "classic" is the 1.x generator
    property string settVocabulary: "default"       // what it writes from: the shipped vocabulary, your library, or one of your games
    property bool settCarryTheme: false
    property bool settBandReturns: false
    property string settSeed: ""                    // a seed names one song; blank draws one
    property var vocabularies: JSON.parse(backend.vocabularies())     // read again whenever the packs change: an import adds one
    Connections { target: backend; function onPacksChanged() { root.vocabularies = JSON.parse(backend.vocabularies()) } }
    readonly property var vocabularyOptions: vocabularies.filter(function(v) { return v.ready }).map(function(v) { return v.name })
    onVocabularyOptionsChanged: if (!root._loading && vocabularyOptions.indexOf(root.settVocabulary) < 0) root.settVocabulary = "default"
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
    onSettGeneratorChanged: _onSettingChanged()
    onSettVocabularyChanged: _onSettingChanged()
    onSettCarryThemeChanged: _onSettingChanged()
    onSettBandReturnsChanged: _onSettingChanged()
    onSettSeedChanged: _onSettingChanged()
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

    readonly property var _savedKeys: ["settGenerator", "settVocabulary", "settCarryTheme", "settBandReturns", "settSeed", "settTempo", "settEnergy", "settScale", "settSound", "settDrumDensity", "settDrumFills",
        "settDrumSwing", "settMelody", "settHarmonyVoicing", "settHarmonyMode", "settBassWeight", "settForm",
        "settEcho", "settEchoWet", "activePreset", "settingsTab", "tab", "ui", "savedW", "savedH"]
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
            "FM DRIVE":     { tempo: "fast",   energy: "intense", scale: "minor",      sound: "genesis", drumDensity: "busy",   fills: true,  swing: "off",   melody: "phrased", voicing: "thin", mode: "stabs",    bass: "heavy",  form: "standard" },
            "GOTHIC":       { tempo: "medium", energy: "normal",  scale: "minor",      sound: "random",  drumDensity: "normal", fills: true,  swing: "off",   melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "aaba" },
            "BOSS FIGHT":   { tempo: "fast",   energy: "intense", scale: "minor",      sound: "genesis", drumDensity: "busy",   fills: true,  swing: "off",   melody: "phrased", voicing: "full", mode: "rhythmic", bass: "heavy",  form: "standard" },
            "OVERWORLD":    { tempo: "medium", energy: "normal",  scale: "major",      sound: "snes",    drumDensity: "normal", fills: true,  swing: "light", melody: "phrased", voicing: "full", mode: "sustain",  bass: "medium", form: "aaba" },
            "CHILL WAVE":   { tempo: "slow",   energy: "chill",   scale: "pentatonic", sound: "snes",    drumDensity: "sparse", fills: false, swing: "light", melody: "simple",  voicing: "thin", mode: "sustain",  bass: "light",  form: "linear" },
            "DUNGEON":      { tempo: "slow",   energy: "chill",   scale: "minor",      sound: "random",  drumDensity: "sparse", fills: false, swing: "off",   melody: "simple",  voicing: "thin", mode: "sustain",  bass: "medium", form: "rondo" },
            "CREDITS":      { tempo: "slow",   energy: "chill",   scale: "major",      sound: "snes",    drumDensity: "sparse", fills: true,  swing: "light", melody: "phrased", voicing: "full", mode: "sustain",  bass: "light",  form: "aaba" },
            "FIGHT THEME":  { tempo: "fast",   energy: "intense", scale: "pentatonic", sound: "genesis", drumDensity: "busy",   fills: true,  swing: "off",   melody: "phrased", voicing: "thin", mode: "rhythmic", bass: "heavy",  form: "short" },
            "CYBER NOIR":   { tempo: "medium", energy: "normal",  scale: "minor",      sound: "genesis", drumDensity: "normal", fills: true,  swing: "heavy", melody: "simple",  voicing: "thin", mode: "stabs",    bass: "heavy",  form: "rondo" },
            "ANY":          { tempo: "random", energy: "random",  scale: "random",     sound: "random",  drumDensity: "random", fills: true,  swing: "random", melody: "random", voicing: "random", mode: "random", bass: "random", form: "random" }
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
        if (settGenerator !== "classic") {                   // the writer: what it writes from, the sounds and the two switches; Classic's options do not apply
            if (settVocabulary !== "default") flags += " --vocabulary " + settVocabulary
            if (isLibraryPack(settSound)) flags += backend.packFlags(settSound)      // else its own set, the default
            if (settCarryTheme) flags += " --carry-theme"
            if (settBandReturns) flags += " --band-returns"
            if (/^\d{1,9}$/.test(settSeed)) flags += " -s " + settSeed
            return flags
        }
        flags += " --classic"
        if (settTempo !== "random") flags += " --tempo " + settTempo
        if (settEnergy !== "random") flags += " --energy " + settEnergy
        if (settScale !== "random") flags += " --scale " + settScale
        if (isLibraryPack(settSound)) flags += backend.packFlags(settSound)
        else if (builtinSounds.indexOf(settSound) > 0) flags += " --sound " + settSound
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

    function vocabularyLabel(name) { var v = vocabularyOf(name); return v ? v.label : name }
    function soundLabel(name) {
        if (name === "random" || name === "") return "the seed's pick"
        var p = packOf(name); if (p) return p.label
        return { bit: "bitComposer", ffvi: "FFVI", mana: "Mana", evermore: "Evermore", megamanx: "Mega Man X", chip: "chip", genesis: "Genesis", snes: "SNES" }[name] || name
    }
    function settingsSummary() {
        var prefix = ""
        if (autoGenerate)
            prefix = (playbackStatus === "Playing" ? "AUTO: the next song is written when this one ends" : "AUTO: written when playback stops") + "   |   "
        if (settGenerator !== "classic") {
            var parts = ["Written by bitComposer" + (settVocabulary !== "default" ? " from " + vocabularyLabel(settVocabulary) : "")]
            parts.push("on " + (isLibraryPack(settSound) ? soundLabel(settSound) + "'s sounds" : "its own sounds"))
            if (settCarryTheme) parts.push("carrying a theme")
            if (settBandReturns) parts.push("the band returning")
            if (/^\d{1,9}$/.test(settSeed)) parts.push("seed " + settSeed)
            return prefix + parts.join(", ")
        }
        if (activePreset && activePreset !== "ANY") return prefix + "Classic: " + activePreset
        var cp = ["Classic"]
        if (settTempo !== "random") cp.push(settTempo)
        if (settEnergy !== "random") cp.push(settEnergy)
        if (settScale !== "random") cp.push(settScale)
        if (settSound !== "random") cp.push(settSound)
        if (settDrumDensity !== "random") cp.push(settDrumDensity + " drums")
        if (!settDrumFills) cp.push("no fills")
        if (settDrumSwing !== "random") cp.push(settDrumSwing + " swing")
        if (settMelody !== "random") cp.push(settMelody + " melody")
        if (settHarmonyVoicing !== "random") cp.push(settHarmonyVoicing + " harmony")
        if (settHarmonyMode !== "random") cp.push(settHarmonyMode)
        if (settBassWeight !== "random") cp.push(settBassWeight + " bass")
        if (settForm !== "random") cp.push(settForm + " form")
        if (settEcho !== "random") cp.push("echo " + settEcho)
        if (settEchoWet !== "random") cp.push(settEchoWet + " echo")
        return prefix + (cp.length > 1 ? cp.join("  ·  ") : "Classic  ·  everything left to chance")
    }

    function generateTrack() {
        if (root.generating) return
        backend.generate(_buildSettingsFlags().trim())
    }
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
        if (root.startTab >= 0) root.tab = root.startTab
        root.showSettings = root.startSettings
        root.showMaster = root.startMaster
        root.channelVolumes = backend.channelVolumes.slice()
        root._resetEchoRatios()
        root._start()
    }

    onClosing: function(close) {
        if (backend.trayAvailable) {
            close.accepted = false
            root.hide()
            backend.hiddenToTray()
        }
    }

    // ── The skin's pieces ──

    // A panel: two-pixel edge, a one-pixel bevel inside it, a hard shadow, a dithered fill.
    component Panel: Item {
        id: pnl
        property bool hot: false            // a pink edge
        property bool shadow: true
        property int pad: Math.round(14 * root.ui)
        default property alias content: pnlInner.data
        implicitWidth: Math.round(120 * root.ui)
        implicitHeight: pnlInner.childrenRect.height + 2 * pad + 4 + (shadow ? 6 : 0)
        Rectangle { visible: pnl.shadow; anchors.fill: frame; anchors.leftMargin: 6; anchors.topMargin: 6; color: "#000000" }
        Rectangle {
            id: frame
            anchors.fill: parent
            anchors.rightMargin: pnl.shadow ? 6 : 0
            anchors.bottomMargin: pnl.shadow ? 6 : 0
            color: root.panel
            border.width: 2
            border.color: pnl.hot ? root.accentPink : root.edge
            Dither { anchors.fill: parent; anchors.margins: 2 }
            Rectangle { x: 2; y: 2; width: parent.width - 4; height: 1; color: root.bevelLight }
            Rectangle { x: 2; y: 2; width: 1; height: parent.height - 4; color: root.bevelLight }
            Rectangle { x: 2; y: parent.height - 3; width: parent.width - 4; height: 1; color: root.bevelDark }
            Rectangle { x: parent.width - 3; y: 2; width: 1; height: parent.height - 4; color: root.bevelDark }
            Item { id: pnlInner; x: pnl.pad + 2; y: pnl.pad + 2; width: parent.width - 2 * (pnl.pad + 2) }
        }
    }

    // The 2x2 dither: a 4x4 tile of the panel's second tone, repeated.
    component Dither: Image {
        fillMode: Image.Tile
        smooth: false
        source: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAF0lEQVR42mNQUtT6D8IMMIAhgFMCJgAAeJMLYTBnUoIAAAAASUVORK5CYII="
    }

    // A button: the panel's edge at small size, pressed it drops its label.
    component PButton: Item {
        id: pb
        property string text: ""
        property bool hot: false            // pink fill: the one thing to press
        property bool on: false             // a pressed-in state (a toggle that is on)
        property bool small: false
        property bool enabledLook: true
        property alias font: pbLabel.font
        signal clicked()
        implicitWidth: pbLabel.implicitWidth + Math.round((pb.small ? 16 : 24) * root.ui) + 4
        implicitHeight: Math.round((pb.small ? 24 : 36) * root.ui)
        opacity: enabledLook ? 1 : 0.45
        Rectangle { anchors.fill: face; anchors.leftMargin: 4; anchors.topMargin: 4; color: "#000000"; visible: !pbMouse.pressed }
        Rectangle {
            id: face
            anchors.fill: parent
            anchors.rightMargin: 4
            anchors.bottomMargin: 4
            anchors.leftMargin: pbMouse.pressed ? 2 : 0
            anchors.topMargin: pbMouse.pressed ? 2 : 0
            color: pb.hot ? root.accentPink : (pb.on ? root.onFill : root.raised)
            border.width: 2
            border.color: pb.hot || pb.on ? root.accentPink : (pbMouse.containsMouse ? root.bevelLight : root.edge)
            Rectangle { x: 2; y: 2; width: parent.width - 4; height: 1; color: pb.hot ? root.pinkLight : root.bevelLight; visible: !pbMouse.pressed && !pb.on }
            Rectangle { x: 2; y: 2; width: 1; height: parent.height - 4; color: pb.hot ? root.pinkLight : root.bevelLight; visible: !pbMouse.pressed && !pb.on }
            Rectangle { x: 2; y: parent.height - 3; width: parent.width - 4; height: 1; color: pb.hot ? root.pinkDark : root.bevelDark }
            Rectangle { x: parent.width - 3; y: 2; width: 1; height: parent.height - 4; color: pb.hot ? root.pinkDark : root.bevelDark }
            Text {
                id: pbLabel
                anchors.centerIn: parent
                anchors.verticalCenterOffset: pbMouse.pressed ? 1 : 0
                text: pb.text
                color: pb.hot ? root.bg : root.textColor
                font.family: root.pixel
                font.pixelSize: Math.round((pb.small ? 9 : 11) * root.ui)
                font.letterSpacing: 1
            }
        }
        MouseArea { id: pbMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: pb.clicked() }
    }

    // A sprite: rows of a glyph string, # lit, drawn on a pixel grid, never smoothed.
    component Sprite: Item {
        id: sp
        property var rows: []
        property color tint: root.textColor
        property int px: Math.max(1, Math.round(2 * root.ui))
        implicitWidth: (rows.length ? rows[0].length : 0) * px
        implicitHeight: rows.length * px
        Repeater {
            model: sp.rows.length
            Item {
                required property int index
                readonly property string row: sp.rows[index]
                y: index * sp.px
                Repeater {
                    model: row.length
                    Rectangle {
                        required property int index
                        x: index * sp.px
                        width: sp.px; height: sp.px
                        color: row.charAt(index) === "#" ? sp.tint : (row.charAt(index) === "P" ? root.accentPink : "transparent")
                    }
                }
            }
        }
    }
    readonly property var glyphs: ({
        play:    ["#.....", "##....", "###...", "####..", "###...", "##....", "#....."],
        pause:   ["##.##", "##.##", "##.##", "##.##", "##.##", "##.##", "##.##"],
        stop:    ["#####", "#####", "#####", "#####", "#####"],
        prev:    ["#...#.#", "#..##.#", "#.#####", "######.", "#.#####", "#..##.#", "#...#.#"],
        next:    ["#.#...#", "#.##..#", "#####.#", ".######", "#####.#", "#.##..#", "#.#...#"],
        shuffle: ["##...##", "..#.#..", "...#...", "..#.#..", "##...##"],
        kept:    ["#####", "#...#", "#.#.#", "#...#", "#####"],
        dot:     ["#####", "#...#", "#.#.#", "#...#", "#####"],
        cursor:  ["#.........", "##........", "###.......", "####......", "#####.....", "#####P....", "####......", "##.##.....", "...##.....", "....##...."]
    })

    // The family's lockup: the Lit bit tile (bitComposer's level bars, the pink bit top-right) and the bracket wordmark.
    component Lockup: RowLayout {
        spacing: Math.round(10 * root.ui)
        Rectangle {
            readonly property int cell: Math.max(3, Math.round(5 * root.ui))
            Layout.preferredWidth: cell * 5 + 4 + Math.round(12 * root.ui)
            Layout.preferredHeight: Layout.preferredWidth
            radius: Math.round(Layout.preferredWidth * 0.22)
            color: root.brandTile
            border.width: 1
            border.color: root.brandTileBorder
            Grid {
                anchors.centerIn: parent
                columns: 5
                spacing: 1
                Repeater {
                    model: ["....P", "..#.#", ".##.#", "#####", "#####"].join("")
                    Rectangle {
                        required property string modelData
                        width: parent.parent.cell; height: parent.parent.cell
                        color: modelData === "#" ? root.brandMint : modelData === "P" ? root.accentPink : root.brandUnlit
                    }
                }
            }
        }
        Text {
            textFormat: Text.StyledText
            text: "<font color='" + root.brandBracket + "'>[</font><b><font color='" + root.brandMint + "'>bit</font></b><font color='" + root.brandBracket + "'>]</font><font color='" + root.brandName + "'>Composer</font>"
            font.family: root.mono
            font.pixelSize: Math.round(16 * root.ui)
        }
    }

    // A label in the pixel face.
    component PxLabel: Text {
        color: root.dimText
        font.family: root.pixel
        font.pixelSize: Math.round(9 * root.ui)
        font.letterSpacing: 1
    }
    // A sentence in the mono face.
    component Body: Text {
        color: root.text2
        font.family: root.mono
        font.pixelSize: Math.round(11 * root.ui)
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    // A row of choices: label on the left, buttons that wrap.
    component OptionRow: RowLayout {
        id: optRow
        property string label: ""
        property var options: []
        property var labels: ({})           // option -> what the button says (else the option, upper case)
        property string value: ""
        signal picked(string choice)
        Layout.fillWidth: true
        spacing: Math.round(10 * root.ui)
        PxLabel {
            Layout.preferredWidth: Math.round(72 * root.ui)
            Layout.alignment: Qt.AlignTop
            topPadding: Math.round(7 * root.ui)
            text: optRow.label
        }
        Flow {
            Layout.fillWidth: true
            spacing: Math.round(6 * root.ui)
            Repeater {
                model: optRow.options
                PButton {
                    required property string modelData
                    small: true
                    text: (optRow.labels[modelData] || modelData).toUpperCase()
                    on: optRow.value === modelData
                    onClicked: optRow.picked(modelData)
                }
            }
        }
    }

    // A segmented meter: `on` of `cells` lit, stepped, never smooth.
    component Meter: Row {
        id: mt
        property int cells: 10
        property int on: 0
        property color tint: root.accentPink
        property int cellW: Math.round(10 * root.ui)
        spacing: 2
        height: Math.round(12 * root.ui)
        Repeater {
            model: mt.cells
            Rectangle {
                required property int index
                width: mt.cellW; height: mt.height
                color: index < mt.on ? mt.tint : root.raised
                Rectangle { x: 1; y: 1; width: parent.width - 2; height: 1; color: Qt.rgba(1, 1, 1, index < mt.on ? 0.35 : 0.08) }
            }
        }
    }

    // A fader: value 0..1, a pixel handle, live on drag.
    component Fader: Item {
        id: fader
        property real ratio: 0
        property color accent: root.accentPink
        property bool centreMark: false
        signal moved(real ratio)
        Layout.fillWidth: true
        implicitHeight: Math.round(18 * root.ui)
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width; height: Math.round(6 * root.ui)
            color: root.bg; border.width: 2; border.color: root.line
        }
        Rectangle {
            visible: fader.centreMark
            x: parent.width / 2; width: 2; height: Math.round(12 * root.ui)
            anchors.verticalCenter: parent.verticalCenter
            color: root.edge
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: 2
            width: Math.max(0, (parent.width - 4) * Math.max(0, Math.min(1, fader.ratio))); height: Math.round(6 * root.ui) - 4
            color: fader.accent
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            x: parent.width * Math.max(0, Math.min(1, fader.ratio)) - width / 2
            width: Math.round(10 * root.ui); height: Math.round(16 * root.ui)
            color: faderMouse.pressed ? root.line : root.raised
            border.width: 2; border.color: faderMouse.containsMouse || faderMouse.pressed ? fader.accent : root.edge
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

    // A pack's part (or its kit, or what is left out): its voices as buttons, each heard and picked with a click.
    component VoiceRow: RowLayout {
        id: voiceRow
        property string label: ""
        property string pack: ""
        property var items: []
        Layout.fillWidth: true
        spacing: Math.round(10 * root.ui)
        PxLabel {
            Layout.preferredWidth: Math.round(72 * root.ui)
            Layout.alignment: Qt.AlignTop
            topPadding: Math.round(7 * root.ui)
            text: voiceRow.label
        }
        Flow {
            Layout.fillWidth: true
            spacing: Math.round(6 * root.ui)
            Repeater {
                model: voiceRow.items
                PButton {
                    required property var modelData
                    small: true
                    text: modelData.text.toUpperCase()
                    on: root.packVoice === modelData.voice && root.packVoicePart === modelData.part
                    onClicked: root.pickVoice(voiceRow.pack, modelData.voice, modelData.part)
                }
            }
        }
    }

    // A screen's heading: a pixel label with a rule after it.
    component Heading: RowLayout {
        property string text: ""
        property string aside: ""
        Layout.fillWidth: true
        spacing: Math.round(10 * root.ui)
        PxLabel { text: parent.text; color: root.dimText; font.pixelSize: Math.round(10 * root.ui) }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 2; color: root.line }
        Text { visible: parent.aside !== ""; text: parent.aside; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui) }
    }

    // ── The window ──
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        opacity: root._shown ? 1 : 0       // laid out, not seen, until the window has its size

        // ── Header: the lockup, the four screens, SET and MIX, the version ──
        Rectangle {
            id: header
            Layout.fillWidth: true
            implicitHeight: headerRow.implicitHeight + Math.round(20 * root.ui)
            color: root.panel
            Dither { anchors.fill: parent }
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 2; color: root.line }
            RowLayout {
                id: headerRow
                anchors.fill: parent
                anchors.leftMargin: Math.round(16 * root.ui)
                anchors.rightMargin: Math.round(16 * root.ui)
                spacing: Math.round(16 * root.ui)
                Lockup {}
                Flow {
                    Layout.fillWidth: true
                    spacing: Math.round(8 * root.ui)
                    Repeater {
                        model: ["PLAY", "WRITE", "LIBRARY", "SOUNDS"]
                        PButton {
                            required property string modelData
                            required property int index
                            text: modelData
                            hot: root.tab === index
                            onClicked: root.tab = index
                        }
                    }
                }
                PButton {
                    visible: backend.updateVersion !== ""
                    small: true
                    text: backend.updating ? "UPDATING…" : "UPDATE " + backend.updateVersion
                    hot: !backend.updating
                    enabledLook: !backend.updating
                    onClicked: backend.applyUpdate()
                }
                PButton { small: true; text: "MIX"; on: root.showMaster; onClicked: root.showMaster = !root.showMaster }
                PButton { small: true; text: "SET"; on: root.showSettings; onClicked: root.showSettings = !root.showSettings }
                Text { text: "v" + backend.version; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
            }
        }

        // ── The screen, scrolling when it does not fit ──
        Flickable {
            id: flick
            objectName: "scroll"
            Layout.fillWidth: true
            Layout.fillHeight: true
            readonly property bool needBar: contentHeight > height + 1
            contentWidth: width
            contentHeight: popupColumn.implicitHeight + Math.round(32 * root.ui)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar {
                id: vbar
                policy: flick.needBar ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                width: Math.round(10 * root.ui)
                contentItem: Rectangle { color: vbar.pressed ? root.accentPink : root.edge }
                background: Rectangle { color: root.bg }
            }

            ColumnLayout {
                id: popupColumn
                x: Math.round(16 * root.ui)
                y: Math.round(16 * root.ui)
                width: flick.width - vbar.width - Math.round(32 * root.ui)
                spacing: Math.round(16 * root.ui)

                // ── SET: the player, not the songs ──
                Panel {
                    id: settingsPanel
                    objectName: "settingsPanel"
                    Layout.fillWidth: true
                    visible: root.showSettings
                    ColumnLayout {
                        width: parent.width
                        spacing: Math.round(10 * root.ui)
                        Heading { text: "SET: THE PLAYER"; aside: "Ctrl +/- zooms the window, Ctrl 0 resets, Ctrl 1-4 pick a screen" }
                        OptionRow {
                            visible: backend.autostartSupported
                            label: "LOGIN"; options: ["on", "off"]; value: backend.autostart ? "on" : "off"
                            onPicked: function(c) { if ((c === "on") !== backend.autostart) backend.setAutostart(c === "on") }
                        }
                        Body {
                            text: !backend.autostartSupported
                                ? "Start at login works from an installed copy (pipx or the installer), not from a checkout."
                                : backend.trayAvailable
                                ? "Start bitComposer when you log in: in the tray, not playing, so the media keys and the tray menu are there from the first minute."
                                : "Start bitComposer when you log in, in the background and not playing: the media keys work from the first minute."
                        }
                        OptionRow {
                            label: "UPDATES"; options: ["on", "off"]; value: backend.checkUpdates ? "on" : "off"
                            onPicked: function(c) { if ((c === "on") !== backend.checkUpdates) backend.setCheckUpdates(c === "on") }
                        }
                        Body { text: "At start the player asks GitHub's releases list whether a newer version exists, for the UPDATE button; nothing else is sent." }
                        OptionRow {
                            visible: backend.checkUpdates
                            label: "CANDIDATES"; options: ["on", "off"]; value: backend.prereleases ? "on" : "off"
                            onPicked: function(c) { if ((c === "on") !== backend.prereleases) backend.setPrereleases(c === "on") }
                        }
                        Body { visible: backend.checkUpdates; text: "On: UPDATE offers release candidates too, the next version before it is out, for trying it." }
                        Body {
                            text: "Media keys: " + (backend.mediaKeys ? backend.mediaKeys : "not available here") + ".  "
                                + (backend.trayAvailable ? "Closing the window keeps the music going in the tray; quit from the tray menu."
                                                         : "Closing the window quits: this desktop has no system tray to keep it in.")
                        }
                        RowLayout { Layout.fillWidth: true; Item { Layout.fillWidth: true } PButton { small: true; text: "CLOSE"; onClicked: root.showSettings = false } }
                    }
                }

                // ── MIX: the channels of the song playing ──
                Panel {
                    id: masterPanel
                    objectName: "masterPanel"
                    Layout.fillWidth: true
                    visible: root.showMaster
                    ColumnLayout {
                        width: parent.width
                        spacing: Math.round(8 * root.ui)
                        Heading { text: "MIX: THE CHANNELS"; aside: root.channelCount ? root.channelCount + " channels" : "nothing loaded" }
                        Component {
                            id: channelRow
                            RowLayout {
                                required property int modelData
                                readonly property int ch: modelData
                                readonly property string voice: root.voiceLabel(ch)
                                readonly property color tint: root.channelColor(ch) === 2 ? root.text2 : root.accentPink
                                Layout.fillWidth: true
                                spacing: Math.round(8 * root.ui)
                                Column {
                                    Layout.preferredWidth: root.mixLabelW
                                    spacing: 0
                                    Text { width: parent.width; text: root.channelLabel(ch); color: root.textColor; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); horizontalAlignment: Text.AlignRight; elide: Text.ElideLeft }
                                    Text { width: parent.width; visible: voice !== ""; text: voice; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); horizontalAlignment: Text.AlignRight; elide: Text.ElideLeft }
                                }
                                Fader {
                                    ratio: (root.channelVolumes[ch] || 0) / 64
                                    accent: tint
                                    onMoved: function(r) { root.applyChannelVolume(ch, Math.round(r * 64)) }
                                }
                                Text { Layout.preferredWidth: root.mixValueW; text: root.channelVolumes[ch] !== undefined ? root.channelVolumes[ch] : ""; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); horizontalAlignment: Text.AlignRight }
                            }
                        }
                        Repeater { model: root.partChannels; delegate: channelRow }
                        RowLayout {
                            visible: root.kitChannels.length > 0
                            Layout.fillWidth: true
                            spacing: Math.round(8 * root.ui)
                            Text {
                                Layout.preferredWidth: root.mixLabelW
                                horizontalAlignment: Text.AlignRight
                                text: (root.kitExpanded ? "▾ " : "▸ ") + "the kit"
                                color: root.textColor; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui)
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.kitExpanded = !root.kitExpanded }
                            }
                            Fader { ratio: root.kitBus / 2; accent: root.text2; centreMark: true; onMoved: function(r) { root.setKitRatio(Math.round(r * 2 * 20) / 20) } }
                            Text { Layout.preferredWidth: root.mixValueW; text: Math.round(root.kitBus * 100) + "%"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); horizontalAlignment: Text.AlignRight }
                        }
                        Repeater { model: root.kitExpanded ? root.kitChannels : []; delegate: channelRow }
                        Repeater {
                            model: root.echoRows
                            delegate: RowLayout {
                                required property string modelData
                                readonly property bool isBus: modelData === "bus"
                                readonly property real ratio: root.echoRatioOf(modelData)
                                Layout.fillWidth: true
                                spacing: Math.round(8 * root.ui)
                                Text {
                                    Layout.preferredWidth: root.mixLabelW
                                    horizontalAlignment: Text.AlignRight
                                    text: isBus ? ((root.echoExpanded ? "▾ " : "▸ ") + "the echo") : ("echo of the " + modelData)
                                    color: isBus ? root.textColor : root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui)
                                    MouseArea { anchors.fill: parent; enabled: isBus; cursorShape: isBus ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: root.echoExpanded = !root.echoExpanded }
                                }
                                Fader { ratio: parent.ratio / 2; accent: root.text2; centreMark: true; onMoved: function(r) { root.setEchoRatio(modelData, Math.round(r * 2 * 20) / 20) } }
                                Text { Layout.preferredWidth: root.mixValueW; text: Math.round(parent.ratio * 100) + "%"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); horizontalAlignment: Text.AlignRight }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Math.round(8 * root.ui)
                            Body { text: "The faders change the song playing; APPLY writes them into its file, so it plays this way from now on." }
                            PButton { visible: root.channelCount > 0; small: true; text: "APPLY TO THE FILE"; onClicked: root._applyMasterToFile() }
                            PButton { small: true; text: "CLOSE"; onClicked: root.showMaster = false }
                        }
                    }
                }

                // ══ PLAY ══
                ColumnLayout {
                    visible: root.tab === 0
                    Layout.fillWidth: true
                    spacing: Math.round(16 * root.ui)

                    Panel {
                        Layout.fillWidth: true
                        pad: Math.round(20 * root.ui)
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(10 * root.ui)
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Math.round(12 * root.ui)
                                Sprite { rows: root.glyphs[root.playbackStatus === "Playing" ? "play" : "pause"]; tint: root.playbackStatus === "Playing" ? root.accentGreen : root.dimText; visible: root.trackTitle !== "" }
                                PxLabel { text: root.trackTitle ? root.playbackStatus.toUpperCase() : "NOTHING LOADED"; color: root.playbackStatus === "Playing" ? root.accentGreen : root.dimText }
                                Text { visible: root.trackDuration > 0; text: root.formatTime(root.trackPosition) + " of " + root.formatTime(root.trackDuration); color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui) }
                                Item { Layout.fillWidth: true }
                                Text { visible: root.trackFormat !== ""; text: root.trackFormat.toUpperCase() + " · " + root.trackChannels + " channels · " + root.trackPatterns + " patterns"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                            }
                            Text {
                                id: titleText
                                Layout.fillWidth: true
                                text: root.trackTitle || "Press GENERATE for a song"
                                color: root.trackTitle ? root.textColor : root.dimText
                                font.family: root.pixel
                                font.bold: true
                                font.pixelSize: Math.round((root.trackTitle ? 26 : 16) * root.ui)
                                font.letterSpacing: 1
                                wrapMode: Text.WordWrap
                                style: Text.Raised; styleColor: "#000000"
                            }
                            Body { visible: root.trackMessage !== ""; text: root.trackMessage; font.pixelSize: Math.round(12 * root.ui) }
                            Body { visible: root.songReadout !== ""; text: root.songReadout; color: root.dimText }
                            Body { visible: root.trackArtist !== "" && root.trackArtist !== "bitComposer"; text: "by " + root.trackArtist }
                            // The position as a strip of blocks over the song.
                            Item {
                                Layout.fillWidth: true
                                implicitHeight: Math.round(22 * root.ui)
                                Rectangle { anchors.fill: parent; color: root.bg; border.width: 2; border.color: root.line }
                                Row {
                                    id: posStrip
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    spacing: 2
                                    readonly property int cells: Math.max(8, Math.floor((width + 2) / (Math.round(8 * root.ui) + 2)))
                                    readonly property int lit: root.trackDuration > 0 ? Math.round(cells * Math.min(1, root.trackPosition / root.trackDuration)) : 0
                                    Repeater {
                                        model: posStrip.cells
                                        Rectangle {
                                            required property int index
                                            width: (posStrip.width - (posStrip.cells - 1) * 2) / posStrip.cells
                                            height: posStrip.height
                                            color: index < posStrip.lit ? root.accentPink : root.raised
                                            Rectangle { x: 1; y: 1; width: parent.width - 2; height: 1; color: Qt.rgba(1, 1, 1, index < posStrip.lit ? 0.35 : 0.08) }
                                        }
                                    }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: root.trackDuration > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
                                    onClicked: function(mouse) { if (root.trackDuration > 0) backend.seek(Math.max(0, Math.min(1, mouse.x / width)) * root.trackDuration) }
                                }
                            }
                        }
                    }

                    // Transport, KEEP, GENERATE.
                    Flow {
                        Layout.fillWidth: true
                        spacing: Math.round(10 * root.ui)
                        PButton { text: ""; implicitWidth: Math.round(52 * root.ui); onClicked: root.dbusPrevious(); Sprite { anchors.centerIn: parent; anchors.horizontalCenterOffset: -2; anchors.verticalCenterOffset: -2; rows: root.glyphs.prev } }
                        PButton { text: ""; implicitWidth: Math.round(72 * root.ui); onClicked: root.dbusPlayPause(); Sprite { anchors.centerIn: parent; anchors.horizontalCenterOffset: -2; anchors.verticalCenterOffset: -2; rows: root.glyphs[root.playbackStatus === "Playing" ? "pause" : "play"]; tint: root.playbackStatus === "Playing" ? root.accentGreen : root.textColor } }
                        PButton { text: ""; implicitWidth: Math.round(52 * root.ui); onClicked: root.dbusStop(); Sprite { anchors.centerIn: parent; anchors.horizontalCenterOffset: -2; anchors.verticalCenterOffset: -2; rows: root.glyphs.stop } }
                        PButton { text: ""; implicitWidth: Math.round(52 * root.ui); onClicked: root.dbusNext(); Sprite { anchors.centerIn: parent; anchors.horizontalCenterOffset: -2; anchors.verticalCenterOffset: -2; rows: root.glyphs.next } }
                        PButton { text: ""; implicitWidth: Math.round(52 * root.ui); on: root.shuffleOn; onClicked: root.dbusToggleShuffle(); Sprite { anchors.centerIn: parent; anchors.horizontalCenterOffset: -2; anchors.verticalCenterOffset: -2; rows: root.glyphs.shuffle; tint: root.shuffleOn ? root.accentPink : root.textColor } }
                        PButton {
                            visible: root.currentIndex >= 0 && root.currentIndex < root.playlistInfo.length && !!root.playlistInfo[root.currentIndex].auto
                            text: "KEEP"
                            onClicked: root.keepTrack(root.currentIndex)
                        }
                        PButton { text: root.autoGenerate ? "AUTO: ON" : "AUTO"; on: root.autoGenerate; onClicked: root.toggleAutoGenerate() }
                        PButton {
                            id: generateButton
                            text: root.generating ? "WRITING…" : "GENERATE"
                            hot: !root.generating
                            enabledLook: !root.generating
                            font.pixelSize: Math.round(13 * root.ui)
                            font.bold: true
                            implicitHeight: Math.round(44 * root.ui)
                            onClicked: root.generateTrack()
                        }
                    }
                    Body { text: root.settingsSummary(); color: root.dimText; font.pixelSize: Math.round(10 * root.ui) }

                    // Gain.
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Math.round(10 * root.ui)
                        PxLabel { text: "GAIN"; Layout.preferredWidth: Math.round(72 * root.ui) }
                        Fader {
                            ratio: root.volumeGain / root.maxGain
                            accent: root.volumeGain > 1.0 ? root.warn : root.accentPink
                            centreMark: false
                            onMoved: function(r) { var g = Math.round(r * root.maxGain * 20) / 20; if (Math.abs(g - 1.0) < 0.06) g = 1.0; root.dbusSetVolume(g) }
                        }
                        Text {
                            Layout.preferredWidth: Math.round(44 * root.ui)
                            text: Math.round(root.volumeGain * 100) + "%"
                            color: root.volumeGain > 1.0 ? root.warn : root.textColor
                            font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); horizontalAlignment: Text.AlignRight
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.dbusSetVolume(1.0) }
                        }
                    }

                    // The band, as the file names its channels.
                    Panel {
                        Layout.fillWidth: true
                        shadow: false
                        visible: root.partChannels.length > 0
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(8 * root.ui)
                            Heading { text: "THE BAND"; aside: root.liveLevels ? "what each channel plays, as it plays" : "each channel's volume; MIX changes them" }
                            Repeater {
                                model: root.partChannels
                                RowLayout {
                                    required property int modelData
                                    readonly property int ch: modelData
                                    Layout.fillWidth: true
                                    spacing: Math.round(12 * root.ui)
                                    Text { Layout.preferredWidth: Math.round(120 * root.ui); text: root.channelLabel(ch); color: root.textColor; font.family: root.mono; font.pixelSize: Math.round(11 * root.ui); elide: Text.ElideRight }
                                    Meter { cells: 16; on: root.meterCells(ch, 16); tint: root.channelColor(ch) === 2 ? root.text2 : root.accentPink }
                                    Item { Layout.fillWidth: true }
                                    Text { text: root.voiceLabel(ch); color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); elide: Text.ElideRight }
                                }
                            }
                            RowLayout {
                                visible: root.kitChannels.length > 0
                                Layout.fillWidth: true
                                spacing: Math.round(12 * root.ui)
                                Text { Layout.preferredWidth: Math.round(120 * root.ui); text: "the kit"; color: root.textColor; font.family: root.mono; font.pixelSize: Math.round(11 * root.ui) }
                                Meter { cells: 16; on: root.kitCells(16); tint: root.text2 }
                                Item { Layout.fillWidth: true }
                                Text { text: root.kitChannels.length + " pieces"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui) }
                            }
                        }
                    }

                    // The songs.
                    Panel {
                        Layout.fillWidth: true
                        shadow: false
                        pad: Math.round(10 * root.ui)
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(8 * root.ui)
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Math.round(10 * root.ui)
                                PxLabel { text: "SONGS"; font.pixelSize: Math.round(10 * root.ui) }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 2; color: root.line }
                                Text { text: root.playlistInfo.length + " songs · AUTO ones are pruned after " + backend.autogenMax; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
                                PButton { small: true; text: "REFRESH"; onClicked: root.rescan() }
                                PButton { small: true; text: "FOLDER"; onClicked: backend.chooseFolder() }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.shortDir() + "  ↗"
                                color: dirMouse.containsMouse ? root.accentPink : root.dimText
                                font.family: root.mono; font.pixelSize: Math.round(9 * root.ui); elide: Text.ElideMiddle
                                MouseArea { id: dirMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.openMusicDir() }
                            }
                            ListView {
                                id: playlistView
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.min(contentHeight, Math.round(30 * root.ui) * 12)
                                clip: true
                                interactive: contentHeight > height
                                boundsBehavior: Flickable.StopAtBounds
                                model: root.playlistInfo
                                ScrollBar.vertical: ScrollBar {
                                    id: listBar
                                    policy: playlistView.contentHeight > playlistView.height + 1 ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff
                                    width: Math.round(8 * root.ui)
                                    contentItem: Rectangle { color: root.edge }
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
                                    readonly property bool current: index === root.currentIndex
                                    width: playlistView.width - (playlistView.contentHeight > playlistView.height + 1 ? listBar.width + 4 : 0)
                                    height: Math.round(30 * root.ui)
                                    color: current ? root.raised : (rowHover.hovered ? root.panel : "transparent")
                                    Rectangle { visible: current; width: 4; height: parent.height; color: root.accentPink }
                                    HoverHandler { id: rowHover }
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.leftMargin: Math.round(12 * root.ui)
                                        anchors.rightMargin: Math.round(8 * root.ui)
                                        spacing: Math.round(10 * root.ui)
                                        z: 1
                                        Sprite { rows: current && root.playbackStatus === "Playing" ? root.glyphs.play : root.glyphs.dot; tint: current ? root.accentPink : (modelData.auto ? root.line : root.accentGreen); px: Math.max(1, Math.round(1.5 * root.ui)) }
                                        Text { Layout.fillWidth: true; text: modelData.title; color: current ? root.textColor : root.text2; font.family: root.mono; font.pixelSize: Math.round(11 * root.ui); elide: Text.ElideRight }
                                        PxLabel { visible: modelData.auto && !rowHover.hovered; text: "AUTO"; font.pixelSize: Math.round(8 * root.ui) }
                                        PButton { visible: modelData.auto && rowHover.hovered; small: true; text: "KEEP"; onClicked: root.keepTrack(index) }
                                    }
                                    MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.dbusPlayIndex(index) }
                                }
                            }
                            Body { visible: root.playlistInfo.length === 0; text: "No songs here yet. GENERATE writes one; AUTO keeps writing them." }
                        }
                    }
                }

                // ══ WRITE ══
                ColumnLayout {
                    visible: root.tab === 1
                    Layout.fillWidth: true
                    spacing: Math.round(16 * root.ui)

                    Heading { text: "1 · WRITTEN FROM"; aside: "a vocabulary is a soundtrack's way with music, counted from its songs" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Math.round(12 * root.ui)
                        Repeater {
                            model: root.settGenerator === "classic" ? [] : root.vocabularies
                            Panel {
                                required property var modelData
                                readonly property bool picked: root.settVocabulary === modelData.name
                                hot: picked
                                pad: Math.round(12 * root.ui)
                                width: Math.round(250 * root.ui)
                                opacity: modelData.ready ? 1 : 0.6
                                ColumnLayout {
                                    width: parent.width
                                    spacing: Math.round(4 * root.ui)
                                    PxLabel {
                                        text: modelData.kind === "shipped" ? "THE DEFAULT" : modelData.ready ? "YOURS · READY" : "YOURS · NOT YET"
                                        color: modelData.kind === "shipped" ? root.accentPink : modelData.ready ? root.accentGreen : root.dimText
                                    }
                                    Text { Layout.fillWidth: true; text: modelData.kind === "shipped" ? "bitComposer" : modelData.label; color: root.textColor; font.family: root.mono; font.bold: true; font.pixelSize: Math.round(14 * root.ui); elide: Text.ElideRight }
                                    Body {
                                        font.pixelSize: Math.round(9 * root.ui); color: root.dimText
                                        text: modelData.kind === "shipped" ? "its own vocabulary, as far as the writing has gone; the README says where it was learned"
                                            : modelData.kind === "library" ? modelData.songs + " songs of every game you have read, together"
                                            : modelData.ready ? modelData.songs + " songs · its own sounds come with it"
                                            : modelData.songs + " songs read; a vocabulary needs 40"
                                    }
                                }
                                MouseArea { anchors.fill: parent; enabled: modelData.ready; cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: root.settVocabulary = modelData.name }
                            }
                        }
                        Panel {
                            visible: root.settGenerator === "classic"
                            hot: true
                            pad: Math.round(12 * root.ui)
                            width: Math.round(250 * root.ui)
                            ColumnLayout {
                                width: parent.width
                                spacing: Math.round(4 * root.ui)
                                PxLabel { text: "THE 1.X GENERATOR"; color: root.accentPink }
                                Text { text: "Classic"; color: root.textColor; font.family: root.mono; font.bold: true; font.pixelSize: Math.round(14 * root.ui) }
                                Body { font.pixelSize: Math.round(9 * root.ui); color: root.dimText; text: "no vocabulary; its own knobs below, the chip and Genesis sounds" }
                            }
                        }
                    }

                    // The writer's song: the two switches and the seed.
                    ColumnLayout {
                        visible: root.settGenerator !== "classic"
                        Layout.fillWidth: true
                        spacing: Math.round(16 * root.ui)
                        Heading { text: "2 · THE SONG" }
                        Panel {
                            Layout.fillWidth: true
                            shadow: false
                            ColumnLayout {
                                width: parent.width
                                spacing: Math.round(8 * root.ui)
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(12 * root.ui)
                                    PButton { small: true; text: root.settCarryTheme ? "ON" : "OFF"; on: root.settCarryTheme; implicitWidth: Math.round(56 * root.ui); onClicked: root.settCarryTheme = !root.settCarryTheme }
                                    Body { text: "<b>Carry a theme.</b> The tune's first phrase comes back later in the song (the games do it in two songs of five; this asks for it every time)."; textFormat: Text.StyledText }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(12 * root.ui)
                                    PButton { small: true; text: root.settBandReturns ? "ON" : "OFF"; on: root.settBandReturns; implicitWidth: Math.round(56 * root.ui); onClicked: root.settBandReturns = !root.settBandReturns }
                                    Body { text: "<b>The band returns with it.</b> Never the tune alone: the chords, the bass or the accompaniment come back too, in the song's own mix."; textFormat: Text.StyledText }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(12 * root.ui)
                                    PxLabel { text: "SEED"; Layout.preferredWidth: Math.round(56 * root.ui) }
                                    TextField {
                                        id: seedField
                                        Layout.preferredWidth: Math.round(120 * root.ui)
                                        text: root.settSeed
                                        maximumLength: 9
                                        validator: RegularExpressionValidator { regularExpression: /\d*/ }
                                        color: root.textColor
                                        font.family: root.mono
                                        font.pixelSize: Math.round(12 * root.ui)
                                        selectByMouse: true
                                        background: Rectangle { color: root.bg; border.width: 2; border.color: seedField.activeFocus ? root.accentPink : root.edge }
                                        onEditingFinished: root.settSeed = text
                                    }
                                    Body { text: "A seed names one song, here and on any machine; blank draws one." }
                                }
                            }
                        }
                    }

                    // The sounds it plays on.
                    Heading { text: (root.settGenerator !== "classic" ? "3" : "2") + " · PLAYED ON" }
                    Panel {
                        Layout.fillWidth: true
                        shadow: false
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(8 * root.ui)
                            OptionRow {
                                visible: root.settGenerator !== "classic"
                                label: "BUILT IN"
                                options: ["bit"]
                                labels: ({ bit: "BITCOMPOSER" })
                                value: root.isLibraryPack(root.settSound) ? "" : "bit"
                                onPicked: function(c) { root.settSound = "random" }
                            }
                            OptionRow {
                                visible: root.settGenerator === "classic"
                                label: "SOUND"
                                options: root.builtinSounds
                                value: root.isLibraryPack(root.settSound) ? "" : root.settSound
                                onPicked: function(c) { root.settSound = c }
                            }
                            OptionRow {
                                visible: root.packNames.length > 0
                                label: "YOUR GAMES"
                                options: root.packNames
                                labels: { var m = {}; for (var i = 0; i < backend.packs.length; i++) m[backend.packs[i].name] = backend.packs[i].label; return m }
                                value: root.isLibraryPack(root.settSound) ? root.settSound : ""
                                onPicked: function(c) { root.settSound = (root.settSound === c) ? "random" : c }
                            }
                            Body {
                                color: root.dimText; font.pixelSize: Math.round(10 * root.ui)
                                text: root.settGenerator !== "classic"
                                    ? "bitComposer's own set: generic instruments, synthesised, each fitted to its part by register and speed. A game you have read lends its own samples instead. The chip, Genesis and styled SNES sets belong to Classic."
                                    : "Classic's sounds: the chip, the Genesis and the SNES sets, or one of your games' packs."
                            }
                        }
                    }

                    // Classic's own knobs.
                    ColumnLayout {
                        visible: root.settGenerator === "classic"
                        Layout.fillWidth: true
                        spacing: Math.round(12 * root.ui)
                        Heading { text: "3 · CLASSIC'S KNOBS" }
                        Panel {
                            Layout.fillWidth: true
                            shadow: false
                            ColumnLayout {
                                width: parent.width
                                spacing: Math.round(8 * root.ui)
                                OptionRow {
                                    label: "PRESET"
                                    options: ["FM DRIVE", "GOTHIC", "BOSS FIGHT", "OVERWORLD", "CHILL WAVE", "DUNGEON", "CREDITS", "FIGHT THEME", "CYBER NOIR", "ANY"]
                                    value: root.activePreset
                                    onPicked: function(c) { root.applyPreset(c) }
                                }
                                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 2; color: root.line }
                                OptionRow { label: "KNOBS"; options: ["compose", "drums", "parts"]; value: ["compose", "drums", "parts"][root.settingsTab]; onPicked: function(c) { root.settingsTab = ["compose", "drums", "parts"].indexOf(c) } }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(6 * root.ui)
                                    visible: root.settingsTab === 0
                                    OptionRow { label: "TEMPO"; options: ["random", "slow", "medium", "fast"]; value: root.settTempo; onPicked: function(c) { root.settTempo = c } }
                                    OptionRow { label: "ENERGY"; options: ["random", "chill", "normal", "intense"]; value: root.settEnergy; onPicked: function(c) { root.settEnergy = c } }
                                    OptionRow { label: "SCALE"; options: ["random", "minor", "major", "pentatonic"]; value: root.settScale; onPicked: function(c) { root.settScale = c } }
                                    OptionRow { label: "ECHO"; options: ["random", "on", "off"]; value: root.settEcho; onPicked: function(c) { root.settEcho = c } }
                                    OptionRow { label: "WET"; options: ["random", "light", "normal", "wet"]; value: root.settEchoWet; onPicked: function(c) { root.settEchoWet = c } }
                                    OptionRow { label: "BASS"; options: ["random", "heavy", "medium", "light"]; value: root.settBassWeight; onPicked: function(c) { root.settBassWeight = c } }
                                    OptionRow { label: "FORM"; options: ["random", "standard", "aaba", "rondo", "short", "linear"]; value: root.settForm; onPicked: function(c) { root.settForm = c } }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(6 * root.ui)
                                    visible: root.settingsTab === 1
                                    OptionRow { label: "DENSITY"; options: ["random", "sparse", "normal", "busy"]; value: root.settDrumDensity; onPicked: function(c) { root.settDrumDensity = c } }
                                    OptionRow { label: "FILLS"; options: ["on", "off"]; value: root.settDrumFills ? "on" : "off"; onPicked: function(c) { root.settDrumFills = (c === "on") } }
                                    OptionRow { label: "SWING"; options: ["random", "off", "light", "heavy"]; value: root.settDrumSwing; onPicked: function(c) { root.settDrumSwing = c } }
                                }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(6 * root.ui)
                                    visible: root.settingsTab === 2
                                    OptionRow { label: "MELODY"; options: ["random", "phrased", "simple"]; value: root.settMelody; onPicked: function(c) { root.settMelody = c } }
                                    Body {
                                        color: root.dimText; font.pixelSize: Math.round(10 * root.ui)
                                        text: root.settMelody === "phrased" ? "Motif-based melodies with phrase structure, contour shaping and chorus callbacks."
                                            : root.settMelody === "simple" ? "Random-walk melodies: simpler, less predictable."
                                            : "Phrased or simple, picked per song."
                                    }
                                    OptionRow { label: "VOICING"; options: ["random", "full", "thin"]; value: root.settHarmonyVoicing; onPicked: function(c) { root.settHarmonyVoicing = c } }
                                    OptionRow { label: "MODE"; options: ["random", "sustain", "stabs", "rhythmic"]; value: root.settHarmonyMode; onPicked: function(c) { root.settHarmonyMode = c } }
                                }
                            }
                        }
                    }

                    // The next song, and the button.
                    Panel {
                        Layout.fillWidth: true
                        hot: true
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(8 * root.ui)
                            PxLabel { text: "THE NEXT SONG" }
                            Body { text: root.settingsSummary(); font.pixelSize: Math.round(12 * root.ui); color: root.textColor }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Math.round(10 * root.ui)
                                PButton { text: root.generating ? "WRITING…" : "WRITE AND PLAY"; hot: !root.generating; enabledLook: !root.generating; font.bold: true; font.pixelSize: Math.round(13 * root.ui); implicitHeight: Math.round(44 * root.ui); onClicked: root.generateTrack() }
                                PButton { text: root.autoGenerate ? "AUTO: ON" : "AUTO: OFF"; on: root.autoGenerate; implicitHeight: Math.round(44 * root.ui); onClicked: root.toggleAutoGenerate() }
                                Item { Layout.fillWidth: true }
                                PxLabel { text: "WRITER" }
                                PButton { small: true; text: "BITCOMPOSER"; on: root.settGenerator !== "classic"; onClicked: root.settGenerator = "bitcomposer" }
                                PButton { small: true; text: "CLASSIC (1.X)"; on: root.settGenerator === "classic"; onClicked: root.settGenerator = "classic" }
                            }
                        }
                    }
                }

                // ══ LIBRARY ══
                ColumnLayout {
                    id: packsPanel
                    visible: root.tab === 2
                    Layout.fillWidth: true
                    spacing: Math.round(16 * root.ui)

                    Heading {
                        text: "THE GAMES YOU HAVE READ"
                        aside: {
                            var lib = root.vocabularyOf("library"), n = backend.packs.length
                            return lib ? lib.songs + (lib.songs === 1 ? " song" : " songs") + " read in all" : (n ? n + (n === 1 ? " game" : " games") : "")
                        }
                    }

                    // Read a game: the drop zone's buttons.
                    Panel {
                        Layout.fillWidth: true
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(8 * root.ui)
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Math.round(10 * root.ui)
                                PxLabel { text: "READ A GAME" }
                                Item { Layout.fillWidth: true }
                                PButton { text: "IMPORT"; hot: backend.canImport && !root.importBusy; enabledLook: backend.canImport && !root.importBusy; onClicked: if (backend.canImport && !root.importBusy) backend.importGame() }
                                PButton { text: "ADD A PACK"; onClicked: backend.addPack() }
                            }
                            Body { text: "IMPORT takes a game's SPC set: a folder of .spc files, a zip, or an .rsn, .rar or .7z. Each song runs through the SNES sound hardware's emulator and is read as music; then the game's vocabulary is counted beside its sounds, and the library's over everything you have read. About six minutes for a whole soundtrack; nothing leaves this machine. ADD brings in a pack someone exported." }
                            RowLayout {
                                visible: !backend.canImport
                                Layout.fillWidth: true
                                spacing: Math.round(10 * root.ui)
                                Body {
                                    color: root.warn
                                    text: backend.updateKind === "pipx"
                                        ? "IMPORT needs the SNES emulator, which this player can add from PyPI. ADD works without it."
                                        : backend.updateKind === "frozen"
                                        ? "IMPORT needs the SNES emulator, which this Windows build is missing: reinstall bitComposer from the latest installer."
                                        : "IMPORT needs the SNES emulator: pip install 'bitcomposer[import]' (on pipx: pipx install --force 'bitcomposer[import]')."
                                }
                                PButton { objectName: "getEmulator"; visible: backend.updateKind === "pipx"; text: "GET THE EMULATOR"; hot: !backend.updating; enabledLook: !backend.updating; onClicked: backend.getEmulator() }
                            }
                            // An import running: the songs read so far.
                            ColumnLayout {
                                visible: root.importBusy
                                Layout.fillWidth: true
                                spacing: Math.round(6 * root.ui)
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(10 * root.ui)
                                    PxLabel { text: "READING " + String(backend.importState.name || "").toUpperCase(); color: root.accentPink }
                                    Item { Layout.fillWidth: true }
                                    Text { text: backend.importState.total ? backend.importState.done + " of " + backend.importState.total + " songs" : "unpacking the set…"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui) }
                                    PButton { small: true; text: "STOP"; onClicked: backend.cancelImport() }
                                }
                                Meter { Layout.fillWidth: true; cells: 40; cellW: Math.max(4, Math.floor((width - 78) / 40)); on: backend.importState.total ? Math.round(40 * backend.importState.done / backend.importState.total) : 0 }
                                Body { color: root.dimText; font.pixelSize: Math.round(10 * root.ui); text: (backend.importState.stage ? backend.importState.stage + "…  " : "") + (backend.importState.stage && backend.importState.stage.indexOf("reading") < 0 ? "a few minutes on a whole soundtrack" : "the songs read so far stay read if you stop") }
                            }
                            RowLayout {
                                visible: !!backend.importState.pendingAdd
                                Layout.fillWidth: true
                                spacing: Math.round(10 * root.ui)
                                Body { color: root.warn; text: "A pack named " + String(backend.importState.pendingAdd || "") + " is here already." }
                                PButton { small: true; text: "REPLACE IT"; hot: true; onClicked: backend.confirmReplace(true) }
                                PButton { small: true; text: "KEEP BOTH OFF"; onClicked: backend.confirmReplace(false) }
                            }
                        }
                    }

                    Body { visible: backend.packs.length === 0 && !root.importBusy; text: "No games read yet. The default vocabulary writes without any; a game you read adds its own sounds and, with 40 songs, its own vocabulary." }

                    // Each game: its songs, its vocabulary, its sounds, and what you can do with it.
                    Repeater {
                        model: backend.packs
                        Panel {
                            id: packItem
                            required property var modelData
                            readonly property var p: modelData
                            readonly property var voc: root.vocabularyOf("pack:" + p.name)
                            readonly property bool inUse: root.settSound === p.name
                            Layout.fillWidth: true
                            shadow: false
                            pad: Math.round(12 * root.ui)
                            ColumnLayout {
                                width: parent.width
                                spacing: Math.round(8 * root.ui)
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Math.round(12 * root.ui)
                                    Text { text: packItem.p.label; color: root.textColor; font.family: root.mono; font.bold: true; font.pixelSize: Math.round(13 * root.ui) }
                                    Text { text: (packItem.p.songs ? packItem.p.songs + " songs · " : "") + (packItem.p.moved !== undefined && packItem.p.moved !== null ? packItem.p.moved + " led by another voice · " : "") + packItem.p.samples + " samples" + (Object.keys(packItem.p.kit).length ? " · a kit of " + Object.keys(packItem.p.kit).length : ""); color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); elide: Text.ElideRight; Layout.fillWidth: true }
                                    PxLabel {
                                        text: packItem.voc ? (packItem.voc.ready ? "■ VOCABULARY READY" : "VOCABULARY NEEDS 40 · " + packItem.voc.songs + " READ") : "NO VOCABULARY YET"
                                        color: packItem.voc && packItem.voc.ready ? root.accentGreen : root.dimText
                                    }
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: Math.round(8 * root.ui)
                                    PButton { small: true; text: packItem.inUse ? "ITS SOUNDS IN USE" : "USE ITS SOUNDS"; on: packItem.inUse; onClicked: root.settSound = packItem.inUse ? "random" : packItem.p.name }
                                    PButton { small: true; text: "SOUNDS"; onClicked: { root.packOpen = packItem.p.name; root.packVoice = ""; root.tab = 3 } }
                                    PButton { small: true; visible: !!packItem.voc && packItem.voc.ready; text: root.settVocabulary === "pack:" + packItem.p.name ? "WRITING FROM IT" : "WRITE FROM IT"; on: root.settVocabulary === "pack:" + packItem.p.name; onClicked: { root.settGenerator = "bitcomposer"; root.settVocabulary = "pack:" + packItem.p.name; root.tab = 1 } }
                                    PButton { small: true; text: "EXPORT"; onClicked: backend.exportPack(packItem.p.name) }
                                    PButton { small: true; visible: root.packRenaming !== packItem.p.name; text: "RENAME"; onClicked: { root.packRenaming = packItem.p.name; root.packConfirm = "" } }
                                    PButton { small: true; visible: root.packConfirm !== packItem.p.name; text: "DELETE"; onClicked: root.packConfirm = packItem.p.name }
                                    PxLabel { visible: root.packConfirm === packItem.p.name; text: "DELETE IT?"; color: root.accentPink; topPadding: Math.round(6 * root.ui) }
                                    PButton { small: true; visible: root.packConfirm === packItem.p.name; text: "YES"; hot: true; onClicked: { var n = packItem.p.name; root.packConfirm = ""; if (root.packOpen === n) root.packOpen = ""; backend.deletePack(n) } }
                                    PButton { small: true; visible: root.packConfirm === packItem.p.name; text: "NO"; onClicked: root.packConfirm = "" }
                                }
                                RowLayout {
                                    visible: root.packRenaming === packItem.p.name
                                    Layout.fillWidth: true
                                    spacing: Math.round(8 * root.ui)
                                    TextField {
                                        id: renameField
                                        Layout.fillWidth: true
                                        text: packItem.p.name
                                        maximumLength: 24
                                        color: root.textColor
                                        font.family: root.mono
                                        font.pixelSize: Math.round(12 * root.ui)
                                        selectByMouse: true
                                        background: Rectangle { color: root.bg; border.width: 2; border.color: renameField.activeFocus ? root.accentPink : root.edge }
                                        onAccepted: saveRename.clicked()
                                    }
                                    PButton {
                                        id: saveRename
                                        small: true; text: "SAVE"
                                        onClicked: {
                                            var n = renameField.text.trim().toLowerCase(), old = packItem.p.name
                                            var used = root.settSound === old
                                            root.packRenaming = ""
                                            if (n === old) return
                                            backend.renamePack(old, n)
                                            if (root.isLibraryPack(n)) {
                                                if (root.packOpen === old) root.packOpen = n
                                                if (used) root.settSound = n
                                            }
                                        }
                                    }
                                    PButton { small: true; text: "CANCEL"; onClicked: root.packRenaming = "" }
                                }
                            }
                        }
                    }

                    // The library's own vocabulary, over everything.
                    Panel {
                        Layout.fillWidth: true
                        shadow: false
                        visible: !!root.vocabularyOf("library")
                        pad: Math.round(12 * root.ui)
                        RowLayout {
                            width: parent.width
                            spacing: Math.round(12 * root.ui)
                            Text { text: "your library"; color: root.textColor; font.family: root.mono; font.bold: true; font.pixelSize: Math.round(13 * root.ui) }
                            Text { Layout.fillWidth: true; text: (root.vocabularyOf("library") ? root.vocabularyOf("library").songs : 0) + " songs of every game together"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui) }
                            PxLabel { text: root.vocabularyOf("library") && root.vocabularyOf("library").ready ? "■ VOCABULARY READY" : "VOCABULARY NEEDS 40"; color: root.vocabularyOf("library") && root.vocabularyOf("library").ready ? root.accentGreen : root.dimText }
                            PButton { small: true; visible: !!root.vocabularyOf("library") && root.vocabularyOf("library").ready; text: root.settVocabulary === "library" ? "WRITING FROM IT" : "WRITE FROM IT"; on: root.settVocabulary === "library"; onClicked: { root.settGenerator = "bitcomposer"; root.settVocabulary = "library"; root.tab = 1 } }
                        }
                    }
                }

                // ══ SOUNDS ══
                ColumnLayout {
                    visible: root.tab === 3
                    Layout.fillWidth: true
                    spacing: Math.round(16 * root.ui)
                    readonly property var pack: root.packOf(root.packOpen)

                    Heading { text: "A SET OF SOUNDS"; aside: parent.pack ? parent.pack.samples + " samples · click one to hear it as the game plays it" : "" }
                    OptionRow {
                        visible: root.packNames.length > 0
                        label: "YOUR GAMES"
                        options: root.packNames
                        labels: { var m = {}; for (var i = 0; i < backend.packs.length; i++) m[backend.packs[i].name] = backend.packs[i].label; return m }
                        value: root.packOpen
                        onPicked: function(c) { root.packOpen = c; root.packVoice = ""; root.packConfirm = ""; root.packRenaming = "" }
                    }
                    Body { visible: root.packNames.length === 0; text: "No games read yet. The built-in sets (FFVI, Mana, Evermore, Mega Man X) are code and cannot be edited; a game you read under LIBRARY shows its samples here, by part, to hear and to move." }
                    Body { visible: root.packNames.length > 0 && !parent.pack; text: "Pick a game above. Each sample sits where the game played it most; move one when the reading got it wrong. A written song takes its samples from here by part." }

                    Panel {
                        Layout.fillWidth: true
                        visible: !!parent.pack
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(10 * root.ui)
                            readonly property var p: root.packOf(root.packOpen)
                            Repeater {
                                model: { var pk = root.packOf(root.packOpen); return pk ? root.partOrder.filter(function(k) { return pk.parts[k] && pk.parts[k].length > 0 }) : [] }
                                VoiceRow {
                                    required property string modelData
                                    label: modelData.replace("_", " ").toUpperCase()
                                    pack: root.packOpen
                                    items: root.packOf(root.packOpen).parts[modelData].map(function(v) { return { voice: v, part: modelData, text: root.shortVoice(v) } })
                                }
                            }
                            VoiceRow {
                                visible: !!parent.p && Object.keys(parent.p.kit).length > 0
                                label: "THE KIT"
                                pack: root.packOpen
                                items: { var pk = root.packOf(root.packOpen); return pk ? root.kitPieces.filter(function(k) { return pk.kit[k] !== undefined }).map(function(k) { return { voice: pk.kit[k], part: k, text: k.replace("_", " ") } }) : [] }
                            }
                            VoiceRow {
                                visible: !!parent.p && parent.p.out.length > 0
                                label: "LEFT OUT"
                                pack: root.packOpen
                                items: { var pk = root.packOf(root.packOpen); return pk ? pk.out.map(function(v) { return { voice: v, part: "out", text: root.shortVoice(v) } }) : [] }
                            }
                        }
                    }

                    // The sample picked: why it is where it is, and where else it can go.
                    Panel {
                        Layout.fillWidth: true
                        hot: true
                        visible: !!parent.pack && root.packVoice !== ""
                        ColumnLayout {
                            width: parent.width
                            spacing: Math.round(8 * root.ui)
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Math.round(12 * root.ui)
                                PxLabel { text: "SELECTED" }
                                Text { text: root.packVoice; color: root.textColor; font.family: root.mono; font.bold: true; font.pixelSize: Math.round(13 * root.ui) }
                                Text { text: root.packVoicePart.replace("_", " "); color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(11 * root.ui) }
                                Item { Layout.fillWidth: true }
                                PButton { small: true; text: "HEAR IT"; onClicked: backend.previewVoice(root.packOpen, root.packVoice, root.packVoicePart) }
                            }
                            Body { text: root.packOf(root.packOpen) ? root.whyText(root.packOf(root.packOpen), root.packVoice) : "" }
                            OptionRow {
                                label: "MOVE TO"
                                options: root.packOf(root.packOpen) ? root.movesFor(root.packOf(root.packOpen), root.packVoice) : []
                                value: root.packVoicePart
                                onPicked: function(c) {
                                    var name = root.packOpen, v = root.packVoice
                                    root.packVoicePart = c
                                    backend.movePack(name, v, c)
                                }
                            }
                            Body { color: root.dimText; font.pixelSize: Math.round(10 * root.ui); text: "A move takes effect on the next song written on this set; the game's reading is kept, so importing the game again starts the set fresh." }
                        }
                    }
                }
            }
        }

        // ── Footer: the last thing the engine said ──
        Rectangle {
            id: footer
            Layout.fillWidth: true
            implicitHeight: footerRow.implicitHeight + Math.round(12 * root.ui)
            color: root.panel
            Dither { anchors.fill: parent }
            Rectangle { width: parent.width; height: 2; color: root.line }
            RowLayout {
                id: footerRow
                anchors.fill: parent
                anchors.leftMargin: Math.round(16 * root.ui)
                anchors.rightMargin: Math.round(16 * root.ui)
                spacing: Math.round(12 * root.ui)
                Sprite { rows: root.glyphs.dot; tint: root.generating ? root.accentPink : root.accentGreen; px: Math.max(1, Math.round(1.5 * root.ui)) }
                Text { text: root.generating ? "writing" : root.importBusy ? "reading" : "ready"; color: root.generating ? root.accentPink : root.accentGreen; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui) }
                Text { Layout.fillWidth: true; text: backend.notice; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(10 * root.ui); elide: Text.ElideRight }
                Text { text: "SNES back end"; color: root.dimText; font.family: root.mono; font.pixelSize: Math.round(9 * root.ui) }
            }
        }
    }

    // ── The update screen ──
    // Over the whole window while an update is asked for, running, or has ended.
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
        color: root.bg
        z: 30
        MouseArea { anchors.fill: parent; hoverEnabled: true; preventStealing: true; onWheel: function(w) { w.accepted = true } }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Math.round(24 * root.ui)
            spacing: Math.round(12 * root.ui)

            RowLayout {
                Layout.fillWidth: true
                spacing: Math.round(12 * root.ui)
                Lockup {}
                PxLabel { text: root.gettingEmulator ? "THE SNES EMULATOR" : "UPDATE"; color: root.accentPink; font.pixelSize: Math.round(11 * root.ui) }
                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 2; color: root.line }
            }
            Text {
                text: root.gettingEmulator ? "v" + backend.version + "  +  bitcomposer-emu" : "v" + backend.version + "  →  v" + backend.updateVersion
                color: root.textColor
                font.family: root.pixel
                font.pixelSize: Math.round(18 * root.ui)
                font.bold: true
            }
            Body {
                color: backend.updateState === "failed" ? root.warn : root.text2
                font.pixelSize: Math.round(12 * root.ui)
                text: {
                    var st = backend.updateState, kind = backend.updateKind
                    if (root.gettingEmulator) {
                        if (st === "confirm") return "pipx adds the SNES emulator from PyPI to this player, restarting it when it is in. IMPORT then reads a game's SPC files here."
                        if (st === "running") return "Getting the emulator…  " + root._updElapsed + " s"
                        if (st === "done") return "Done. Restarting…"
                        if (st === "failed") return "The emulator was not installed; the player is unchanged. The log says why."
                        return ""
                    }
                    if (st === "confirm") {
                        if (kind === "pipx") return "pipx reinstalls bitComposer at the new version (with Qt, a minute or so), then the player restarts. Your songs, packs and settings stay."
                        if (kind === "frozen") return "The new installer downloads here, then runs with its own window; this player closes when it starts. Your songs, packs and settings stay."
                        return "This copy was not installed by pipx or the installer (a checkout, or a plain pip install), so it updates the way it was installed: see the release page."
                    }
                    if (st === "running") return (kind === "frozen" ? "Downloading the installer…" : "Updating…  " + root._updElapsed + " s")
                    if (st === "done") return kind === "pipx" ? "Updated. Restarting…" : "The installer is starting; this player closes now."
                    if (st === "failed") return "The update did not finish; the player is unchanged. The log says why; the release page has the installer and the notes."
                    return ""
                }
            }
            Meter {
                visible: backend.updateState === "running" || backend.updateState === "done"
                cells: 40
                cellW: Math.max(4, Math.floor((parent.width - 78) / 40))
                on: backend.updateState === "done" ? 40 : backend.updateProgress >= 0 ? Math.round(40 * Math.max(0, Math.min(1, backend.updateProgress))) : (root._updElapsed % 40)
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                visible: backend.updateState !== "confirm"
                color: "#0a0a0e"
                border.width: 2
                border.color: root.line
                ListView {
                    id: updLog
                    objectName: "updateLog"
                    anchors.fill: parent
                    anchors.margins: Math.round(10 * root.ui)
                    clip: true
                    model: backend.updateLog
                    boundsBehavior: Flickable.StopAtBounds
                    onCountChanged: Qt.callLater(updLog.positionViewAtEnd)
                    ScrollBar.vertical: ScrollBar { policy: updLog.contentHeight > updLog.height ? ScrollBar.AlwaysOn : ScrollBar.AlwaysOff; contentItem: Rectangle { color: root.edge } }
                    delegate: Text {
                        required property string modelData
                        width: updLog.width - Math.round(10 * root.ui)
                        text: modelData
                        wrapMode: Text.WrapAnywhere
                        color: modelData.indexOf("$ ") === 0 ? root.accentPink
                             : /failed|error|exited with|not found|could not/i.test(modelData) ? root.warn
                             : root.text2
                        font.family: root.mono
                        font.pixelSize: Math.round(10 * root.ui)
                        lineHeight: 1.15
                    }
                }
            }
            Item { Layout.fillHeight: true; visible: backend.updateState === "confirm" }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: Math.round(10 * root.ui)
                PButton { visible: backend.updateState === "confirm" || backend.updateState === "failed"; text: backend.updateState === "failed" ? "CLOSE" : "LATER"; onClicked: backend.closeUpdate() }
                PButton { visible: backend.updateState === "failed" || (backend.updateState === "confirm" && backend.updateKind === "other"); text: root.gettingEmulator ? "BUILDING IT" : "RELEASE PAGE"; onClicked: backend.openReleasePage() }
                PButton { objectName: "updateNow"; visible: backend.updateState === "confirm" && backend.updateKind !== "other"; text: root.gettingEmulator ? "GET IT" : "UPDATE NOW"; hot: true; onClicked: backend.confirmUpdate() }
            }
        }
    }
}
