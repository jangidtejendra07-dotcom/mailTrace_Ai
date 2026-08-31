"""
Trains the TF-IDF + Logistic Regression intent classifier described in
Section 3 (AI / NLP Engine) of the spec, and persists it with joblib.

Run:  python -m app.ml.train_model
"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.ml.dataset import build_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")


def train():
    texts, labels = build_dataset()

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            multi_class="auto",
        )),
    ])

    pipeline.fit(texts, labels)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Model trained on {len(texts)} samples and saved to {MODEL_PATH}")
    return pipeline


if __name__ == "__main__":
    train()
