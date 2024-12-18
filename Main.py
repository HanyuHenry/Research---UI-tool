import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import numpy as np
import threading
import time

# Define color map for different data types
color_map = {
    "Numeric": "blue",
    "Nominal": "green",
    "Ordinal": "red"
}

# Store user selections
selection_dict = {}
# Store all warning labels
warning_labels = []
# Add a variable to store the threshold value (default 20)
threshold_value = 20
# Add a variable to store the feature names (either from the first row or NaN if no header)
feature_names = []
# Store the current state of the loading spinner
loading_index = 0
# Spinner animation characters
spinner_states = ['|', '/', '-', '\\']
# Timer start and thread stop flag
start_time = 0
stop_flag = False

# Function to check if the first row is a header
def check_if_header(first_row):
    try:
        first_row_numeric = pd.to_numeric(first_row)
        return False
    except ValueError:
        return True

# Enable or disable "Run" and "Export" buttons based on warnings
def update_button_states():
    if not warning_labels:  # If there are no warnings
        run_button.config(state=tk.NORMAL)
        export_button.config(state=tk.NORMAL)
    else:
        run_button.config(state=tk.DISABLED)
        export_button.config(state=tk.DISABLED)

# Function to refresh the display based on the new threshold
def refresh_display():
    global warning_labels
    warning_labels = []

    # Clear previous content
    for widget in result_frame.winfo_children():
        widget.destroy()

    # Display selection prompt
    select_prompt = ttk.Label(result_frame, text="Please select the category for each feature:", anchor='w', font=("Helvetica", 10, "italic"))
    select_prompt.pack(fill='both', pady=5)

    # Dropdown menu options
    options = ["Numeric", "Nominal", "Ordinal"]

    for idx, column in enumerate(data.columns, start=1):
        frame = tk.Frame(result_frame)
        frame.pack(fill='x', padx=10, pady=5)

        unique_count = data[column].nunique()
        feature_name = feature_names[idx - 1]

        column_label_text = f"{column}: ({unique_count} unique values) - Label: {feature_name if feature_name else 'NaN'}"
        column_label = ttk.Label(frame, text=column_label_text, anchor='w', font=("Helvetica", 10), foreground=color_map["Numeric"])
        column_label.pack(side=tk.LEFT, padx=10, pady=5)

        warning_label = None
        if unique_count < threshold_value:
            warning_label = ttk.Label(frame, text="⚠️", foreground="red")
            warning_label.pack(side=tk.LEFT, padx=5, pady=5)
            warning_labels.append(warning_label)

        combo = ttk.Combobox(frame, values=options, state="readonly", font=("Helvetica", 10))
        combo.pack(side=tk.RIGHT, padx=10, pady=5)
        combo.current(0)

        selection_dict[column] = "Numeric"
        handle_selection_initial(combo, column_label)
        combo.bind("<<ComboboxSelected>>", lambda event, col=column, lbl=column_label, warn_lbl=warning_label: handle_selection(event, col, lbl, warn_lbl))

    update_button_states()  # Update button state after refreshing

def load_csv():
    global warning_labels, feature_names, data, run_button, export_button
    warning_labels = []

    for widget in result_frame.winfo_children():
        widget.destroy()

    # Clear previous results and labels when reloading new data
    result_label.config(text="")
    loading_label.pack_forget()
    timer_label.pack_forget()
    stop_button.pack_forget()

    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    
    if file_path:
        temp_data = pd.read_csv(file_path, header=None, nrows=1)
        first_row = temp_data.iloc[0]

        has_header = check_if_header(first_row)

        if has_header:
            data = pd.read_csv(file_path)
            feature_names = data.columns.tolist()
        else:
            data = pd.read_csv(file_path, header=None)
            feature_names = [None] * data.shape[1]

        data.columns = [f"Feature #{i}" for i in range(data.shape[1])]

        info_label = ttk.Label(result_frame, text=f"Dataset Info: {data.shape[0]} rows, {data.shape[1]} columns", anchor='w', font=("Helvetica", 12, "bold"))
        info_label.pack(fill='both', pady=10)

        refresh_display()

        # Ensure that only one set of buttons (Run and Export) are created
        run_button.config(state=tk.DISABLED)
        export_button.config(state=tk.DISABLED)

def handle_selection_initial(combo, label):
    selected_value = combo.get()
    label.config(foreground=color_map[selected_value])

def handle_selection(event, column, label, warning_label):
    selected_value = event.widget.get()
    label.config(foreground=color_map[selected_value])
    selection_dict[column] = selected_value
    if warning_label:
        warning_label.destroy()
        warning_labels.remove(warning_label)
    update_button_states()  # Recheck the button state after selection change

def export_csv():
    if any(warning_label.winfo_exists() for warning_label in warning_labels):
        messagebox.showwarning("Warning", "Please address the features with warnings before exporting.")
        return

    ordered_columns = (
        [col for col in selection_dict if selection_dict[col] == "Nominal"] +
        [col for col in selection_dict if selection_dict[col] == "Ordinal"] +
        [col for col in selection_dict if selection_dict[col] == "Numeric"]
    )

    ordered_data = data[ordered_columns]

    export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if export_path:
        ordered_data.to_csv(export_path, index=False, header=False)
        print(f"Data exported to {export_path}")

# Function to run a simple calculation (average) and display loading animation
def run_calculation():
    global start_time, stop_flag
    stop_flag = False
    start_time = time.time()

    # Create a loading label with a spinning animation and a timer
    global loading_index
    loading_index = 0
    loading_label.config(text="")
    loading_label.pack(pady=10)
    
    timer_label.config(text="0 seconds")
    timer_label.pack(pady=10)

    # Start the spinner animation
    def animate_spinner():
        global loading_index
        if not stop_flag:
            loading_label.config(text=f"Calculating average... {spinner_states[loading_index % len(spinner_states)]}")
            loading_index += 1
            timer_label.config(text=f"{int(time.time() - start_time)} seconds")
            root.after(200, animate_spinner)

    animate_spinner()

    # Add Stop button
    stop_button.pack(pady=10)

    # Run the calculation in a separate thread to avoid blocking the UI
    thread = threading.Thread(target=calculate_average)
    thread.start()

# Calculate the average of the data
def calculate_average():
    global stop_flag
    try:
        time.sleep(5)  # Simulate calculation time
        if stop_flag:
            return

        numeric_data = data.select_dtypes(include=[np.number])
        mean_value = numeric_data.mean().mean()

        loading_label.pack_forget()  # Remove loading label after calculation
        timer_label.pack_forget()
        stop_button.pack_forget()  # Remove Stop button
        result_label.config(text=f"Average of data: {mean_value:.4f}")  # Display result at the bottom of the window
    except Exception as e:
        loading_label.pack_forget()
        timer_label.pack_forget()
        stop_button.pack_forget()  # Remove Stop button
        result_label.config(text=f"Error occurred: {str(e)}")

# Function to stop the running thread
def stop_calculation():
    global stop_flag
    stop_flag = True
    loading_label.pack_forget()
    timer_label.pack_forget()
    stop_button.pack_forget()
    result_label.config(text="Calculation stopped.")

def center_window(window, width=600, height=500):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y}')

def handle_threshold_change(event):
    global threshold_value
    try:
        threshold_value = int(threshold_entry.get())
        refresh_display()
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid number for the threshold.")

# Create main window
root = tk.Tk()
root.title("Data Analyzer")

# Center window on screen
center_window(root, 600, 500)

# Add instruction label
instruction_label = ttk.Label(root, text="Please import the data to be analyzed:", font=("Helvetica", 14, "bold"))
instruction_label.pack(pady=10)

# Create "Import Data" button
import_button = ttk.Button(root, text="Import Data", command=load_csv, style="TButton")
import_button.pack(pady=10)

# Create threshold input label and entry
threshold_label = ttk.Label(root, text="Set Threshold for Warnings:", font=("Helvetica", 12))
threshold_label.pack(pady=5)

threshold_entry = ttk.Entry(root)
threshold_entry.insert(0, "20")
threshold_entry.pack(pady=5)
threshold_entry.bind("<Return>", handle_threshold_change)

# Create a frame with a scrollbar for displaying results
result_frame_container = tk.Frame(root)
result_frame_container.pack(fill="both", expand=True)

canvas = tk.Canvas(result_frame_container)
scrollbar = ttk.Scrollbar(result_frame_container, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(
        scrollregion=canvas.bbox("all")
    )
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

scrollbar.pack(side="right", fill="y")
canvas.pack(side="left", fill="both", expand=True)

result_frame = scrollable_frame

# Frame to hold buttons like "Run" and "Export CSV"
button_frame = tk.Frame(root)
button_frame.pack(fill="x", pady=10)

# Add Run and Export buttons
run_button = ttk.Button(button_frame, text="Run", command=run_calculation, state=tk.DISABLED)
run_button.pack(side=tk.LEFT, pady=20, padx=10)

export_button = ttk.Button(button_frame, text="Export CSV", command=export_csv, state=tk.DISABLED)
export_button.pack(side=tk.LEFT, pady=20, padx=10)

# Loading and timer label
loading_label = ttk.Label(root, text="")
timer_label = ttk.Label(root, text="")

# Stop button (initially hidden)
stop_button = ttk.Button(root, text="Stop", command=stop_calculation)

# Label to display result at the bottom
result_label = ttk.Label(root, text="", font=("Helvetica", 12, "bold"))
result_label.pack(pady=10)

# Run main loop
root.mainloop()
