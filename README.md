Homework Tracker with Chat Assistant
==================================

A comprehensive homework tracking application with an integrated Chat Assistant to help manage your academic workload.

Features
--------
1. Modern GUI interface with:
   - Dashboard: Overview of assignments due in the upcoming week (next 7 days), grouped by day.
   - Assignments Tab: Comprehensive assignment management including add, edit (double-click), delete, mark as complete/incomplete, and search.
   - Calendar View: Visual display of assignment due dates.
   - Statistics: Charts visualizing assignment distribution by priority, class, and difficulty, plus an upcoming assignment timeline.
   - Chat Assistant: Integrated assistant for help and suggestions.

2. Smart Features:
   - Priority-based organization and highlighting.
   - Personalized study tips based on current assignments.
   - Workload analysis and warnings.
   - Assignments grouped by class for analysis.
   - Progress tracking: Basic completion status for assignments is tracked.

3. Chat Assistant capabilities:
   - Assignment scheduling advice
   - Study tips
   - Time management suggestions
   - Class-specific help
   - Workload analysis and suggestions.

Chat Assistant Technology
-------------------------
Our Chat Assistant utilizes modern Natural Language Understanding (NLU) techniques locally on your machine, ensuring privacy and no external API calls for core NLU processing.
- **Intent Detection**: Powered by a Hugging Face Transformers model (`cross-encoder/nli-distilroberta-base`), using zero-shot classification to understand user commands.
- **Emotion Detection**: Employs another Hugging Face Transformers model (`j-hartmann/emotion-english-distilroberta-base`) to gauge user sentiment and tailor responses.
- **Conversational Memory**: Uses Langchain's `ConversationBufferMemory` with `FileChatMessageHistory` to remember the context of the current conversation session, with persistent multi-session history available via the 'History' button.
- **Core Technologies**: `transformers` (Hugging Face), `torch` (PyTorch), and `langchain`.
- **Local Processing**: All NLU tasks run locally. An internet connection is only required for the initial download of the transformer models.

Installation
------------
1. Ensure Python 3.8+ is installed
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

Usage
-----
1. Navigate to the project root directory.
2. Run the application using:
   ```bash
   python main.py
   ```

3. Use the tabs to navigate different features:
   - Dashboard: Overview of assignments due in the upcoming week (next 7 days), grouped by day.
   - Assignments: Add, edit, delete, complete/uncomplete, and search assignments.
   - Calendar: View assignments marked on their due dates.
   - Statistics: Visualize assignment distributions and timelines.
   - Chat Assistant: Get help, study tips, and schedule suggestions.

4. The Chat Assistant can help with:
   - Generating study tips tailored to your assignments.
   - Suggesting a basic study schedule.
   - Analyzing your current workload.
   - Providing information about your upcoming assignments, classes, and priorities.

Data Storage
-----------
- Assignments are automatically saved in the `data/assignments.json` file.

Contributing
-----------
Feel free to submit issues and enhancement requests. 

License
-------
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.