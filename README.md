Homework Tracker with Chatbot Assistant
==================================

A comprehensive homework tracking application with an integrated, locally-run Chatbot Assistant to help you manage your academic workload effectively.

Features
--------
1.  **Modern GUI Interface**:
    *   **Dashboard**: Get a quick overview of assignments due in the next 7 days, conveniently grouped by day.
    *   **Assignments Tab**: Manage all your assignments with ease. Add new assignments (specifying name, class, due date, priority, and difficulty), edit existing ones (double-click an assignment), delete, mark as complete/incomplete, and search through your list.
    *   **Calendar View**: Visualize your assignment deadlines on an interactive calendar. Select a date to see assignments due.
    *   **Statistics**: Charts for assignments by priority, by class (active vs. completed), difficulty, and a 30-day due-date timeline.
    *   **Chat Assistant**: Manage assignments by just telling the assistant what you need.

2.  **Smart Features**:
    *   **Priority-Based Organization**: Assignments are handled with priority levels (Low, Medium, High, Urgent), and the most urgent work is always listed first.
    *   **Personalized Study Tips**: Tips tailored to your most pressing assignment.
    *   **Workload Analysis**: Warnings when the week gets heavy, plus a suggested study schedule.
    *   **Progress Tracking**: Track the completion status of your assignments.

3.  **Chat Assistant Capabilities**:
    *   **Natural Language Actions**: "Add a math quiz due Friday, high priority", "I finished the lab report", "push my essay to next Monday", "mark hw #1 done and move the lab to Oct 10", "rename the essay to essay draft", "move the lab to my biology class". Changes show up in every tab immediately.
    *   **Safe Deletes**: "Delete the art sketches" asks for a "yes" first; anything else cancels.
    *   **Follow-ups**: Remembers the last few exchanges, so "actually make it urgent" works.
    *   **Study Support**: Study plans, workload warnings, and tips.
    *   **Chat History**: Every conversation is saved and can be browsed with the History button.
    *   **Works Offline**: Everything runs locally. Simple commands ("priorities", "schedule", "tips", "list assignments") also work through keyword matching while the models load.

Chat Assistant Technology
-------------------------
Everything runs **locally** on your machine with no API keys or cloud calls; an internet connection is only needed to download the models the first time.

**LLM agent (LangChain + Hugging Face Transformers)**
*   **Agent**: A LangChain `create_agent` agent with tools for adding, completing, rescheduling, reprioritizing, renaming, re-classing, and deleting assignments, plus study plans and tips. Tools are `return_direct`, so each request needs only one model call.
*   **Model**: [IBM Granite 4.0 1B](https://huggingface.co/ibm-granite/granite-4.0-1b) (Apache 2.0) running on CPU. It was chosen by benchmarking ten small open models (from Google, Microsoft, IBM, Alibaba, Liquid AI, and Hugging Face) on tool calling, then putting the finalists through a 20-request scored test of the real agent (typos, vague references, follow-ups, undo, chit-chat, and unsupported requests). Granite was the only model to pass every request. The model can be changed with `assistant_model` in `data/settings.json` (set it to `null` to turn the assistant off).
*   **Custom LangChain chat model** (`src/core/local_chat_model.py`): LangChain's Hugging Face integration can't run agents on local models (it doesn't pass tools, parse tool calls, or accept tool results), so this class renders tools with the model's own chat template, parses its tool calls, and caches the attention state of the fixed system prompt so each request only processes new text (about 35% faster).
*   **Reliability guards**: A small model sometimes picks the wrong action, assignment, or date, so every change is checked against the user's own words before it runs:
    *   Dates are passed through as spoken ("next monday") and resolved in Python; if the message contains a date, that date wins.
    *   A change only runs if the message asks for that kind of change ("rename X" can't turn into "mark X done"), and if the model picks the opposite action ("unmark" vs. "mark done"), the user's words win.
    *   Assignment names are fuzzy-matched; if the user's words fit several assignments, or several assignments share the same name, it asks which one instead of guessing.
    *   Questions ("is X done?") and bulk requests ("mark everything done") never change data.
    *   Deleting needs a "yes" in the very next message, checked in code rather than by the model; any other reply cancels it.
    *   Listings are filtered by what the user asked about ("today", "this week", "overdue", "chem").
*   **Tested**: Beyond the unit tests, the agent was run against about 90 varied, scored requests with the real model.

**Supporting models and fallbacks**
*   **Emotion Detection**: [`SamLowe/roberta-base-go_emotions`](https://huggingface.co/SamLowe/roberta-base-go_emotions) (MIT, trained on Google's GoEmotions dataset) adds an empathetic touch when a feeling is clearly expressed ("I'm so stressed", "finally finished it!").
*   **Fixed Commands**: Keyword matching answers simple commands while the LLM loads, or if it's turned off. Small talk ("thanks", "hey how's it going") is answered directly so it can never trigger an action.
*   **Model Safety**: Models load from `safetensors` files only (pickle weights can run code) and are pinned to the exact commits that were tested.
*   **Background Loading**: All models load in the background, so the app window opens immediately and the chat stays responsive while the model thinks.

Installation
------------
1.  Ensure you have Python 3.10 or newer installed, and about 8 GB of free RAM for the assistant model.
2.  Clone this repository or download the source code.
3.  Open a terminal or command prompt in the project's root directory.
4.  Create a virtual environment and install the required Python packages:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate   # macOS/Linux: source .venv/bin/activate
    pip install --upgrade -r requirements.txt
    ```
5.  The first launch downloads the models (about 4 GB), so the assistant takes a few minutes to become ready the first time.

Usage
-----
1.  Navigate to the project's root directory in your terminal.
2.  Run the application:
    ```bash
    python main.py
    ```
3.  Explore the different tabs:
    *   **Dashboard**: See your upcoming assignments.
    *   **Assignments**: Add, edit, delete, and manage the status of your homework.
    *   **Calendar**: Visually track due dates.
    *   **Statistics**: Analyze your workload and assignment distribution.
    *   **Chat Assistant**: Tell it what to add, finish, or move, or ask for a study plan. Type `help` for examples.

Running Tests
-------------
```bash
pip install -r requirements-dev.txt
python -m pytest
```

Data Storage
------------
*   User data such as assignments, settings, and chat history are stored locally in the `data/` directory (e.g., `assignments.json`, `settings.json`, `persistent_chat_log.json`).
*   Assignments and chat history are written to a temporary file and then swapped in, so a crash or power loss mid-save can't leave a half-written file.
*   If `assignments.json` exists but can't be loaded (for example it's locked by another program, has an unexpected encoding, or isn't a list of assignments), a copy is saved as `assignments.json.corrupted.<timestamp>`, the app shows an error, and it **won't save any changes** until the problem is fixed and the app is restarted, so your real file is never overwritten with an empty list.
*   If the chat history file is unreadable, it's backed up the same way (`persistent_chat_log.json.corrupted.<timestamp>`) and a new history is started.
*   **Important**: This `data/` directory is included in `.gitignore` to prevent accidental committing of personal data.

License
-------
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.