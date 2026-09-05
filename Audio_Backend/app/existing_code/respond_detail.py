import os
import json
import re
from collections import defaultdict
import ollama
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
MODEL_NAME = "richardyoung/llama-3.2-3b-instruct-abliterated:Q4_K_M"
JSON_FILE = "translated_conversation.json"
OUTPUT_FILE = "communication_quality_report.txt"
OUTPUT_JSON = "communication_quality_report.json"

# ==========================================
# LOAD AND PROCESS JSON DATA
# ==========================================

def load_transcript(json_file):
    """Load the transcript JSON file - handles translated format"""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict) and 'translations' in data:
            segments = []
            for item in data['translations']:
                english_text = item.get('english', '').strip()
                if not english_text or len(english_text) < 3:
                    continue
                if any(pattern in english_text.lower() for pattern in [
                    'note:', 'translation', 'however, without more context',
                    'if you could provide', 'none of these words appear'
                ]):
                    continue
                
                segments.append({
                    'speaker': item.get('speaker', 'Unknown'),
                    'text': english_text,
                    'hindi': item.get('hindi', ''),
                    'start': item.get('time_seconds', 0),
                    'end': item.get('time_seconds', 0) + 2,
                    'time': item.get('time', '00:00')
                })
            return segments
        elif isinstance(data, dict) and 'segments' in data:
            return data['segments']
        elif isinstance(data, list):
            return data
        else:
            print(f"⚠️ Unknown JSON format: {type(data)}")
            return []
            
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return []

def identify_teacher(segments, json_file):
    """Identify the teacher from data"""
    speakers = set()
    for seg in segments:
        if 'speaker' in seg:
            speakers.add(seg['speaker'])
    
    # Common teacher names
    common_teachers = ['Danish', 'Danish Hayat', 'Teacher', 'Sir', 'Madam', 'Mam', 'Hayat']
    for teacher in common_teachers:
        for speaker in speakers:
            if teacher.lower() in speaker.lower():
                return speaker
    
    # Fallback to most frequent speaker
    speaker_counts = defaultdict(int)
    for seg in segments:
        speaker = seg.get('speaker', '')
        if speaker:
            speaker_counts[speaker] += 1
    
    if speaker_counts:
        return max(speaker_counts, key=speaker_counts.get)
    
    return "Teacher"

def is_disturbance_text(text):
    """Check if text contains disturbance patterns"""
    disturbance_patterns = [
        'Hindi and English mixed', 'speech conversation',
        '[Music]', '[Applause]', '[Silence]',
        '...', '. . .',
        'speech recognition', 'transcription',
        'Note:', 'Translation:',
    ]
    
    text_lower = text.lower().strip()
    if len(text) < 3:
        return True
    
    for pattern in disturbance_patterns:
        if pattern.lower() in text_lower:
            return True
    return False

def clean_text(text):
    """Clean and normalize text"""
    text = re.sub(r'\(Note:.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(Translation.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def assess_response_quality(question, response):
    """Assess the quality of a response using LLM"""
    try:
        prompt = f"""
Evaluate the quality of this response to a classroom question.

Question: "{question}"
Response: "{response}"

Rate the response on these criteria (1-10):
1. Relevance - How well does it answer the question?
2. Completeness - Is the answer complete or partial?
3. Clarity - Is it clearly expressed?
4. Accuracy - Is the information correct?

Provide:
- Brief overall quality assessment (2-3 sentences)
- Ratings for each criterion
- Constructive feedback

Format:
OVERALL: [assessment]
RELEVANCE: [rating]/10
COMPLETENESS: [rating]/10
CLARITY: [rating]/10
ACCURACY: [rating]/10
FEEDBACK: [feedback]
"""
        
        response_llm = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': 'You are an educational communication expert. Provide constructive, fair assessments.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        return response_llm['message']['content']
        
    except Exception as e:
        print(f"⚠️ Error assessing response quality: {e}")
        return "QUALITY ASSESSMENT UNAVAILABLE"

def assess_question_quality(question):
    """Assess the quality of a question using LLM"""
    try:
        prompt = f"""
Evaluate the quality of this classroom question:
Question: "{question}"

Rate on these criteria (1-10):
1. Clarity - Is the question clearly worded?
2. Relevance - Is it relevant to the topic?
3. Engagement - Does it encourage thinking?
4. Specificity - Is it specific or too vague?

Format:
OVERALL: [assessment]
CLARITY: [rating]/10
RELEVANCE: [rating]/10
ENGAGEMENT: [rating]/10
SPECIFICITY: [rating]/10
FEEDBACK: [feedback]
"""
        
        response_llm = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': 'You are an educational communication expert. Provide constructive assessments.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        return response_llm['message']['content']
        
    except Exception as e:
        print(f"⚠️ Error assessing question quality: {e}")
        return "QUESTION ASSESSMENT UNAVAILABLE"

# ==========================================
# COMMUNICATION QUALITY ANALYSIS
# ==========================================

def analyze_communication_quality(segments, teacher_name):
    """Analyze communication quality including response time and quality"""
    
    # Filter and clean segments
    clean_segments = []
    for seg in segments:
        text = seg.get('text', '').strip()
        if not text or is_disturbance_text(text):
            continue
        
        clean_text_segment = clean_text(text)
        if len(clean_text_segment) < 3:
            continue
        
        clean_segments.append({
            'speaker': seg.get('speaker', 'Unknown'),
            'text': clean_text_segment,
            'start': seg.get('start', 0),
            'end': seg.get('end', 0),
            'is_teacher': seg.get('speaker', '') == teacher_name,
            'time': seg.get('time', '00:00'),
            'hindi': seg.get('hindi', '')
        })
    
    if not clean_segments:
        return None
    
    # Mark questions
    question_patterns = [
        r'[?？]',
        r'\b(?:what|why|how|when|where|who|which|is|are|was|were|do|does|did|has|have|will|shall|can|could|would|should|may|might|must)\b',
        r'\b(?:can you|could you|would you|will you|are you|do you|did you|have you|is it|are they)\b'
    ]
    
    for seg in clean_segments:
        text_lower = seg['text'].lower()
        is_question = False
        for pattern in question_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                is_question = True
                break
        seg['is_question'] = is_question
    
    # Analyze interactions with quality assessment
    interactions = {
        'teacher_initiated': {
            'total_questions': 0,
            'students': defaultdict(list),  # List of interactions
            'quality_assessments': []  # Full quality assessments
        },
        'student_initiated': {
            'total_questions': 0,
            'students': defaultdict(list),  # List of interactions
            'quality_assessments': []  # Full quality assessments
        },
        'all_interactions': [],
        'summary_stats': {
            'avg_response_time_teacher_to_student': 0,
            'avg_response_time_student_to_teacher': 0,
            'total_interactions': 0
        }
    }
    
    total_response_time_teacher = 0
    total_response_time_student = 0
    count_response_time_teacher = 0
    count_response_time_student = 0
    
    for i in range(len(clean_segments) - 1):
        current = clean_segments[i]
        next_seg = clean_segments[i + 1]
        
        speaker1 = current['speaker']
        speaker2 = next_seg['speaker']
        
        if speaker1 == speaker2:
            continue
        
        response_time = next_seg['start'] - current['end']
        
        # Teacher asked, Student responded
        if current['is_teacher'] and current['is_question']:
            interactions['teacher_initiated']['total_questions'] += 1
            
            if not speaker2 == teacher_name:
                response_time_seconds = response_time if response_time > 0 and response_time < 30 else None
                
                # Assess response quality
                quality_assessment = assess_response_quality(current['text'], next_seg['text'])
                
                interaction = {
                    'type': 'teacher_asked_student_responded',
                    'teacher_question': current['text'],
                    'student': speaker2,
                    'student_response': next_seg['text'],
                    'time': current['start'],
                    'timestamp': current.get('time', '00:00'),
                    'response_time': response_time_seconds,
                    'response_time_text': f"{response_time_seconds:.1f}s" if response_time_seconds else "N/A",
                    'quality_assessment': quality_assessment,
                    'hindi_question': current.get('hindi', ''),
                    'hindi_response': next_seg.get('hindi', '')
                }
                
                interactions['teacher_initiated']['students'][speaker2].append(interaction)
                interactions['all_interactions'].append(interaction)
                interactions['teacher_initiated']['quality_assessments'].append(quality_assessment)
                
                if response_time_seconds:
                    total_response_time_teacher += response_time_seconds
                    count_response_time_teacher += 1
        
        # Student asked, Teacher responded
        elif not current['is_teacher'] and current['is_question']:
            student_name = speaker1
            interactions['student_initiated']['total_questions'] += 1
            
            if speaker2 == teacher_name:
                response_time_seconds = response_time if response_time > 0 and response_time < 30 else None
                
                # Assess question quality
                question_quality = assess_question_quality(current['text'])
                # Assess response quality
                response_quality = assess_response_quality(current['text'], next_seg['text'])
                
                interaction = {
                    'type': 'student_asked_teacher_responded',
                    'student': student_name,
                    'student_question': current['text'],
                    'teacher_response': next_seg['text'],
                    'time': current['start'],
                    'timestamp': current.get('time', '00:00'),
                    'response_time': response_time_seconds,
                    'response_time_text': f"{response_time_seconds:.1f}s" if response_time_seconds else "N/A",
                    'question_quality': question_quality,
                    'response_quality': response_quality,
                    'hindi_question': current.get('hindi', ''),
                    'hindi_response': next_seg.get('hindi', '')
                }
                
                interactions['student_initiated']['students'][student_name].append(interaction)
                interactions['all_interactions'].append(interaction)
                interactions['student_initiated']['quality_assessments'].append(response_quality)
                
                if response_time_seconds:
                    total_response_time_student += response_time_seconds
                    count_response_time_student += 1
    
    # Calculate average response times
    if count_response_time_teacher > 0:
        interactions['summary_stats']['avg_response_time_teacher_to_student'] = total_response_time_teacher / count_response_time_teacher
    if count_response_time_student > 0:
        interactions['summary_stats']['avg_response_time_student_to_teacher'] = total_response_time_student / count_response_time_student
    
    interactions['summary_stats']['total_interactions'] = len(interactions['all_interactions'])
    
    return interactions

# ==========================================
# GENERATE COMMUNICATION QUALITY REPORT
# ==========================================

def generate_quality_report(interactions, teacher_name, json_file):
    """Generate a comprehensive communication quality report"""
    
    report_lines = []
    
    # Header
    report_lines.append("=" * 120)
    report_lines.append(" " * 35 + "COMMUNICATION QUALITY ANALYSIS REPORT")
    report_lines.append("=" * 120)
    report_lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f" Source File: {json_file}")
    report_lines.append(f" Teacher: {teacher_name}")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    if not interactions or not interactions['all_interactions']:
        report_lines.append(" No interactions found for analysis.")
        return report_lines
    
    # SECTION 1: SUMMARY STATISTICS
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 1: SUMMARY STATISTICS")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    total = interactions['summary_stats']['total_interactions']
    teacher_init = interactions['teacher_initiated']['total_questions']
    student_init = interactions['student_initiated']['total_questions']
    
    report_lines.append(f" Total Interactions Analyzed: {total}")
    report_lines.append(f" Teacher-Initiated Questions: {teacher_init} ({teacher_init/total*100:.1f}%)" if total > 0 else " Teacher-Initiated Questions: 0")
    report_lines.append(f" Student-Initiated Questions: {student_init} ({student_init/total*100:.1f}%)" if total > 0 else " Student-Initiated Questions: 0")
    report_lines.append("")
    
    if interactions['summary_stats']['avg_response_time_teacher_to_student'] > 0:
        report_lines.append(f" Average Response Time (Teacher → Student): {interactions['summary_stats']['avg_response_time_teacher_to_student']:.1f} seconds")
        if interactions['summary_stats']['avg_response_time_teacher_to_student'] < 3:
            report_lines.append("   ✅ Excellent response time (fast responses)")
        elif interactions['summary_stats']['avg_response_time_teacher_to_student'] < 7:
            report_lines.append("   ✅ Good response time")
        else:
            report_lines.append("   ⚠️ Slow response time (may indicate disengagement)")
    report_lines.append("")
    
    if interactions['summary_stats']['avg_response_time_student_to_teacher'] > 0:
        report_lines.append(f" Average Response Time (Student → Teacher): {interactions['summary_stats']['avg_response_time_student_to_teacher']:.1f} seconds")
        if interactions['summary_stats']['avg_response_time_student_to_teacher'] < 3:
            report_lines.append("   ✅ Excellent response time (teacher attentive)")
        elif interactions['summary_stats']['avg_response_time_student_to_teacher'] < 7:
            report_lines.append("   ✅ Good response time")
        else:
            report_lines.append("   ⚠️ Slow response time (may need to improve attentiveness)")
    report_lines.append("")
    
    # SECTION 2: TEACHER-INITIATED INTERACTIONS
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 2: TEACHER-INITIATED INTERACTIONS (Teacher Question → Student Response)")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    teacher_students = interactions['teacher_initiated']['students']
    if teacher_students:
        report_lines.append(f" Total Teacher Questions: {interactions['teacher_initiated']['total_questions']}")
        report_lines.append("")
        
        # Student-wise breakdown
        for student, interactions_list in sorted(teacher_students.items(), key=lambda x: len(x[1]), reverse=True):
            report_lines.append(f" 📌 Student: {student} ({len(interactions_list)} interactions)")
            report_lines.append("─" * 100)
            
            for idx, inter in enumerate(interactions_list[:5], 1):  # Show first 5 interactions
                report_lines.append(f"")
                report_lines.append(f"   [{idx}] Time: {inter['timestamp']}")
                report_lines.append(f"   🗣️ Teacher Question: {inter['teacher_question'][:100]}...")
                report_lines.append(f"   💬 Student Response: {inter['student_response'][:100]}...")
                report_lines.append(f"   ⏱️ Response Time: {inter['response_time_text']}")
                if inter.get('hindi_question'):
                    report_lines.append(f"   🗣️ Hindi: {inter['hindi_question'][:80]}...")
                report_lines.append(f"")
                report_lines.append(f"   📊 Quality Assessment:")
                if inter['quality_assessment']:
                    for line in inter['quality_assessment'].split('\n'):
                        if line.strip():
                            report_lines.append(f"      {line}")
                report_lines.append("")
            
            if len(interactions_list) > 5:
                report_lines.append(f"   ... and {len(interactions_list) - 5} more interactions")
            report_lines.append("")
    else:
        report_lines.append(" No teacher-initiated interactions found.")
        report_lines.append("")
    
    # SECTION 3: STUDENT-INITIATED INTERACTIONS
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 3: STUDENT-INITIATED INTERACTIONS (Student Question → Teacher Response)")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    student_teachers = interactions['student_initiated']['students']
    if student_teachers:
        report_lines.append(f" Total Student Questions: {interactions['student_initiated']['total_questions']}")
        report_lines.append("")
        
        for student, interactions_list in sorted(student_teachers.items(), key=lambda x: len(x[1]), reverse=True):
            report_lines.append(f" 📌 Student: {student} ({len(interactions_list)} interactions)")
            report_lines.append("─" * 100)
            
            for idx, inter in enumerate(interactions_list[:5], 1):
                report_lines.append(f"")
                report_lines.append(f"   [{idx}] Time: {inter['timestamp']}")
                report_lines.append(f"   💡 Student Question: {inter['student_question'][:100]}...")
                report_lines.append(f"   🗣️ Teacher Response: {inter['teacher_response'][:100]}...")
                report_lines.append(f"   ⏱️ Response Time: {inter['response_time_text']}")
                if inter.get('hindi_question'):
                    report_lines.append(f"   🗣️ Hindi: {inter['hindi_question'][:80]}...")
                report_lines.append(f"")
                report_lines.append(f"   📊 Question Quality Assessment:")
                if inter.get('question_quality'):
                    for line in inter['question_quality'].split('\n'):
                        if line.strip():
                            report_lines.append(f"      {line}")
                report_lines.append(f"")
                report_lines.append(f"   📊 Response Quality Assessment:")
                if inter.get('response_quality'):
                    for line in inter['response_quality'].split('\n'):
                        if line.strip():
                            report_lines.append(f"      {line}")
                report_lines.append("")
            
            if len(interactions_list) > 5:
                report_lines.append(f"   ... and {len(interactions_list) - 5} more interactions")
            report_lines.append("")
    else:
        report_lines.append(" No student-initiated interactions found.")
        report_lines.append("")
    
    # SECTION 4: QUALITY RATING SUMMARY
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 4: QUALITY RATING SUMMARY")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    # Extract ratings from quality assessments (simplified extraction)
    def extract_ratings(text, prefix):
        ratings = []
        for line in text.split('\n'):
            if line.strip().startswith(prefix):
                try:
                    rating = int(re.search(r'(\d+)/10', line).group(1))
                    ratings.append(rating)
                except:
                    pass
        return ratings
    
    teacher_ratings = {
        'relevance': [],
        'completeness': [],
        'clarity': [],
        'accuracy': []
    }
    
    student_ratings = {
        'clarity': [],
        'relevance': [],
        'engagement': [],
        'specificity': []
    }
    
    # Parse teacher-initiated responses
    for inter in interactions['all_interactions']:
        if inter['type'] == 'teacher_asked_student_responded' and inter.get('quality_assessment'):
            text = inter['quality_assessment']
            teacher_ratings['relevance'].extend(extract_ratings(text, 'RELEVANCE:'))
            teacher_ratings['completeness'].extend(extract_ratings(text, 'COMPLETENESS:'))
            teacher_ratings['clarity'].extend(extract_ratings(text, 'CLARITY:'))
            teacher_ratings['accuracy'].extend(extract_ratings(text, 'ACCURACY:'))
    
    # Parse student-initiated questions
    for inter in interactions['all_interactions']:
        if inter['type'] == 'student_asked_teacher_responded' and inter.get('question_quality'):
            text = inter['question_quality']
            student_ratings['clarity'].extend(extract_ratings(text, 'CLARITY:'))
            student_ratings['relevance'].extend(extract_ratings(text, 'RELEVANCE:'))
            student_ratings['engagement'].extend(extract_ratings(text, 'ENGAGEMENT:'))
            student_ratings['specificity'].extend(extract_ratings(text, 'SPECIFICITY:'))
    
    # Calculate averages
    def avg_rating(ratings):
        return sum(ratings) / len(ratings) if ratings else 0
    
    report_lines.append(" 📊 TEACHER QUESTION → STUDENT RESPONSE QUALITY:")
    report_lines.append(" ─" * 80)
    report_lines.append(f"   Relevance: {avg_rating(teacher_ratings['relevance']):.1f}/10 ({len(teacher_ratings['relevance'])} ratings)")
    report_lines.append(f"   Completeness: {avg_rating(teacher_ratings['completeness']):.1f}/10 ({len(teacher_ratings['completeness'])} ratings)")
    report_lines.append(f"   Clarity: {avg_rating(teacher_ratings['clarity']):.1f}/10 ({len(teacher_ratings['clarity'])} ratings)")
    report_lines.append(f"   Accuracy: {avg_rating(teacher_ratings['accuracy']):.1f}/10 ({len(teacher_ratings['accuracy'])} ratings)")
    report_lines.append("")
    
    report_lines.append(" 📊 STUDENT QUESTION → TEACHER RESPONSE QUALITY:")
    report_lines.append(" ─" * 80)
    report_lines.append(f"   Question Clarity: {avg_rating(student_ratings['clarity']):.1f}/10 ({len(student_ratings['clarity'])} ratings)")
    report_lines.append(f"   Question Relevance: {avg_rating(student_ratings['relevance']):.1f}/10 ({len(student_ratings['relevance'])} ratings)")
    report_lines.append(f"   Engagement: {avg_rating(student_ratings['engagement']):.1f}/10 ({len(student_ratings['engagement'])} ratings)")
    report_lines.append(f"   Specificity: {avg_rating(student_ratings['specificity']):.1f}/10 ({len(student_ratings['specificity'])} ratings)")
    report_lines.append("")
    
    # SECTION 5: RECOMMENDATIONS
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 5: RECOMMENDATIONS")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    recommendations = generate_quality_recommendations(interactions, teacher_name)
    for rec in recommendations:
        report_lines.append(f" • {rec}")
        report_lines.append("")
    
    report_lines.append("=" * 120)
    report_lines.append(" " * 40 + "END OF REPORT")
    report_lines.append("=" * 120)
    
    return report_lines

def generate_quality_recommendations(interactions, teacher_name):
    """Generate recommendations based on communication quality analysis"""
    
    recommendations = []
    
    # Check response times
    if interactions['summary_stats']['avg_response_time_teacher_to_student'] > 7:
        recommendations.append(
            f"Student response time ({interactions['summary_stats']['avg_response_time_teacher_to_student']:.1f}s) is slow. "
            f"Consider giving students more think time or using engaging activities to improve responsiveness."
        )
    
    if interactions['summary_stats']['avg_response_time_student_to_teacher'] > 7:
        recommendations.append(
            f"Teacher response time ({interactions['summary_stats']['avg_response_time_student_to_teacher']:.1f}s) is slow. "
            f"Teacher '{teacher_name}' should improve attentiveness to student questions."
        )
    
    # Check interaction balance
    teacher_init = interactions['teacher_initiated']['total_questions']
    student_init = interactions['student_initiated']['total_questions']
    total = interactions['summary_stats']['total_interactions']
    
    if total > 0 and student_init / total < 0.2:
        recommendations.append(
            f"Low student initiative ({student_init}/{total} questions). "
            f"Encourage students to ask more questions to increase engagement."
        )
    
    if total > 0 and teacher_init / total > 0.8:
        recommendations.append(
            f"Teacher dominates the conversation ({teacher_init}/{total} questions). "
            f"Consider more student-centered discussion techniques."
        )
    
    # Check individual students with low engagement
    for student, interactions_list in interactions['teacher_initiated']['students'].items():
        if len(interactions_list) > 3:
            # Check if responses are quick or slow
            slow_responses = [i for i in interactions_list if i.get('response_time', 0) and i['response_time'] > 7]
            if len(slow_responses) / len(interactions_list) > 0.5:
                recommendations.append(
                    f"Student '{student}' has slow responses to teacher questions. "
                    f"Consider checking if they're understanding the material."
                )
    
    if not recommendations:
        recommendations.append(
            "Communication quality appears excellent. Continue maintaining "
            "good engagement and responsiveness in the classroom."
        )
    
    return recommendations[:5]

# ==========================================
# SAVE JSON OUTPUT
# ==========================================

def save_quality_json(interactions, teacher_name, json_file):
    """Save communication quality data to JSON"""
    
    json_output = {
        "metadata": {
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_file": json_file,
            "teacher": teacher_name
        },
        "summary": {
            "total_interactions": interactions['summary_stats']['total_interactions'],
            "teacher_initiated": interactions['teacher_initiated']['total_questions'],
            "student_initiated": interactions['student_initiated']['total_questions'],
            "avg_response_time_teacher_to_student": round(interactions['summary_stats']['avg_response_time_teacher_to_student'], 1) if interactions['summary_stats']['avg_response_time_teacher_to_student'] > 0 else 0,
            "avg_response_time_student_to_teacher": round(interactions['summary_stats']['avg_response_time_student_to_teacher'], 1) if interactions['summary_stats']['avg_response_time_student_to_teacher'] > 0 else 0
        },
        "interactions": {
            "teacher_initiated": [
                {
                    "timestamp": inter['timestamp'],
                    "teacher_question": inter['teacher_question'],
                    "student": inter['student'],
                    "student_response": inter['student_response'],
                    "response_time": round(inter['response_time'], 1) if inter.get('response_time') else 0,
                    "quality_assessment": inter.get('quality_assessment', '')
                }
                for inter in interactions['all_interactions'] 
                if inter['type'] == 'teacher_asked_student_responded'
            ],
            "student_initiated": [
                {
                    "timestamp": inter['timestamp'],
                    "student": inter['student'],
                    "student_question": inter['student_question'],
                    "teacher_response": inter['teacher_response'],
                    "response_time": round(inter['response_time'], 1) if inter.get('response_time') else 0,
                    "question_quality": inter.get('question_quality', ''),
                    "response_quality": inter.get('response_quality', '')
                }
                for inter in interactions['all_interactions'] 
                if inter['type'] == 'student_asked_teacher_responded'
            ]
        }
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    print(f"💾 JSON saved to: {OUTPUT_JSON}")

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    print("\n" + "=" * 120)
    print(" " * 35 + "COMMUNICATION QUALITY ANALYZER")
    print("=" * 120)
    
    try:
        ollama.list()
        print("✅ Ollama is running")
    except Exception as e:
        print(f"❌ Ollama not running: {e}")
        return
    
    print(f"\n📂 Loading transcript: {JSON_FILE}")
    segments = load_transcript(JSON_FILE)
    
    if not segments:
        print("❌ No data found")
        return
    
    print(f"   ✓ Loaded {len(segments)} segments")
    
    print(f"\n🔍 Identifying teacher...")
    teacher_name = identify_teacher(segments, JSON_FILE)
    print(f"   ✓ Teacher identified: {teacher_name}")
    
    print(f"\n📊 Analyzing communication quality...")
    print("   🤖 Assessing response quality with LLM (this may take a few moments)...")
    interactions = analyze_communication_quality(segments, teacher_name)
    
    if not interactions or not interactions['all_interactions']:
        print("❌ No interactions found")
        return
    
    print(f"   ✓ Total interactions: {interactions['summary_stats']['total_interactions']}")
    print(f"   ✓ Teacher questions: {interactions['teacher_initiated']['total_questions']}")
    print(f"   ✓ Student questions: {interactions['student_initiated']['total_questions']}")
    if interactions['summary_stats']['avg_response_time_teacher_to_student'] > 0:
        print(f"   ✓ Avg response (T→S): {interactions['summary_stats']['avg_response_time_teacher_to_student']:.1f}s")
    if interactions['summary_stats']['avg_response_time_student_to_teacher'] > 0:
        print(f"   ✓ Avg response (S→T): {interactions['summary_stats']['avg_response_time_student_to_teacher']:.1f}s")
    
    print(f"\n📝 Generating quality report...")
    report_lines = generate_quality_report(interactions, teacher_name, JSON_FILE)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in report_lines:
            f.write(line + "\n")
    
    print(f"💾 TXT report saved to: {OUTPUT_FILE}")
    
    print(f"\n💾 Saving JSON output...")
    save_quality_json(interactions, teacher_name, JSON_FILE)
    
    print("\n" + "=" * 120)
    print(" " * 35 + "ANALYSIS COMPLETE")
    print("=" * 120)

if __name__ == "__main__":
    main()