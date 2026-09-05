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
FINAL_OUTPUT_FILE = "final_conclusion_report.txt"
FINAL_OUTPUT_JSON = "final_conclusion_report.json"

# Input files from previous analyses
FILES = {
    "interaction_report": "interaction_analysis_report.json",
    "communication_quality": "communication_quality_report.json",
    "student_performance": "student_performance_analysis_report.json",
    "translated_conversation": "translated_conversation.json"
}

# ==========================================
# LOAD ALL ANALYSIS FILES
# ==========================================

def load_json_file(file_path):
    """Load JSON file with error handling"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON: {file_path}")
        return None

def load_all_analyses():
    """Load all analysis outputs"""
    data = {}
    
    print("\n📂 Loading analysis files...")
    
    for name, file_path in FILES.items():
        print(f"   Loading: {file_path}")
        data[name] = load_json_file(file_path)
        if data[name]:
            print(f"   ✅ Loaded successfully")
        else:
            print(f"   ⚠️ Could not load, will use fallback")
    
    return data

# ==========================================
# EXTRACT KEY INSIGHTS
# ==========================================

def extract_interaction_insights(data):
    """Extract insights from interaction analysis"""
    if not data:
        return {
            'total_interactions': 0,
            'teacher_questions': 0,
            'student_questions': 0,
            'student_response_rate': 0,
            'teacher_response_rate': 0,
            'unresponded_teacher': 0,
            'unresponded_student': 0
        }
    
    summary = data.get('summary', {})
    unresponded = data.get('unresponded', {})
    
    return {
        'total_interactions': summary.get('total_interactions', 0),
        'teacher_questions': summary.get('teacher_questions', 0),
        'student_questions': summary.get('student_questions', 0),
        'student_response_rate': summary.get('student_response_rate', 0),
        'teacher_response_rate': summary.get('teacher_response_rate', 0),
        'unresponded_teacher': len(unresponded.get('teacher_questions', [])),
        'unresponded_student': len(unresponded.get('student_questions', []))
    }

def extract_quality_insights(data):
    """Extract insights from communication quality analysis"""
    if not data:
        return {
            'avg_response_time_teacher_to_student': 0,
            'avg_response_time_student_to_teacher': 0,
            'teacher_questions': 0,
            'student_questions': 0,
            'total_interactions': 0
        }
    
    summary = data.get('summary', {})
    
    return {
        'avg_response_time_teacher_to_student': summary.get('avg_response_time_teacher_to_student', 0),
        'avg_response_time_student_to_teacher': summary.get('avg_response_time_student_to_teacher', 0),
        'teacher_questions': summary.get('teacher_initiated', 0),
        'student_questions': summary.get('student_initiated', 0),
        'total_interactions': summary.get('total_interactions', 0)
    }

def extract_performance_insights(data):
    """Extract insights from student performance analysis"""
    if not data:
        return {
            'total_messages': 0,
            'useful_messages': 0,
            'distraction_messages': 0,
            'useful_percentage': 0,
            'distraction_percentage': 0,
            'students': {}
        }
    
    summary = data.get('summary', {})
    students = data.get('students', {})
    
    student_performance = {}
    for name, info in students.items():
        classification = info.get('classification', 'Unknown')
        metrics = info.get('metrics', {})
        student_performance[name] = {
            'type': classification,
            'score': metrics.get('score', 0),
            'accuracy': metrics.get('accuracy', 0),
            'quality_ratio': metrics.get('quality_ratio', 0),
            'questions_asked': metrics.get('questions_asked', 0)
        }
    
    return {
        'total_messages': summary.get('total_messages', 0),
        'useful_messages': summary.get('useful_messages', 0),
        'distraction_messages': summary.get('distraction_messages', 0),
        'useful_percentage': summary.get('useful_percentage', 0),
        'distraction_percentage': summary.get('distraction_percentage', 0),
        'students': student_performance
    }

def extract_translation_insights(data):
    """Extract insights from translated conversation"""
    if not data:
        return {
            'total_sentences': 0,
            'speakers': {}
        }
    
    translations = data.get('translations', [])
    
    speaker_counts = defaultdict(int)
    for item in translations:
        speaker_counts[item.get('speaker', 'Unknown')] += 1
    
    return {
        'total_sentences': len(translations),
        'speakers': dict(speaker_counts)
    }

# ==========================================
# GENERATE COMPREHENSIVE ANALYSIS
# ==========================================

def generate_comprehensive_analysis(all_data):
    """Generate comprehensive analysis using LLM"""
    
    # Extract all insights
    interaction = extract_interaction_insights(all_data.get('interaction_report'))
    quality = extract_quality_insights(all_data.get('communication_quality'))
    performance = extract_performance_insights(all_data.get('student_performance'))
    translation = extract_translation_insights(all_data.get('translated_conversation'))
    
    # Prepare summary for LLM
    prompt = f"""
You are an educational analyst. Based on the following classroom conversation data, provide a comprehensive final conclusion.

========================================
SESSION OVERVIEW
========================================
Total Messages Analyzed: {translation['total_sentences']}
Total Interactions: {interaction['total_interactions']}
Teacher Questions: {interaction['teacher_questions']}
Student Questions: {interaction['student_questions']}

========================================
TEACHER PERFORMANCE
========================================
- Student Response Rate: {interaction['student_response_rate']:.1f}%
- Unresponded Teacher Questions: {interaction['unresponded_teacher']}
- Average Response Time: {quality['avg_response_time_student_to_teacher']:.1f}s

========================================
STUDENT PERFORMANCE
========================================
- Teacher Response Rate: {interaction['teacher_response_rate']:.1f}%
- Unresponded Student Questions: {interaction['unresponded_student']}
- Average Response Time: {quality['avg_response_time_teacher_to_student']:.1f}s

========================================
COMMUNICATION QUALITY
========================================
- Useful Communication: {performance['useful_percentage']:.1f}%
- Distractions: {performance['distraction_percentage']:.1f}%

========================================
INDIVIDUAL STUDENT PERFORMANCE
========================================
{json.dumps(performance['students'], indent=2)}

Based on ALL this data, provide:

1. EXECUTIVE SUMMARY (3-4 sentences)
   - Overall assessment of the session
   - Key strengths and weaknesses

2. TEACHER CONCLUSION
   - Teaching effectiveness
   - Questioning strategy
   - Responsiveness to students
   - Areas for improvement

3. STUDENT CONCLUSION
   - Overall student engagement
   - Performance trends
   - Individual student highlights (top performers and those needing support)

4. KEY METRICS ANALYSIS
   - Response rates (what do they indicate?)
   - Communication quality (is it effective?)
   - Participation balance (is it equal?)

5. CRITICAL INSIGHTS
   - Most important findings
   - Patterns observed
   - Red flags (if any)

6. ACTIONABLE RECOMMENDATIONS
   - For the teacher (3-5 specific suggestions)
   - For students (3-5 specific suggestions)

7. FINAL VERDICT (1-2 sentences)
   - Overall grade/rating of the session
   - Summary statement

Provide a clear, structured, and insightful analysis.
"""

    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': 'You are an expert educational analyst. Provide clear, insightful, and structured conclusions based on comprehensive data analysis.'},
                {'role': 'user', 'content': prompt}
            ]
        )
        
        return response['message']['content']
    
    except Exception as e:
        print(f"❌ Error generating analysis: {e}")
        return None

# ==========================================
# GENERATE FINAL REPORT
# ==========================================

def generate_final_report(analysis_text, all_data):
    """Generate the final conclusion report"""
    
    report_lines = []
    
    # Header
    report_lines.append("=" * 120)
    report_lines.append(" " * 40 + "FINAL CONCLUSION REPORT")
    report_lines.append("=" * 120)
    report_lines.append(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    if not analysis_text:
        report_lines.append("❌ Could not generate analysis.")
        report_lines.append("")
        return report_lines
    
    # Analysis text
    report_lines.append(analysis_text)
    report_lines.append("")
    
    # Additional Data Summary
    report_lines.append("=" * 120)
    report_lines.append(" APPENDIX: RAW DATA SUMMARY")
    report_lines.append("=" * 120)
    report_lines.append("")
    
    # Extract and display raw metrics
    interaction = extract_interaction_insights(all_data.get('interaction_report'))
    quality = extract_quality_insights(all_data.get('communication_quality'))
    performance = extract_performance_insights(all_data.get('student_performance'))
    translation = extract_translation_insights(all_data.get('translated_conversation'))
    
    report_lines.append("📊 SESSION METRICS:")
    report_lines.append(f"   Total Messages: {translation['total_sentences']}")
    report_lines.append(f"   Total Interactions: {interaction['total_interactions']}")
    report_lines.append(f"   Teacher Questions: {interaction['teacher_questions']}")
    report_lines.append(f"   Student Questions: {interaction['student_questions']}")
    report_lines.append("")
    
    report_lines.append("📊 RESPONSE RATES:")
    report_lines.append(f"   Student Response Rate: {interaction['student_response_rate']:.1f}%")
    report_lines.append(f"   Teacher Response Rate: {interaction['teacher_response_rate']:.1f}%")
    report_lines.append("")
    
    report_lines.append("📊 RESPONSE TIMES:")
    report_lines.append(f"   Teacher → Student: {quality['avg_response_time_teacher_to_student']:.1f}s")
    report_lines.append(f"   Student → Teacher: {quality['avg_response_time_student_to_teacher']:.1f}s")
    report_lines.append("")
    
    report_lines.append("📊 COMMUNICATION QUALITY:")
    report_lines.append(f"   Useful Messages: {performance['useful_percentage']:.1f}%")
    report_lines.append(f"   Distractions: {performance['distraction_percentage']:.1f}%")
    report_lines.append("")
    
    report_lines.append("📊 UNRESPONDED QUESTIONS:")
    report_lines.append(f"   Teacher Questions Unresponded: {interaction['unresponded_teacher']}")
    report_lines.append(f"   Student Questions Unresponded: {interaction['unresponded_student']}")
    report_lines.append("")
    
    report_lines.append("=" * 120)
    report_lines.append(" " * 40 + "END OF REPORT")
    report_lines.append("=" * 120)
    
    return report_lines

# ==========================================
# SAVE JSON OUTPUT
# ==========================================

def save_final_json(analysis_text, all_data):
    """Save final conclusion to JSON"""
    
    # Extract data for JSON
    interaction = extract_interaction_insights(all_data.get('interaction_report'))
    quality = extract_quality_insights(all_data.get('communication_quality'))
    performance = extract_performance_insights(all_data.get('student_performance'))
    translation = extract_translation_insights(all_data.get('translated_conversation'))
    
    json_output = {
        "metadata": {
            "generated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "type": "Final Conclusion Report"
        },
        "summary_metrics": {
            "total_messages": translation['total_sentences'],
            "total_interactions": interaction['total_interactions'],
            "teacher_questions": interaction['teacher_questions'],
            "student_questions": interaction['student_questions'],
            "student_response_rate": round(interaction['student_response_rate'], 1),
            "teacher_response_rate": round(interaction['teacher_response_rate'], 1),
            "avg_response_time_teacher_to_student": round(quality['avg_response_time_teacher_to_student'], 1),
            "avg_response_time_student_to_teacher": round(quality['avg_response_time_student_to_teacher'], 1),
            "useful_percentage": round(performance['useful_percentage'], 1),
            "distraction_percentage": round(performance['distraction_percentage'], 1),
            "unresponded_teacher_questions": interaction['unresponded_teacher'],
            "unresponded_student_questions": interaction['unresponded_student']
        },
        "student_performance": performance['students'],
        "conclusion": analysis_text
    }
    
    with open(FINAL_OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    
    print(f"💾 JSON saved to: {FINAL_OUTPUT_JSON}")

# ==========================================
# MAIN FUNCTION
# ==========================================

def main():
    print("\n" + "=" * 120)
    print(" " * 40 + "FINAL CONCLUSION GENERATOR")
    print("=" * 120)
    
    # Check Ollama
    try:
        ollama.list()
        print("✅ Ollama is running")
    except Exception as e:
        print(f"❌ Ollama not running: {e}")
        return
    
    # Load all analysis files
    all_data = load_all_analyses()
    
    # Check if we have any data
    has_data = any(v is not None for v in all_data.values())
    if not has_data:
        print("\n❌ No analysis files found. Please run previous analysis codes first.")
        print("\nRequired files:")
        for name, path in FILES.items():
            print(f"   - {path}")
        return
    
    print("\n📊 Analyzing all data...")
    
    # Generate comprehensive analysis
    analysis_text = generate_comprehensive_analysis(all_data)
    
    if not analysis_text:
        print("❌ Could not generate analysis")
        return
    
    # Generate final report
    print("\n📝 Generating final report...")
    report_lines = generate_final_report(analysis_text, all_data)
    
    # Save TXT report
    with open(FINAL_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in report_lines:
            f.write(line + "\n")
    
    print(f"💾 TXT report saved to: {FINAL_OUTPUT_FILE}")
    
    # Save JSON
    print("💾 Saving JSON output...")
    save_final_json(analysis_text, all_data)
    
    print("\n" + "=" * 120)
    print(" " * 40 + "FINAL CONCLUSION COMPLETE")
    print("=" * 120)

if __name__ == "__main__":
    main()