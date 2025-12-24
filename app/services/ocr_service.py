"""
OCR Service (DEPRECATED)

NOTE: This service is no longer used. The application now uses GPT-4o-mini's 
vision capabilities to directly analyze images, which provides better accuracy
and understanding of mathematical equations, diagrams, and context.

See: app/services/ai_service.py - solve_question_with_image()

Kept for reference/fallback purposes only.
"""

# OCR Service is deprecated - using GPT-4o-mini Vision instead
# The vision model can understand:
# - Mathematical equations and formulas
# - Diagrams and graphs
# - Handwritten text
# - Complex problem layouts
# 
# This provides better results than traditional OCR for educational content.

ocr_service = None  # Deprecated - not used
