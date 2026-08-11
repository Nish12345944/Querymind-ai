import json
import time
from pathlib import Path

import requests

from evaluation_db import execute_sql
from result_normalizer import normalize_rows


# ============================================================
# Configuration
# ============================================================

API_URL = "http://127.0.0.1:8000/query/"

REQUEST_TIMEOUT = 90

BASE_DIR = Path(__file__).resolve().parent

QUESTIONS_FILE = BASE_DIR / "questions.json"
GROUND_TRUTH_FILE = BASE_DIR / "ground_truth.json"


# ============================================================
# Load datasets
# ============================================================

with open(
    QUESTIONS_FILE,
    "r",
    encoding="utf-8"
) as file:
    questions = json.load(file)


with open(
    GROUND_TRUTH_FILE,
    "r",
    encoding="utf-8"
) as file:
    ground_truth = json.load(file)


ground_truth_map = {
    item["id"]: item["sql"]
    for item in ground_truth
}


# ============================================================
# Metrics
# ============================================================

total = len(questions)

correct = 0

sql_expected = 0
sql_behavior_correct = 0
sql_execution_correct = 0

clarification_expected = 0
clarification_correct = 0

unsupported_expected = 0
unsupported_correct = 0


# ============================================================
# Helper functions
# ============================================================

def compare_results(
    actual_rows,
    expected_rows
):
    actual = normalize_rows(
        actual_rows
    )

    expected = normalize_rows(
        expected_rows
    )

    return actual == expected


def call_api(question):
    """
    Call QueryMind with retry logic.

    Retries transient connection/time-out errors.
    """

    last_error = None

    for attempt in range(1, 4):

        try:

            response = requests.post(
                API_URL,
                json={
                    "question": question
                },
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            return response.json()

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ) as exc:

            last_error = exc

            print(
                f"  Request attempt "
                f"{attempt}/3 failed: {exc}"
            )

            if attempt < 3:

                time.sleep(2)

    raise last_error


# ============================================================
# Evaluation
# ============================================================

print()
print("=" * 75)
print("QueryMind AI Evaluation")
print("=" * 75)
print()


for item in questions:

    question_id = item["id"]

    question = item["question"]

    expected_behavior = item["expected_behavior"]

    print(
        f"[{question_id}] {question}"
    )

    # --------------------------------------------------------
    # Call QueryMind
    # --------------------------------------------------------

    try:

        result = call_api(
            question
        )

    except Exception as exc:

        print(
            f"  API ERROR: {exc}"
        )

        print()

        continue

    actual_status = result.get(
        "status"
    )

    # ========================================================
    # SQL expected
    # ========================================================

    if expected_behavior == "sql":

        sql_expected += 1

        # ----------------------------------------------------
        # Check behavior
        # ----------------------------------------------------

        if actual_status != "query_executed":

            print(
                "  Behavior: FAIL"
            )

            print(
                "  Expected: query_executed"
            )

            print(
                f"  Actual:   {actual_status}"
            )

            if result.get("reason"):

                print(
                    f"  Reason:   "
                    f"{result.get('reason')}"
                )

            print()

            continue

        sql_behavior_correct += 1

        # ----------------------------------------------------
        # Ground truth
        # ----------------------------------------------------

        expected_sql = ground_truth_map.get(
            question_id
        )

        if expected_sql is None:

            print(
                "  Behavior: PASS"
            )

            print(
                "  Execution: NOT CHECKED"
            )

            print()

            continue

        # ----------------------------------------------------
        # Execute ground truth
        # ----------------------------------------------------

        try:

            expected_rows = execute_sql(
                expected_sql
            )

        except Exception as exc:

            print(
                f"  Ground-truth ERROR: {exc}"
            )

            print()

            continue

        # ----------------------------------------------------
        # Actual rows
        # ----------------------------------------------------

        actual_rows = result.get(
            "rows",
            []
        )

        # ----------------------------------------------------
        # Compare
        # ----------------------------------------------------

        if compare_results(
            actual_rows,
            expected_rows
        ):

            sql_execution_correct += 1

            correct += 1

            print(
                "  Behavior: PASS"
            )

            print(
                "  Execution: PASS"
            )

        else:

            print(
                "  Behavior: PASS"
            )

            print(
                "  Execution: FAIL"
            )

            print(
                f"  Expected rows: "
                f"{len(expected_rows)}"
            )

            print(
                f"  Actual rows:   "
                f"{len(actual_rows)}"
            )

            # ------------------------------------------------
            # Debug information
            # ------------------------------------------------

            print()

            print(
                "--- Expected normalized rows ---"
            )

            print(
                normalize_rows(
                    expected_rows
                )
            )

            print()

            print(
                "--- Actual normalized rows ---"
            )

            print(
                normalize_rows(
                    actual_rows
                )
            )

            print()

            print(
                "--- Generated SQL ---"
            )

            print(
                result.get(
                    "sql",
                    "N/A"
                )
            )

    # ========================================================
    # Clarification expected
    # ========================================================

    elif expected_behavior == "clarification":

        clarification_expected += 1

        if actual_status == "clarification_required":

            clarification_correct += 1

            correct += 1

            print(
                "  Clarification: PASS"
            )

        else:

            print(
                "  Clarification: FAIL"
            )

            print(
                f"  Actual status: "
                f"{actual_status}"
            )

            if result.get("reason"):

                print(
                    f"  Reason: "
                    f"{result.get('reason')}"
                )

    # ========================================================
    # Unsupported expected
    # ========================================================

    elif expected_behavior == "unsupported":

        unsupported_expected += 1

        if actual_status in (
            "sql_rejected",
            "execution_failed",
            "unsupported"
        ):

            unsupported_correct += 1

            correct += 1

            print(
                "  Unsupported: PASS"
            )

        else:

            print(
                "  Unsupported: FAIL"
            )

            print(
                f"  Actual status: "
                f"{actual_status}"
            )

    print()


# ============================================================
# Metrics
# ============================================================

overall_accuracy = (
    correct / total * 100
    if total
    else 0
)


sql_behavior_accuracy = (
    sql_behavior_correct
    / sql_expected
    * 100
    if sql_expected
    else 0
)


sql_execution_accuracy = (
    sql_execution_correct
    / sql_expected
    * 100
    if sql_expected
    else 0
)


clarification_accuracy = (
    clarification_correct
    / clarification_expected
    * 100
    if clarification_expected
    else 0
)


unsupported_accuracy = (
    unsupported_correct
    / unsupported_expected
    * 100
    if unsupported_expected
    else 0
)


# ============================================================
# Final report
# ============================================================

print("=" * 75)
print("Evaluation Results")
print("=" * 75)
print()

print(
    f"Total test cases:          {total}"
)

print(
    f"Overall accuracy:          "
    f"{overall_accuracy:.2f}%"
)

print(
    f"SQL behavior accuracy:     "
    f"{sql_behavior_accuracy:.2f}%"
)

print(
    f"SQL execution accuracy:    "
    f"{sql_execution_accuracy:.2f}%"
)

print(
    f"Clarification accuracy:    "
    f"{clarification_accuracy:.2f}%"
)

print(
    f"Unsupported detection:     "
    f"{unsupported_accuracy:.2f}%"
)

print()

print("=" * 75)