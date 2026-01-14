"""
Past Questions PDF Processing Service
Uses GPT-4o-mini Vision to extract questions and answers from PDF pages
"""
from openai import OpenAI
from app.core.config import settings
from typing import List, Dict, Optional
import json
import base64
import io
import os

try:
    from pdf2image import convert_from_path
    from PIL import Image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not installed. PDF processing will not work.")


class PastQuestionProcessor:
    """Service for extracting past questions from PDF files"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Using vision model
    
    def process_pdf(self, pdf_path: str, exam_type: str, subject: str, year: str) -> List[Dict]:
        """
        Process a PDF file and extract all questions
        
        Args:
            pdf_path: Path to the PDF file
            exam_type: "JAMB", "WAEC", "NECO"
            subject: Subject name
            year: Year of the exam
            
        Returns:
            List of question dictionaries
        """
        if not PDF2IMAGE_AVAILABLE:
            raise ValueError("pdf2image is not installed. Please install it with: pip install pdf2image")
        
        # Convert PDF to images (one per page)
        try:
            images = convert_from_path(pdf_path)
        except Exception as e:
            raise ValueError(f"Error converting PDF to images: {str(e)}. Make sure poppler is installed.")
        
        all_questions = []
        
        for page_num, image in enumerate(images, 1):
            # Convert PIL image to base64
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Extract questions from this page
            questions = self._extract_questions_from_image(
                img_base64, 
                page_num, 
                exam_type, 
                subject, 
                year
            )
            all_questions.extend(questions)
        
        return all_questions
    
    def _extract_questions_from_image(
        self, 
        image_base64: str, 
        page_num: int,
        exam_type: str,
        subject: str,
        year: str
    ) -> List[Dict]:
        """
        Extract questions from a single PDF page image
        """
        system_prompt = f"""You are an expert at extracting exam questions from PDF pages.

You are processing a {exam_type} {subject} past question paper from {year}.

Your task:
1. Identify all questions on this page
2. For each question, extract:
   - The question number
   - The complete question text
   - All options (A, B, C, D, and sometimes E)
   - The correct answer (look for checkmarks, ticks, or marked answers)
   - The topic/subject area if identifiable, otherwise create a new topic based on the question text

IMPORTANT:
- Questions may span multiple lines
- Options are typically labeled A, B, C, D (sometimes E)
- The correct answer may be marked with a tick (✓), checkmark, or highlighted (if not, choose the option that is most likely to be correct)
- Some questions may have diagrams or images - describe them in text
- Preserve all mathematical notation and formulas exactly as shown
- If you see answers at the end of the page or document, use those to identify correct answers

Return a JSON object with a "questions" array in this format:
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "Full question text here...",
      "options": {{"A": "option A text", "B": "option B text", "C": "option C text", "D": "option D text"}},
      "correct_answer": "A",
      "topic": "Topic name if identifiable, otherwise create a new topic based on the question text"
    }},
    ...
  ]
}}

IMPORTANT:
- If you cannot find the correct answer for a question, set "correct_answer" to the option that is most likely to be correct
- Only include questions where you can extract the question text and at least 2 options
- If no questions found on this page, return {{"questions": []}}."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": f"Extract all questions from this page (page {page_num})."
                            }
                        ]
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Low temperature for accuracy
            )
            
            result = json.loads(response.choices[0].message.content)
            questions = result.get("questions", [])
            
            # Add metadata to each question
            for q in questions:
                q["page_number"] = page_num
                q["source_pdf"] = f"{exam_type}_{subject}_{year}.pdf"
            
            return questions
            
        except Exception as e:
            print(f"Error processing page {page_num}: {str(e)}")
            return []


# Singleton instance
pq_processor = PastQuestionProcessor()
