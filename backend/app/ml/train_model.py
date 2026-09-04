"""
Advanced Section 3 — AI / NLP Engine Intent Classifier.
Trains an ensemble model using TF-IDF (Word & Character n-grams) 
with Logistic Regression and Linear SVC, persisted via joblib.

Run:  python -m app.ml.train_model
"""
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import VotingClassifier
from sklearn.pipeline import FeatureUnion, Pipeline

from app.ml.dataset import build_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")


def train():
    texts, labels = build_dataset()

    # Advanced Feature Extraction: Combine Word n-grams and Character n-grams
    # Character n-grams help catch typos, obfuscated phrases, and keyword variations.
    feature_union = FeatureUnion([
        ("word_tfidf", TfidfVectorizer(
            analyzer="word",
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 3),
            min_df=1,
            sublinear_tf=True
        )),
        ("char_tfidf", TfidfVectorizer(
            analyzer="char_wb",
            lowercase=True,
            ngram_range=(2, 5),
            min_df=2,
            sublinear_tf=True
        ))
    ])

    # Ensemble Classifier combining Logistic Regression and Linear SVC for high-precision intent classification
    ensemble_clf = VotingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=2000, class_weight="balanced", C=2.0)),
            ("svc", LinearSVC(class_weight="balanced", C=1.0, max_iter=2000))
        ],
        voting="hard"
    )

    pipeline = Pipeline([
        ("features", feature_union),
        ("clf", ensemble_clf),
    ])

    print(f"Training advanced ensemble NLP model on {len(texts)} samples...")
    pipeline.fit(texts, labels)
    
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Advanced model successfully trained and saved to {MODEL_PATH}")
    return pipeline


if __name__ == "__main__":
    train()