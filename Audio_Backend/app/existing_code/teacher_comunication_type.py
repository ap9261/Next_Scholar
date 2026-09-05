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
    
    # Energy/Volume
    energy = np.mean(librosa.feature.rms(y=segment))
    
    # Pitch
    pitches, magnitudes = librosa.piptrack(y=segment, sr=sr)
    valid_pitches = pitches[magnitudes > np.median(magnitudes)]
    pitch = np.mean(valid_pitches) if len(valid_pitches) > 0 else 0
    
    # Speech rate
    zcr = np.mean(librosa.feature.zero_crossing_rate(segment))
    speech_rate = zcr * sr * 5
    
    # Classification
    if energy > 0.025 and pitch > 160 and speech_rate > 3.5:
        return "positive"
    elif energy < 0.012 and pitch < 130 and speech_rate < 2.8:
        return "negative"
    else:
        return "neutral"

def analyze_entire_class(audio_file, json_file=None):
    """Analyze sentiment of the entire class"""
    
    print("\n" + "="*70)
    print(" 📊 COMPLETE CLASS SENTIMENT ANALYSIS")
    print("="*70)
    
    # Load audio
    print("\n🎵 Loading audio file...")
    y, sr = librosa.load(audio_file, sr=16000, mono=True)
    total_duration = len(y) / sr
    print(f"   Duration: {total_duration:.0f} seconds ({total_duration/60:.1f} minutes)")
    
    # Split into segments (every 3 seconds)
    segment_duration = 3.0
    hop_duration = 1.0
    segment_samples = int(segment_duration * sr)
    hop_samples = int(hop_duration * sr)
    
    segments = []
    timestamps = []
    
    for start in range(0, len(y) - segment_samples + 1, hop_samples):
        segment = y[start:start + segment_samples]
        if np.max(np.abs(segment)) > 0.01:
            segments.append(segment)
            timestamps.append(start / sr)
    
    print(f"   Analyzing {len(segments)} segments...")
    
    # Analyze each segment
    sentiments = {'positive': 0, 'neutral': 0, 'negative': 0}
    segment_results = []
    
    for segment, timestamp in zip(segments, timestamps):
        sentiment = get_sentiment(segment, sr)
        sentiments[sentiment] += 1
        segment_results.append({
            'time': timestamp,
            'sentiment': sentiment
        })
    
    # Calculate percentages
    total_segments = len(segments)
    pos_pct = (sentiments['positive'] / total_segments) * 100
    neu_pct = (sentiments['neutral'] / total_segments) * 100
    neg_pct = (sentiments['negative'] / total_segments) * 100
    
    # Determine overall class sentiment
    if sentiments['positive'] > sentiments['negative'] and sentiments['positive'] > sentiments['neutral']:
        overall = "POSITIVE"
        emoji = "😊"
    elif sentiments['negative'] > sentiments['positive'] and sentiments['negative'] > sentiments['neutral']:
        overall = "NEGATIVE"
        emoji = "😠"
    else:
        overall = "NEUTRAL"
        emoji = "😐"
    
    # Find key moments
    positive_segments = [r for r in segment_results if r['sentiment'] == 'positive']
    negative_segments = [r for r in segment_results if r['sentiment'] == 'negative']
    
    # Calculate minute-by-minute sentiment
    minute_sentiments = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0, 'total': 0})
    
    for result in segment_results:
        minute = int(result['time'] / 60)
        minute_sentiments[minute][result['sentiment']] += 1
        minute_sentiments[minute]['total'] += 1
    
    
    print("\n" + "="*70)
    print(" 📈 OVERALL CLASS STATISTICS")
    print("="*70)
    
    print(f"\n⏱️  Total Class Duration: {total_duration:.0f} seconds ({total_duration/60:.1f} minutes)")
    print(f"🎤 Audio Segments Analyzed: {total_segments}")
    
    print("\n" + "="*70)
    print(f"🎭 SENTIMENT BREAKDOWN:")
    print("="*70)

    print(f"   😊 POSITIVE : {sentiments['positive']:4} segments ({pos_pct:5.1f}%)")
    print(f"   😐 NEUTRAL  : {sentiments['neutral']:4} segments ({neu_pct:5.1f}%)")
    print(f"   😠 NEGATIVE : {sentiments['negative']:4} segments ({neg_pct:5.1f}%)")
    
    # Calculate metrics
    engagement_score = pos_pct
    negativity_score = neg_pct
    
    print("\n" + "="*70)
    # print(f"\n🎭 SENTIMENT BREAKDOWN:")
    print(f"📊 CLASS METRICS:")
    print("="*70)
    print(f"   Engagement Score: {engagement_score:.1f}% (percentage of positive speech)")
    print(f"   Negativity Score: {negativity_score:.1f}% (percentage of negative speech)")
    # print(f"   Positivity Ratio: {pos_pct/neg_pct:.1f}x" if neg_pct > 0 else "   Positivity Ratio: ∞")
    
    
    if positive_segments:
        print(f"\n😊 MOST POSITIVE MOMENT:")
        print(f"   Time: {positive_segments[0]['time']:.0f}s")
        print(f"   The class was most energetic and engaged at this point")
    
    if negative_segments:
        print(f"\n😠 MOST NEGATIVE MOMENT:")
        print(f"   Time: {negative_segments[0]['time']:.0f}s")
        print(f"   The class showed lower energy or frustration at this point")
    
   
    
    
    
    return {
        'sentiments': sentiments,
        'percentages': {'positive': pos_pct, 'neutral': neu_pct, 'negative': neg_pct},
        'overall': overall,
        'engagement_score': engagement_score,
        'negativity_score': negativity_score,
        # 'grade': grade
    }

# ==========================================
# RUN ANALYSIS
# ==========================================

if __name__ == "__main__":
    # Update these paths
    audio_file = "audio_file.wav"
    json_file = "NS26B_Math-Science Danish Sir_20260220_155725_timeline.json"
    
    # Analyze entire class
    results = analyze_entire_class(audio_file, json_file)