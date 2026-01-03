import time
import numpy as np
from biometrics import BiometricsEngine

def mock_keystroke_sequence(phrase, dwell_mean=0.1, flight_mean=0.15, noise=0.01):
    """Generates a list of (char, 'down'/'up', timestamp) for a phrase."""
    events = []
    current_time = time.time()
    
    for i, char in enumerate(phrase):
        # Down
        events.append((char, 'down', current_time))
        # Dwell
        dwell = max(0.01, np.random.normal(dwell_mean, noise))
        release_time = current_time + dwell
        events.append((char, 'up', release_time))
        
        # Flight to next
        if i < len(phrase) - 1:
            flight = max(0.01, np.random.normal(flight_mean, noise))
            current_time = release_time + flight
        
    return events

def test_pipeline():
    print("--- Starting Simulation Test ---")
    bio = BiometricsEngine()
    passphrase = "The quick brown fox jumps over the lazy dog"
    
    # 1. Feature Extraction Robustness
    print("Testing Feature Extraction...")
    clean_events = mock_keystroke_sequence(passphrase)
    feats = bio.extract_features(clean_events)
    assert feats is not None, "Clean extraction failed"
    print(f"Clean Features Size: {len(feats)}")
    
    # Test Backspace Rejection
    dirty_events = list(clean_events)
    dirty_events.insert(5, ("Key.backspace", 'down', time.time()))
    feats_dirty = bio.extract_features(dirty_events)
    assert feats_dirty is None, "Backspace rejection failed"
    print("Backspace rejection confirmed.")
    
    # 2. Collect Training Data
    print("Collecting training data...")
    features_list = []
    for _ in range(10):
        # User is consistent
        ev = mock_keystroke_sequence(passphrase, dwell_mean=0.1, flight_mean=0.15, noise=0.005)
        features_list.append(bio.extract_features(ev))

    # 3. Train
    print("Testing Training...")
    try:
        std, mean, thresh = bio.train_model(features_list)
        print(f"Training Complete. Threshold: {thresh}")
    except Exception as e:
        print(f"Training Failed: {e}")
        return

    # 4. Authenticate
    print("Testing Verification...")
    
    # Good Attempt
    good_ev = mock_keystroke_sequence(passphrase, dwell_mean=0.1, flight_mean=0.15, noise=0.01)
    good_feat = bio.extract_features(good_ev)
    success, dist, score = bio.authenticate(good_feat, mean, std, thresh)
    print(f"Good Attempt: Success={success}, Score={score:.2f} (Dist={dist:.4f})")
    assert success, "Good attempt failed verification"
    
    # Bad Attempt (Clumsy)
    bad_ev = mock_keystroke_sequence(passphrase, dwell_mean=0.2, flight_mean=0.3, noise=0.01)
    bad_feat = bio.extract_features(bad_ev)
    success, dist, score = bio.authenticate(bad_feat, mean, std, thresh)
    print(f"Bad Attempt (Clumsy): Success={success}, Score={score:.2f} (Dist={dist:.4f})")
    assert not success, "Bad attempt passed verification"
    
    # Close Impostor
    close_ev = mock_keystroke_sequence(passphrase, dwell_mean=0.12, flight_mean=0.18, noise=0.005)
    close_feat = bio.extract_features(close_ev)
    success, dist, score = bio.authenticate(close_feat, mean, std, thresh)
    print(f"Close Impostor (20% diff): Success={success}, Score={score:.2f} (Dist={dist:.4f})")
    
    # We expect this to fail (Success=False) if the model is good.
    # Dist should be > Threshold (~85)
    
    print("--- Simulation Test Passed ---")

if __name__ == "__main__":
    test_pipeline()
