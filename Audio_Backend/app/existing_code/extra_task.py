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
OUTPUT_FILE = "student_performance_analysis_report.txt"
OUTPUT_JSON = "student_performance_analysis_report.json"

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
    
    common_teachers = ['Danish', 'Danish Hayat', 'Teacher', 'Sir', 'Madam', 'Mam', 'Hayat']
    for teacher in common_teachers:
        for speaker in speakers:
            if teacher.lower() in speaker.lower():
                return speaker
    
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

# ==========================================
# STUDENT CLASSIFICATION FUNCTIONS
# ==========================================

def classify_student_type(student_data):
    """Classify student as Sharp or Poor based on performance metrics"""
    
    if not student_data:
        return {
            'type': 'Unknown',
            'score': 0,
            'reason': 'No data available'
        }
    
    # Extract metrics
    total_answers = len(student_data.get('answers', []))
    correct_answers = len(student_data.get('correct_answers', []))
    incorrect_answers = len(student_data.get('incorrect_answers', []))
    questions_asked = len(student_data.get('questions_asked', []))
    quality_responses = len(student_data.get('quality_responses', []))
    
    # Calculate metrics
    if total_answers > 0:
        accuracy = correct_answers / total_answers
    else:
        accuracy = 0
    
    if total_answers > 0:
        quality_ratio = quality_responses / total_answers
    else:
        quality_ratio = 0
    
    # Calculate overall score (0-100)
    score = 0
    if total_answers > 0:
        score += accuracy * 40  # Accuracy weight: 40%
        score += quality_ratio * 30  # Quality weight: 30%
        score += min(questions_asked * 3, 30)  # Initiative weight: 30%
    
    # Determine type
    if score >= 70:
        student_type = "Sharp (High Performing)"
    elif score >= 50:
        student_type = "Average (Moderate Performing)"
    elif score >= 30:
        student_type = "Struggling (Poor Performing)"
    else:
        student_type = "Critical (Very Poor Performing)"
    
    return {
        'type': student_type,
        'score': round(score, 1),
        'accuracy': round(accuracy * 100, 1),
        'quality_ratio': round(quality_ratio * 100, 1),
        'total_answers': total_answers,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,
        'questions_asked': questions_asked,
        'reason': f"Accuracy: {accuracy*100:.1f}%, Quality: {quality_ratio*100:.1f}%, Initiative: {questions_asked} questions"
    }

def classify_communication_type(text):
    """Classify communication as Useful or Distraction using LLM"""
    try:
        prompt = f"""
Classify this classroom communication as either "Useful" or "Distraction":

Text: "{text}"

Useful communication:
- Directly related to the topic
- Asks or answers relevant questions
- Contributes to learning
- Provides clarification

Distraction:
- Off-topic or irrelevant
- Disrupts the flow of learning
- Non-educational chatter
- Technical issues or complaints

Provide:
1. Classification: [Useful/Distraction]
2. Confidence: [High/Medium/Low]
3. Brief reason (1 sentence)

Format:
CLASSIFICATION: [Useful/Distraction]
CONFIDENCE: [High/Medium/Low]
REASON: [brief reason]
"""
        
        response_llm = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': 'You are a classroom observer. Classify communication accurately.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        result = response_llm['message']['content']
        
        # Parse the result
        classification = "Distraction"  # Default
        confidence = "Medium"
        reason = "Could not classify"
        
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('CLASSIFICATION:'):
                classification = line.split('CLASSIFICATION:')[1].strip()
            elif line.startswith('CONFIDENCE:'):
                confidence = line.split('CONFIDENCE:')[1].strip()
            elif line.startswith('REASON:'):
                reason = line.split('REASON:')[1].strip()
        
        return {
            'classification': classification,
            'confidence': confidence,
            'reason': reason
        }
        
    except Exception as e:
        print(f"⚠️ Error classifying communication: {e}")
        return {
            'classification': 'Distraction',
            'confidence': 'Low',
            'reason': 'Error in classification'
        }

def evaluate_answer_quality(question, answer):
    """Evaluate if an answer is correct/incorrect and its quality"""
    try:
        prompt = f"""
Evaluate this classroom interaction:

Question: "{question}"
Student Answer: "{answer}"

Determine:
1. Is the answer correct? (Yes/No/Partially)
2. Quality of answer (1-10)
3. Brief feedback (1 sentence)

Format:
CORRECT: [Yes/No/Partially]
QUALITY: [rating]/10
FEEDBACK: [brief feedback]
"""
        
        response_llm = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': 'You are an educational evaluator. Provide fair assessments.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        result = response_llm['message']['content']
        
        correct = "No"
        quality = 5
        feedback = "Could not evaluate"
        
        for line in result.split('\n'):
            line = line.strip()
            if line.startswith('CORRECT:'):
                correct = line.split('CORRECT:')[1].strip()
            elif line.startswith('QUALITY:'):
                try:
                    quality = int(re.search(r'(\d+)/10', line).group(1))
                except:
                    pass
            elif line.startswith('FEEDBACK:'):
                feedback = line.split('FEEDBACK:')[1].strip()
        
        return {
            'correct': correct,
            'quality': quality,
            'feedback': feedback
        }
        
    except Exception as e:
        print(f"⚠️ Error evaluating answer: {e}")
        return {
            'correct': 'No',
            'quality': 5,
            'feedback': 'Error in evaluation'
        }

# ==========================================
# STUDENT PERFORMANCE ANALYSIS
# ==========================================

def analyze_student_performance(segments, teacher_name):
    """Analyze student performance and classify students"""
    
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
    
    # Track student data
    student_data = defaultdict(lambda: {
        'answers': [],
        'correct_answers': [],
        'incorrect_answers': [],
        'questions_asked': [],
        'quality_responses': [],
        'distractions': [],
        'useful_communications': [],
        'communication_types': [],
        'interactions': []
    })
    
    teacher_data = {
        'useful_communications': [],
        'distractions': [],
        'total_messages': 0
    }
    
    # Track all communications
    all_communications = []
    
    # Analyze interactions
    for i in range(len(clean_segments) - 1):
        current = clean_segments[i]
        next_seg = clean_segments[i + 1]
        
        speaker1 = current['speaker']
        speaker2 = next_seg['speaker']
        
        if speaker1 == speaker2:
            continue
        
        # Classify communication type for current message
        comm_type = classify_communication_type(current['text'])
        all_communications.append({
            'speaker': speaker1,
            'text': current['text'],
            'time': current['time'],
            'classification': comm_type['classification'],
            'confidence': comm_type['confidence'],
            'reason': comm_type['reason']
        })
        
        if current['is_teacher']:
            teacher_data['total_messages'] += 1
            if comm_type['classification'] == 'Useful':
                teacher_data['useful_communications'].append(current['text'])
            else:
                teacher_data['distractions'].append(current['text'])
        
        # Student data
        if not current['is_teacher']:
            student = speaker1
            
            # Track communication type
            student_data[student]['communication_types'].append(comm_type)
            if comm_type['classification'] == 'Useful':
                student_data[student]['useful_communications'].append(current['text'])
            else:
                student_data[student]['distractions'].append(current['text'])
            
            # Teacher asked, Student responded
            if current['is_teacher'] and current['is_question']:
                if not speaker2 == teacher_name:
                    # Evaluate the answer
                    eval_result = evaluate_answer_quality(current['text'], next_seg['text'])
                    
                    student_data[student]['answers'].append({
                        'question': current['text'],
                        'answer': next_seg['text'],
                        'evaluation': eval_result
                    })
                    
                    if eval_result['correct'] in ['Yes', 'Partially']:
                        student_data[student]['correct_answers'].append({
                            'question': current['text'],
                            'answer': next_seg['text'],
                            'eval': eval_result
                        })
                    else:
                        student_data[student]['incorrect_answers'].append({
                            'question': current['text'],
                            'answer': next_seg['text'],
                            'eval': eval_result
                        })
                    
                    if eval_result['quality'] >= 7:
                        student_data[student]['quality_responses'].append({
                            'question': current['text'],
                            'answer': next_seg['text'],
                            'eval': eval_result
                        })
            
            # Student asked
            elif not current['is_teacher'] and current['is_question']:
                student_data[student]['questions_asked'].append({
                    'question': current['text'],
                    'time': current['time']
                })
    
    # Calculate student classifications
    student_classifications = {}
    for student, data in student_data.items():
        classification = classify_student_type(data)
        student_classifications[student] = {
            'classification': classification,
            'data': data
        }
    
    # Calculate teacher statistics
    teacher_total = teacher_data['total_messages']
    teacher_useful = len(teacher_data['useful_communications'])
    teacher_distractions = len(teacher_data['distractions'])
    
    # Count distractions and useful communications overall
    total_useful = sum(1 for c in all_communications if c['classification'] == 'Useful')
    total_distractions = sum(1 for c in all_communications if c['classification'] == 'Distraction')
    
    return {
        'student_classifications': student_classifications,
        'teacher_data': teacher_data,
        'all_communications': all_communications,
        'summary': {
            'total_messages': len(all_communications),
            'useful_messages': total_useful,
            'distraction_messages': total_distractions,
            'useful_percentage': (total_useful / len(all_communications) * 100) if all_communications else 0,
            'distraction_percentage': (total_distractions / len(all_communications) * 100) if all_communications else 0,
            'teacher_useful_percentage': (teacher_useful / teacher_total * 100) if teacher_total > 0 else 0,
            'teacher_distraction_percentage': (teacher_distractions / teacher_total * 100) if teacher_total > 0 else 0
        }
    }

# ==========================================
# GENERATE PERFORMANCE REPORT
# ==========================================

def generate_performance_report(analysis_data, teacher_name, json_file):
    """Generate a comprehensive student performance and communication analysis report"""
    
    report_lines = []
    
    # Header
    report_lines.append("=" * 120)
    report_lines.append(" " * 35 + "STUDENT PERFORMANCE & COMMUNICATION ANALYSIS REPORT")
    report_lines.append("=" * 120)
    report_lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f" Source File: {json_file}")
    report_lines.append(f" Teacher: {teacher_name}")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    if not analysis_data:
        report_lines.append(" No analysis data found.")
        return report_lines
    
    # SECTION 1: OVERALL COMMUNICATION SUMMARY
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 1: OVERALL COMMUNICATION SUMMARY")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    summary = analysis_data['summary']
    report_lines.append(f" Total Messages Analyzed: {summary['total_messages']}")
    report_lines.append(f" Useful Communications: {summary['useful_messages']} ({summary['useful_percentage']:.1f}%)")
    report_lines.append(f" Distractions: {summary['distraction_messages']} ({summary['distraction_percentage']:.1f}%)")
    report_lines.append("")
    
    report_lines.append(f" Teacher's Communication:")
    report_lines.append(f"   Useful: {summary['teacher_useful_percentage']:.1f}%")
    report_lines.append(f"   Distractions: {summary['teacher_distraction_percentage']:.1f}%")
    report_lines.append("")
    
    # SECTION 2: STUDENT CLASSIFICATION
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 2: STUDENT CLASSIFICATION")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    report_lines.append("┌─────────────────────┬──────────────────────┬──────────┬──────────┬──────────┬──────────────┐")
    report_lines.append("│ STUDENT             │ TYPE                 │ SCORE    │ ACCURACY │ QUALITY  │ QUESTIONS    │")
    report_lines.append("├─────────────────────┼──────────────────────┼──────────┼──────────┼──────────┼──────────────┤")
    
    sorted_students = sorted(
        analysis_data['student_classifications'].items(),
        key=lambda x: x[1]['classification']['score'],
        reverse=True
    )
    
    for student, data in sorted_students:
        cls = data['classification']
        display_name = student[:20] + "..." if len(student) > 20 else student
        type_display = cls['type'][:20] + "..." if len(cls['type']) > 20 else cls['type']
        report_lines.append(
            f"│ {display_name:<19} │ {type_display:<20} │ {cls['score']:>6}   │ {cls['accuracy']:>6}%  │ {cls['quality_ratio']:>6}%  │ {cls['questions_asked']:>8}   │"
        )
    
    report_lines.append("└─────────────────────┴──────────────────────┴──────────┴──────────┴──────────┴──────────────┘")
    report_lines.append("")
    
    report_lines.append(" LEGEND:")
    report_lines.append("   SCORE: Overall performance score (0-100)")
    report_lines.append("   ACCURACY: Percentage of correct answers")
    report_lines.append("   QUALITY: Percentage of high-quality responses (≥7/10)")
    report_lines.append("   QUESTIONS: Number of questions asked by student")
    report_lines.append("")
    
    # SECTION 3: DETAILED STUDENT ANALYSIS
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 3: DETAILED STUDENT ANALYSIS")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    for student, data in sorted_students:
        cls = data['classification']
        student_data = data['data']
        
        report_lines.append("─" * 120)
        report_lines.append(f" 📌 STUDENT: {student}")
        report_lines.append("─" * 120)
        report_lines.append("")
        
        report_lines.append(f" 🏷️ Classification: {cls['type']}")
        report_lines.append(f" 📊 Score: {cls['score']:.1f}/100")
        report_lines.append(f" 🎯 Accuracy: {cls['accuracy']:.1f}%")
        report_lines.append(f" 💡 Quality Responses: {cls['quality_ratio']:.1f}%")
        report_lines.append(f" ❓ Questions Asked: {cls['questions_asked']}")
        report_lines.append(f" 📝 Reason: {cls['reason']}")
        report_lines.append("")
        
        # Communication Type Breakdown
        comm_types = student_data['communication_types']
        if comm_types:
            useful_count = sum(1 for c in comm_types if c['classification'] == 'Useful')
            distraction_count = sum(1 for c in comm_types if c['classification'] == 'Distraction')
            
            report_lines.append(" 📊 COMMUNICATION BREAKDOWN:")
            report_lines.append(f"    Useful Communications: {useful_count}")
            report_lines.append(f"    Distractions: {distraction_count}")
            report_lines.append("")
        
        # Sample Correct Answers
        if student_data['correct_answers']:
            report_lines.append(" ✅ CORRECT RESPONSE EXAMPLES:")
            for i, ans in enumerate(student_data['correct_answers'][:3], 1):
                report_lines.append(f"    [{i}] Q: {ans['question'][:80]}...")
                report_lines.append(f"        A: {ans['answer'][:80]}...")
                report_lines.append(f"        Quality: {ans['eval']['quality']}/10")
                report_lines.append(f"        Feedback: {ans['eval']['feedback']}")
                report_lines.append("")
        
        # Sample Incorrect Answers
        if student_data['incorrect_answers']:
            report_lines.append(" ❌ INCORRECT RESPONSE EXAMPLES:")
            for i, ans in enumerate(student_data['incorrect_answers'][:3], 1):
                report_lines.append(f"    [{i}] Q: {ans['question'][:80]}...")
                report_lines.append(f"        A: {ans['answer'][:80]}...")
                report_lines.append(f"        Quality: {ans['eval']['quality']}/10")
                report_lines.append(f"        Feedback: {ans['eval']['feedback']}")
                report_lines.append("")
        
        # Sample Distractions
        if student_data['distractions']:
            report_lines.append(" ⚠️ DISTRACTION EXAMPLES:")
            for i, text in enumerate(student_data['distractions'][:3], 1):
                report_lines.append(f"    [{i}] \"{text[:80]}...\"")
                report_lines.append("")
        
        # Sample Useful Communications
        if student_data['useful_communications']:
            report_lines.append(" 💡 USEFUL COMMUNICATION EXAMPLES:")
            for i, text in enumerate(student_data['useful_communications'][:3], 1):
                report_lines.append(f"    [{i}] \"{text[:80]}...\"")
                report_lines.append("")
    
    # SECTION 4: RECOMMENDATIONS
    report_lines.append("=" * 120)
    report_lines.append(" SECTION 4: RECOMMENDATIONS")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    recommendations = generate_performance_recommendations(analysis_data)
    for rec in recommendations:
        report_lines.append(f" • {rec}")
        report_lines.append("")
    
    report_lines.append("=" * 120)
    report_lines.append(" " * 40 + "END OF REPORT")
    report_lines.append("=" * 120)
    
    return report_lines

def generate_performance_recommendations(analysis_data):
    """Generate recommendations based on student performance analysis"""
    
    recommendations = []
    
    # Student-based recommendations
    for student, data in analysis_data['student_classifications'].items():
        cls = data['classification']
        
        if cls['type'].startswith('Sharp'):
            recommendations.append(
                f"Student '{student}' is performing excellently ({cls['score']:.1f}%). "
                f"Consider providing advanced material or leadership opportunities."
            )
        elif cls['type'].startswith('Critical'):
            recommendations.append(
                f"Student '{student}' needs immediate support ({cls['score']:.1f}%). "
                f"Provide personalized attention and remedial material."
            )
        elif cls['type'].startswith('Struggling'):
            recommendations.append(
                f"Student '{student}' needs support ({cls['score']:.1f}%). "
                f"Consider additional practice and simpler explanations."
            )
    
    # Communication-based recommendations
    summary = analysis_data['summary']
    if summary['distraction_percentage'] > 30:
        recommendations.append(
            f"High distraction rate ({summary['distraction_percentage']:.1f}%). "
            f"Consider implementing focused teaching strategies and minimizing off-topic discussions."
        )
    
    if summary['teacher_distraction_percentage'] > 20:
        recommendations.append(
            f"Teacher has {summary['teacher_distraction_percentage']:.1f}% distractions. "
            f"Focus on clear, concise, and on-topic communication."
        )
    
    if not recommendations:
        recommendations.append(
            "All students are performing well. Continue maintaining good engagement "
            "and communication standards."
        )
    
    return recommendations[:5]

# ==========================================
# SAVE JSON OUTPUT
# ==========================================

def save_performance_json(analysis_data, teacher_name, json_file):
    """Save performance analysis to JSON"""
    
    json_output = {
        "metadata": {
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_file": json_file,
            "teacher": teacher_name
        },
        "summary": analysis_data['summary'],
        "students": {}
    }
    
    for student, data in analysis_data['student_classifications'].items():
        cls = data['classification']
        student_data = data['data']
        
        json_output['students'][student] = {
            "classification": cls['type'],
            "score": cls['score'],
            "metrics": {
                "accuracy": cls['accuracy'],
                "quality_ratio": cls['quality_ratio'],
                "total_answers": cls['total_answers'],
                "correct_answers": cls['correct_answers'],
                "incorrect_answers": cls['incorrect_answers'],
                "questions_asked": cls['questions_asked']
            },
            "communication": {
                "useful_count": len(student_data['useful_communications']),
                "distraction_count": len(student_data['distractions']),
                "useful_examples": student_data['useful_communications'][:5],
                "distraction_examples": student_data['distractions'][:5]
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
    print(" " * 35 + "STUDENT PERFORMANCE & COMMUNICATION ANALYZER")
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
    
    print(f"\n📊 Analyzing student performance and communication...")
    print("   🤖 Classifying communication types and evaluating responses...")
    print("   ⏳ This may take a few moments...")
    
    analysis_data = analyze_student_performance(segments, teacher_name)
    
    if not analysis_data:
        print("❌ No analysis data found")
        return
    
    print(f"   ✓ Total messages analyzed: {analysis_data['summary']['total_messages']}")
    print(f"   ✓ Useful messages: {analysis_data['summary']['useful_messages']}")
    print(f"   ✓ Distractions: {analysis_data['summary']['distraction_messages']}")
    print(f"   ✓ Students analyzed: {len(analysis_data['student_classifications'])}")
    
    print(f"\n📝 Generating performance report...")
    report_lines = generate_performance_report(analysis_data, teacher_name, JSON_FILE)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in report_lines:
            f.write(line + "\n")
    
    print(f"💾 TXT report saved to: {OUTPUT_FILE}")
    
    print(f"\n💾 Saving JSON output...")
    save_performance_json(analysis_data, teacher_name, JSON_FILE)
    
    print("\n" + "=" * 120)
    print(" " * 35 + "ANALYSIS COMPLETE")
    print("=" * 120)

if __name__ == "__main__":
    main()