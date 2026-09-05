import json
import numpy as np
import librosa
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')



def time_to_seconds(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def get_sentiment(segment, sr):

    if len(segment) < sr * 0.3:
        return "neutral"
    
    
    energy = np.mean(librosa.feature.rms(y=segment))
    
    
    pitches, magnitudes = librosa.piptrack(y=segment, sr=sr)
    valid_pitches = pitches[magnitudes > np.median(magnitudes)]
    pitch = np.mean(valid_pitches) if len(valid_pitches) > 0 else 0
    
    
    zcr = np.mean(librosa.feature.zero_crossing_rate(segment))
    speech_rate = zcr * sr * 5
    
    

    # Main part
    if energy > 0.025 and pitch > 160 and speech_rate > 3.5:
        return "positive"
    elif energy < 0.012 and pitch < 130 and speech_rate < 2.8:
        return "negative"
    else:
        return "neutral"
    


def extract_speaker_timeline(json_file):


    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    timeline = data["timeline"]
    
    speaker_times = defaultdict(list)
    user_is_teacher = {}
    

    for entry in timeline:
        current_time = time_to_seconds(entry["ts"])
        
        for user in entry.get("users", []):
            username = user.get("username", "").strip()
            zoom_userid = user.get("zoom_userid", "").strip()
            
            if not username:
                continue
            
            speaker_times[username].append(current_time)
            
            # Mark teacher (has zoom_userid)
            if username not in user_is_teacher:
                user_is_teacher[username] = bool(zoom_userid)
    
    # Convert timestamps to continuous intervals
    speaker_intervals = {}
    
    for speaker, times in speaker_times.items():
        if len(times) < 2:
            continue
        
        times.sort()
        intervals = []
        start = times[0]
        prev = times[0]
        
        for t in times[1:]:
            if t - prev > 2.0:
                intervals.append((start, prev))
                start = t
            prev = t
        intervals.append((start, prev))
        
        speaker_intervals[speaker] = intervals
    
    return speaker_intervals, user_is_teacher

def analyze_student_sentiment(audio_file, json_file):
    
    
    # print("\n" + "="*60)
    # print(" STUDENT SENTIMENT ANALYSIS")
    # print("="*60)
    
    # Load audio
    print("\nLoading audio...")
    y, sr = librosa.load(audio_file, sr=16000, mono=True)
    
    # Get speaker timelines
    print("Loading Zoom data...")
    speaker_intervals, user_is_teacher = extract_speaker_timeline(json_file)
    
    # Separate teacher and students
    students = []
    teacher_name = None
    
    for speaker, is_teacher in user_is_teacher.items():
        if is_teacher:
            teacher_name = speaker
        else:
            if speaker in speaker_intervals:
                students.append(speaker)
    
    print(f"   Found {len(students)} students\n")
    
    # Analyze each student
    student_results = {}
    
    for student in students:
        print(f"🔍 Analyzing {student}...")
        
        intervals = speaker_intervals.get(student, [])
        if not intervals:
            student_results[student] = {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0}
            continue
        
        # Analyze each speaking segment
        sentiments = {'positive': 0, 'neutral': 0, 'negative': 0}
        total_duration = 0
        
        for start, end in intervals:
            start_sample = int(start * sr)
            end_sample = int(end * sr)
            
            if end_sample > start_sample:
                segment = y[start_sample:end_sample]
                if len(segment) > sr * 0.5:
                    duration = end - start
                    total_duration += duration
                    
                    sentiment = get_sentiment(segment, sr)
                    sentiments[sentiment] += duration
        
        # Calculate percentages
        total = sum(sentiments.values())
        if total > 0:
            pos_pct = (sentiments['positive'] / total) * 100
            neu_pct = (sentiments['neutral'] / total) * 100
            neg_pct = (sentiments['negative'] / total) * 100
        else:
            pos_pct = neu_pct = neg_pct = 0
        
        # Determine overall sentiment
        if sentiments['positive'] > sentiments['negative'] and sentiments['positive'] > sentiments['neutral']:
            overall = "POSITIVE"
        elif sentiments['negative'] > sentiments['positive'] and sentiments['negative'] > sentiments['neutral']:
            overall = "NEGATIVE"
        else:
            overall = "NEUTRAL"
        
        student_results[student] = {
            'duration': total_duration,
            'positive_pct': pos_pct,
            'neutral_pct': neu_pct,
            'negative_pct': neg_pct,
            'overall': overall
        }
    
    # SIMPLE OUTPUT
    print("\n" + "="*60)
    print(" RESULTS")
    print("="*60)
    
    # print("\n📊 INDIVIDUAL STUDENT SENTIMENT:")
    # print("-" * 60)
    
    for student in students:
        r = student_results.get(student, {})
        if r.get('duration', 0) > 0:
            # Emoji based on sentiment
            emoji = {'POSITIVE': '😊', 'NEUTRAL': '😐', 'NEGATIVE': '😠'}.get(r['overall'], '😐')
            
            print(f"\n{emoji} {student}")
            # print(f"   Time: {r['duration']:.0f} sec ({r['duration']/60:.1f} min)")
            print(f"   Sentiment: {r['overall']}")
            print(f"   😊 {r['positive_pct']:.0f}%  😐 {r['neutral_pct']:.0f}%  😠 {r['negative_pct']:.0f}%")
    
    # SUMMARY TABLE
    print("\n" + "="*60)
    print(" SUMMARY TABLE")
    print("="*60)
    print(f"\n{'Student':<25}  {'Sentiment':<12} {'😊':<6} {'😐':<6} {'😠':<6}")
    print("-" * 60)
    
    for student in students:
        r = student_results.get(student, {})
        if r.get('duration', 0) > 0:
            emoji = {'POSITIVE': '😊', 'NEUTRAL': '😐', 'NEGATIVE': '😠'}.get(r['overall'], '😐')
            print(f"{student[:24]:<25}  {emoji} {r['overall']:<6}   {r['positive_pct']:.0f}%    {r['neutral_pct']:.0f}%    {r['negative_pct']:.0f}%")
    
    print("\n" + "="*60)
    
    return student_results


# RUN ANALYSIS


if __name__ == "__main__":
    # Update these paths
    audio_file = "audio_file.wav"
    json_file = "NS26B_Math-Science Danish Sir_20260220_155725_timeline.json"
    
    # Run analysis
    results = analyze_student_sentiment(audio_file, json_file)