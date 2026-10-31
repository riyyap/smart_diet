import streamlit as st
import sqlite3
import hashlib
import secrets
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, datetime
import random

# ---------------- CONFIGURATION ----------------

st.set_page_config(
    page_title="NutriGlow Smart Diet Planner",
    page_icon="🥗",
    layout="wide"
)

DB = "nutriglow_student.db"

# ---------------- DATABASE ----------------

def get_connection():
    return sqlite3.connect(DB, timeout=10)

def setup_database():
    with get_connection() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                uid INTEGER PRIMARY KEY,
                name TEXT DEFAULT '',
                age INTEGER DEFAULT 21,
                height REAL DEFAULT 165,
                weight REAL DEFAULT 60,
                target REAL DEFAULT 55,
                diet TEXT DEFAULT 'Vegetarian'
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                day TEXT NOT NULL,
                weight REAL,
                water INTEGER DEFAULT 0,
                exercise INTEGER DEFAULT 0
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS groceries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                item TEXT NOT NULL
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                rating INTEGER,
                message TEXT,
                day TEXT
            )
        """)

setup_database()

# ---------------- ACCOUNT FUNCTIONS ----------------

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        150000
    ).hex()

def create_account(username, password):
    username = username.strip()

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    salt = secrets.token_bytes(16).hex()
    hashed = password_hash(password, salt)

    try:
        with get_connection() as con:
            cur = con.execute(
                "INSERT INTO users(username,salt,password_hash) VALUES(?,?,?)",
                (username, salt, hashed)
            )

            con.execute(
                "INSERT INTO profiles(uid) VALUES(?)",
                (cur.lastrowid,)
            )

        return True, "Account created successfully! Please log in."

    except sqlite3.IntegrityError:
        return False, "This username already exists."

def login_user(username, password):
    with get_connection() as con:
        row = con.execute(
            "SELECT id,username,salt,password_hash FROM users "
            "WHERE lower(username)=lower(?)",
            (username.strip(),)
        ).fetchone()

    if row is None:
        return None

    try:
        entered_hash = password_hash(password, row[2])

        if secrets.compare_digest(entered_hash, row[3]):
            return {"id": row[0], "username": row[1]}

    except (ValueError, TypeError):
        return None

    return None

def load_profile(uid):
    with get_connection() as con:
        row = con.execute(
            "SELECT name,age,height,weight,target,diet "
            "FROM profiles WHERE uid=?",
            (uid,)
        ).fetchone()

    if row is None:
        return {
            "name": "",
            "age": 21,
            "height": 165.0,
            "weight": 60.0,
            "target": 55.0,
            "diet": "Vegetarian"
        }

    return dict(zip(
        ["name", "age", "height", "weight", "target", "diet"],
        row
    ))

def save_profile(uid, name, age, height, weight, target, diet):
    with get_connection() as con:
        con.execute("""
            INSERT OR REPLACE INTO profiles
            (uid,name,age,height,weight,target,diet)
            VALUES(?,?,?,?,?,?,?)
        """, (uid, name, age, height, weight, target, diet))

def add_progress(uid, weight, water, exercise):
    with get_connection() as con:
        con.execute("""
            INSERT INTO progress(uid,day,weight,water,exercise)
            VALUES(?,?,?,?,?)
        """, (
            uid,
            datetime.now().isoformat(timespec="seconds"),
            weight,
            water,
            exercise
        ))

# ---------------- MEAL DATA ----------------

VEG_MEALS = {
    "Breakfast": [
        "🥣 Oats with banana",
        "🥞 Besan chilla",
        "🍚 Vegetable poha",
        "🥗 Idli with sambar",
        "🥪 Paneer sandwich"
    ],
    "Lunch": [
        "🍛 Dal, roti and vegetables",
        "🥗 Rajma rice",
        "🫓 Chole with roti",
        "🥘 Vegetable pulao with curd",
        "🧀 Paneer vegetable bowl"
    ],
    "Snack": [
        "🍎 Apple and nuts",
        "🥜 Roasted chana",
        "🍓 Fruit and yogurt",
        "🌰 Roasted makhana"
    ],
    "Dinner": [
        "🍲 Vegetable khichdi",
        "🧀 Paneer bhurji with roti",
        "🥗 Dal and vegetables",
        "🥘 Vegetable soup with toast"
    ]
}

NONVEG_MEALS = {
    "Breakfast": [
        "🍳 Egg omelette with toast",
        "🥚 Boiled eggs and fruit",
        "🥣 Oats with banana",
        "🥪 Egg sandwich"
    ],
    "Lunch": [
        "🍗 Chicken curry with rice",
        "🥚 Egg curry with roti",
        "🐟 Fish curry with rice",
        "🍗 Chicken vegetable bowl"
    ],
    "Snack": [
        "🍎 Fruit and yogurt",
        "🥚 Boiled egg and fruit",
        "🥜 Roasted chana",
        "🍌 Banana and nuts"
    ],
    "Dinner": [
        "🍗 Chicken with vegetables",
        "🐟 Fish with roti",
        "🥚 Egg bhurji with roti",
        "🍲 Chicken soup with toast"
    ]
}

VEG_WEEK = {
    "Monday": ["Oats with banana", "Dal and roti", "Apple and nuts", "Vegetable khichdi"],
    "Tuesday": ["Besan chilla", "Rajma rice", "Roasted chana", "Paneer bhurji"],
    "Wednesday": ["Vegetable poha", "Chole and roti", "Fruit and yogurt", "Dal and vegetables"],
    "Thursday": ["Idli and sambar", "Vegetable pulao", "Roasted makhana", "Paneer curry"],
    "Friday": ["Oats with fruit", "Dal and rice", "Apple and nuts", "Vegetable soup and toast"],
    "Saturday": ["Paneer sandwich", "Chole and roti", "Seasonal fruit", "Vegetable khichdi"],
    "Sunday": ["Dosa and sambar", "Vegetable biryani", "Fruit bowl", "Paneer and roti"]
}

NONVEG_WEEK = {
    "Monday": ["Eggs and toast", "Chicken curry and rice", "Fruit and nuts", "Fish and vegetables"],
    "Tuesday": ["Vegetable omelette", "Chicken rice bowl", "Yogurt and fruit", "Egg curry and roti"],
    "Wednesday": ["Boiled eggs and fruit", "Fish curry and rice", "Roasted chana", "Chicken soup"],
    "Thursday": ["Egg sandwich", "Chicken pulao", "Banana and yogurt", "Fish with vegetables"],
    "Friday": ["Omelette and toast", "Egg curry and rice", "Seasonal fruit", "Chicken and vegetables"],
    "Saturday": ["Boiled eggs", "Chicken rice bowl", "Fruit and nuts", "Egg bhurji and roti"],
    "Sunday": ["Eggs and toast", "Chicken biryani", "Fruit yogurt", "Grilled fish and vegetables"]
}

FESTIVALS = {
    "Navratri": ["Fruit and yogurt", "Sabudana khichdi", "Kuttu roti with curd"],
    "Diwali": ["Vegetable poha", "Dal and roti", "Fruit and nuts"],
    "Holi": ["Oats with fruit", "Vegetable pulao", "Fresh fruit bowl"],
    "Uttarayan": ["Besan chilla", "Dal and roti", "Roasted chana"],
    "Eid": ["Eggs or besan chilla", "Balanced rice meal", "Fruit and yogurt"]
}

RECIPES = {
    "Fruit Yogurt Bowl": {
        "ingredients": ["Plain yogurt", "Banana", "Apple", "Seasonal fruit"],
        "steps": [
            "Wash and cut the fruit.",
            "Add yogurt to a bowl.",
            "Mix the fruit with the yogurt.",
            "Serve fresh."
        ]
    },
    "Vegetable Poha": {
        "ingredients": ["Poha", "Onion", "Peas", "Lemon", "Spices"],
        "steps": [
            "Rinse the poha gently.",
            "Cook onion and peas.",
            "Add spices and poha.",
            "Cook until ready and add lemon."
        ]
    },
    "Paneer Vegetable Bowl": {
        "ingredients": ["Paneer", "Capsicum", "Carrot", "Onion", "Spices"],
        "steps": [
            "Wash and chop the vegetables.",
            "Cook the vegetables with spices.",
            "Add paneer.",
            "Cook thoroughly and serve."
        ]
    },
    "Egg Omelette": {
        "ingredients": ["Eggs", "Onion", "Tomato", "Pepper"],
        "steps": [
            "Beat the eggs.",
            "Add chopped vegetables.",
            "Cook in a pan until fully set."
        ]
    },
    "Chicken Bowl": {
        "ingredients": ["Chicken", "Rice", "Vegetables", "Spices"],
        "steps": [
            "Season the chicken.",
            "Cook chicken thoroughly.",
            "Prepare rice and vegetables.",
            "Serve together."
        ]
    }
}

# ---------------- DESIGN ----------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: Poppins, sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #FAF8EF, #E8F3E2, #FFF0E4);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #DCEFD4, #FFF0E4);
}

h1, h2, h3 {
    color: #285C45;
}

div[data-testid="stMetric"] {
    background: white;
    padding: 15px;
    border-radius: 16px;
    border: 1px solid #DCE8D4;
    box-shadow: 0 4px 12px #607D6015;
}

.stButton > button, .stDownloadButton > button {
    background: linear-gradient(120deg, #B8D8A9, #F5C5A5);
    color: #234A36;
    border-radius: 12px;
    font-weight: 600;
}

.food-card {
    background: linear-gradient(145deg, #FFFFFF, #FFF3E7);
    border: 1px solid #E3E8DA;
    border-radius: 16px;
    padding: 18px;
    margin: 8px 0;
    box-shadow: 0 5px 12px #607D6010;
}

.hero {
    background: linear-gradient(120deg, #DCEFD4, #FFEBDD);
    border-radius: 22px;
    padding: 22px;
}
</style>
""", unsafe_allow_html=True)

def show_card(title, content):
    st.markdown(
        f'<div class="food-card"><h3>{title}</h3><p>{content}</p></div>',
        unsafe_allow_html=True
    )

def show_basket():
    try:
        st.image("healthy_food_basket.jpg", use_container_width=True)
    except Exception:
        st.markdown(
            '<div class="food-card" style="text-align:center">'
            '<h1>🧺🥦🍎🥕🍊</h1><h3>Healthy Food Basket</h3></div>',
            unsafe_allow_html=True
        )

# ---------------- LOGIN PAGE ----------------

if "user" not in st.session_state:
    st.session_state["user"] = None

if st.session_state["user"] is None:
    left, right = st.columns(2)

    with left:
        st.markdown(
            '<div class="hero"><h1>🥗 NutriGlow</h1>'
            '<h3>Smart Diet Planner</h3>'
            '<p>Eat Smart. Glow Strong. ✨</p></div>',
            unsafe_allow_html=True
        )
        show_basket()
        st.info("🌱 Small healthy choices create beautiful habits.")

    with right:
        st.title("Welcome! 💚")
        mode = st.radio("Account option", ["Login", "Create Account"],
                        horizontal=True)

        if mode == "Create Account":
            with st.form("create_account_form"):
                new_username = st.text_input("Create username")
                new_password = st.text_input("Create password", type="password")
                confirm_password = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("🌿 Create Account")

            if submitted:
                if new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    ok, message = create_account(new_username, new_password)
                    if ok:
                        st.success(message)
                    else:
                        st.error(message)

        else:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("✨ Login")

            if submitted:
                account = login_user(username, password)
                if account:
                    st.session_state["user"] = account
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")

    st.stop()

# ---------------- USER SESSION ----------------

user = st.session_state["user"]
uid = user["id"]
profile = load_profile(uid)

with st.sidebar:
    st.title("🥗 NutriGlow")
    st.write("Hello, " + (profile["name"] or user["username"]) + "!")

    page = st.radio("Choose a page", [
        "🏡 Dashboard",
        "👤 My Profile",
        "🥗 Daily Meal Planner",
        "📅 Weekly Meal Planner",
        "💧 Water Tracker",
        "🏃 Exercise Suggestions",
        "🎉 Festival Diet",
        "👩‍🍳 Recipes",
        "🛒 Grocery List",
        "📈 Progress & Graphs",
        "⭐ Feedback"
    ])

    if st.button("🚪 Logout"):
        st.session_state["user"] = None
        st.rerun()

# ---------------- DASHBOARD ----------------

if page == "🏡 Dashboard":
    st.markdown(
        '<div class="hero"><h1>Welcome to NutriGlow! 🌿</h1>'
        '<h3>Your personal wellness companion</h3>'
        '<p>Good Food • Good Mood • Better You 💚</p></div>',
        unsafe_allow_html=True
    )

    show_basket()

    c1, c2, c3 = st.columns(3)
    c1.metric("⚖️ Current weight", f"{profile['weight']:.1f} kg")
    c2.metric("🎯 Target weight", f"{profile['target']:.1f} kg")

    with get_connection() as con:
        water = con.execute(
            "SELECT COALESCE(SUM(water),0) FROM progress "
            "WHERE uid=? AND substr(day,1,10)=?",
            (uid, date.today().isoformat())
        ).fetchone()[0]

    c3.metric("💧 Water logged today", f"{water} ml")

    st.subheader("🍽 Meal inspiration")
    diet_data = VEG_MEALS if profile["diet"] == "Vegetarian" else NONVEG_MEALS

    for meal, choices in diet_data.items():
        show_card(meal, random.choice(choices))

    st.success("✨ Your health journey begins with one small step!")

# ---------------- PROFILE ----------------

elif page == "👤 My Profile":
    st.title("👤 My Health Profile")

    with st.form("profile_form"):
        name = st.text_input("Your name", value=profile["name"])
        age = st.number_input("Age", min_value=13, max_value=100,
                              value=int(profile["age"]), step=1)
        height = st.number_input("Height (cm)", min_value=100.0,
                                 max_value=230.0, value=float(profile["height"]),
                                 step=0.5, format="%.1f")
        weight = st.number_input("Current weight (kg)", min_value=25.0,
                                 max_value=300.0, value=float(profile["weight"]),
                                 step=0.5, format="%.1f")
        target = st.number_input("Target weight (kg)", min_value=25.0,
                                 max_value=300.0, value=float(profile["target"]),
                                 step=0.5, format="%.1f")

        diet_options = ["Vegetarian", "Non-Vegetarian"]
        diet_index = 0 if profile["diet"] == "Vegetarian" else 1

        diet = st.selectbox("Food preference", diet_options, index=diet_index)

        submitted = st.form_submit_button("💚 Save Profile")

    if submitted:
        save_profile(uid, name, int(age), float(height),
                     float(weight), float(target), diet)

        st.success("Profile saved successfully!")
        st.rerun()

    bmi = profile["weight"] / ((profile["height"] / 100) ** 2)
    st.metric("BMI estimate", f"{bmi:.1f}")
    st.caption("BMI is a rough screening measure, not a medical diagnosis.")

# ---------------- DAILY MEAL PLANNER ----------------

elif page == "🥗 Daily Meal Planner":
    st.title("🥗 Daily Meal Planner")

    diet = st.radio("Choose diet", ["Vegetarian", "Non-Vegetarian"],
                    index=0 if profile["diet"] == "Vegetarian" else 1,
                    horizontal=True)

    meals = VEG_MEALS if diet == "Vegetarian" else NONVEG_MEALS

    if st.button("🔄 Generate Meal Plan"):
        st.session_state["daily_meals"] = {
            meal: random.choice(options) for meal, options in meals.items()
        }

    if "daily_meals" not in st.session_state:
        st.session_state["daily_meals"] = {
            meal: random.choice(options) for meal, options in meals.items()
        }

    for meal, food in st.session_state["daily_meals"].items():
        show_card(meal, food)

    if st.button("🛒 Add meals to grocery list"):
        with get_connection() as con:
            for food in st.session_state["daily_meals"].values():
                con.execute("INSERT INTO groceries(uid,item) VALUES(?,?)",
                            (uid, food))
        st.success("Meal ideas added to grocery list!")

# ---------------- WEEKLY MEAL PLANNER ----------------

elif page == "📅 Weekly Meal Planner":
    st.title("📅 Your 7-Day Meal Planner")

    diet = st.radio("Choose meal preference",
                    ["Vegetarian", "Non-Vegetarian"],
                    index=0 if profile["diet"] == "Vegetarian" else 1,
                    horizontal=True)

    weekly = VEG_WEEK if diet == "Vegetarian" else NONVEG_WEEK

    rows = []
    for day_name, foods in weekly.items():
        with st.expander("📆 " + day_name):
            for label, food in zip(
                ["🌅 Breakfast", "☀️ Lunch", "🍓 Snack", "🌙 Dinner"], foods
            ):
                st.write(f"**{label}:** {food}")
                rows.append({
                    "Day": day_name,
                    "Diet": diet,
                    "Meal": label,
                    "Food": food
                })

    st.download_button(
        "📥 Download Weekly Meal Plan",
        pd.DataFrame(rows).to_csv(index=False),
        "Weekly_Meal_Plan.csv",
        "text/csv"
    )

# ---------------- WATER TRACKER ----------------

elif page == "💧 Water Tracker":
    st.title("💧 Hydration Station")

    goal = st.slider("Example daily water goal (ml)", 1000, 4000, 2500, 250)

    with get_connection() as con:
        total = con.execute(
            "SELECT COALESCE(SUM(water),0) FROM progress "
            "WHERE uid=? AND substr(day,1,10)=?",
            (uid, date.today().isoformat())
        ).fetchone()[0]

    st.metric("💧 Water logged today", f"{total} ml")
    st.progress(min(float(total) / goal, 1.0))

    st.caption("Choose a button to record water consumed.")

    for amount in [150, 250, 500]:
        if st.button(f"💧 Add {amount} ml", key=f"water_{amount}"):
            add_progress(uid, profile["weight"], amount, 0)
            st.rerun()

    st.info("This version records water when you click. Automatic background reminders require additional setup.")

# ---------------- EXERCISE ----------------

elif page == "🏃 Exercise Suggestions":
    st.title("🏃 Exercise Studio")

    level = st.selectbox("Choose your comfort level", [
        "Beginner", "General Fitness", "Low Impact", "Strength"
    ])

    exercises = {
        "Beginner": "🚶 Comfortable walking and gentle stretching",
        "General Fitness": "🚴 Walking, cycling, dancing and suitable strength exercises",
        "Low Impact": "🧘 Gentle yoga, easy walking or chair exercises",
        "Strength": "💪 Appropriate resistance exercises with good technique and rest"
    }

    show_card("✨ Recommended activity", exercises[level])

    with st.form("exercise_form"):
        activity = st.selectbox("Activity completed", [
            "Walking", "Cycling", "Yoga", "Dancing", "Strength training"
        ])
        minutes = st.number_input("Minutes completed", 0, 300, 20)
        submitted = st.form_submit_button("💪 Save Exercise")

    if submitted:
        add_progress(uid, profile["weight"], 0, int(minutes))
        st.success(f"Saved {minutes} minutes of {activity}!")

# ---------------- FESTIVAL DIET ----------------

elif page == "🎉 Festival Diet":
    st.title("🎉 Festival Special Meals")
    festival = st.selectbox("Choose festival", list(FESTIVALS.keys()))

    show_basket()

    for number, meal in enumerate(FESTIVALS[festival], 1):
        show_card(f"🌿 Meal Idea {number}", meal)

    st.caption("Adapt meals to your dietary needs and fasting practices.")

# ---------------- RECIPES ----------------

elif page == "👩‍🍳 Recipes":
    st.title("👩‍🍳 Recipe Corner")

    recipe_names = list(RECIPES.keys())

    if profile["diet"] == "Vegetarian":
        recipe_names = [
            item for item in recipe_names
            if item not in ["Egg Omelette", "Chicken Bowl"]
        ]

    recipe = st.selectbox("Choose a recipe", recipe_names)
    details = RECIPES[recipe]

    show_card("🧺 Ingredients", ", ".join(details["ingredients"]))

    st.subheader("👩‍🍳 Cooking steps")
    for i, step in enumerate(details["steps"], 1):
        st.write(f"**Step {i}:** {step}")

    if st.button("🛒 Add ingredients to grocery list"):
        with get_connection() as con:
            for item in details["ingredients"]:
                con.execute("INSERT INTO groceries(uid,item) VALUES(?,?)",
                            (uid, item))
        st.success("Ingredients added!")

# ---------------- GROCERY LIST ----------------

elif page == "🛒 Grocery List":
    st.title("🛒 Smart Grocery Basket")
    st.write("View your ingredients without checkboxes. 🥦")

    with st.form("add_grocery_form"):
        item = st.text_input("Add grocery item")
        submitted = st.form_submit_button("➕ Add Item")

    if submitted:
        if item.strip():
            with get_connection() as con:
                con.execute("INSERT INTO groceries(uid,item) VALUES(?,?)",
                            (uid, item.strip()))
            st.success("Item added!")
            st.rerun()
        else:
            st.warning("Please enter an item.")

    with get_connection() as con:
        items = con.execute(
            "SELECT id,item FROM groceries WHERE uid=? ORDER BY id DESC",
            (uid,)
        ).fetchall()

    if items:
        for number, (_, item_name) in enumerate(items, 1):
            st.write(f"{number}. 🥕 {item_name}")

        st.download_button(
            "📥 Download Grocery List",
            pd.DataFrame([{"Item": item} for _, item in items]).to_csv(index=False),
            "Grocery_List.csv",
            "text/csv"
        )

        selected_id = st.selectbox(
            "Select item to remove",
            [row[0] for row in items],
            format_func=lambda item_id: next(
                row[1] for row in items if row[0] == item_id
            )
        )

        if st.button("🗑️ Remove Selected Item"):
            with get_connection() as con:
                con.execute("DELETE FROM groceries WHERE id=? AND uid=?",
                            (selected_id, uid))
            st.rerun()
    else:
        st.info("Your grocery list is empty.")

# ---------------- PROGRESS AND GRAPHS ----------------

elif page == "📈 Progress & Graphs":
    st.title("📈 Your Wellness Analysis")

    with st.form("progress_form"):
        weight = st.number_input(
            "Current weight (kg)",
            min_value=25.0,
            max_value=300.0,
            value=float(profile["weight"]),
            step=0.5,
            format="%.1f"
        )

        water = st.number_input("Water consumed today (ml)", 0, 10000, 0)
        exercise = st.number_input("Exercise minutes", 0, 300, 0)

        submitted = st.form_submit_button("💚 Save Progress")

    if submitted:
        add_progress(uid, float(weight), int(water), int(exercise))

        save_profile(
            uid, profile["name"], profile["age"], profile["height"],
            float(weight), profile["target"], profile["diet"]
        )

        st.success("Progress saved successfully!")
        st.rerun()

    with get_connection() as con:
        df = pd.read_sql_query(
            "SELECT day,weight,water,exercise FROM progress "
            "WHERE uid=? ORDER BY day",
            con,
            params=(uid,)
        )

    if not df.empty:
        df["day"] = pd.to_datetime(df["day"], errors="coerce")

        st.subheader("⚖️ Weight Analysis")
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(df["day"], df["weight"], marker="o", label="Weight")
        ax.axhline(profile["target"], linestyle="--", label="Target")
        ax.set_ylabel("Weight (kg)")
        ax.legend()
        ax.grid(alpha=0.25)
        fig.autofmt_xdate()
        st.pyplot(fig)
        plt.close(fig)

        left, right = st.columns(2)

        with left:
            st.subheader("💧 Water Intake")
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(df["day"].dt.strftime("%d %b"), df["water"])
            ax.set_ylabel("Water (ml)")
            ax.tick_params(axis="x", rotation=35)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        with right:
            st.subheader("🏃 Exercise")
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(df["day"].dt.strftime("%d %b"), df["exercise"])
            ax.set_ylabel("Minutes")
            ax.tick_params(axis="x", rotation=35)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

        st.dataframe(df, use_container_width=True)

        st.download_button(
            "📥 Download Progress",
            df.to_csv(index=False),
            "NutriGlow_Progress.csv",
            "text/csv"
        )
    else:
        st.info("Save your first progress entry to see graphs.")

# ---------------- FEEDBACK ----------------

elif page == "⭐ Feedback":
    st.title("⭐ We Value Your Feedback!")

    with st.form("feedback_form"):
        rating = st.slider("Rate your experience", 1, 5, 5)
        message = st.text_area("What should we improve?")
        submitted = st.form_submit_button("💌 Submit Feedback")

    if submitted:
        with get_connection() as con:
            con.execute(
                "INSERT INTO feedback(uid,rating,message,day) VALUES(?,?,?,?)",
                (uid, int(rating), message.strip(), date.today().isoformat())
            )
        st.success("Thank you for your feedback! 💚")

    with get_connection() as con:
        feedback_rows = con.execute(
            "SELECT rating,message,day FROM feedback WHERE uid=? ORDER BY id DESC",
            (uid,)
        ).fetchall()

    for rating, message, day in feedback_rows:
        show_card("⭐" * rating, message or "Thank you for your rating!")
        st.caption(day)

# ---------------- FOOTER ----------------

st.divider()

st.markdown(
    '<div style="text-align:center">'
    '<h3>🥗 NutriGlow Smart Diet Planner</h3>'
    '<p>Eat Smart • Stay Active • Glow Naturally 💚</p>'
    '<small>Educational student project. Not a substitute for professional medical advice.</small>'
    '</div>',
    unsafe_allow_html=True
)