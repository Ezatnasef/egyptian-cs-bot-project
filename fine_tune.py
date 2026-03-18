"""
Fine-tuning and Formatting Script for Egyptian CS Bot
Focus: Preparing audio-text datasets for local STT models
"""

import json
import os
import argparse
from pathlib import Path
from tqdm import tqdm

DATASET_PATH = Path(__file__).parent / "dataset" / "egyptian_cs_dataset.json"

def format_stt_dataset(audio_dir: str, output_json: str):
    """
    Format dataset for STT local fine-tuning.
    Expects audio files in `audio_dir` named `id_role_turn.wav`.
    For example: `1_customer_0.wav` corresponds to conversation id 1, role customer, turn 0.
    """
    import soundfile as sf
    import librosa
    
    print(f"Reading textual dataset from {DATASET_PATH}...")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        text_dataset = json.load(f)
        
    stt_data = []
    missing_audios = 0
    found_audios = 0
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_json) if os.path.dirname(output_json) else ".", exist_ok=True)
    
    print(f"Scanning '{audio_dir}' for corresponding audio files...")
    
    # Iterate through textual conversations
    for conv in tqdm(text_dataset):
        conv_id = conv["id"]
        dialect = conv["dialect"]
        
        for turn_idx, turn in enumerate(conv["conversation"]):
            # For STT, we primarily care about the customer's voice
            if turn["role"] == "customer":
                # Expected file format: audio_dir/1_customer_0.wav
                expected_filename = f"{conv_id}_{turn['role']}_{turn_idx}.wav"
                audio_path = os.path.join(audio_dir, expected_filename)
                
                if os.path.exists(audio_path):
                    try:
                        # Validate audio matches local STT requirements (e.g. 16kHz)
                        duration = librosa.get_duration(path=audio_path)
                        stt_data.append({
                            "audio_path": os.path.abspath(audio_path),
                            "transcription": turn["text"],
                            "dialect": dialect,
                            "duration_sec": round(duration, 2)
                        })
                        found_audios += 1
                    except Exception as e:
                        print(f"Error Processing {audio_path}: {e}")
                else:
                    missing_audios += 1

    # Save STT dataset
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(stt_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n✅ STT Dataset Formatting Complete!")
    print(f"Output saved to: {output_json}")
    print(f"Matched audio files: {found_audios}")
    print(f"Missing audio files: {missing_audios} (generate or record these to expand the dataset)")
    print("\nYou can now use this JSON file to fine-tune Wav2Vec2 or Whisper locally.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare dataset for Local STT.")
    parser.add_argument("--mode", choices=["stt-prep"], default="stt-prep", help="Mode string")
    parser.add_argument("--audio-dir", required=True, help="Directory containing the .wav audio files")
    parser.add_argument("--output", default="./dataset/stt_dataset.json", help="Output JSON path")
    
    args = parser.parse_args()
    
    if args.mode == "stt-prep":
        if not os.path.exists(args.audio_dir):
            print(f"❌ Error: Audio directory '{args.audio_dir}' does not exist.")
            exit(1)
        format_stt_dataset(args.audio_dir, args.output)
