---
name: rpg-tts-production
description: Prepare, record, verify and hand off an assigned Kolkhoz speech or wordless resident voice batch with Gemini TTS. Use for new takes and approved retakes.
---

# RPG voice production

Read [AGENTS.md](../../AGENTS.md), the design's Audio → Speech section, and the
speaker's current passport. The [resident palette proposal](../../manual/voice/character-voices-proposal.md)
records its approval and implementation status. For the prologue, use the
[cues and passports](../../manual/voice/prologue-pilot.md).

1. Confirm the assigned batch, exact approved RU and EN, revisions, scene
   eligibility, speaker and cue. Check `approved_rev = rev` in the source and
   EN `src_rev = rev` with reviewed status in the shared catalog. An old take
   keeps its original revision. Once text changes, mark the mismatch until
   the replacement has been placed in the build.
2. Reuse the speaker's accepted voice in both languages. When selecting a new
   stock voice, check its catalog gender before a paid audition and compare
   its delivery to the intended age and character. Use the exact transcript
   as spoken text. Put performance direction in speech metadata. Wordless
   cues use the same voice and go to Sounds. Treat «М-да» as subtitled speech.
3. Read and update [the budget ledger](../../ai/gemini-budget-balance.txt)
   before any authorized paid run. Verify current rates with
   [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing). Use the
   existing model runner or `tools/voice_prologue_v2.py`'s one-line request
   function for a scoped batch. The runner should share
   `tools/voice_rate_limit.py` and its attempt log. Consult Audio → Speech
   for the 429 recovery procedure. Confirm credentials without printing them.
4. Keep locale, key, avatar, exact transcript and hash, source revision, voice,
   direction, model, WAV hash, duration, interaction ID and usage in the
   receipt. Account for paid failures and replacements as well as successes.
   Flag missing usage and never count a copied receipt twice. Use a separate
   output directory for replacements and preserve earlier takes.
5. Validate the expected WAV/receipt pairs and current transcripts. The
   existing Gemini runner returns complete mono PCM16 WAVs at 24 kHz. For
   listening review check delivery, pronunciation, extra words, and scene
   timing. Keep technical validation and hearing approval recorded separately.
6. Hand the manifest and raw WAVs to the coordinator for sound mastering and
   UE placement. A copy under `/data/kolkhoz/voice/` is for handoff or review.
   Keep the source copies according to the repository's voice layout. Record
   the actual cost, cumulative spend and estimated remainder in the budget
   ledger and clean your temporary files after delivery.
