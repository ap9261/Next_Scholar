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
OUTPUT_FILE = "interaction_analysis_report.txt"
OUTPUT_JSON = "interaction_analysis_report.json"

# ==========================================
# LOAD AND PROCESS JSON DATA
# ==========================================

def load_transcript(json_file):
    """Load the transcript JSON file - handles translated format"""
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check if it's the translated format
        if isinstance(data, dict) and 'translations' in data:
            segments = []
            for item in data['translations']:
                # Clean the English text
                english_text = item.get('english', '').strip()
                # Skip if the English translation is a note or too short
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
        
        # Handle old format
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

def extract_teacher_from_filename(json_file):
    """Extract teacher name from filename"""
    base_name = os.path.basename(json_file)
    base_name = os.path.splitext(base_name)[0]
    
    patterns = [
        r'(?:[A-Z0-9]+_)?(?:[A-Za-z-]+ )?([A-Za-z\s]+) (?:Sir|Madam|Ma\'am|Teacher)',
        r'([A-Za-z\s]+) (?:Sir|Madam|Ma\'am|Teacher)_\d+',
        r'Teacher[_\s]+([A-Za-z_]+)',
        r'^([A-Za-z\s]+)(?:_\d+|\.\w+)?$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, base_name, re.IGNORECASE)
        if match:
            teacher_name = match.group(1).strip()
            teacher_name = re.sub(r'[_\s]+', ' ', teacher_name).strip()
            return teacher_name
    return None

def identify_teacher(segments, json_file):
    """Identify the teacher from filename or data"""
    teacher_name = extract_teacher_from_filename(json_file)
    
    speakers = set()
    for seg in segments:
        if 'speaker' in seg:
            speakers.add(seg['speaker'])
    
    if teacher_name:
        for speaker in speakers:
            if teacher_name.lower() in speaker.lower() or speaker.lower() in teacher_name.lower():
                return speaker
    
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
        'Hindi and English mixed speech conversation',
        'speech conversation',
        '[Music]', '[Applause]', '[Silence]',
        '...', '. . .',
        'speech recognition', 'transcription',
        'Note:', 'Translation:',
        'However, without more context',
        'If you could provide',
        'None of these words appear',
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
    text = re.sub(r'\n.*?Note:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def generate_llm_summary(text):
    """Generate a natural English summary using Llama model"""
    try:
        prompt = f"""
Provide a concise, natural English summary of this classroom question/conversation:

Text: "{text}"

Rules:
- Write in natural, conversational English
- Keep it brief (1 sentence)
- Focus on the key question or main point
- Use proper grammar

Summary:
"""
        
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': 'You are a classroom observer. Provide brief, natural English summaries of classroom conversations.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        summary = response['message']['content'].strip()
        summary = re.sub(r'^Summary:?\s*', '', summary, flags=re.IGNORECASE)
        summary = re.sub(r'^"|"$', '', summary)
        return summary[:100]
        
    except Exception as e:
        print(f"⚠️ Error generating LLM summary: {e}")
        words = text.split()
        if len(words) <= 7:
            return text
        return ' '.join(words[:7]) + '...'

def generate_short_summary(text):
    """Generate a short summary"""
    words = text.split()
    if len(words) <= 7:
        return text
    return ' '.join(words[:7]) + '...'

# ==========================================
# INTERACTION ANALYSIS
# ==========================================

def analyze_interactions(segments, teacher_name):
    """Analyze teacher-student interactions and response patterns"""
    
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
    
    # Mark questions using English patterns
    question_patterns = [
        r'[?？]',
        r'\b(?:what|why|how|when|where|who|which|whom|whose|is|are|was|were|do|does|did|has|have|had|will|shall|can|could|would|should|may|might|must)\b',
        r'\b(?:can you|could you|would you|will you|are you|do you|did you|have you|is it|are they)\b',
        r'\b(?:isn\'t|aren\'t|wasn\'t|weren\'t|don\'t|doesn\'t|didn\'t|hasn\'t|haven\'t|hadn\'t|won\'t|wouldn\'t|shouldn\'t|couldn\'t|can\'t)\b'
    ]
    
    for seg in clean_segments:
        text_lower = seg['text'].lower()
        is_question = False
        for pattern in question_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                is_question = True
                break
        seg['is_question'] = is_question
    
    # Analyze interactions
    interactions = {
        'teacher_initiated': {
            'total_questions': 0,
            'students': defaultdict(lambda: {'responded': 0, 'not_responded': 0})
        },
        'student_initiated': {
            'total_questions': 0,
            'students': defaultdict(lambda: {'asked': 0, 'teacher_responded': 0, 'teacher_not_responded': 0})
        },
        'conversation_flow': [],
        'response_times': defaultdict(list),
        'unresponded_teacher_questions': [],
        'unresponded_student_questions': []
    }
    
    for i in range(len(clean_segments) - 1):
        current = clean_segments[i]
        next_seg = clean_segments[i + 1]
        
        speaker1 = current['speaker']
        speaker2 = next_seg['speaker']
        
        if speaker1 == speaker2:
            continue
        
        response_time = next_seg['start'] - current['end']
        if response_time > 0 and response_time < 30:
            interactions['response_times'][speaker2].append(response_time)
        
        # Teacher asked, Student responded
        if current['is_teacher'] and current['is_question']:
            interactions['teacher_initiated']['total_questions'] += 1
            
            if not speaker2 == teacher_name:
                interactions['teacher_initiated']['students'][speaker2]['responded'] += 1
                interactions['conversation_flow'].append({
                    'type': 'teacher_asked_student_responded',
                    'teacher': current['text'],
                    'student': speaker2,
                    'student_response': next_seg['text'],
                    'time': current['start'],
                    'response_time': response_time
                })
            else:
                # Teacher asked but student didn't respond
                student_found = False
                for j in range(i-1, max(0, i-5), -1):
                    if not clean_segments[j]['is_teacher']:
                        student_name = clean_segments[j]['speaker']
                        interactions['teacher_initiated']['students'][student_name]['not_responded'] += 1
                        
                        llm_summary = generate_llm_summary(current['text'])
                        unresponded = {
                            'teacher': current['text'],
                            'student': student_name,
                            'time': current['start'],
                            'timestamp': current.get('time', f"{int(current['start']//60)}:{int(current['start']%60):02d}"),
                            'summary': generate_short_summary(current['text']),
                            'llm_summary': llm_summary,
                            'hindi': current.get('hindi', '')
                        }
                        interactions['unresponded_teacher_questions'].append(unresponded)
                        interactions['conversation_flow'].append({
                            'type': 'teacher_asked_student_not_responded',
                            'teacher': current['text'],
                            'student': student_name,
                            'time': current['start']
                        })
                        student_found = True
                        break
                
                if not student_found:
                    interactions['teacher_initiated']['students']['Unknown']['not_responded'] += 1
                    llm_summary = generate_llm_summary(current['text'])
                    unresponded = {
                        'teacher': current['text'],
                        'student': 'Unknown',
                        'time': current['start'],
                        'timestamp': current.get('time', f"{int(current['start']//60)}:{int(current['start']%60):02d}"),
                        'summary': generate_short_summary(current['text']),
                        'llm_summary': llm_summary,
                        'hindi': current.get('hindi', '')
                    }
                    interactions['unresponded_teacher_questions'].append(unresponded)
        
        # Student asked, Teacher responded or not
        elif not current['is_teacher'] and current['is_question']:
            student_name = speaker1
            interactions['student_initiated']['total_questions'] += 1
            interactions['student_initiated']['students'][student_name]['asked'] += 1
            
            if speaker2 == teacher_name:
                interactions['student_initiated']['students'][student_name]['teacher_responded'] += 1
                interactions['conversation_flow'].append({
                    'type': 'student_asked_teacher_responded',
                    'student': student_name,
                    'student_question': current['text'],
                    'teacher_response': next_seg['text'],
                    'time': current['start'],
                    'response_time': response_time
                })
            else:
                interactions['student_initiated']['students'][student_name]['teacher_not_responded'] += 1
                llm_summary = generate_llm_summary(current['text'])
                unresponded = {
                    'student': student_name,
                    'question': current['text'],
                    'time': current['start'],
                    'timestamp': current.get('time', f"{int(current['start']//60)}:{int(current['start']%60):02d}"),
                    'summary': generate_short_summary(current['text']),
                    'llm_summary': llm_summary,
                    'hindi': current.get('hindi', '')
                }
                interactions['unresponded_student_questions'].append(unresponded)
                interactions['conversation_flow'].append({
                    'type': 'student_asked_teacher_not_responded',
                    'student': student_name,
                    'student_question': current['text'],
                    'time': current['start']
                })
    
    # Calculate summary statistics
    summary = {
        'teacher_initiated': {
            'total_questions': interactions['teacher_initiated']['total_questions'],
            'student_response_rate': 0,
            'students': {}
        },
        'student_initiated': {
            'total_questions': interactions['student_initiated']['total_questions'],
            'teacher_response_rate': 0,
            'students': {}
        },
        'student_summary': {},
        'average_response_time': {},
        'unresponded_teacher_questions': interactions['unresponded_teacher_questions'],
        'unresponded_student_questions': interactions['unresponded_student_questions']
    }
    
    # Teacher-initiated stats
    total_teacher_questions = interactions['teacher_initiated']['total_questions']
    total_student_responses = 0
    total_student_non_responses = 0
    
    for student, data in interactions['teacher_initiated']['students'].items():
        responded = data['responded']
        not_responded = data['not_responded']
        total_student_responses += responded
        total_student_non_responses += not_responded
        
        summary['teacher_initiated']['students'][student] = {
            'responded': responded,
            'not_responded': not_responded,
            'total': responded + not_responded,
            'response_rate': (responded / (responded + not_responded) * 100) if (responded + not_responded) > 0 else 0
        }
    
    if total_teacher_questions > 0:
        summary['teacher_initiated']['student_response_rate'] = (total_student_responses / total_teacher_questions) * 100
    
    # Student-initiated stats
    total_student_questions = interactions['student_initiated']['total_questions']
    total_teacher_responses = 0
    total_teacher_non_responses = 0
    
    for student, data in interactions['student_initiated']['students'].items():
        asked = data['asked']
        teacher_responded = data['teacher_responded']
        teacher_not_responded = data['teacher_not_responded']
        total_teacher_responses += teacher_responded
        total_teacher_non_responses += teacher_not_responded
        
        summary['student_initiated']['students'][student] = {
            'asked': asked,
            'teacher_responded': teacher_responded,
            'teacher_not_responded': teacher_not_responded,
            'teacher_response_rate': (teacher_responded / asked * 100) if asked > 0 else 0
        }
    
    if total_student_questions > 0:
        summary['student_initiated']['teacher_response_rate'] = (total_teacher_responses / total_student_questions) * 100
    
    # Average response times
    for speaker, times in interactions['response_times'].items():
        if times:
            summary['average_response_time'][speaker] = sum(times) / len(times)
    
    # Combined student summary
    all_students = set()
    for s in summary['teacher_initiated']['students'].keys():
        all_students.add(s)
    for s in summary['student_initiated']['students'].keys():
        all_students.add(s)
    
    for student in all_students:
        teacher_init = summary['teacher_initiated']['students'].get(student, {})
        student_init = summary['student_initiated']['students'].get(student, {})
        
        teacher_asked = teacher_init.get('responded', 0) + teacher_init.get('not_responded', 0)
        student_asked = student_init.get('asked', 0)
        response_rate = teacher_init.get('response_rate', 0) if teacher_asked > 0 else 0
        
        summary['student_summary'][student] = {
            'teacher_asked_total': teacher_asked,
            'student_responded': teacher_init.get('responded', 0),
            'student_not_responded': teacher_init.get('not_responded', 0),
            'student_response_rate': response_rate,
            'student_asked_total': student_asked,
            'teacher_responded': student_init.get('teacher_responded', 0),
            'teacher_not_responded': student_init.get('teacher_not_responded', 0),
            'teacher_response_rate': student_init.get('teacher_response_rate', 0) if student_asked > 0 else 0,
            'avg_response_time': summary['average_response_time'].get(student, 0)
        }
    
    summary['total_interactions'] = len(interactions['conversation_flow'])
    summary['clean_segments'] = clean_segments
    
    return summary

# ==========================================
# GENERATE INTERACTION REPORT
# ==========================================

def generate_interaction_report(interaction_data, teacher_name, json_file):
    """Generate a comprehensive interaction analysis report"""
    
    report_lines = []
    
    # Header
    report_lines.append("=" * 100)
    report_lines.append(" " * 30 + "TEACHER-STUDENT INTERACTION ANALYSIS REPORT")
    report_lines.append("=" * 100)
    report_lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f" Source File: {json_file}")
    report_lines.append(f" Teacher: {teacher_name}")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    if not interaction_data:
        report_lines.append(" No interaction data found.")
        return report_lines
    
    # SECTION 1: OVERVIEW
    report_lines.append("=" * 100)
    report_lines.append(" SECTION 1: INTERACTION OVERVIEW")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    total_interactions = interaction_data['total_interactions']
    report_lines.append(f" Total Turn-Taking Events: {total_interactions}")
    report_lines.append("")
    
    # Teacher Initiated
    teacher_total = interaction_data['teacher_initiated']['total_questions']
    response_rate = interaction_data['teacher_initiated']['student_response_rate']
    report_lines.append(" 📊 TEACHER-INITIATED INTERACTIONS:")
    report_lines.append(f"    Total Questions Asked by Teacher: {teacher_total}")
    report_lines.append(f"    Student Response Rate: {response_rate:.1f}%")
    report_lines.append(f"    Student Non-Response Rate: {100 - response_rate:.1f}%")
    report_lines.append("")
    
    # Student Initiated
    student_total = interaction_data['student_initiated']['total_questions']
    teacher_response_rate = interaction_data['student_initiated']['teacher_response_rate']
    report_lines.append(" 📊 STUDENT-INITIATED INTERACTIONS:")
    report_lines.append(f"    Total Questions Asked by Students: {student_total}")
    report_lines.append(f"    Teacher Response Rate: {teacher_response_rate:.1f}%")
    report_lines.append(f"    Teacher Non-Response Rate: {100 - teacher_response_rate:.1f}%")
    report_lines.append("")
    
    # SECTION 2: UNRESPONDED TEACHER QUESTIONS
    report_lines.append("=" * 100)
    report_lines.append(" SECTION 2: UNRESPONDED TEACHER QUESTIONS")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    unresponded_teacher = interaction_data.get('unresponded_teacher_questions', [])
    if unresponded_teacher:
        report_lines.append(f" Total Unresponded Teacher Questions: {len(unresponded_teacher)}")
        report_lines.append("")
        report_lines.append("┌─────┬──────────┬────────────────────────────────────────────────────────────────────┬──────────────────┐")
        report_lines.append("│ No. │ Time     │ LLM Summary                                                  │ Student Name     │")
        report_lines.append("├─────┼──────────┼────────────────────────────────────────────────────────────────────┼──────────────────┤")
        
        for i, item in enumerate(unresponded_teacher, 1):
            llm_summary = item['llm_summary'][:55] + "..." if len(item['llm_summary']) > 55 else item['llm_summary']
            student = item['student'][:18] if len(item['student']) > 18 else item['student']
            report_lines.append(f"│ {i:3} │ {item['timestamp']:>6} │ {llm_summary:<56} │ {student:<16} │")
        
        report_lines.append("└─────┴──────────┴────────────────────────────────────────────────────────────────────┴──────────────────┘")
        report_lines.append("")
        
        report_lines.append(" DETAILED UNRESPONDED TEACHER QUESTIONS:")
        report_lines.append(" ─" * 80)
        for i, item in enumerate(unresponded_teacher, 1):
            report_lines.append(f"")
            report_lines.append(f"   {i}. [Time: {item['timestamp']}]")
            report_lines.append(f"      📝 LLM Summary: {item['llm_summary']}")
            if item.get('hindi'):
                report_lines.append(f"      🗣️ Hindi: {item['hindi']}")
            report_lines.append(f"      📄 English: {item['teacher']}")
            report_lines.append(f"      👤 Expected Student: {item['student']}")
            report_lines.append(f"      ⏱️ Time (seconds): {item['time']:.0f}s")
            report_lines.append("")
    else:
        report_lines.append(" ✅ No unresponded teacher questions found.")
        report_lines.append("")
    
    # SECTION 3: UNRESPONDED STUDENT QUESTIONS
    report_lines.append("=" * 100)
    report_lines.append(" SECTION 3: UNRESPONDED STUDENT QUESTIONS")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    unresponded_student = interaction_data.get('unresponded_student_questions', [])
    if unresponded_student:
        report_lines.append(f" Total Unresponded Student Questions: {len(unresponded_student)}")
        report_lines.append("")
        report_lines.append("┌─────┬──────────┬────────────────────────────────────────────────────────────────────┬──────────────────┐")
        report_lines.append("│ No. │ Time     │ LLM Summary                                                  │ Student Name     │")
        report_lines.append("├─────┼──────────┼────────────────────────────────────────────────────────────────────┼──────────────────┤")
        
        for i, item in enumerate(unresponded_student, 1):
            llm_summary = item['llm_summary'][:55] + "..." if len(item['llm_summary']) > 55 else item['llm_summary']
            student = item['student'][:18] if len(item['student']) > 18 else item['student']
            report_lines.append(f"│ {i:3} │ {item['timestamp']:>6} │ {llm_summary:<56} │ {student:<16} │")
        
        report_lines.append("└─────┴──────────┴────────────────────────────────────────────────────────────────────┴──────────────────┘")
        report_lines.append("")
        
        report_lines.append(" DETAILED UNRESPONDED STUDENT QUESTIONS:")
        report_lines.append(" ─" * 80)
        for i, item in enumerate(unresponded_student, 1):
            report_lines.append(f"")
            report_lines.append(f"   {i}. [Time: {item['timestamp']}]")
            report_lines.append(f"      📝 LLM Summary: {item['llm_summary']}")
            if item.get('hindi'):
                report_lines.append(f"      🗣️ Hindi: {item['hindi']}")
            report_lines.append(f"      📄 English: {item['question']}")
            report_lines.append(f"      👤 Student: {item['student']}")
            report_lines.append(f"      ⏱️ Time (seconds): {item['time']:.0f}s")
            report_lines.append("")
    else:
        report_lines.append(" ✅ No unresponded student questions found.")
        report_lines.append("")
    
    # SECTION 4: STUDENT SUMMARY TABLE
    report_lines.append("=" * 100)
    report_lines.append(" SECTION 4: INDIVIDUAL STUDENT RESPONSE ANALYSIS")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    # Table Header
    report_lines.append("┌─────────────────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐")
    report_lines.append("│ STUDENT             │ T ASKED  │ T RESP  │ T NON   │ S ASKED │ T RESP  │ T NON   │")
    report_lines.append("│                     │ (T→S)   │ RESP    │ RESP    │ (S→T)  │ RESP    │ RESP    │")
    report_lines.append("├─────────────────────┼──────────┼──────────┼──────────┼──────────┼──────────┼──────────┤")
    
    sorted_students = sorted(interaction_data['student_summary'].items(), 
                            key=lambda x: x[1]['teacher_asked_total'] + x[1]['student_asked_total'], 
                            reverse=True)
    
    for student, data in sorted_students:
        display_name = student[:20] + "..." if len(student) > 20 else student
        report_lines.append(
            f"│ {display_name:<19} │ {data['teacher_asked_total']:>6}   │ {data['student_responded']:>6}   │ {data['student_not_responded']:>6}   │ {data['student_asked_total']:>6}   │ {data['teacher_responded']:>6}   │ {data['teacher_not_responded']:>6}   │"
        )
    
    report_lines.append("└─────────────────────┴──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘")
    report_lines.append("")
    report_lines.append(" LEGEND:")
    report_lines.append("   T ASKED (T→S) = Teacher asked student (total questions)")
    report_lines.append("   T RESP = Student responded to teacher")
    report_lines.append("   T NON RESP = Student did NOT respond to teacher")
    report_lines.append("   S ASKED (S→T) = Student asked teacher (total questions)")
    report_lines.append("   T RESP = Teacher responded to student")
    report_lines.append("   T NON RESP = Teacher did NOT respond to student")
    report_lines.append("")
    
    # SECTION 5: DETAILED STUDENT ANALYSIS
    report_lines.append("=" * 100)
    report_lines.append(" SECTION 5: DETAILED STUDENT ANALYSIS")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    for student, data in sorted_students:
        report_lines.append("─" * 100)
        report_lines.append(f" 📌 STUDENT: {student}")
        report_lines.append("─" * 100)
        report_lines.append("")
        
        if data['teacher_asked_total'] > 0:
            response_pct = data['student_response_rate']
            report_lines.append(" 🗣️ WHEN TEACHER ASKS THIS STUDENT:")
            report_lines.append(f"    Total Questions: {data['teacher_asked_total']}")
            report_lines.append(f"    Student Responded: {data['student_responded']} times ({response_pct:.1f}%)")
            report_lines.append(f"    Student Did NOT Respond: {data['student_not_responded']} times ({100-response_pct:.1f}%)")
            
            if response_pct > 70:
                report_lines.append("    ✅ Response Quality: EXCELLENT")
            elif response_pct > 50:
                report_lines.append("    ✅ Response Quality: GOOD")
            elif response_pct > 30:
                report_lines.append("    ⚠️ Response Quality: AVERAGE")
            else:
                report_lines.append("    ❌ Response Quality: POOR")
            report_lines.append("")
        else:
            report_lines.append(" 🗣️ WHEN TEACHER ASKS THIS STUDENT: No questions asked")
            report_lines.append("")
        
        if data['student_asked_total'] > 0:
            teacher_response_pct = data['teacher_response_rate']
            report_lines.append(" 💡 WHEN STUDENT INITIATES QUESTIONS:")
            report_lines.append(f"    Total Questions Asked: {data['student_asked_total']}")
            report_lines.append(f"    Teacher Responded: {data['teacher_responded']} times ({teacher_response_pct:.1f}%)")
            report_lines.append(f"    Teacher Did NOT Respond: {data['teacher_not_responded']} times ({100-teacher_response_pct:.1f}%)")
            
            if teacher_response_pct > 70:
                report_lines.append("    ✅ Teacher Support: EXCELLENT")
            elif teacher_response_pct > 50:
                report_lines.append("    ✅ Teacher Support: GOOD")
            elif teacher_response_pct > 30:
                report_lines.append("    ⚠️ Teacher Support: AVERAGE")
            else:
                report_lines.append("    ❌ Teacher Support: POOR")
            report_lines.append("")
        else:
            report_lines.append(" 💡 STUDENT INITIATIVES: This student did not ask questions")
            report_lines.append("")
        
        if data['avg_response_time'] > 0:
            report_lines.append(f" ⏱️ Average Response Time: {data['avg_response_time']:.1f} seconds")
            if data['avg_response_time'] < 3:
                report_lines.append("    ✅ Response Speed: FAST")
            elif data['avg_response_time'] < 7:
                report_lines.append("    ✅ Response Speed: NORMAL")
            else:
                report_lines.append("    ⚠️ Response Speed: SLOW")
            report_lines.append("")
        
        total_interactions_student = data['teacher_asked_total'] + data['student_asked_total']
        if total_interactions_student > 0:
            engagement_score = ((data['student_responded'] + data['student_asked_total']) / 
                              (total_interactions_student * 2) * 100) if total_interactions_student > 0 else 0
            
            if engagement_score > 70:
                engagement_level = "🟢 HIGH ENGAGEMENT"
            elif engagement_score > 40:
                engagement_level = "🟡 MODERATE ENGAGEMENT"
            else:
                engagement_level = "🔴 LOW ENGAGEMENT"
            
            report_lines.append(f" 📊 Overall Engagement Level: {engagement_level} ({engagement_score:.1f}%)")
            report_lines.append("")
    
    # SECTION 6: RECOMMENDATIONS
    report_lines.append("=" * 100)
    report_lines.append(" SECTION 6: RECOMMENDATIONS")
    report_lines.append("=" * 100)
    report_lines.append("")
    
    recommendations = generate_interaction_recommendations(interaction_data, teacher_name)
    for rec in recommendations:
        report_lines.append(f" • {rec}")
        report_lines.append("")
    
    report_lines.append("=" * 100)
    report_lines.append(" " * 40 + "END OF REPORT")
    report_lines.append("=" * 100)
    
    return report_lines

def generate_interaction_recommendations(interaction_data, teacher_name):
    """Generate recommendations based on interaction analysis"""
    
    recommendations = []
    
    teacher_response_rate = interaction_data['teacher_initiated']['student_response_rate']
    if teacher_response_rate < 50:
        recommendations.append(
            f"Low student response rate ({teacher_response_rate:.1f}%). Consider using more engaging questioning techniques."
        )
    
    student_response_rate = interaction_data['student_initiated']['teacher_response_rate']
    if student_response_rate < 50 and interaction_data['student_initiated']['total_questions'] > 0:
        recommendations.append(
            f"Low teacher response rate ({student_response_rate:.1f}%). Teacher should prioritize responding to student queries."
        )
    
    unresponded_teacher = len(interaction_data.get('unresponded_teacher_questions', []))
    if unresponded_teacher > 5:
        recommendations.append(
            f"High number of unresponded teacher questions ({unresponded_teacher}). "
            f"Consider using different questioning strategies."
        )
    
    unresponded_student = len(interaction_data.get('unresponded_student_questions', []))
    if unresponded_student > 3:
        recommendations.append(
            f"High number of unresponded student questions ({unresponded_student}). "
            f"Teacher should ensure all student queries are addressed."
        )
    
    for student, data in interaction_data['student_summary'].items():
        if data['teacher_asked_total'] > 3 and data['student_response_rate'] < 40:
            recommendations.append(
                f"Student '{student}' has low response rate ({data['student_response_rate']:.1f}%). "
                f"Consider providing additional support."
            )
    
    if not recommendations:
        recommendations.append(
            "Interaction patterns appear well-balanced. Continue maintaining good engagement."
        )
    
    return recommendations[:5]

# ==========================================
# SAVE JSON OUTPUT
# ==========================================

def save_json_output(interaction_data, teacher_name, json_file):
    """Save interaction data to a well-formatted JSON file"""
    
    json_output = {
        "metadata": {
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "source_file": json_file,
            "teacher": teacher_name
        },
        "summary": {
            "total_interactions": interaction_data['total_interactions'],
            "teacher_questions": interaction_data['teacher_initiated']['total_questions'],
            "student_questions": interaction_data['student_initiated']['total_questions'],
            "student_response_rate": round(interaction_data['teacher_initiated']['student_response_rate'], 1),
            "teacher_response_rate": round(interaction_data['student_initiated']['teacher_response_rate'], 1)
        },
        "unresponded": {
            "teacher_questions": [
                {
                    "id": i + 1,
                    "timestamp": item['timestamp'],
                    "time_seconds": round(item['time'], 1),
                    "llm_summary": item['llm_summary'],
                    "summary": item['summary'],
                    "full_text": item['teacher'],
                    "hindi_text": item.get('hindi', ''),
                    "expected_student": item['student']
                }
                for i, item in enumerate(interaction_data.get('unresponded_teacher_questions', []))
            ],
            "student_questions": [
                {
                    "id": i + 1,
                    "timestamp": item['timestamp'],
                    "time_seconds": round(item['time'], 1),
                    "llm_summary": item['llm_summary'],
                    "summary": item['summary'],
                    "full_text": item['question'],
                    "hindi_text": item.get('hindi', ''),
                    "student": item['student']
                }
                for i, item in enumerate(interaction_data.get('unresponded_student_questions', []))
            ]
        },
        "students": {}
    }
    
    for student, data in interaction_data['student_summary'].items():
        json_output['students'][student] = {
            "teacher_questions_asked": data['teacher_asked_total'],
            "student_responses": {
                "responded": data['student_responded'],
                "not_responded": data['student_not_responded'],
                "response_rate": round(data['student_response_rate'], 1)
            },
            "student_questions_asked": data['student_asked_total'],
            "teacher_responses": {
                "responded": data['teacher_responded'],
                "not_responded": data['teacher_not_responded'],
                "response_rate": round(data['teacher_response_rate'], 1)
            },
            "average_response_time": round(data['avg_response_time'], 1) if data['avg_response_time'] > 0 else 0,
            "engagement_score": round(
                ((data['student_responded'] + data['student_asked_total']) / 
                ((data['teacher_asked_total'] + data['student_asked_total']) * 2) * 100) 
                if (data['teacher_asked_total'] + data['student_asked_total']) > 0 else 0,
                1
            )
        }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    print(f"💾 JSON saved to: {OUTPUT_JSON}")

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    print("\n" + "=" * 100)
    print(" " * 30 + "TEACHER-STUDENT INTERACTION ANALYZER")
    print("=" * 100)
    
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
    
    print(f"\n📊 Analyzing interactions...")
    print("   🤖 Generating LLM summaries...")
    interaction_data = analyze_interactions(segments, teacher_name)
    
    if not interaction_data:
        print("❌ No interaction data found")
        return
    
    print(f"   ✓ Total interactions: {interaction_data['total_interactions']}")
    print(f"   ✓ Teacher questions: {interaction_data['teacher_initiated']['total_questions']}")
    print(f"   ✓ Student questions: {interaction_data['student_initiated']['total_questions']}")
    print(f"   ✓ Unresponded teacher questions: {len(interaction_data.get('unresponded_teacher_questions', []))}")
    print(f"   ✓ Unresponded student questions: {len(interaction_data.get('unresponded_student_questions', []))}")
    
    print(f"\n📝 Generating interaction report...")
    report_lines = generate_interaction_report(interaction_data, teacher_name, JSON_FILE)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in report_lines:
            f.write(line + "\n")
    
    print(f"💾 TXT report saved to: {OUTPUT_FILE}")
    
    print(f"\n💾 Saving JSON output...")
    save_json_output(interaction_data, teacher_name, JSON_FILE)
    
    print("\n" + "=" * 100)
    print(" " * 35 + "ANALYSIS COMPLETE")
    print("=" * 100)

if __name__ == "__main__":
    main()