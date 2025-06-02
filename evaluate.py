import unittest
from qa_chain import answer_query, clear_cache_and_memory
from datetime import datetime
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test set
TEST_QUESTIONS = [
    {
        "question": "What is TaskTracker?",
        "expected_answer": "TaskTracker is a lightweight task and time management tool designed for developers to organize and track their work."
    },
    {
        "question": "What is the current version of TaskTracker?",
        "expected_answer": "The current version of TaskTracker is 1.2.3."
    },
    {
        "question": "When did the TaskTracker project start and when is it expected to end?",
        "expected_answer": "The project started on February 1, 2025, and is expected to end on October 31, 2025."
    },
    {
        "question": "Who are the authors of TaskTracker and what are their roles?",
        "expected_answer": "The authors are Jane Doe, the Lead Developer, and John Smith, the UI/UX Designer."
    },
    {
        "question": "What are the main dependencies used by TaskTracker?",
        "expected_answer": "TaskTracker depends on React version 18.2.0, Node.js version 20.0.0, and MongoDB version 6.0."
    },
    {
        "question": "What does the Authentication module do in TaskTracker?",
        "expected_answer": "The Authentication module handles user registration, login, and session management."
    },
    {
        "question": "What functionality does the TaskManagement module provide?",
        "expected_answer": "The TaskManagement module contains the core logic for creating, updating, and tracking tasks."
    },
    {
        "question": "What kind of reports does the Reporting module generate?",
        "expected_answer": "The Reporting module generates weekly and monthly productivity reports."
    },
    {
        "question": "How can you build and run the TaskTracker project?",
        "expected_answer": "To build and run TaskTracker, clone the repository, run 'npm install' to install dependencies, use 'npm start' to launch the development server, and 'npm run build' for production builds."
    },
    {
        "question": "What new features were added in version 1.2.3 of TaskTracker?",
        "expected_answer": "Version 1.2.3 added real-time sync for tasks across devices and improved report generation speed by 40%. It also fixed the login issue on Safari browsers."
    },
    {
        "question": "What are ",
        "expected_answer": "Version 1.2.3 added real-time sync for tasks across devices and improved report generation speed by 40%. It also fixed the login issue on Safari browsers."
    },
]


class TestHelpdeskBotIntegration(unittest.TestCase):
    def setUp(self):
        self.user_id = "test_user"
        self.doc_id = "tasktracker_v1"
        clear_cache_and_memory()
        self.results = []

    def test_actual_llm_chain_answers(self):
        for i, test_case in enumerate(TEST_QUESTIONS, 1):
            question = test_case["question"]
            expected = test_case["expected_answer"]

            # Call the real logic
            actual, status = answer_query(
                query=question,
                user_id=self.user_id,
                doc_id=self.doc_id
            )

            passed = expected.lower() in actual.lower()

            self.results.append({
                "test_case": f"Question {i}",
                "question": question,
                "expected": expected,
                "actual": actual,
                "status": status,
                "passed": passed
            })

    def tearDown(self):
        print("\nTest Results:")
        print("| Test Case | Question | Expected | Actual | Status | Passed |")
        print("|-----------|----------|----------|--------|--------|--------|")
        for result in self.results:
            passed = "✅" if result["passed"] else "❌"
            print(f"| {result['test_case']} | {result['question'][:30]} | {result['expected'][:30]} | {result['actual'][:30]} | {result['status']} | {passed} |")

        try:
            df = pd.DataFrame(self.results)
            df.columns = ["Test Case", "Question", "Expected", "Actual", "Status", "Passed"]
            df["Passed"] = df["Passed"].apply(lambda x: "Pass" if x else "Fail")
            df.to_excel("test_results_actual_llm.xlsx", index=False)
            logger.info("Test results saved to test_results_actual_llm.xlsx")
        except Exception as e:
            logger.error(f"Failed to save results to Excel: {e}")

if __name__ == "__main__":
    unittest.main()
