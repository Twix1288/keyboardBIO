import customtkinter as ctk
import time
# Removed pynput to fix macOS crash (Trace/BPT trap)
# Using native Tkinter bindings instead.
import tkinter as tk

PASSPHRASE = "The quick brown fox jumps over the lazy dog"
REQUIRED_SAMPLES = 10

class AuthUI(ctk.CTk):
    def __init__(self, db_manager, biometrics_engine):
        print("[DEBUG] AuthUI __init__ start")
        super().__init__()
        
        self.db = db_manager
        self.bio = biometrics_engine
        
        print("[DEBUG] Setting Up Window...")
        self.title("Keystroke Auth")
        self.geometry("400x320")
        self.resizable(False, False)
        ctk.set_appearance_mode("Dark")
        
        self.current_user = None
        self.model_data = None
        
        # Data Collection
        self.current_keys = []
        self.training_samples = []
        self.listener = None
        self.listening_active = False
        
        print("[DEBUG] Creating Container...")
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        
        print("[DEBUG] Showing Login...")
        self.show_login()
        print("[DEBUG] AuthUI __init__ done")

    def clear_frame(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    # --- KEYSTROKE CAPTURE ---
    def setup_keystroke_bindings(self, widget):
        """Binds KeyPress and KeyRelease events to the widget."""
        widget.bind("<KeyPress>", self.on_key_press)
        widget.bind("<KeyRelease>", self.on_key_release)
        # Allowed chars set for strict filtering
        self.allowed_chars = set(PASSPHRASE)

    def on_key_press(self, event):
        timestamp = time.time()
        char = event.char
        # Strict Filter: Only allow chars exactly in the passphrase
        if not char or (char not in self.allowed_chars and char != '\r'):
             if event.keysym == "BackSpace":
                 self.current_keys.append(("Key.backspace", 'down', timestamp))
             return
        
        if char == '\r': return # Ignore Enter itself

        self.current_keys.append((char, 'down', timestamp))

    def on_key_release(self, event):
        timestamp = time.time()
        char = event.char
        # Strict Filter Match
        if not char or (char not in self.allowed_chars and char != '\r'):
             return
        
        if char == '\r': return

        self.current_keys.append((char, 'up', timestamp))

    # --- LOGIN VIEW ---
    def show_login(self):
        self.clear_frame()
        self.geometry("400x320")
        self.deiconify() # Ensure visible
        self.attributes('-topmost', False)
        
        ctk.CTkLabel(self.container, text="Login", font=("Arial", 24)).pack(pady=20)
        
        self.username_entry = ctk.CTkEntry(self.container, placeholder_text="Username")
        self.username_entry.pack(pady=10)
        
        ctk.CTkButton(self.container, text="Continue", command=self.handle_login).pack(pady=20)
        
        self.lbl_msg = ctk.CTkLabel(self.container, text="", text_color="red")
        self.lbl_msg.pack()

    def handle_login(self):
        username = self.username_entry.get()
        if not username: return
        
        user = self.db.register_user(username)
        if user:
            self.current_user = user
            # Check if model exists
            model = self.db.get_model(user['id'])
            if model:
                self.model_data = model
                self.show_widget_mode()
            else:
                self.show_onboarding()

    # --- ONBOARDING VIEW ---
    def show_onboarding(self):
        self.clear_frame()
        self.geometry("600x450")
        
        ctk.CTkLabel(self.container, text="Welcome to Keystroke Auth", font=("Arial", 24)).pack(pady=(20, 10))
        
        instruction_text = (
            f"We need to learn your typing pattern.\n"
            f"Please type the passphrase below exactly as shown, {REQUIRED_SAMPLES} times.\n"
            "type 'natural' - don't rush, just be yourself."
        )
        ctk.CTkLabel(self.container, text=instruction_text, wraplength=500).pack(pady=5)

        # Passphrase Display with dynamic status
        self.lbl_passphrase = ctk.CTkLabel(self.container, text=PASSPHRASE, font=("Courier", 18), text_color="cyan")
        self.lbl_passphrase.pack(pady=15)
        
        self.progress_bar = ctk.CTkProgressBar(self.container, width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        self.lbl_progress = ctk.CTkLabel(self.container, text=f"Progress: 0/{REQUIRED_SAMPLES}")
        self.lbl_progress.pack()
        
        # Feedback Label (Live updates)
        self.lbl_feedback = ctk.CTkLabel(self.container, text="Start typing when ready...", font=("Arial", 14), text_color="gray")
        self.lbl_feedback.pack(pady=(10, 0))

        # Input Field
        self.input_entry = ctk.CTkEntry(self.container, width=450, placeholder_text="Type phrase here...", font=("Courier", 14))
        self.input_entry.pack(pady=10)

        # Retry Logic Wrapper
        self.input_entry.bind("<Return>", lambda e: self.attempt_submission_with_retry(self.handle_onboarding_submission_logic))
        
        # Keystroke Bindings
        self.setup_keystroke_bindings(self.input_entry)
        
        # LIVE FEEDBACK BINDING
        self.input_entry.bind("<KeyRelease>", self.check_onboarding_typing, add="+")
        
        # Clear keys on focus
        self.input_entry.bind("<FocusIn>", lambda e: self.reset_input_state())
        
        self.input_entry.focus()

    def reset_input_state(self):
        self.current_keys.clear()
        self.lbl_feedback.configure(text="Start typing...", text_color="gray")
        self.lbl_passphrase.configure(text_color="cyan") # Reset color

    def check_onboarding_typing(self, event):
        """Provides real-time feedback as the user types."""
        current_text = self.input_entry.get()
        if not current_text:
            return

        # Check for immediate typos (prefix matching)
        if PASSPHRASE.startswith(current_text):
            self.lbl_feedback.configure(text="Looking good...", text_color="#55FF55")
            self.lbl_passphrase.configure(text_color="cyan")
        else:
            self.lbl_feedback.configure(text="Typo detected! Check your spelling.", text_color="#FF5555")
            self.lbl_passphrase.configure(text_color="orange")

    def attempt_submission_with_retry(self, callback, attempts=0):
        features = self.bio.extract_features(self.current_keys)
        
        expected_len = len(PASSPHRASE) + (len(PASSPHRASE) - 1)
        
        if features is not None and len(features) == expected_len:
            callback()
            return

        if attempts < 3:
            self.after(50, lambda: self.attempt_submission_with_retry(callback, attempts+1))
        else:
            callback()

    def handle_onboarding_submission_logic(self):
        self.handle_onboarding_submission(None)

    def handle_onboarding_submission(self, event):
        text = self.input_entry.get()
        
        # 1. Content Accuracy Check
        if text != PASSPHRASE:
            self.lbl_progress.configure(text=f"Progress: {len(self.training_samples)}/{REQUIRED_SAMPLES}")
            self.identify_typo(text)
            self.input_entry.delete(0, 'end')
            self.current_keys = []
            return
            
        # 2. Extract Features
        features = self.bio.extract_features(self.current_keys)
        
        expected_dwells = len(PASSPHRASE)
        expected_flights = len(PASSPHRASE) - 1
        expected_total = expected_dwells + expected_flights
        
        # 3. Quality Check
        if features is None:
            self.lbl_feedback.configure(text="Oops! Please type naturally without using Backspace.", text_color="orange")
            self.input_entry.delete(0, 'end')
            self.current_keys = []
            return

        if len(features) != expected_total:
             if len(features) < expected_total:
                 msg = "Too fast! Some keys overlapped. Try typing slightly slower."
             else:
                 msg = "Typing inconsistent. Please try again."
             
             self.lbl_feedback.configure(text=msg, text_color="orange")
             self.input_entry.delete(0, 'end')
             self.current_keys = []
             return
        
        # 4. Success!
        self.training_samples.append(features)
        
        count = len(self.training_samples)
        self.progress_bar.set(count / REQUIRED_SAMPLES)
        self.lbl_progress.configure(text=f"Progress: {count}/{REQUIRED_SAMPLES}")
        self.lbl_feedback.configure(text=f"Great! Sample {count} recorded.", text_color="#55FF55")
        
        self.input_entry.delete(0, 'end')
        self.current_keys = []
        
        if count >= REQUIRED_SAMPLES:
            self.finish_onboarding()

    def identify_typo(self, actual):
        """Provides specific feedback on why the string didn't match."""
        if len(actual) != len(PASSPHRASE):
            self.lbl_feedback.configure(text=f"Length mismatch: Expected {len(PASSPHRASE)} chars, got {len(actual)}.", text_color="#FF5555")
            return

        for i, (a, b) in enumerate(zip(actual, PASSPHRASE)):
            if a != b:
                self.lbl_feedback.configure(text=f"Typo: Wrote '{a}' instead of '{b}'", text_color="#FF5555")
                return

    def finish_onboarding(self):
        self.lbl_progress.configure(text="Training Model...", text_color="yellow")
        self.update()
        
        # Train
        std_vec, mean_vec, threshold = self.bio.train_model(self.training_samples)
        
        # Save (We store std_vec in the 'transform_matrix' column for schema compat)
        self.db.save_model(self.current_user['id'], std_vec, mean_vec, threshold)
        
        self.model_data = {
            "transform_matrix": std_vec, # Actually std_vector now
            "mean_vector": mean_vec,
            "threshold": threshold
        }
        
        self.after(1000, self.show_widget_mode)

    # --- WIDGET VIEW ---
    def show_widget_mode(self):
        self.stop_listener() # Verify explicit only
        
        # Minimize/Reposition
        self.withdraw() # Hide, then show as small window
        
        # Create a specific Toplevel for the widget or reuse root?
        # Reusing root is easier for lifecycle.
        self.clear_frame()
        self.geometry("250x120+50+50") # Bottom corner approx?
        self.deiconify()
        self.attributes('-topmost', True)
        self.title("BioAuth Widget")
        
        # Status
        self.status_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.status_frame.pack(pady=10)
        
        self.status_indicator = ctk.CTkLabel(self.status_frame, text="●", font=("Arial", 30), text_color="gray")
        self.status_indicator.pack(side="left", padx=5)
        self.status_text = ctk.CTkLabel(self.status_frame, text="Idle", font=("Arial", 16))
        self.status_text.pack(side="left")
        
        # Verify Button
        self.btn_verify = ctk.CTkButton(self.container, text="Verify", command=self.open_verify_popup)
        self.btn_verify.pack(pady=10)



    def open_verify_popup(self):
        # Popup window
        if hasattr(self, 'popup') and self.popup.winfo_exists():
            self.popup.lift()
            return

        self.popup = ctk.CTkToplevel(self)
        self.popup.geometry("500x250")
        self.popup.title("Verification")
        self.popup.attributes('-topmost', True)
        
        ctk.CTkLabel(self.popup, text=f"Type: {PASSPHRASE}", font=("Courier", 12)).pack(pady=10)
        
        self.verify_entry = ctk.CTkEntry(self.popup, width=400)
        self.verify_entry.pack(pady=10)
        
        self.lbl_verify_msg = ctk.CTkLabel(self.popup, text="Press Enter when done", text_color="gray")
        self.lbl_verify_msg.pack(pady=5)
        
        self.verify_entry.focus()
        
        self.verify_entry.bind("<Return>", lambda e: self.attempt_submission_with_retry(self.perform_verification_logic))
        
        # Use safe bindings
        self.setup_keystroke_bindings(self.verify_entry)
        # Clear keys on focus
        self.verify_entry.bind("<FocusIn>", lambda e: self.current_keys.clear())
        
        # Reset keys
        self.current_keys = []

    def perform_verification_logic(self):
        self.perform_verification(None)

    def perform_verification(self, event):
        text = self.verify_entry.get()
        if text != PASSPHRASE:
            self.verify_entry.delete(0, 'end')
            self.lbl_verify_msg.configure(text="Wrong Passphrase! Try again.", text_color="red")
            return

        features = self.bio.extract_features(self.current_keys)
        try:
             mean_vec = self.model_data['mean_vector']
        except:
             return
        
        if features is None or features.shape != mean_vec.shape:
             self.verify_entry.delete(0, 'end')
             self.lbl_verify_msg.configure(text="Typing unclear. Try smoother.", text_color="orange")
             return

        success, dist, score = self.bio.authenticate(
            features,
            self.model_data['mean_vector'],
            self.model_data['transform_matrix'],
            self.model_data['threshold']
        )
        
        if success:
            self.popup.destroy()
            
            # --- ADAPTIVE LEARNING (The "Smartness") ---
            # If high confidence (Score > 85?), update the model
            if score > 85:
                print("[INFO] Adaptive Update Triggered")
                new_mean = self.bio.adapt_model(self.model_data['mean_vector'], features)
                self.db.update_mean_vector(self.current_user['id'], new_mean)
                # Update local state
                self.model_data['mean_vector'] = new_mean
                self.update_widget_status(True, score, "Verified + Learned")
            else:
                self.update_widget_status(True, score)
                
        else:
            self.verify_entry.delete(0, 'end')
            self.lbl_verify_msg.configure(text=f"Failed ({int(score)}%). Try again.", text_color="red")
            self.update_widget_status(False, score, "Last Attempt Failed")

    def update_widget_status(self, success, score, message=None):
        if success:
            color = "#00FF00" # Green
            text = message if message else f"Verified ({int(score)}%)"
        else:
            color = "#FF0000" # Red
            text = message if message else f"Failed ({int(score)}%)"
            
        self.status_indicator.configure(text_color=color)
        self.status_text.configure(text=text)
        
        # Reset after 3 seconds
        self.after(3000, self.reset_widget_status)
        
    def reset_widget_status(self):
        self.status_indicator.configure(text_color="gray")
        self.status_text.configure(text="Idle")
