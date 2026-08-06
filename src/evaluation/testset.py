from __future__ import annotations

from typing import Any

import pandas as pd


from core.utils import write_json

def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe."""
    if len(df) < 3:
        raise ValueError(f"Cleaned dataframe has too few records ({len(df)}) to build a test set (minimum required is 3).")

    # Select representative papers (e.g. up to 6 papers to have 24 questions)
    num_papers = min(len(df), 6)
    selected_papers = df.iloc[:num_papers]

    test_set: list[dict[str, Any]] = []
    question_counter = 0

    for _, row in selected_papers.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]

        # 1. Summary question
        if row.get("summary"):
            question_counter += 1
            test_set.append({
                "id": f"q_{question_counter:03d}",
                "question_type": "summary",
                "question": f"What is the summary of the paper '{title}'?",
                "ground_truth": row["summary"],
                "ground_truth_doc_ids": [paper_id]
            })

        # 2. Authors question
        if row.get("authors_joined"):
            question_counter += 1
            test_set.append({
                "id": f"q_{question_counter:03d}",
                "question_type": "authors",
                "question": f"Who are the authors of the paper '{title}'?",
                "ground_truth": row["authors_joined"],
                "ground_truth_doc_ids": [paper_id]
            })

        # 3. Date question
        if row.get("published"):
            question_counter += 1
            test_set.append({
                "id": f"q_{question_counter:03d}",
                "question_type": "date",
                "question": f"What is the publication date of the paper '{title}'?",
                "ground_truth": row["published"],
                "ground_truth_doc_ids": [paper_id]
            })

        # 4. Categories question
        if row.get("categories_joined"):
            question_counter += 1
            test_set.append({
                "id": f"q_{question_counter:03d}",
                "question_type": "categories",
                "question": f"What are the categories of the paper '{title}'?",
                "ground_truth": row["categories_joined"],
                "ground_truth_doc_ids": [paper_id]
            })

    write_json(output_path, test_set)
    return test_set

