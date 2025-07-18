#!/usr/bin/env python3
"""
Test script for the new Gemini-based animation detector
"""

import os
import logging
from dotenv import load_dotenv
from animation_detector import is_animated

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_animation_detector():
    """Test the animation detector with sample videos"""
    
    # Check if Gemini API key is available
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY environment variable not set")
        logger.info("Please set your Gemini API key: export GEMINI_API_KEY='your-key-here'")
        return False
    
    # Test videos - mix of animated and live-action
    test_videos = [
        {
            "url": "https://www.youtube.com/watch?v=hwiyUuYZLHE",
            "expected": "animated",
            "description": "Expected animated video"
        },
        {
            "url": "https://www.youtube.com/watch?v=RtU8nBnpFVE", 
            "expected": "live-action",
            "description": "Expected live-action video"
        },
        {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "expected": "live-action", 
            "description": "Rick Astley - Never Gonna Give You Up (live-action)"
        }
    ]
    
    logger.info("🎬 Testing Gemini-based Animation Detector")
    logger.info("=" * 60)
    
    results = []
    
    for i, test_case in enumerate(test_videos, 1):
        logger.info(f"\n📹 Test {i}/3: {test_case['description']}")
        logger.info(f"URL: {test_case['url']}")
        logger.info(f"Expected: {test_case['expected']}")
        
        try:
            # Test the animation detector
            is_animated_result = is_animated(test_case['url'])
            
            # Interpret result
            detected = "animated" if is_animated_result else "live-action"
            is_correct = detected == test_case['expected']
            
            result_emoji = "✅" if is_correct else "❌"
            logger.info(f"Detected: {detected}")
            logger.info(f"Result: {result_emoji} {'CORRECT' if is_correct else 'INCORRECT'}")
            
            results.append({
                "test": i,
                "url": test_case['url'],
                "expected": test_case['expected'],
                "detected": detected,
                "correct": is_correct
            })
            
        except Exception as e:
            logger.error(f"❌ Test {i} failed with error: {str(e)}")
            results.append({
                "test": i,
                "url": test_case['url'],
                "expected": test_case['expected'],
                "detected": "error",
                "correct": False,
                "error": str(e)
            })
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("📊 Test Summary")
    logger.info("=" * 60)
    
    correct_count = sum(1 for r in results if r['correct'])
    total_count = len(results)
    
    for result in results:
        status = "✅ PASS" if result['correct'] else "❌ FAIL"
        logger.info(f"Test {result['test']}: {status} - Expected: {result['expected']}, Got: {result['detected']}")
    
    logger.info(f"\nOverall: {correct_count}/{total_count} tests passed")
    
    if correct_count == total_count:
        logger.info("🎉 All tests passed! Animation detector is working correctly.")
        return True
    else:
        logger.warning(f"⚠️ {total_count - correct_count} tests failed. Check the results above.")
        return False

if __name__ == "__main__":
    success = test_animation_detector()
    exit(0 if success else 1) 