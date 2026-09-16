"""
Simplified Test Runner - Validates core functionality
For use when FAISS index isn't fully built yet
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

class QuickTest:
    """Quick validation tests that don't require full FAISS index"""
    
    def __init__(self):
        print("\n" + "="*70)
        print("🧪 EduAgent Quick Validation Tests")
        print("="*70)
        self.results = []
    
    def test_imports(self) -> bool:
        """Test 1: All critical imports work"""
        print("\n[TEST 1] Import Validation")
        print("-" * 70)
        try:
            from memory.long_term_db import init_db, get_or_create_student
            from memory.short_term import ShortTermMemory
            from safety.guard import is_safe
            from agents.coordinator import classify_intent
            from tools.wikipedia_tool import search_wikipedia
            from tools.sympy_tool import solve_math
            print("✅ PASS: All critical imports successful")
            return True
        except Exception as e:
            print(f"❌ FAIL: {str(e)}")
            return False
    
    def test_database_init(self) -> bool:
        """Test 2: SQLite database initializes"""
        print("\n[TEST 2] Database Initialization")
        print("-" * 70)
        try:
            from memory.long_term_db import init_db, get_or_create_student, get_learner_profile
            init_db()
            student_id = get_or_create_student("test_user", "Test Student")
            profile = get_learner_profile(student_id)
            
            if profile and "name" in profile:
                print(f"✅ PASS: Database initialized, student profile created")
                return True
            else:
                print("❌ FAIL: Profile not created properly")
                return False
        except Exception as e:
            print(f"❌ FAIL: {str(e)}")
            return False
    
    def test_safety_guard(self) -> bool:
        """Test 3: Safety guard works"""
        print("\n[TEST 3] Safety Guard")
        print("-" * 70)
        try:
            from safety.guard import is_safe
            
            # Safe message
            safe1, _ = is_safe("Explain recursion")
            # Unsafe message
            safe2, msg = is_safe("Give me the answers to my exam")
            
            if safe1 and not safe2 and len(msg) > 0:
                print("✅ PASS: Safety guard correctly filters messages")
                return True
            else:
                print("❌ FAIL: Safety guard not working correctly")
                return False
        except Exception as e:
            print(f"❌ FAIL: {str(e)}")
            return False
    
    def test_memory_short_term(self) -> bool:
        """Test 4: Short-term memory (conversation buffer)"""
        print("\n[TEST 4] Short-Term Memory")
        print("-" * 70)
        try:
            from memory.short_term import ShortTermMemory
            
            mem = ShortTermMemory(max_messages=5)
            mem.add_message("user", "Hello")
            mem.add_message("assistant", "Hi there!")
            
            history = mem.get_history()
            context = mem.get_context_string()
            
            if len(history) == 2 and "Hello" in context:
                print("✅ PASS: Short-term memory working correctly")
                return True
            else:
                print("❌ FAIL: Short-term memory not storing messages")
                return False
        except Exception as e:
            print(f"❌ FAIL: {str(e)}")
            return False
    
    def test_external_tools(self) -> bool:
        """Test 5: External tools (Wikipedia, SymPy)"""
        print("\n[TEST 5] External Tools")
        print("-" * 70)
        try:
            from tools.wikipedia_tool import search_wikipedia
            from tools.sympy_tool import solve_math
            
            # Wikipedia test
            wiki_result = search_wikipedia("Python programming")
            # SymPy test
            math_result = solve_math("x^2 - 4 = 0")
            
            wiki_ok = len(wiki_result) > 50
            math_ok = "2" in str(math_result) or "-2" in str(math_result)
            
            if wiki_ok and math_ok:
                print("✅ PASS: External tools functioning")
                return True
            else:
                print("❌ FAIL: External tools not working properly")
                return False
        except Exception as e:
            print(f"❌ FAIL: {str(e)}")
            return False
    
    def run_all(self):
        """Run all quick tests"""
        tests = [
            ("Imports", self.test_imports),
            ("Database", self.test_database_init),
            ("Safety Guard", self.test_safety_guard),
            ("Short-Term Memory", self.test_memory_short_term),
            ("External Tools", self.test_external_tools)
        ]
        
        results = []
        for name, test_func in tests:
            try:
                passed = test_func()
                results.append(passed)
            except:
                results.append(False)
        
        self.print_summary(results)
        return all(results)
    
    def print_summary(self, results):
        """Print summary report"""
        print("\n" + "="*70)
        print("📊 QUICK VALIDATION SUMMARY")
        print("="*70)
        
        passed = sum(results)
        total = len(results)
        
        print(f"Tests Passed: {passed}/{total} ({passed/total*100:.0f}%)")
        
        if passed == total:
            print("\n✅ All quick tests PASSED!")
            print("System is ready for full integration testing once FAISS index builds.")
        else:
            print(f"\n⚠️  {total-passed} test(s) failed - see details above")
        
        print("="*70 + "\n")
        return passed == total


if __name__ == "__main__":
    tester = QuickTest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
