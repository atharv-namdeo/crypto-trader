"""
Self-training loop — retrain a RandomForest model on historical trade outcomes
stored in Firestore, then save the model for use by the signal engine.
"""
import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from utils.firebase_client import db


def fetch_trade_history():
    """Pull all completed trades from Firestore."""
    if db is None:
        print("[Retrain] Firebase not initialised — cannot fetch trades.")
        return []
    trades = db.collection('trades').stream()
    return [t.to_dict() for t in trades]


def build_features(trades):
    """
    Build feature matrix X and label vector y from trade history.
    Label: 1 if trade was profitable, 0 otherwise.
    """
    X, y = [], []
    for t in trades:
        try:
            rsi = float(t.get('rsi', 50))
            atr = float(t.get('atr', 0))
            entry = float(t.get('entry', 0))
            sl = float(t.get('sl', 0))
            tp = float(t.get('tp', 0))
            direction = 1 if t.get('direction') == 'LONG' else 0

            # Feature vector
            X.append([rsi, atr, abs(entry - sl), abs(tp - entry), direction])

            # Label (profit if TP was hit, simplified heuristic)
            pnl = t.get('pnl', None)
            if pnl is not None:
                y.append(1 if float(pnl) > 0 else 0)
            else:
                y.append(1)  # default if PnL not recorded yet
        except (ValueError, TypeError):
            continue

    return np.array(X), np.array(y)


def retrain():
    """Fetch trades, build features, train model, save to disk."""
    trades = fetch_trade_history()
    if len(trades) < 50:
        print(f"[Retrain] Only {len(trades)} trades — need at least 50 to retrain.")
        return

    X, y = build_features(trades)
    if len(X) < 50:
        print("[Retrain] Not enough valid feature rows after parsing.")
        return

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    print(f"[Retrain] Train accuracy: {train_acc:.2%}  |  Test accuracy: {test_acc:.2%}")

    model_path = 'ml/model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    print(f"[Retrain] Model saved to {model_path}")


if __name__ == "__main__":
    retrain()
