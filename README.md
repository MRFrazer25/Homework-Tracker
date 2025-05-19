Homework Tracker with Chatbot Assistant
==================================

A homework tracking application with an integrated, locally-run Chatbot Assistant to help you manage your academic workload effectively.

Features
--------
1.  **Modern GUI Interface**:
    *   **Dashboard**: Get a quick overview of assignments due in the next 7 days, conveniently grouped by day.
    *   **Assignments Tab**: Manage all your assignments with ease. Add new assignments (specifying name, class, due date, priority, and difficulty), edit existing ones (double-click an assignment), delete, mark as complete/incomplete, and search through your list.
    *   **Calendar View**: Visualize your assignment deadlines on an interactive calendar. Select a date to see assignments due.
    *   **Statistics**: Gain insights into your workload with charts visualizing assignment distribution by priority, difficulty, and an upcoming assignment timeline.
    *   **Chat Assistant**: Interact with a chatbot assistant for help, study tips, and task management.

2.  **Smart Features**:
    *   **Priority-Based Organization**: Assignments are handled with priority levels (Low, Medium, High).
    *   **Personalized Study Tips**: The Chat Assistant can provide study tips.
    *   **Workload Analysis**: Basic workload insights can be provided by the Chat Assistant.
    *   **Progress Tracking**: Track the completion status of your assignments.

3.  **Chatbot Assistant Capabilities**:
    *   **NLU Powered**: Understands your requests regarding assignments, classes, and scheduling.
    *   **Task Management**: Helps list assignments, find due dates, and understand your schedule.
    *   **Study Support**: Offers study tips and can help analyze workload.
    *   **Conversational**: Remembers the current conversation context and provides access to persistent chat history.

Chat Assistant Technology
-------------------------
The Chat Assistant utilizes modern Natural Language Understanding (NLU) techniques, running **locally** on your machine. This ensures your data privacy, with no external API calls required for core NLU processing.

*   **Intent Detection**: Powered by `cross-encoder/nli-distilroberta-base` (Hugging Face Transformers) for zero-shot classification of user commands.
*   **Emotion Detection**: Employs `j-hartmann/emotion-english-distilroberta-base` (Hugging Face Transformers) to understand user sentiment.
*   **Conversational Memory**: Uses Langchain's `ConversationBufferMemory` with `FileChatMessageHistory` for session memory and persistent multi-session chat log access.
*   **Core Libraries**: `transformers`, `torch`, `langchain`, `langchain-community`, `sentencepiece`.
*   **Local First**: All NLU tasks run locally. An internet connection is only needed for the initial download of the transformer models.

Installation
------------
1.  Ensure you have Python 3.8 or newer installed.
2.  Clone this repository or download the source code.
    ```bash
    git clone https://github.com/MRFrazer25/homework_tracker
    cd homework_tracker
    ```
3.  Open a terminal or command prompt in the project's root directory.
4.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

Usage
-----
1.  Navigate to the project's root directory in your terminal.
    ```bash
    cd homework_tracker
    ```
2.  Run the application:
    ```bash
    python main.py
    ```
3.  Explore the different tabs:
    *   **Dashboard**: See your upcoming assignments.
    *   **Assignments**: Add, edit, delete, and manage the status of your homework.
    *   **Calendar**: Visually track due dates.
    *   **Statistics**: Analyze your workload and assignment distribution.
    *   **Chat Assistant**: Ask for help, get study tips, or inquire about your schedule.

Data Storage
------------
*   User data such as assignments, settings, and chat history are stored locally in the `data/` directory (e.g., `assignments.json`, `settings.json`).
*   **Important**: This `data/` directory is included in `.gitignore` to prevent accidental committing of personal data.

License
-------
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.