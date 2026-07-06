"""
Build the hackathon video presentation with a natural neural voice.

Run this on any machine with normal internet access (the CI/dev sandbox that
built everything else has an egress allowlist that blocks TTS services, which
is why the fallback video used a synthetic voice).

Usage:
    pip install edge-tts imageio-ffmpeg
    python assets/build_video.py

Output: hybrid-routing-agent-presentation.mp4 (1080p, ~2.5 min) in the repo root.
Change the voice with e.g.:  VOICE=en-US-AriaNeural python assets/build_video.py
Preview available voices:    edge-tts --list-voices | grep en-US
"""
import asyncio
import os
import subprocess
import sys
import wave

import edge_tts
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "_video_build")
FINAL = os.path.join(HERE, "..", "hybrid-routing-agent-presentation.mp4")
VOICE = os.environ.get("VOICE", "en-US-AndrewNeural")
FF = imageio_ffmpeg.get_ffmpeg_exe()

NARRATION = {
    1: "Hi! This is the Hybrid Routing Agent, our entry for Track 1 of the AMD "
       "Developer Hackathon. The idea is simple: every query takes the cheapest "
       "path that still gets the answer right.",
    2: "The competition scores in two steps. First, an LLM judge checks accuracy — "
       "fail the bar and you're off the leaderboard. Then survivors are ranked by "
       "total Fireworks tokens, and fewest wins. Our insight: most prompts don't "
       "need a frontier model. Paying big-model tokens to answer twelve plus "
       "forty-seven is throwing away rank.",
    3: "At the core is a twelve-signal complexity router. Regex and keyword "
       "signals — covering code, math, reasoning, entity extraction, sentiment, "
       "and format constraints — score every prompt from zero to one, with no "
       "extra LLM call. Easy prompts run on a local phi-3 mini model, for free. "
       "Hard ones go straight to Fireworks. In between, a cascade tries the local "
       "model first, and only escalates when a confidence check says the answer "
       "looks shaky.",
    4: "Everything ships as one Docker container built for the judging harness. "
       "It reads tasks from input, answers them concurrently with per-task "
       "isolation and an internal deadline, and writes valid results before "
       "exiting. The local model's weights are baked into the image, and every "
       "credential and model name comes from the environment at runtime — nothing "
       "is hardcoded.",
    5: "And this is all proven, not promised. On the published image, our CI "
       "verified twelve out of twelve sample answers with zero remote tokens, all "
       "eight capability categories answered end to end, a fifty-second batch "
       "against a ten-minute limit, and a three point six gigabyte image against "
       "a ten gigabyte cap.",
    6: "We also never waste an answer. If a remote call fails, the agent returns "
       "the local answer it already computed — a shaky answer can still pass the "
       "judge, but an empty one never can. One crashing task can't sink the "
       "batch, and every failure path is exercised in CI.",
    7: "Hybrid Routing Agent. Big-model accuracy, small-model bill. The image is "
       "public on GitHub Container Registry. Thanks for watching!",
}


async def synth(i: int, text: str) -> None:
    mp3 = os.path.join(OUT_DIR, f"narr{i}.mp3")
    await edge_tts.Communicate(text, VOICE).save(mp3)
    # decode to wav so we can measure duration with the stdlib
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", mp3,
                    os.path.join(OUT_DIR, f"narr{i}.wav")], check=True)


def wav_duration(path: str) -> float:
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Synthesizing narration with voice {VOICE!r}…")
    loop = asyncio.new_event_loop()
    for i, text in NARRATION.items():
        loop.run_until_complete(synth(i, text))
        print(f"  slide {i} narrated")

    concat = os.path.join(OUT_DIR, "concat.txt")
    with open(concat, "w") as f:
        for i in NARRATION:
            slide = os.path.join(HERE, "slides", f"slide{i}.png")
            wav = os.path.join(OUT_DIR, f"narr{i}.wav")
            seg = os.path.join(OUT_DIR, f"seg{i}.mp4")
            seg_dur = wav_duration(wav) + 1.4  # 0.7s lead-in + tail room
            subprocess.run([FF, "-y", "-loglevel", "error",
                "-loop", "1", "-framerate", "30", "-t", f"{seg_dur:.2f}", "-i", slide,
                "-i", wav,
                "-af", "adelay=700|700,apad",
                "-t", f"{seg_dur:.2f}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "21",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                seg], check=True)
            f.write(f"file '{seg}'\n")
            print(f"  segment {i} rendered ({seg_dur:.1f}s)")

    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", concat, "-c", "copy", FINAL], check=True)
    print(f"\nDone: {os.path.abspath(FINAL)}")


if __name__ == "__main__":
    sys.exit(main())
