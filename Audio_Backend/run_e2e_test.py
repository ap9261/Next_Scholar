#!/usr/bin/env python3
"""
End-to-end test for the NextScholar Audio Backend.

This script tests the complete audio pipeline with a real classroom audio file:
1. Start FastAPI server
2. Upload real audio file
3. Trigger analysis
4. Poll for completion
5. Retrieve and validate results
6. Report findings
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"
REAL_AUDIO = r"D:\Intership\NextSchlor\test_2\NS26B_Math-Science Danish Sir_20260221_155836_audio_only.m4a"
TIMELINE_JSON = r"D:\Intership\NextSchlor\test_2\NS26B_Math-Science Danish Sir_20260221_155836_timeline.json"
OUTPUT_DIR = Path("D:/Intership/NextSchlor/Backend_testing/outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def wait_for_server(max_retries=30, delay=2):
    for i in range(max_retries):
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=5)
            if resp.status_code == 200:
                print(f"[OK] Server ready after {i * delay}s")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(delay)
    print("[FAIL] Server did not start in time")
    return False


def upload_audio(audio_path, timeline_path=None):
    print(f"\n[STEP] Uploading audio: {Path(audio_path).name}")
    with open(audio_path, "rb") as f:
        files = {"file": (Path(audio_path).name, f, "audio/mp4")}
        data = {}
        if timeline_path and os.path.exists(timeline_path):
            with open(timeline_path, "rb") as tf:
                files["timeline_json"] = (Path(timeline_path).name, tf, "application/json")
                resp = requests.post(f"{BASE_URL}/api/audio/upload", files=files)
        else:
            resp = requests.post(f"{BASE_URL}/api/audio/upload", files=files)

    if resp.status_code != 200:
        print(f"[FAIL] Upload failed: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    audio_id = data.get("audio_id")
    print(f"[OK] Uploaded. audio_id={audio_id}")
    print(f"      filename={data.get('filename')}")
    print(f"      duration={data.get('duration')}s")
    print(f"      format={data.get('format')}")
    print(f"      sample_rate={data.get('sample_rate')}")
    print(f"      channels={data.get('channels')}")
    print(f"      file_size={data.get('file_size')} bytes")
    return audio_id


def start_analysis(audio_id):
    print(f"\n[STEP] Starting analysis for audio_id={audio_id}")
    resp = requests.post(f"{BASE_URL}/api/audio/analyze", params={"audio_id": audio_id})
    if resp.status_code != 200:
        print(f"[FAIL] Analysis start failed: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    job_id = data.get("job_id")
    print(f"[OK] Analysis queued. job_id={job_id}")
    return job_id


def poll_job(job_id, timeout=7200, interval=30):
    print(f"\n[STEP] Polling job {job_id} (timeout={timeout}s, interval={interval}s)")
    start = time.time()
    last_stage = None
    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            print(f"[TIMEOUT] Job did not complete within {timeout}s")
            return None
        resp = requests.get(f"{BASE_URL}/api/audio/status/{job_id}")
        if resp.status_code != 200:
            print(f"[FAIL] Status check failed: {resp.status_code}")
            return None
        data = resp.json()
        status = data.get("status")
        stage = data.get("current_stage")
        progress = data.get("progress", 0)
        if stage != last_stage:
            print(f"  [{elapsed:.0f}s] status={status} stage={stage} progress={progress:.1f}%")
            last_stage = stage
        if status in ("completed", "failed"):
            print(f"[OK] Job finished with status={status}")
            return data
        time.sleep(interval)


def retrieve_result(job_id):
    print(f"\n[STEP] Retrieving result for job_id={job_id}")
    resp = requests.get(f"{BASE_URL}/api/audio/result/{job_id}")
    if resp.status_code != 200:
        print(f"[FAIL] Result retrieval failed: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data


def validate_result(result):
    print("\n[STEP] Validating result structure")
    required_top = ["job_id", "status", "audio", "transcript", "analysis"]
    for key in required_top:
        if key not in result:
            print(f"[FAIL] Missing top-level key: {key}")
            return False
    audio = result.get("audio", {})
    if not audio.get("filename"):
        print("[FAIL] Missing audio filename")
        return False
    transcript = result.get("transcript")
    if not transcript:
        print("[WARN] No transcript in result")
    else:
        segments = transcript.get("segments", [])
        print(f"      Transcript segments: {len(segments)}")
        if segments:
            print(f"      Sample segment: {segments[0]}")
    analysis = result.get("analysis", {})
    print(f"      Analysis keys: {list(analysis.keys())}")
    for key in ["interaction", "communication_quality", "student_performance", "communication_sentiment", "final_report"]:
        if key not in analysis:
            print(f"[WARN] Missing analysis section: {key}")
        else:
            print(f"      {key}: present")
    print("[OK] Result structure validated")
    return True


def save_report(result, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"[OK] Report saved to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", default=REAL_AUDIO)
    parser.add_argument("--timeline", default=TIMELINE_JSON)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--interval", type=int, default=30)
    args = parser.parse_args()

    audio_path = args.audio
    timeline_path = args.timeline

    if not os.path.exists(audio_path):
        print(f"[FAIL] Audio file not found: {audio_path}")
        sys.exit(1)

    print("=" * 70)
    print(" AUDIO BACKEND END-TO-END TEST")
    print("=" * 70)
    print(f"Audio file : {audio_path}")
    print(f"File size  : {os.path.getsize(audio_path) / (1024*1024):.1f} MB")
    print(f"Timeline   : {timeline_path if os.path.exists(timeline_path) else 'None'}")

    if not wait_for_server():
        sys.exit(1)

    audio_id = upload_audio(audio_path, timeline_path)
    if not audio_id:
        sys.exit(1)

    job_id = start_analysis(audio_id)
    if not job_id:
        sys.exit(1)

    job_status = poll_job(job_id, timeout=args.timeout, interval=args.interval)
    if not job_status:
        sys.exit(1)

    if job_status.get("status") == "failed":
        print(f"[FAIL] Job failed: {job_status.get('error_message')}")
        sys.exit(1)

    result = retrieve_result(job_id)
    if not result:
        sys.exit(1)

    validate_result(result)

    report_path = OUTPUT_DIR / f"e2e_test_report_{job_id}.json"
    save_report(result, report_path)

    print("\n" + "=" * 70)
    print(" END-TO-END TEST COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Job ID     : {job_id}")
    print(f"Audio ID   : {audio_id}")
    print(f"Status     : {result.get('status')}")
    print(f"Report     : {report_path}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
