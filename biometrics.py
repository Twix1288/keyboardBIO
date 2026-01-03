import numpy as np
from scipy.linalg import fractional_matrix_power

class BiometricsEngine:
    def __init__(self):
        pass

    def extract_features(self, key_events):
        """
        Extracts Dwell Times and Flight Times.
        Handles key rollover (overlapping keystrokes) correctly.
        """
        # 1. Validation for Bad Keys
        for char, event, ts in key_events:
            if char == "Key.backspace" or char is None:
                return None
        
        # 2. Group events into Keystrokes (Down + Up pair)
        # We assume the user intends the order defined by the KeyDown events.
        
        # Sort all events by time
        sorted_events = sorted(key_events, key=lambda x: x[2])
        
        # Temporary registry for pending Down events: {char: timestamp}
        # Note: If a char is typed twice (e.g. 'o' in good), we need to handle the instance.
        # But 'key_events' is just a stream.
        # Since we just want to pair safely, we can pop from a list of downs for that char.
        
        from collections import defaultdict
        pending_downs = defaultdict(list)
        
        keystrokes = [] # List of dict: {'char': c, 'down': t, 'up': t}
        
        for char, event_type, timestamp in sorted_events:
            if event_type == 'down':
                pending_downs[char].append(timestamp)
                # Placeholder in keystrokes list?
                # No, we can't create the Keystroke obj yet because we don't know the up time.
                # But we know the ORDER is determined by Down time.
                # So we can just collect all complete keystrokes later?
                # No, to calculate Flight, we need the sequence N, N+1.
                # The sequence is defined by Down times.
                
            elif event_type == 'up':
                if pending_downs[char]:
                    # Match with the earliest unmatched down for this char
                    down_ts = pending_downs[char].pop(0)
                    keystrokes.append({'char': char, 'down': down_ts, 'up': timestamp})
        
        # Now we sort the complete keystrokes by their DOWN timestamp to establish N, N+1 sequence
        keystrokes.sort(key=lambda x: x['down'])
        
        # 3. Validation: Did we capture enough valid keystrokes?
        # If we have dangling downs or ups, they are ignored.
        if not keystrokes:
            return None
            
        dwell_times = []
        flight_times = []
        
        for i in range(len(keystrokes)):
            current = keystrokes[i]
            
            # Dwell
            dwell = current['up'] - current['down']
            dwell_times.append(dwell)
            
            # Flight (to next key)
            if i < len(keystrokes) - 1:
                next_key = keystrokes[i+1]
                # Flight: Down(N+1) - Up(N)
                flight = next_key['down'] - current['up']
                
                # Outlier check for pauses (e.g. > 2.0s)
                # Note: Negative flight is VALID (rollover).
                if flight > 2.0:
                    return None 
                    
                flight_times.append(flight)
        
        return np.array(dwell_times + flight_times)

    def train_model(self, sample_vectors):
        """
        Computes robust Mean and Standard Deviation vectors.
        Includes Outlier Removal to ensure the best possible model.
        """
        X = np.array(sample_vectors)
        
        # 1. Outlier Removal (The "Smart" Cleaning)
        # We calculate a temporary median vector (robust center)
        median_vec = np.median(X, axis=0)
        
        # Calculate Manhattan distance of each sample to the median
        distances = np.sum(np.abs(X - median_vec), axis=1)
        
        # Filter out the worst 20% of samples (e.g. 2 out of 10) if they are far off
        # This removes "bad typing" from the training set.
        cutoff = np.percentile(distances, 80)
        clean_X = X[distances <= cutoff]
        
        # Fallback if too many removed (shouldn't happen with percentile)
        if len(clean_X) < 5:
            clean_X = X
            
        # 2. Compute Parameters on CLEAN data
        mean_vector = np.mean(clean_X, axis=0)
        
        # Standard Deviation (Scaling Factor)
        std_vector = np.std(clean_X, axis=0)
        
        # Enforce Minimum Variance (The "Best Math" Fix for Overfitting)
        # We assume human variance is at least 10% of the duration.
        # This prevents the denominator from being too small, which would explode the distance.
        min_std = mean_vector * 0.10
        std_vector = np.maximum(std_vector, min_std)
        
        # 3. Threshold Calculation
        # Calculate self-distance (Validation)
        scores = []
        for x in clean_X:
            # Scaled Manhattan: sum( |x - mean| / std )
            dist = np.sum(np.abs(x - mean_vector) / std_vector)
            scores.append(dist)
            
        mu_dist = np.mean(scores)
        sigma_dist = np.std(scores)
        
        # Threshold: Mean + 6.0*Std
        calculated_threshold = mu_dist + 6.0 * sigma_dist
        
        # Enforce Theoretical Lower Bound (Chi-Square Expected Value)
        # Expected distance for D degrees of freedom is D.
        # We shouldn't demand better than random chance variation (1 sigma).
        min_threshold = len(mean_vector) # ~85
        
        threshold = max(calculated_threshold, min_threshold)
        
        return std_vector, mean_vector, threshold

    def authenticate(self, attempt_vector, mean_vector, std_vector, threshold):
        """
        Verifies a user attempt using Scaled Manhattan Distance.
        """
        # 1. Calculate Distance
        # Vectorized operation: |x - u| / sigma
        diff = np.abs(attempt_vector - mean_vector)
        scaled_diff = diff / std_vector
        distance = np.sum(scaled_diff)
        
        is_authenticated = distance <= threshold
        
        # Score Calculation
        # Distance = 0 -> 100%
        # Distance = Threshold -> 70%
        # Distance = 2*Threshold -> 0%
        
        if distance <= threshold:
            ratio = distance / threshold
            score = 100 - (30 * ratio)
        else:
            ratio = (distance - threshold) / threshold
            score = 70 - (70 * ratio)
            
        return is_authenticated, distance, max(0, score)

    def adapt_model(self, current_mean, new_sample, learning_rate=0.1):
        """EMA Update for Mean Vector."""
        return ((1.0 - learning_rate) * current_mean) + (learning_rate * new_sample)
