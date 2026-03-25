#!/usr/bin/env python3
"""Generate podcast audio with OpenAI TTS."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request


def load_api_key(env_path: str) -> str:
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"]

    with open(env_path, "r", encoding="utf-8") as f:
        value = f.read().strip()
    if not value:
        raise RuntimeError(f"empty API key file: {env_path}")
    return value


MAX_CHARS_PER_REQUEST = 3500


def synthesize_chunk(
    api_key: str,
    model: str,
    voice: str,
    instructions: str,
    text: str,
    response_format: str,
    out_path: str,
) -> None:
    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "instructions": instructions,
        "response_format": response_format,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            audio = resp.read()
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI TTS request failed: HTTP {exc.code}: {details}") from exc

    with open(out_path, "wb") as f:
        f.write(audio)


def split_text(text: str, max_chars: int) -> list[str]:
    chunks = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n\n", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = remaining.rfind(". ", 0, max_chars)
        if split_at < max_chars // 2:
            split_at = remaining.rfind(" ", 0, max_chars)
        if split_at <= 0:
            split_at = max_chars

        chunk = remaining[:split_at].strip()
        remaining = remaining[split_at:].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def concat_wavs_to_mp3(wav_files: list[str], out_path: str) -> None:
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
        concat_file = f.name
        for wav_file in wav_files:
            f.write(f"file '{wav_file}'\n")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file,
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")
    finally:
        os.unlink(concat_file)


def generate_audio_file(
    script_file: str,
    out_file: str,
    *,
    env_file: str = "/agent/identity/openai.env",
    model: str = "gpt-4o-mini-tts",
    voice: str = "cedar",
    instructions: str = (
        "Speak like a confident podcast host. Warm, clear, and conversational. "
        "Keep a steady pace, slight smile in the voice, and crisp enunciation for numbers."
    ),
) -> dict:
    api_key = load_api_key(env_file)
    with open(script_file, "r", encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        raise RuntimeError(f"empty script file: {script_file}")

    chunks = split_text(text, MAX_CHARS_PER_REQUEST)
    with tempfile.TemporaryDirectory(prefix="openai-tts-") as tmpdir:
        wav_files = []
        for i, chunk in enumerate(chunks, start=1):
            wav_path = os.path.join(tmpdir, f"chunk-{i:02d}.wav")
            synthesize_chunk(
                api_key,
                model,
                voice,
                instructions,
                chunk,
                "wav",
                wav_path,
            )
            wav_files.append(wav_path)
        concat_wavs_to_mp3(wav_files, out_file)

    return {
        "characters": len(text),
        "chunks": len(chunks),
        "model": model,
        "voice": voice,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script_file")
    parser.add_argument("out_file")
    parser.add_argument("--env-file", default="/agent/identity/openai.env")
    parser.add_argument("--model", default="gpt-4o-mini-tts")
    parser.add_argument("--voice", default="cedar")
    parser.add_argument(
        "--instructions",
        default=(
            "Speak like a confident podcast host. Warm, clear, and conversational. "
            "Keep a steady pace, slight smile in the voice, and crisp enunciation for numbers."
        ),
    )
    args = parser.parse_args()

    result = generate_audio_file(
        args.script_file,
        args.out_file,
        env_file=args.env_file,
        model=args.model,
        voice=args.voice,
        instructions=args.instructions,
    )

    print(f"Wrote {args.out_file}")
    print(f"Characters: {result['characters']}")
    print(f"Chunks: {result['chunks']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
