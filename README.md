# TODO-LIST-APPLICATION
# 📝 Smart Task Manager

An interactive and visually-rich **To-Do List & Productivity App** built using **Streamlit**. It supports task creation, prioritization, scheduling, reflection journaling, and insightful visual analytics — all in one place.

---

## 🚀 Features

- 🎯 **Task Management**: Add, edit, delete, and reorder tasks with support for priority levels and due times.
- 🗣️ **Voice Input Support** *(optional)*: Use your mic to add tasks via speech.
- 📅 **Calendar Integration**: Visualize your weekly task schedule using an interactive calendar.
- ⭐ **Gamified Experience**: Earn stars for completing tasks and track progress.
- 🧠 **Reflection Journal**: Write daily reflections and store them securely in the database.
- 📊 **Analytics Dashboard**: Get insightful visual summaries using interactive charts (Plotly).
- 🎨 **Theming & UI Customization**: Choose from multiple built-in themes for a personalized experience.
- 🔒 **Login Screen**: User login system with profile management (name, age, picture, etc.).

---

## 📦 Tech Stack

| Layer        | Technology Used                             |
|--------------|----------------------------------------------|
| Frontend     | [Streamlit](https://streamlit.io)           |
| Backend      | Python + SQLite                             |
| Visuals      | Plotly Express (charts), streamlit-calendar |
| Voice Input  | streamlit-mic-recorder (optional)           |
| UX Features  | Custom CSS, streamlit-sortables             |

---

## 📁 Installation

1. **Clone the Repository**  
```bash
git clone https://github.com/your-username/smart-task-manager.git
cd smart-task-manager

2. **Install Requirements**
pip install -r requirements.txt

3. **RUN THE APP**
streamlit run app.py

📘 Notes
First-time users are asked to log in and select a theme.

User data (tasks, stats, reflections) is stored in a local tasks.db SQLite file.

Some optional features like voice input require additional permissions or dependencies.


✨ Future Improvements
Multi-user login with separate dashboards

Notifications and reminders

Cloud database support (e.g., Firebase, PostgreSQL)
