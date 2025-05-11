Homework Tracker with AI Assistant
================================

A comprehensive homework tracking application with an integrated AI chatbot assistant to help manage your academic workload.

Features
--------
1. Modern GUI interface with:
   - Dashboard: Overview of assignments due in the upcoming week (next 7 days), grouped by day.
   - Assignments Tab: Comprehensive assignment management including add, edit (double-click), delete, mark as complete/incomplete, and search.
   - Calendar View: Visual display of assignment due dates.
   - Statistics: Charts visualizing assignment distribution by priority, subject (class), and difficulty, plus an upcoming assignment timeline.
   - AI Chatbot: Integrated assistant for help and suggestions.

2. Smart Features:
   - Priority-based organization and highlighting.
   - Personalized study tips based on current assignments.
   - Workload analysis and warnings.
   - Assignments grouped by subject/class for analysis.
   - Progress tracking: Basic completion status for assignments is tracked.

3. AI Assistant capabilities:
   - Assignment scheduling advice
   - Study tips
   - Time management suggestions
   - Subject-specific help
   - Workload analysis and suggestions.

Installation
------------
1. Ensure Python 3.8+ is installed
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

Project Structure (Key Files)
-----------------------------
/ (Project Root)
├── homework_tracker/           # Main application package
│   ├── main.py                 # Main application entry point
│   ├── data/
│   │   └── assignments.json    # Stores assignment data
│   └── src/
│       ├── gui/                # GUI components
│       │   ├── app.py          # Main application window and tab management
│       │   ├── assignments_tab.py
│       │   ├── calendar_tab.py
│       │   ├── chatbot_tab.py
│       │   ├── dashboard_tab.py
│       │   └── statistics_tab.py
│       ├── core/               # Core logic
│       │   ├── assignment_manager.py # Handles CRUD operations for assignments
│       │   ├── chatbot.py      # AI Chatbot logic
│       │   ├── data_handler.py # Loads and saves assignment data
│       │   └── study_tips.py   # Generates study advice
│       └── utils/              # Utility functions
│           └── helpers.py
├── requirements.txt            # Project dependencies
└── readme.txt                  # This file

Usage
-----
1. Navigate to the project root directory (the directory containing this `readme.txt` file and the `homework_tracker` folder).
2. Run the application using:
   ```
   python homework_tracker/main.py
   ```
   Alternatively, you can navigate into the `homework_tracker` directory:
   ```
   cd homework_tracker
   python main.py
   ```

2. Use the tabs to navigate different features:
   - Dashboard: Overview of assignments due in the upcoming week (next 7 days), grouped by day.
   - Assignments: Add, edit, delete, complete/uncomplete, and search assignments.
   - Calendar: View assignments marked on their due dates.
   - Statistics: Visualize assignment distributions and timelines.
   - AI Chatbot: Get help, study tips, and schedule suggestions.

3. The AI assistant can help with:
   - Generating study tips tailored to your assignments.
   - Suggesting a basic study schedule.
   - Analyzing your current workload.
   - Providing information about your upcoming assignments, subjects, and priorities.

Data Storage
-----------
- Assignments are automatically saved in the `data/assignments.json` file within the `homework_tracker` directory.

Contributing
-----------
Feel free to submit issues and enhancement requests.
