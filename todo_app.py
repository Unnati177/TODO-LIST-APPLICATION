import subprocess, sys
try:
    from streamlit_sortables import sort_items
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit-sortables"])
    from streamlit_sortables import sort_items

import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import base64
from datetime import datetime, date, time
from streamlit_calendar import calendar

# Optional voice support
try:
    from streamlit_mic_recorder import speech_to_text
    VOICE = True
except ImportError:
    VOICE = False

# ——— Helpers to load & encode images ———
def _get_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

login_b64  = _get_base64("login_bg.jpg")
sticky_b64 = _get_base64("sticky_notes.jpg")

# ——— Database setup ———
DB = "tasks.db"
def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                task        TEXT    NOT NULL,
                priority    TEXT    NOT NULL,
                due_date    TEXT    NOT NULL,
                start_time  TEXT    NOT NULL,
                end_time    TEXT    NOT NULL,
                done        INTEGER DEFAULT 0
            )
        """)
init_db()

def init_stats_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id    INTEGER PRIMARY KEY,
                stars INTEGER DEFAULT 0
            );
        """)
        conn.execute("INSERT OR IGNORE INTO stats(id,stars) VALUES(1,0);")
init_stats_db()

get_stars = lambda: run_q("SELECT stars FROM stats WHERE id=1", fetch=True)[0][0]
add_star  = lambda n=1: run_q("UPDATE stats SET stars = stars + ? WHERE id=1", (n,))

# ——— Query helpers ———
def run_q(q, args=(), fetch=False):
    with sqlite3.connect(DB) as conn:
        cur = conn.execute(q, args)
        return cur.fetchall() if fetch else None

fetch_tasks = lambda: run_q("SELECT * FROM tasks", fetch=True)
add_task     = lambda t,p,d,st,en: run_q(
    "INSERT INTO tasks(task,priority,due_date,start_time,end_time) VALUES(?,?,?,?,?)",
    (t,p,d,st,en)
)
update_task  = lambda i,t,p,d,st,en,done: run_q(
    "UPDATE tasks SET task=?,priority=?,due_date=?,start_time=?,end_time=?,done=? WHERE id=?",
    (t,p,d,st,en,int(done),i)
)
delete_task  = lambda i: run_q("DELETE FROM tasks WHERE id=?", (i,))
clear_done   = lambda: run_q("DELETE FROM tasks WHERE done=1")

# ——— LOGIN SCREEN ———
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown(f"""
    <style>
      [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/jpeg;base64,{login_b64}");
        background-size: cover;
        background-position: center;
        background-color: rgba(255,255,255,0.2);
        background-blend-mode: lighten;
      }}
      [data-testid="stAppViewContainer"] > section {{
        background: rgba(255,255,255,0.85) !important;
        padding: 2rem !important;
        border-radius: 1rem !important;
      }}
      [data-testid="stSidebar"] {{
        background: rgba(0,0,0,0.5) !important;
      }}
      label, .css-1n76uvr {{ color: #000 !important; font-weight: 600 !important; }}
      .stTextInput input,
      .stSelectbox div div input,
      .stDateInput input {{
        background-color: #fff !important;
        color:            #000 !important;
      }}
      .stButton > button {{
        background-color: #fff !important;
        color:            #000 !important;
        font-weight:      600 !important;
      }}
    </style>
    """, unsafe_allow_html=True)

    st.title("🔒 Login")
    email = st.text_input("Email")
    pwd   = st.text_input("Password", type="password")
    th    = st.selectbox("Theme (initial)", ["Dark","Light","Green","Pink","Purple"])
    if st.button("Login"):
        if email and pwd:
            st.session_state.logged_in = True
            st.session_state.theme     = th
            st.session_state.email     = email
        else:
            st.warning("Please enter both email & password.")
    st.stop()

# ─── Sidebar (after login) ───
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"
if "sidebar_rows" not in st.session_state:
    st.session_state.sidebar_rows = fetch_tasks()
if "sidebar_search" not in st.session_state:
    st.session_state.sidebar_search = ""
if "sidebar_filter" not in st.session_state:
    st.session_state.sidebar_filter = "All" 


with st.sidebar:
    # 1) top‐level menu
    page = st.radio(
        "🔧 Menu",
        ["Home", "Search", "Reflection", "Settings"],
        index=0,
        key="sidebar_page"
    )

    if page == "Home":
        st.header("🔐 User")
        st.write("Logged in as")
        st.caption(st.session_state.email)
        stars = get_stars()
        st.markdown(f"**⭐ Points: {stars}**")
        st.markdown("---")
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()

    elif page == "Search":
        st.header("🔍 Search & Reorder Tasks")

        # 2) Search box
        search_txt = st.text_input(
            "Search Tasks",
            st.session_state.sidebar_search,
            key="sidebar_search"
        )

        # 3) Fetch & filter
        all_rows = fetch_tasks()
        order_map = {"High": 0, "Medium": 1, "Low": 2}
        all_rows.sort(key=lambda r: (order_map[r[2]], r[6]))

        if search_txt:
            filtered = [r for r in all_rows if search_txt.lower() in r[1].lower()]
        else:
            filtered = all_rows

        # 4) Drag‐and‐drop, with a unique key per sidebar render
        items = [f"{r[0]}: {r[1]}" for r in filtered]
        new_order = sort_items(
            items,
            key=f"sidebar_sort_{len(items)}",  # unique each time
            direction="vertical",
            header=None,
            multi_containers=False,
        )

        # 5) Rebuild rows from new order
        sidebar_rows = []
        for lbl in new_order:
            tid, _ = lbl.split(":", 1)
            for r in filtered:
                if str(r[0]) == tid:
                    sidebar_rows.append(r)
                    break

        # store for main display
        st.session_state.sidebar_rows = sidebar_rows

        # 6) Optional backlog view
        if search_txt:
            st.markdown("📜 Backlog (last 30 days)")
            cutoff = (date.today() - pd.Timedelta(days=30)).isoformat()
            backlog = run_q(
                "SELECT * FROM tasks WHERE task LIKE ? AND due_date>=? ORDER BY due_date DESC",
                (f"%{search_txt}%", cutoff),
                fetch=True,
            )
            for _, t, p, d, stt, ent, done in backlog:
                st.write(f"- {d} ⏰ {stt}–{ent} ⭐ {p} Done={'Yes' if done else 'No'}")

    elif page == "Reflection":
      st.header("💭 Daily Reflection")
      ref_date = st.date_input("Select date", date.today())
      existing = run_q(
          "SELECT entry FROM reflections WHERE date=?", 
            (ref_date.isoformat(),), 
            fetch=True
        )
      initial = existing[0][0] if existing else ""
        
        # large diary textarea
      ntry = st.text_area("Write your reflection", initial, height=300)
        
        # save button
      if st.button("💾 Save Reflection"):
            if existing:
                run_q(
                    "UPDATE reflections SET entry=? WHERE date=?", 
                    (entry, ref_date.isoformat())
                )
            else:
                run_q(
                    "INSERT INTO reflections(date, entry) VALUES(?,?)", 
                    (ref_date.isoformat(), entry)
                )
            st.success("Reflection saved!")
            st.markdown("---")

    else:
        st.header("⚙️ Settings")
        st.subheader("👤 Profile")
        owner = st.text_input("Name", value=st.session_state.get("owner_name",""))
        email = st.text_input("Email ID", value=st.session_state.email)
        phone = st.text_input("Phone number", value=st.session_state.get("phone",""))
        gender = st.selectbox(
            "Gender",
            ["Prefer not to say","Female","Male","Other"],
            index=["Prefer not to say","Female","Male","Other"]
                  .index(st.session_state.get("gender","Prefer not to say"))
        )
        age = st.number_input("Age", min_value=0, max_value=120,
                              value=st.session_state.get("age",0))
        pwd = st.text_input("Change password", type="password", key="pwd_field")
        pic = st.file_uploader("Profile picture", type=["jpg","png","jpeg"])
        if pic:
            b64 = base64.b64encode(pic.read()).decode()
            st.session_state["profile_pic"] = b64
            st.image(pic, width=80, caption="Preview")
        if st.button("💾 Save Profile"):
            st.session_state.owner_name = owner
            st.session_state.email      = email
            st.session_state.phone      = phone
            st.session_state.gender     = gender
            st.session_state.age        = age
            st.success("Profile updated!")
        st.markdown("---")
        st.subheader("🎨 Preferences")
        theme_choice = st.radio(
            "Theme palette",
            ["Dark","Light","Green","Pink","Purple"],
            index=["Dark","Light","Green","Pink","Purple"]
                  .index(st.session_state.theme),
            key="sidebar_theme"
        )
        if theme_choice != st.session_state.theme:
            st.session_state.theme = theme_choice
            st.rerun()
        st.radio("Show Tasks",
                 ["All","Priority Only","Non-Priority Only"],
                 key="sidebar_filter"
        )


# ——— Apply Theme & Global Background ———
THEMES = {
    "Dark":   {"bg":"#121212","fg":"#eee","inp":"#2c2c2c"},
    "Light":  {"bg":"#fafafa","fg":"#111","inp":"#fff"},
    "Green":  {"bg":"#e8f5e9","fg":"#1b5e20","inp":"#c8e6c9"},
    "Pink":   {"bg":"#fce4ec","fg":"#880e4f","inp":"#f8bbd0"},
    "Purple": {"bg":"#f3e5f5","fg":"#4a148c","inp":"#e1bee7"},
}
cfg = THEMES[st.session_state.theme]

# ——— Base CSS ———
st.markdown(f"""
<style>
  [data-testid="stAppViewContainer"] {{
    background-image:
      linear-gradient(rgba(255,255,255,0.6),rgba(255,255,255,0.6)),
      url("data:image/jpeg;base64,{sticky_b64}");
    background-size: cover;
    background-position: center;
    background-blend-mode: lighten;
  }}
  .stApp, label, .css-1n76uvr {{
    color: {cfg['fg']} !important;
  }}
  .stTextInput input,
  .stDateInput input,
  .stSelectbox div div input {{
    background-color: {cfg['inp']} !important;
    color:            {cfg['fg']} !important;
  }}
  .stButton > button {{
    background-color: #007ACC !important;
    color:            white   !important;
  }}
  h1, h2 {{
    color:           {cfg['fg']} !important;
    text-shadow:     2px 2px 4px rgba(0,0,0,0.9) !important;
  }}
  .task-title {{
    font-size:      1.4rem     !important;
    color:          {cfg['fg']} !important;
    font-weight:    600        !important;
    margin-bottom:  0.2rem     !important;
  }}
  .task-meta {{
    font-size:      1.0rem     !important;
    color:          {cfg['fg']} !important;
    opacity:        0.9        !important;
    margin-bottom:  0.5rem     !important;
  }}
  [data-testid="stSidebar"] {{
    background-color: {cfg['bg']} !important;
  }}
  [data-testid="stSidebar"] * {{
    color: {cfg['fg']} !important;
  }}
</style>
""", unsafe_allow_html=True)

# ——— Dark-mode CSS ———
if st.session_state.theme == "Dark":
    st.markdown(f"""
    <style>
      /* dark overlay on sticky notes */
      [data-testid="stAppViewContainer"] {{
        background-image:
          linear-gradient(rgba(0,0,0,0.5),rgba(0,0,0,0.5)),
          url("data:image/jpeg;base64,{sticky_b64}") !important;
        background-blend-mode: darken !important;
      }}

      /* headings */
      h1, h2, h3 {{
        color: #fff !important;
        background-color: rgba(255,255,255,0.15) !important;
        padding: 0.3rem 0.6rem !important;
        border-radius: 0.4rem !important;
      }}

      /* main panel sticky */
      .sticky-bg {{
        background-color: #333 !important;
        border: 1px solid #555 !important;
      }}

      /* text & password inputs */
      input[type="text"],
      input[type="password"] {{
        background-color: #2c2c2c !important;
        color:            #eee    !important;
        border:           1px solid #555 !important;
      }}

      /* selectboxes (Gender) */
      .stSelectbox > div > div > input {{
        background-color: #2c2c2c !important;
        color:            #eee    !important;
        border:           1px solid #555 !important;
      }}
      .stSelectbox svg {{
        fill: #eee !important;
      }}

      /* number input spinner (Age) */
      input[type="number"] {{
        background-color: #2c2c2c !important;
        color:            #eee    !important;
        border:           1px solid #555 !important;
      }}
      button[aria-label="increment"],
      button[aria-label="decrement"] {{
        background-color: #2c2c2c !important;
        color:            #eee    !important;
        border:           1px solid #555 !important;
      }}

      /* eye-toggle on password */
      .stTextInput button {{
        background-color: #2c2c2c !important;
        color:            #eee    !important;
        border:           1px solid #555 !important;
      }}

      /* file uploader (Profile picture) */
      [data-testid="stFileUploader"] > section,
      [data-testid="stFileUploader"] > section > div {{
        background-color: #2c2c2c !important;
        border:           1px solid #555 !important;
        border-radius:    0.5rem !important;
      }}
      [data-testid="stFileUploader"] label,
      [data-testid="stFileUploader"] span {{
        color: #eee !important;
      }}
      [data-testid="stFileUploader"] button {{
        background-color: #444 !important;
        color:            #eee !important;
        border:           1px solid #555 !important;
      }}
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
<style>
/* 1) Make the SELECTBOX placeholder (e.g. "Prefer not to say") black */
.stSelectbox div div input::placeholder {
  color: #000 !important;
  opacity: 1 !important;
}
/* 2) Make the NUMBER-INPUT value and spinner buttons black */
input[type="number"] {
  color: #000 !important;
}
button[aria-label="increment"],
button[aria-label="decrement"] {
  color: #000 !important;
}
/* 3) Make the password-TOGGLE EYE button black */
.stTextInput > div > button {
  color: #000 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Make all selectboxes have black background + white text */
.stSelectbox > div > div {
  background-color: #000 !important;
  color:            #fff !important;
}
/* Placeholder (“Prefer not to say”) in selectboxes */
.stSelectbox > div > div input::placeholder {
  color: #888 !important;
  opacity: 1 !important;
}
/* Make the dropdown arrow icon white */
.stSelectbox svg {
  fill: #fff !important;
}
/* Also fix the date‐picker boxes to match */
.stDateInput > div > div > input {
  background-color: #000 !important;
  color:            #fff !important;
}
</style>
""", unsafe_allow_html=True)



# ——— Sticky-notes panel behind task list ———
st.markdown(f"""
<style>
  .sticky-bg {{
    background-color: {cfg['inp']} !important;
    padding: 1.5rem !important;
    border-radius: 0.75rem !important;
    margin-bottom: 2rem !important;
    border: 1px solid {cfg['fg']} !important;
  }}
  .sticky-bg * {{
    color: #333 !important;
    text-shadow: 0 1px 2px rgba(255,255,255,0.8);
  }}
  .stExpander {{
    background-color: {cfg['inp']} !important;
    border: 1px solid {cfg['fg']} !important;
    border-radius: 0.5rem !important;
    padding: 1rem !important;
    margin-bottom: 1rem !important;
  }}
</style>
<div class="sticky-bg">
""", unsafe_allow_html=True)

# ——— Main: Add a New Task ———
st.title("📝 Todo List")
st.markdown("### ➕ Add a New Task")

voice_txt = ""
if VOICE:
    voice_txt = speech_to_text(
        language="en",
        start_prompt="🎙️ Speak",
        stop_prompt="⏹️ Stop",
        just_once=True,
        key="mic"
    ) or ""
    if voice_txt:
        st.success("Recognized: " + voice_txt)

txt  = st.text_input("Task", value=voice_txt or "")
prio = st.selectbox("Priority", ["High","Medium","Low"])
due  = st.date_input("Due Date", date.today())
stt  = st.time_input("Start Time", value=time(9,0))
ent  = st.time_input("End Time",   value=time(18,0))

if st.button("Add Task"):
    if txt.strip():
        add_task(txt.strip(), prio, due.isoformat(),
                 stt.strftime("%H:%M"), ent.strftime("%H:%M"))
        st.success("✅ Task added!")
        st.rerun()
    else:
        st.warning("⚠️ Task cannot be empty")

# ─── Fetch, sort & reorder according to sidebar ───
rows = st.session_state.get("sidebar_rows", fetch_tasks())
order = {"High":0,"Medium":1,"Low":2}
rows = sorted(rows, key=lambda r:(order[r[2]], r[6]))
if st.session_state.sidebar_filter == "Priority Only":
    rows = [r for r in rows if r[2]=="High"]
elif st.session_state.sidebar_filter == "Non-Priority Only":
    rows = [r for r in rows if r[2]!="High"]

# ——— Drag-and-drop reorder ———
# Build a list of "id: task text" labels
items = [f"{r[0]}: {r[1]}" for r in rows]

# Render the draggable list (each bar now shows the task text)
new_order = sort_items(
    items,                    # <- pass labels positionally
    key="task_sorter",
    direction="vertical",
    header=None,
    multi_containers=False
)

# Re‐assemble `rows` in the new order
ordered_rows = []
for label in new_order:
    id_str, _ = label.split(":", 1)
    for r in rows:
        if str(r[0]) == id_str:
            ordered_rows.append(r)
            break

rows = ordered_rows

# ——— Display tasks with update block ———
if not rows:
    st.info("No tasks to show.")
else:
    for tid, task, pr, dd, stt_val, ent_val, done in rows:
        c1, c2 = st.columns([6,1])

        with c1:
            st.markdown(f'<div class="task-title">{task}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="task-meta">📅 {dd}   ⏰ {stt_val}–{ent_val}   ⭐ {pr}</div>',
                unsafe_allow_html=True
            )

            # ⭐— done‐checkbox + star logic (NOT inside any expander) —⭐
            prev_done = bool(done)
            done_val  = st.checkbox("✅ Done", value=prev_done, key=f"done_{tid}")

            if done_val != prev_done:
                if done_val:
                    add_star(1)
                    st.success("⭐ You earned a star!")
                update_task(tid, task, pr, dd, stt_val, ent_val, done_val)
            else:
                update_task(tid, task, pr, dd, stt_val, ent_val, done_val)

            # ——— ONLY ONE expander per task ———
            with st.expander("Edit Task"):
                new_txt = st.text_input("Task", value=task, key=f"edit_txt_{tid}")
                new_pr  = st.selectbox(
                    "Priority", ["High","Medium","Low"],
                    index=["High","Medium","Low"].index(pr),
                    key=f"edit_prio_{tid}"
                )
                new_dd  = st.date_input(
                    "Due Date", datetime.fromisoformat(dd).date(),
                    key=f"edit_dd_{tid}"
                )
                new_st  = st.time_input(
                    "Start Time", datetime.strptime(stt_val, "%H:%M").time(),
                    key=f"edit_stt_{tid}"
                )
                new_en  = st.time_input(
                    "End Time", datetime.strptime(ent_val, "%H:%M").time(),
                    key=f"edit_ent_{tid}"
                )
                if st.button("Save", key=f"save_{tid}"):
                    update_task(
                        tid,
                        new_txt.strip(),
                        new_pr,
                        new_dd.isoformat(),
                        new_st.strftime("%H:%M"),
                        new_en.strftime("%H:%M"),
                        done_val
                    )
                    st.success("✅ Task updated!")
                    st.rerun()

        with c2:
            if st.button("🗑️", key=f"del_{tid}"):
                delete_task(tid)
                st.rerun()

    # Clear completed sits outside the for-loop
    if st.button("🧹 Clear Completed"):
        clear_done()
        st.rerun()

# ——— FullCalendar (00:00–23:00) ———
st.markdown("---")
st.subheader("📆 Calendar View")
if st.button("🔁 Refresh Calendar"):
    st.rerun()

events, seen = [], set()
for tid, task, pr, dd, stt, ent, done in rows:
    key = (tid, stt, ent)
    if key in seen: continue
    seen.add(key)
    events.append({
        "id":    str(tid),
        "title": f"{task} ({pr})",
        "start": f"{dd}T{stt}",
        "end":   f"{dd}T{ent}",
        "allDay": False
    })

st.markdown("""
<style>
  .fc, .fc-theme-standard { max-width:100%!important; margin:auto; }
  .fc-timegrid-slot-label { height:24px!important; }
</style>
""", unsafe_allow_html=True)

calendar_options = {
    "initialView":   "timeGridWeek",
    "editable":      False,
    "selectable":    False,
    "height":        300,
    "slotMinTime":   "00:00:00",
    "slotMaxTime":   "23:00:00",
    "eventOverlap":  False,
    "eventDisplay":  "block",
    "eventColor":    "#a66bbe",
    "headerToolbar": {
        "left":   "prev,next today",
        "center": "title",
        "right":  "timeGridWeek,timeGridDay"
    }
}
calendar(events=events, options=calendar_options)

# ——— SUMMARY VISUALS ———
st.markdown("---")
st.subheader("📈 Summary Visuals")

df_sum = pd.DataFrame(rows, columns=[
    "id","task","priority","due_date","start_time","end_time","done"
])
df_sum["Status"] = df_sum["done"].map({0:"Not Completed",1:"Completed"})

c1, c2, c3 = st.columns(3)

with c1:
    pie = px.pie(
        df_sum,
        names="Status",
        hole=0.4,
        title="Completed vs Not Completed",
        color="Status",
        color_discrete_map={
            "Completed":    "blue",
            "Not Completed":"red"
        }
    )
    st.plotly_chart(pie, use_container_width=True)

with c2:
    by_date = df_sum.groupby("due_date").size().reset_index(name="count")
    bar_date = px.bar(
        by_date,
        x="due_date",
        y="count",
        title="Tasks by Due Date",
        labels={"due_date":"Due Date","count":"# Tasks"}
    )
    st.plotly_chart(bar_date, use_container_width=True)

with c3:
    by_pr = df_sum.groupby("priority").size().reset_index(name="count")
    bar_pr = px.bar(
        by_pr,
        x="priority",
        y="count",
        color="priority",
        color_discrete_map={
            "High":   "red",
            "Medium": "orange",
            "Low":    "yellow"
        },
        title="Tasks by Priority",
        labels={"priority":"Priority","# Tasks":"count"}
    )
    st.plotly_chart(bar_pr, use_container_width=True)

    