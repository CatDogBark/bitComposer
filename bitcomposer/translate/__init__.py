"""
The translator: a game's songs read as music, for a pack (docs/TRANSLATOR.md).

Step 4 of docs/SPC-IMPORT.md. The SNES chip decoder (bitcomposer.spc.notes)
gives the notes as the driver played them; the translator reads them as
music: each note named (`events`), the beat and bar they sit on (`beat`),
then the chords, the roles and the form, measured rather than assumed, and
kept in a database on the user's machine. The readings are the music as
played, in no vocabulary of the generator's, so a pack in any vocabulary
can be made from them.

`python -m bitcomposer.translate FILE.spc` reports a song's reading.
"""
