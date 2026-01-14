"""
AI Service using OpenAI GPT-4o-mini for question solving and teaching
Includes vision capabilities for image-based questions
"""
from openai import OpenAI
from app.core.config import settings
from typing import Dict, List, Optional
import json
import base64


class AIService:
    """Service for AI-powered tutoring using OpenAI"""
    
    def __init__(self):
        """Initialize OpenAI client"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4.1"  # Using GPT-4o-mini as specified
    
    def solve_question(self, question_text: str, subject: Optional[str] = None) -> Dict:
        """
        Solve a question with step-by-step explanation
        
        Args:
            question_text: The question to solve
            subject: Optional subject hint (e.g., "Mathematics", "Physics")
            
        Returns:
            Dictionary with solution, steps, subject, and topic
        """
        # Build prompt
        system_prompt = """You are an expert tutor for Nigerian secondary school students preparing for WAEC, NECO, and JAMB exams. 
Your job is to:
1. Identify the subject and topic of the question
2. Provide a clear, step-by-step solution
3. Explain concepts in simple terms
4. Reference the WAEC/JAMB syllabus topic

IMPORTANT - Math/Formula Formatting:
- Use LaTeX syntax for ALL mathematical expressions, equations, formulas, and chemical formulas
- Inline math: Use $...$ for formulas within text (e.g., $E = mc^2$, $H_2SO_4$, $v = u + at$)
- Block math: Use $$...$$ for displayed equations (e.g., $$\\int_{a}^{b} f(x) dx = F(b) - F(a)$$)
- Examples:
  * Mathematics: $x^2 + 5x - 6 = 0$, $\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$
  * Physics: $F = ma$, $E = \\frac{1}{2}mv^2$, $v = u + at$
  * Chemistry: $H_2SO_4$, $CaCO_3$, $2H_2 + O_2 \\rightarrow 2H_2O$
  * Always format formulas, equations, and chemical equations using LaTeX

IMPORTANT - Table Formatting:
- Use markdown table format for ALL tables, comparison charts, data sets, and structured information
- Format: | Header 1 | Header 2 | Header 3 |
          |----------|----------|----------|
          | Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
          | Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |
- Use tables for: periodic table data, comparison tables, formula tables, conversion tables, etc.
- You can use LaTeX math ($...$) inside table cells

Response format (JSON):
{
    "subject": "subject name",
    "topic": "specific topic from syllabus",
    "solution": "final answer (use LaTeX for any math, tables in markdown format)",
    "steps": [
        {"step_number": 1, "description": "what to do", "formula": "formula in LaTeX if any (e.g., $F = ma$)", "explanation": "why we do this (use LaTeX for math, tables in markdown)"},
        ...
    ],
    "related_topics": ["topic1", "topic2"]
}"""
        
        user_prompt = f"""Question: {question_text}"""
        if subject:
            user_prompt += f"\nSubject hint: {subject}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            raise ValueError(f"AI service error: {str(e)}")
    
    def solve_question_with_image(
        self, 
        image_base64: str, 
        subject: Optional[str] = None,
        additional_context: Optional[str] = None,
        image_type: str = "image/jpeg"
    ) -> Dict:
        """
        Solve a question from an image using GPT-4o-mini vision capabilities
        
        Args:
            image_base64: Base64 encoded image data
            subject: Optional subject hint (e.g., "Mathematics", "Physics")
            additional_context: Optional additional text context from user
            image_type: MIME type of the image (e.g., "image/jpeg", "image/png")
            
        Returns:
            Dictionary with solution, steps, subject, and topic
        """
        system_prompt = """You are an expert tutor for Nigerian secondary school students preparing for WAEC, NECO, and JAMB exams.

Look at the image provided. It contains a question or problem that needs solving.

Your job is to:
1. Carefully read and understand the question in the image
2. Identify the subject and topic
3. Provide a clear, step-by-step solution
4. Explain concepts in simple terms that Nigerian students can understand
5. Reference the WAEC/JAMB syllabus topic

IMPORTANT - Math/Formula Formatting:
- Use LaTeX syntax for ALL mathematical expressions, equations, formulas, and chemical formulas
- Inline math: Use $...$ for formulas within text (e.g., $E = mc^2$, $H_2SO_4$, $v = u + at$)
- Block math: Use $$...$$ for displayed equations (e.g., $$\\int_{a}^{b} f(x) dx = F(b) - F(a)$$)
- Examples:
  * Mathematics: $x^2 + 5x - 6 = 0$, $\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$
  * Physics: $F = ma$, $E = \\frac{1}{2}mv^2$, $v = u + at$
  * Chemistry: $H_2SO_4$, $CaCO_3$, $2H_2 + O_2 \\rightarrow 2H_2O$
  * Always format formulas, equations, and chemical equations using LaTeX

IMPORTANT - Table Formatting:
- Use markdown table format for ALL tables, comparison charts, data sets, and structured information
- Format: | Header 1 | Header 2 | Header 3 |
          |----------|----------|----------|
          | Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
          | Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |
- Use tables for: periodic table data, comparison tables, formula tables, conversion tables, etc.
- You can use LaTeX math ($...$) inside table cells

Response format (JSON):
{
    "subject": "subject name",
    "topic": "specific topic from syllabus",
    "question_text": "the question you identified from the image",
    "solution": "final answer (use LaTeX for any math, tables in markdown format)",
    "steps": [
        {"step_number": 1, "description": "what to do", "formula": "formula in LaTeX if any (e.g., $F = ma$)", "explanation": "why we do this (use LaTeX for math, tables in markdown)"},
        ...
    ],
    "related_topics": ["topic1", "topic2"]
}"""

        # Build the user message with image
        user_content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_type};base64,{image_base64}",
                    "detail": "high"  # Use high detail for better accuracy with equations/diagrams
                }
            },
            {
                "type": "text",
                "text": "Please analyze this image and solve the question/problem shown."
            }
        ]
        
        # Add subject hint if provided
        if subject:
            user_content.append({
                "type": "text",
                "text": f"Subject hint: {subject}"
            })
        
        # Add additional context if provided
        if additional_context:
            user_content.append({
                "type": "text",
                "text": f"Additional context from student: {additional_context}"
            })
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.7,
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            raise ValueError(f"AI vision service error: {str(e)}")
    
    def teach_topic(self, subject: str, topic: str, difficulty: str = "medium") -> Dict:
        """
        Teach a specific topic with examples
        
        Args:
            subject: Subject name (e.g., "Mathematics")
            topic: Topic name (e.g., "Quadratic Equations")
            difficulty: Difficulty level ("simple", "medium", "advanced")
            
        Returns:
            Dictionary with teaching content
        """
        system_prompt = """You are an expert tutor teaching Nigerian secondary school students for WAEC/JAMB.
Provide clear, engaging explanations with real-world examples.

IMPORTANT - Math/Formula Formatting:
- Use LaTeX syntax for ALL mathematical expressions, equations, formulas, and chemical formulas
- Inline math: Use $...$ for formulas within text (e.g., $E = mc^2$, $H_2SO_4$, $v = u + at$)
- Block math: Use $$...$$ for displayed equations (e.g., $$\\int_{a}^{b} f(x) dx = F(b) - F(a)$$)
- Examples:
  * Mathematics: $x^2 + 5x - 6 = 0$, $\\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$
  * Physics: $F = ma$, $E = \\frac{1}{2}mv^2$, $v = u + at$
  * Chemistry: $H_2SO_4$, $CaCO_3$, $2H_2 + O_2 \\rightarrow 2H_2O$
  * Always format formulas, equations, and chemical equations using LaTeX

IMPORTANT - Table Formatting:
- Use markdown table format for ALL tables, comparison charts, data sets, and structured information
- Format: | Header 1 | Header 2 | Header 3 |
          |----------|----------|----------|
          | Row 1 Col 1 | Row 1 Col 2 | Row 1 Col 3 |
          | Row 2 Col 1 | Row 2 Col 2 | Row 2 Col 3 |
- Use tables for: periodic table data, comparison tables, formula tables, conversion tables, etc.
- You can use LaTeX math ($...$) inside table cells

Response format (JSON):
{
    "summary": "2-3 sentence overview (use LaTeX for any math)",
    "detailed_explanation": "comprehensive explanation with diagrams described (use LaTeX for all formulas and equations, markdown tables for structured data)",
    "key_concepts": ["concept1", "concept2"],
    "examples": [
        "Example problem with solution (in new line). Use LaTeX for formulas: Problem: Solve $x^2 - 5x + 6 = 0$. Solution: Using factorization, $(x-2)(x-3) = 0$, so $x = 2$ or $x = 3$. Use markdown tables when comparing data."
    ],
    "practice_questions": ["question1 (use LaTeX for math, tables in markdown)", "question2", "question3"],
    "common_mistakes": ["mistake1", "mistake2"],
    "exam_tips": ["tip1", "tip2"]
}"""
        
        user_prompt = f"""Teach me about {topic} in {subject}.
Difficulty level: {difficulty}
Make it relevant to WAEC/JAMB exams."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            raise ValueError(f"AI service error: {str(e)}")
    
    def chat_about_topic(self, subject: str, topic: str, user_message: str, conversation_history: List[Dict] = None) -> str:
        """
        Chat with AI about a specific topic
        
        Args:
            subject: Subject name (e.g., "Mathematics")
            topic: Topic name (e.g., "Quadratic Equations")
            user_message: User's message/question
            conversation_history: Previous messages in format [{"role": "user/assistant", "content": "message"}, ...]
            
        Returns:
            AI response message
        """
        system_prompt = f"""You are an expert tutor helping a Nigerian student understand {topic} in {subject}.
Your role is to answer questions, clarify concepts, and provide explanations ONLY about this specific topic.

IMPORTANT - Math/Formula Formatting:
- Use LaTeX syntax for ALL mathematical expressions, equations, formulas, and chemical formulas
- Inline math: Use $...$ for formulas within text (e.g., $E = mc^2$, $H_2SO_4$, $v = u + at$)
- Block math: Use $$...$$ for displayed equations

IMPORTANT - Table Formatting:
- Use markdown table format for ALL tables, comparison charts, data sets
- Format: | Header 1 | Header 2 |
          |----------|----------|
          | Row 1 Col 1 | Row 1 Col 2 |

Stay focused on {topic} in {subject}. If the user asks about something unrelated, politely redirect them back to this topic.
Keep explanations clear, simple, and relevant to WAEC/JAMB exams."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("message", msg.get("content", ""))
                })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise ValueError(f"AI chat service error: {str(e)}")
    
    def generate_study_plan(
        self, 
        subjects: List[str], 
        hours_per_day: int, 
        days_per_week: int,
        weeks_until_exam: int,
        weak_areas: List[str] = []
    ) -> Dict:
        """
        Generate a personalized study plan
        
        Args:
            subjects: List of subjects to study
            hours_per_day: Available study hours per day
            days_per_week: Study days per week
            weeks_until_exam: Weeks until exam
            weak_areas: Topics that need more focus
            
        Returns:
            Structured study plan
        """
        system_prompt = """You are a study planning expert for WAEC/JAMB preparation.
Create a balanced, realistic study schedule.

Response format (JSON):
{
    "plan_overview": "summary of the plan",
    "weekly_breakdown": [
        {
            "week": 1,
            "focus": "what to focus on this week",
            "daily_schedule": [
                {"day": "Monday", "subject": "Mathematics", "topic": "Algebra", "duration_minutes": 120, "activities": ["study", "practice"]}
            ]
        }
    ],
    "revision_strategy": "how to revise",
    "exam_preparation_tips": ["tip1", "tip2"]
}"""
        
        user_prompt = f"""Create a study plan:
- Subjects: {', '.join(subjects)}
- Hours per day: {hours_per_day}
- Days per week: {days_per_week}
- Weeks until exam: {weeks_until_exam}
- Weak areas: {', '.join(weak_areas) if weak_areas else 'None specified'}

Focus more time on weak areas."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            raise ValueError(f"AI service error: {str(e)}")
    
    def simplify_explanation(self, original_explanation: str, topic: str) -> str:
        """
        Simplify an explanation (for "Explain Again in Simpler Way" button)
        
        Args:
            original_explanation: The original explanation
            topic: The topic being explained
            
        Returns:
            Simplified explanation
        """
        system_prompt = """You are a tutor who can explain complex concepts in the simplest way possible.
Use everyday language, analogies, and examples that Nigerian students can relate to.

IMPORTANT - Math/Formula Formatting:
- Use LaTeX syntax for ALL mathematical expressions, equations, formulas, and chemical formulas
- Inline math: Use $...$ for formulas within text (e.g., $E = mc^2$, $H_2SO_4$, $v = u + at$)
- Block math: Use $$...$$ for displayed equations
- Always format formulas, equations, and chemical equations using LaTeX

IMPORTANT - Table Formatting:
- Use markdown table format for ALL tables, comparison charts, data sets, and structured information
- Format: | Header 1 | Header 2 |
          |----------|----------|
          | Row 1 Col 1 | Row 1 Col 2 |
- You can use LaTeX math ($...$) inside table cells"""
        
        user_prompt = f"""Simplify this explanation about {topic}:

{original_explanation}

Make it much simpler, use analogies, and relate to everyday life."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9
            )
            
            return response.choices[0].message.content
        except Exception as e:
            raise ValueError(f"AI service error: {str(e)}")


# Singleton instance
ai_service = AIService()
